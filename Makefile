#
# Setup Makefile to match your environment
#
PYTHON=/usr/bin/python3

# check for executables

PYFLAKES = $(shell { command -v pyflakes-3 || command -v pyflakes3 || command -v pyflakes; }  2> /dev/null)

PYCODESTYLE := $(shell { command -v pycodestyle-3 || command -v pycodestyle3 || command -v pycodestyle; } 2> /dev/null)

# Debian / Ubuntu have /bin/sh -> dash
SHELL = /bin/bash

TOP_DIR:=$(shell pwd)
DESTDIR=/

prefix=devinstall
statepath=/tmp/cobbler_settings/$(prefix)

all: clean build


clean:
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
	@rm -f MANIFEST AUTHORS README
	@rm -f config/version
	@rm -f docs/*.1.gz
	@echo "cleaning: temp files"
	@rm -f *~
	@rm -rf buildiso
	@rm -f *.tmp
	@rm -f *.log

cleandoc:
	@echo "cleaning: documentation"
	@cd docs; make clean > /dev/null 2>&1

readme:
	@echo "creating: README"
	@cat README.md | sed -e 's/^\[!.*//g' | tail -n "+3" > README

doc:
	@echo "creating: documentation"
	@cd docs; make html > /dev/null 2>&1

qa:
ifdef PYFLAKES
	@echo "checking: pyflakes ${PYFLAKES}"
	@${PYFLAKES} \
		*.py \
		cobbler/*.py \
		cobbler/modules/*.py \
		cobbler/web/*.py cobbler/web/templatetags/*.py \
		bin/cobbler* bin/*.py web/cobbler.wsgi
else
	@echo "No pyflakes found"
endif
ifdef PYCODESTYLE
	@echo "checking: pycodestyle"
	@${PYCODESTYLE} -r --ignore E501,E402,E722,W504 \
	        *.py \
		cobbler/*.py \
		cobbler/modules/*.py \
		cobbler/web/*.py cobbler/web/templatetags/*.py \
		bin/cobbler* bin/*.py web/cobbler.wsgi
else
	@echo "No pycodestyle found"
endif

authors:
	@echo "creating: AUTHORS"
	@cp AUTHORS.in AUTHORS
	@git log --format='%aN <%aE>' | grep -v 'root' | sort -u >> AUTHORS

sdist: readme authors
	@echo "creating: sdist"
	@${PYTHON} setup.py sdist > /dev/null

release: clean qa readme authors sdist
	@echo "creating: release artifacts"
	@mkdir release
	@cp dist/*.gz release/
	@cp cobbler.spec release/

test:
	make savestate prefix=test
	make rpms
	make install
	make eraseconfig
	/sbin/service cobblerd restart
	-(make nosetests)
	make restorestate prefix=test
	/sbin/service cobblerd restart

test-centos7:
	./tests/build-and-install-rpms.sh --with-tests el7 dockerfiles/CentOS7.dockerfile

test-centos8:
	./tests/build-and-install-rpms.sh --with-tests el8 dockerfiles/CentOS8.dockerfile

test-fedora31:
	./tests/build-and-install-rpms.sh --with-tests f31 dockerfiles/Fedora31.dockerfile

test-debian10:
	./tests/build-and-install-debs.sh --with-tests deb10 dockerfiles/Debian10.dockerfile

nosetests:
	PYTHONPATH=./cobbler/ nosetests -v -w tests/cli/ 2>&1 | tee test.log

build:
	${PYTHON} setup.py build -f

# Debian/Ubuntu requires an additional parameter in setup.py
install: build
	@${PYTHON} setup.py install --root $(DESTDIR) -f

devinstall:
	-rm -rf $(DESTDIR)/usr/share/cobbler
	make savestate
	make install
	make restorestate

savestate:
	@${PYTHON} setup.py -v savestate --root $(DESTDIR); \


# Check if we are on Red Hat, Suse or Debian based distribution
restorestate:
	@${PYTHON} setup.py -v restorestate --root $(DESTDIR); \
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

webtest: devinstall
	make clean
	make devinstall
	make restartservices

# Check if we are on Red Hat, Suse or Debian based distribution
restartservices:
	if [ -x /sbin/service ] ; then \
		/sbin/service cobblerd restart; \
		if [ -f /etc/init.d/httpd ] ; then \
			/sbin/service httpd restart; \
		elif [ -f /usr/lib/systemd/system/httpd.service ]; then \
			/bin/systemctl restart httpd.service; \
		else \
			/sbin/service apache2 restart; \
		fi; \
	elif [ -x /bin/systemctl ]; then \
		if [ -d /lib/systemd/system/apache2.service.d ]; then \
			/bin/systemctl restart apache2.service; \
		else \
			/bin/systemctl restart httpd.service; \
		fi \
	else \
		/usr/sbin/service cobblerd restart; \
		/usr/sbin/service apache2 restart; \
	fi

rpms: release
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
debs: release
	mkdir -p deb-build
	mkdir -p deb-build/{BUILD,BUILDROOT,DEBS,SDEBS,SOURCES}
	cp dist/*.gz deb-build/
	debbuild --define "_topdir %(pwd)/deb-build" \
	--define "_builddir %{_topdir}" \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-vv -bb cobbler.spec

eraseconfig:
	-rm /var/lib/cobbler/collections/distros/*
	-rm /var/lib/cobbler/collections/images/*
	-rm /var/lib/cobbler/collections/profiles/*
	-rm /var/lib/cobbler/collections/systems/*
	-rm /var/lib/cobbler/collections/repos/*
	-rm /var/lib/cobbler/collections/mgmtclasses/*
	-rm /var/lib/cobbler/collections/files/*
	-rm /var/lib/cobbler/collections/packages/*

.PHONY: tags
tags:
	find . \( -name build -o -name .git \) -prune -o -type f -name '*.py' -print | xargs etags -o TAGS --
