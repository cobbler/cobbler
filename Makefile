#MESSAGESPOT=po/messages.pot

TOP_DIR:=$(shell pwd)

prefix=devinstall
statepath=/tmp/cobbler_settings/$(prefix)

all: clean build

clean:
	-rm -rf build rpm-build
	-rm -f *~
	-rm -f cobbler/*.pyc
	-rm -rf dist
	-rm -rf buildiso
	-rm MANIFEST
	-rm -f koan/*.pyc
	-rm -f config/modules.conf config/settings config/version
	-rm -f docs/*.1.gz 
	-rm *.tmp
	-rm *.log

manpage: clean
	pod2man --center="cobbler" --release="" ./docs/cobbler.pod | gzip -c > ./docs/cobbler.1.gz
	pod2man --center="koan" --release="" ./docs/koan.pod | gzip -c > ./docs/koan.1.gz
	pod2man --center="cobbler-register" --release="" ./docs/cobbler-register.pod | gzip -c > ./docs/cobbler-register.1.gz

test:
	make savestate prefix=test
	make rpms
	make install
	make eraseconfig
	/sbin/service cobblerd restart
	-(make nosetests)
	make restorestate prefix=test

nosetests:
	nosetests cobbler/*.py -v | tee test.log

build: manpage
	python setup.py build -f

install: build manpage
	python setup.py install -f
	chown -R apache /usr/share/cobbler/web

debinstall: manpage
	python setup.py install -f --root $(DESTDIR)

devinstall:
	-rm -rf /usr/share/cobbler
	make savestate
	make install
	make restorestate

savestate:
	mkdir -p $(statepath)
	cp -a /var/lib/cobbler/config $(statepath)
	cp /etc/cobbler/settings $(statepath)/settings
	cp /etc/cobbler/modules.conf $(statepath)/modules.conf
	cp /etc/httpd/conf.d/cobbler.conf $(statepath)/http.conf
	cp /etc/httpd/conf.d/cobbler_web.conf $(statepath)/cobbler_web.conf
	cp /etc/cobbler/users.conf $(statepath)/users.conf
	cp /etc/cobbler/users.digest $(statepath)/users.digest
	cp /etc/cobbler/dhcp.template $(statepath)/dhcp.template
	cp /etc/cobbler/rsync.template $(statepath)/rsync.template


restorestate:
	cp -a $(statepath)/config /var/lib/cobbler
	cp $(statepath)/settings /etc/cobbler/settings
	cp $(statepath)/modules.conf /etc/cobbler/modules.conf
	cp $(statepath)/users.conf /etc/cobbler/users.conf
	cp $(statepath)/users.digest /etc/cobbler/users.digest
	cp $(statepath)/http.conf /etc/httpd/conf.d/cobbler.conf
	cp $(statepath)/cobbler_web.conf /etc/httpd/conf.d/cobbler_web.conf
	cp $(statepath)/dhcp.template /etc/cobbler/dhcp.template
	cp $(statepath)/rsync.template /etc/cobbler/rsync.template
	find /var/lib/cobbler/triggers | xargs chmod +x
	chown -R apache /var/www/cobbler
	chmod -R +x /var/www/cobbler/web
	chmod -R +x /var/www/cobbler/svc
	rm -rf $(statepath)

completion:
	python mkbash.py

webtest: devinstall
	make clean
	make devinstall
	make restartservices

restartservices:
	/sbin/service cobblerd restart
	/sbin/service httpd restart

sdist: manpage
	python setup.py sdist

rpms: clean manpage sdist
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

tags:
	find . -type f -name '*.py' | xargs etags -c TAGS
