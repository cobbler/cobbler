MAKEFLAGS += --no-print-directory

#
# Setup Makefile to match your environment
#
PYTHON=/usr/bin/python3

# check for executables

BLACK = $(shell which black)
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
	@rm -rf cobbler/__pycache__
	@rm -rf cobbler/**/__pycache__
	@echo "cleaning: build artifacts"
	@rm -rf build release dist cobbler.egg-info
	@rm -rf rpm-build/*
	@rm -rf deb-build/*
	@rm -f MANIFEST AUTHORS
	@rm -f config/version
	@rm -f docs/*.1.gz
	@rm -rf docs/_build
	@echo "cleaning: temp files"
	@rm -f *~
	@rm -rf buildiso
	@rm -f *.tmp
	@rm -f *.log
	@rm -f supervisord.pid
	@rm -rf .pytest_cache

cleandoc: ## Cleans the docs directory.
	@echo "cleaning: documentation"
	@cd docs; make clean > /dev/null 2>&1

doc: ## Creates the documentation with sphinx in html form.
	@echo "creating: documentation"
	@cd docs; make html > /dev/null 2>&1

man: ## Creates documentation and man pages using Sphinx
	@${PYTHON} -m sphinx -b man -j auto ./docs ./build/sphinx/man

qa: ## If black is found then it is run.
ifeq ($(strip $(BLACK)),)
	@echo "No black found"
else
	@echo "checking: black ${BLACK}"
	@${BLACK} .
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

test-rocky9: ## Executes the testscript for testing cobbler in a docker container on Rocky Linux 9.
	./docker/rpms/build-and-install-rpms.sh rl8 docker/rpms/Rocky_Linux_9/Rocky_Linux_9.dockerfile

test-rocky10: ## Executes the testscript for testing cobbler in a docker container on Rocky Linux 10.
	./docker/rpms/build-and-install-rpms.sh rl10 docker/rpms/Rocky_Linux_10/Rocky_Linux_10.dockerfile

test-fedora37: ## Executes the testscript for testing cobbler in a docker container on Fedora 37.
	./docker/rpms/build-and-install-rpms.sh fc37 docker/rpms/Fedora_37/Fedora37.dockerfile

test-debian11: ## Executes the testscript for testing cobbler in a docker container on Debian 11.
	./docker/debs/build-and-install-debs.sh deb11 docker/debs/Debian_11/Debian11.dockerfile

test-debian12: ## Executes the testscript for testing cobbler in a docker container on Debian 12.
	./docker/debs/build-and-install-debs.sh deb12 docker/debs/Debian_12/Debian12.dockerfile

system-test: ## Runs the system tests
	$(MAKE) -C system-tests

system-test-env: ## Configures the environment for system tests
	$(MAKE) -C system-tests bootstrap

build: ## Runs the Python Build.
	@source distro_build_configs.sh; \
	${PYTHON} setup.py build -f --executable=${PYTHON}

install: build ## Runs the build target and then installs via setup.py
	# Debian/Ubuntu requires an additional parameter in setup.py
	@source distro_build_configs.sh; \
	git config --add safe.directory /code; \
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
	# Check if we are on Red Hat, SUSE or Debian based distribution
	@source distro_build_configs.sh; \
	${PYTHON} setup.py -v restorestate --root $(DESTDIR); \
	find $(DESTDIR)/var/lib/cobbler/triggers | xargs chmod +x
	if [ -d $(DESTDIR)/var/www/cobbler ] ; then \
		chmod -R +x $(DESTDIR)/var/www/cobbler/svc; \
	fi
	if [ -d $(DESTDIR)/srv/www/cobbler/svc ]; then \
		chmod -R +x $(DESTDIR)/srv/www/cobbler/svc; \
	fi
	rm -rf $(statepath)

webtest: devinstall ## Runs the task devinstall and then runs the targets clean and devinstall.
	make clean
	make devinstall

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
debs: authors ## Creates native debs in a directory called deb-build. The release target is called during the build process.
	@source distro_build_configs.sh; \
    debuild -us -uc
	@mkdir -p deb-build; \
    cp ../cobbler_* deb-build/; \
    cp ../cobbler-tests* deb-build/

eraseconfig: ## Deletes the cobbler data jsons which are created when using the file provider.
	-rm /var/lib/cobbler/cobbler_collections/distros/*
	-rm /var/lib/cobbler/cobbler_collections/images/*
	-rm /var/lib/cobbler/cobbler_collections/profiles/*
	-rm /var/lib/cobbler/cobbler_collections/systems/*
	-rm /var/lib/cobbler/cobbler_collections/repos/*
	-rm /var/lib/cobbler/cobbler_collections/mgmtclasses/*
	-rm /var/lib/cobbler/cobbler_collections/files/*
	-rm /var/lib/cobbler/cobbler_collections/packages/*
	-rm /var/lib/cobbler/cobbler_collections/menus/*

.PHONY: system-test
