
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
	@rm -rf build rpm-build release dist
	@rm -f MANIFEST AUTHORS README
	@rm -f config/version
	@rm -f docs/*.1.gz
	@echo "cleaning: temp files"
	@rm -f *~
	@rm -rf buildiso
	@rm -f *.tmp
	@rm -f *.log
	@echo "cleaning: documentation"
	@cd docs; make clean > /dev/null 2>&1

readme:
	@echo "creating: README"
	@cat README.md | sed -e 's/^\[!.*//g' | tail -n "+3" > README

doc:
	@echo "creating: documentation"
	@cd docs; make html > /dev/null 2>&1

qa:
	@echo "checking: pyflakes"
	@pyflakes \
		*.py \
		cobbler/*.py \
		cobbler/modules/*.py \
		cobbler/web/*.py cobbler/web/templatetags/*.py \
		bin/cobbler* bin/*.py web/cobbler.wsgi
	@echo "checking: pep8"
	@pep8 -r --ignore E501 \
        *.py \
        cobbler/*.py \
        cobbler/modules/*.py \
        cobbler/web/*.py cobbler/web/templatetags/*.py \
        bin/cobbler* bin/*.py web/cobbler.wsgi

authors:
	@echo "creating: AUTHORS"
	@cp AUTHORS.in AUTHORS
	@git log --format='%aN <%aE>' | grep -v 'root' | sort -u >> AUTHORS

sdist: readme authors
	@echo "creating: sdist"
	@python setup.py sdist > /dev/null

release: clean qa readme authors sdist doc
	@echo "creating: release artifacts"
	@mkdir release
	@cp dist/*.gz release/
	@cp cobbler.spec release/
	@cp debian/cobbler.dsc release/
	@cp debian/changelog release/debian.changelog
	@cp debian/control release/debian.control
	@cp debian/rules release/debian.rules

test:
	make savestate prefix=test
	make rpms
	make install
	make eraseconfig
	/sbin/service cobblerd restart
	-(make nosetests)
	make restorestate prefix=test
	/sbin/service cobblerd restart

nosetests:
	PYTHONPATH=./cobbler/ nosetests -v -w tests/cli/ 2>&1 | tee test.log

build:
	python setup.py build -f

# Debian/Ubuntu requires an additional parameter in setup.py
install: build
	python setup.py install --root $(DESTDIR) -f

devinstall:
	-rm -rf $(DESTDIR)/usr/share/cobbler
	make savestate
	make install
	make restorestate

savestate:
	python setup.py -v savestate --root $(DESTDIR); \


# Check if we are on Red Hat, Suse or Debian based distribution
restorestate:
	python setup.py -v restorestate --root $(DESTDIR); \
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
