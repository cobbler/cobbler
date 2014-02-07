#MESSAGESPOT=po/messages.pot

TOP_DIR:=$(shell pwd)

DESTDIR=/

prefix=devinstall
statepath=/tmp/cobbler_settings/$(prefix)

all: clean build

clean:
	-rm -rf build rpm-build
	-rm -f *~
	-rm -f cobbler/*.pyc
	-rm -rf dist
	-rm -rf buildiso
	-rm -f MANIFEST
	-rm -f koan/*.pyc
	-rm -f config/version
	-rm -f docs/*.1.gz 
	-rm -f *.tmp
	-rm -f *.log

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
	PYTHONPATH=./cobbler/ nosetests -v -w newtests/ 2>&1 | tee test.log

build:
	python setup.py build -f

# Debian/Ubuntu requires an additional parameter in setup.py
install: build
	if [ -e /etc/debian_version ]; then \
		python setup.py install --root $(DESTDIR) -f --install-layout=deb; \
	else \
		python setup.py install --root $(DESTDIR) -f; \
	fi

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
		# Red Hat-based
		chown -R apache $(DESTDIR)/var/www/cobbler; \
	elif [ -n "`getent passwd wwwrun`" ] ; then \
		# Suse-based
		chown -R wwwrun $(DESTDIR)/usr/share/cobbler/web/cobbler_web; \
	elif [-n "`getent passwd www-data`"] ; then \
		# Debian / Ubuntu
		chown -R www-data $(DESTDIR)/usr/share/cobbler/web/cobbler_web; \
	fi
	if [ -d $(DESTDIR)/var/www/cobbler ] ; then \
		chmod -R +x $(DESTDIR)/var/www/cobbler/web; \
		chmod -R +x $(DESTDIR)/var/www/cobbler/svc; \
	fi
	if [ -d $(DESTDIR)/usr/share/cobbler/web ] ; then \
		chmod -R +x $(DESTDIR)/usr/share/cobbler/web/cobbler_web; \
		chmod -R +x $(DESTDIR)/srv/www/cobbler/svc; \
	fi
	rm -rf $(statepath)

completion:
	python mkbash.py

webtest: devinstall
	make clean
	make devinstall
	make restartservices

# Check if we are on Red Hat, Suse or Debian based distribution
restartservices:
	if [ -x /sbin/service ] ; then \
		# Red Hat-based or Suse-based
		/sbin/service cobblerd restart; \
	    if [ -f /etc/init.d/httpd ] ; then \
			# Red Hat-based
			/sbin/service httpd restart; \
		else \
			# Suse-based
			/sbin/service apache2 restart; \
	else \
		# Debian / Ubuntu
		/usr/sbin/service cobblerd restart; \
		/usr/sbin/service apache2 restart; \
	fi

sdist: clean
	python setup.py sdist

rpms: clean sdist
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
	-rm /var/lib/cobbler/distros*
	-rm /var/lib/cobbler/profiles*
	-rm /var/lib/cobbler/systems*
	-rm /var/lib/cobbler/repos*
	-rm /var/lib/cobbler/networks*
	-rm /var/lib/cobbler/config/distros.d/*
	-rm /var/lib/cobbler/config/images.d/*
	-rm /var/lib/cobbler/config/profiles.d/*
	-rm /var/lib/cobbler/config/systems.d/*
	-rm /var/lib/cobbler/config/repos.d/*
	-rm /var/lib/cobbler/config/networks.d/*

.PHONY: tags
tags: 
	find . \( -name build -o -name .git \) -prune -o -type f -name '*.py' -print | xargs etags -o TAGS --
