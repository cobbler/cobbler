#
# Setup Makefile to match your environment
#
PYTHON=/usr/bin/python3

# check for executables

PYFLAKES = $(shell { command -v pyflakes-3 || command -v pyflakes3 || command -v pyflakes; }  2> /dev/null)
PYCODESTYLE := $(shell { command -v pycodestyle-3 || command -v pycodestyle3 || command -v pycodestyle; } 2> /dev/null)
HTTPD = $(shell which httpd)
APACHE2 = $(shell which apache2)

# Debian / Ubuntu have /bin/sh -> dash
SHELL = /bin/bash

TOP_DIR:=$(shell pwd)
DESTDIR=/

prefix=devinstall
statepath=/tmp/cobbler_settings/$(prefix)

# Taken from: https://marmelab.com/blog/2016/02/29/auto-documented-makefile.html
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

all: clean build ## Executes the clean target and afterwards the build target.

clean: ## Cleans Python bytecode, build artifacts and the temp files.
	@echo "cleaning: python bytecode"
	@rm -f *.pyc
	@rm -f cobbler/*.pyc
	@rm -f cobbler/modules/*.pyc
	@rm -f cobbler/web/*.pyc
	@rm -f cobbler/web/templatetags/*.pyc
	@echo "cleaning: build artifacts"
	@rm -rf build release dist cobbler.egg-info
	@rm -rf rpm-build/*
	@rm -rf deb-build/*
	@rm -f MANIFEST AUTHORS
	@rm -f config/version
	@rm -f docs/*.1.gz
	@echo "cleaning: temp files"
	@rm -f *~
	@rm -rf buildiso
	@rm -f *.tmp
	@rm -f *.log

cleandoc: ## Cleans the docs directory.
	@echo "cleaning: documentation"
	@cd docs; make clean > /dev/null 2>&1

doc: ## Creates the documentation with sphinx in html form.
	@echo "creating: documentation"
	@cd docs; make html > /dev/null 2>&1

qa: ## If pyflakes and/or pycodestyle is found then they are run.
ifeq ($(strip $(PYFLAKES)),)
	@echo "No pyflakes found"
else
	@echo "checking: pyflakes ${PYFLAKES}"
	@${PYFLAKES} \
		*.py \
		cobbler/*.py \
		cobbler/modules/*.py \
		cobbler/web/*.py cobbler/web/templatetags/*.py \
		bin/cobbler* bin/*.py web/cobbler.wsgi
endif

ifeq ($(strip $(PYCODESTYLE)),)
	@echo "No pycodestyle found"
else
	@echo "checking: pycodestyle"
	@${PYCODESTYLE} -r --ignore E501,E402,E722,W504 \
			*.py \
		cobbler/*.py \
		cobbler/modules/*.py \
		cobbler/web/*.py cobbler/web/templatetags/*.py \
		bin/cobbler* bin/*.py web/cobbler.wsgi
endif

authors: ## Creates the AUTHORS file.
	@echo "creating: AUTHORS"
	@cp AUTHORS.in AUTHORS
	@git log --format='%aN <%aE>' | grep -v 'root' | sort -u >> AUTHORS

sdist: authors ## Creates the sdist for release preparation.
	@echo "creating: sdist"
	@source distro_build_configs.sh; \
	${PYTHON} setup.py sdist bdist_wheel

release: clean qa authors sdist ## Creates the full release.
	@echo "creating: release artifacts"
	@mkdir release
	@cp dist/*.gz release/
	@cp distro_build_configs.sh release/
	@cp cobbler.spec release/

test-centos7: ## Executes the testscript for testing cobbler in a docker container on CentOS7.
	./tests/build-and-install-rpms.sh --with-tests el7 dockerfiles/CentOS7.dockerfile

test-centos8: ## Executes the testscript for testing cobbler in a docker container on CentOS8.
	./tests/build-and-install-rpms.sh --with-tests el8 dockerfiles/CentOS8.dockerfile

test-fedora31: ## Executes the testscript for testing cobbler in a docker container on Fedora 31.
	./tests/build-and-install-rpms.sh --with-tests f31 dockerfiles/Fedora31.dockerfile

test-debian10: ## Executes the testscript for testing cobbler in a docker container on Debian 10.
	./tests/build-and-install-debs.sh --with-tests deb10 dockerfiles/Debian10.dockerfile

build: ## Runs the Python Build.
	@source distro_build_configs.sh; \
	${PYTHON} setup.py build -f

install: build ## Runs the build target and then installs via setup.py
	# Debian/Ubuntu requires an additional parameter in setup.py
	@source distro_build_configs.sh; \
	${PYTHON} setup.py install --root $(DESTDIR) -f

devinstall: ## This deletes the /usr/share/cobbler directory and then runs the targets savestate, install and restorestate.
	-rm -rf $(DESTDIR)/usr/share/cobbler
	make savestate
	make install
	make restorestate

savestate: ## This runs the setup.py task savestate.
	@source distro_build_configs.sh; \
	${PYTHON} setup.py -v savestate --root $(DESTDIR); \


restorestate: ## This restores a state which was previously saved via the target savestate. (Also run via setup.py)
	# Check if we are on Red Hat, Suse or Debian based distribution
	@source distro_build_configs.sh; \
	${PYTHON} setup.py -v restorestate --root $(DESTDIR); \
	find $(DESTDIR)/var/lib/cobbler/triggers | xargs chmod +x
	if [ -n "`getent passwd apache`" ] ; then \
		chown -R apache $(DESTDIR)/var/www/cobbler; \
	elif [ -n "`getent passwd wwwrun`" ] ; then \
		chown -R wwwrun $(DESTDIR)/usr/share/cobbler/web; \
	elif [ -n "`getent passwd www-data`"] ; then \
		chown -R www-data $(DESTDIR)/usr/share/cobbler/web; \
	fi
	if [ -d $(DESTDIR)/var/www/cobbler ] ; then \
		chmod -R +x $(DESTDIR)/var/www/cobbler/svc; \
	fi
	if [ -d $(DESTDIR)/usr/share/cobbler/web ] ; then \
		chmod -R +x $(DESTDIR)/usr/share/cobbler/web; \
	fi
	if [ -d $(DESTDIR)/srv/www/cobbler/svc ]; then \
		chmod -R +x $(DESTDIR)/srv/www/cobbler/svc; \
	fi
	rm -rf $(statepath)

webtest: devinstall ## Runs the task devinstall and then runs the targets clean, devinstall and restartservices.
	make clean
	make devinstall
	make restartservices

restartservices: ## Restarts the Apache2 and Cobbler-Web via init.d, service or systemctl.
	$(shell systemctl restart cobblerd)
ifneq ($(strip $(HTTPD)),)
	systemctl restart httpd
else ifneq ($(strip $(APACHE2)),)
	systemctl restart apache2
else
	$(error "No apache2 or httpd in $(PATH), consider installing one of the two (depending on the distro)!")
endif

rpms: release ## Runs the target release and then creates via rpmbuild the rpms in a directory called rpm-build.
	mkdir -p rpm-build
	cp dist/*.gz rpm-build/
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define "_specdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_sourcedir  %{_topdir}" \
	-ba cobbler.spec

# Only build a binary package
debs: release ## Runs the target release and then creates via debbuild the debs in a directory called deb-build.
	mkdir -p deb-build
	mkdir -p deb-build/{BUILD,BUILDROOT,DEBS,SDEBS,SOURCES}
	cp dist/*.gz deb-build/
	debbuild --define "_topdir %(pwd)/deb-build" \
	--define "_builddir %{_topdir}" \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-vv -bb cobbler.spec

eraseconfig: ## Deletes the cobbler data jsons which are created when using the file provider.
	-rm /var/lib/cobbler/cobbler_collections/distros/*
	-rm /var/lib/cobbler/cobbler_collections/images/*
	-rm /var/lib/cobbler/cobbler_collections/profiles/*
	-rm /var/lib/cobbler/cobbler_collections/systems/*
	-rm /var/lib/cobbler/cobbler_collections/repos/*
	-rm /var/lib/cobbler/cobbler_collections/mgmtclasses/*
	-rm /var/lib/cobbler/cobbler_collections/files/*
	-rm /var/lib/cobbler/cobbler_collections/packages/*
