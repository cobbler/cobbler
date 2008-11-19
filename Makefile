#MESSAGESPOT=po/messages.pot

prefix=devinstall
statepath=/tmp/cobbler_settings/$(prefix)

all: clean rpms

clean:
	-rm -f pod2htm*.tmp
	-rm -f cobbler*.gz cobbler*.rpm MANIFEST
	-rm -rf cobbler-* dist build
	-rm -rf *~
	-rm -rf rpm-build/
	#-rm -f docs/cobbler.1.gz
	#-rm -f docs/cobbler.html
	#-rm -f po/messages.pot*
	-rm -f cobbler/*.pyc
	-rm -f cobbler/yaml/*.pyc
	-rm -f cobbler/webui/master.py
	-rm -f config/modules.conf config/settings config/version
	-rm -f docs/cobbler.1.gz docs/cobbler.html

manpage:
	pod2man --center="cobbler" --release="" ./docs/cobbler.pod | gzip -c > ./docs/cobbler.1.gz
	pod2html ./docs/cobbler.pod > ./docs/cobbler.html
 
test: 
	make savestate prefix=test
	make rpms
	make install
	make eraseconfig
	-(make nosetests)
	make restorestate prefix=test

nosetests:
	#nosetests tests -w cobbler --with-coverage --cover-package=cobbler --cover-erase --quiet | tee test.log
	nosetests cobbler/*.py -v | tee test.log

build: manpage updatewui
	python setup.py build -f

install: manpage updatewui
	python setup.py install -f

devinstall: 
	make savestate 
	make install 
	make restorestate

savestate:
	mkdir -p $(statepath)
	cp -a /var/lib/cobbler/config $(statepath)
	cp /etc/cobbler/settings $(statepath)/settings
	cp /etc/cobbler/modules.conf $(statepath)/modules.conf
	cp /etc/httpd/conf.d/cobbler.conf $(statepath)/http.conf
	cp /etc/cobbler/acls.conf $(statepath)/acls.conf
	cp /etc/cobbler/users.conf $(statepath)/users.conf
	cp /etc/cobbler/users.digest $(statepath)/users.digest


restorestate:
	cp -a $(statepath)/config /var/lib/cobbler
	cp $(statepath)/settings /etc/cobbler/settings
	cp $(statepath)/modules.conf /etc/cobbler/modules.conf
	cp $(statepath)/users.conf /etc/cobbler/users.conf
	cp $(statepath)/acls.conf /etc/cobbler/acls.conf
	cp $(statepath)/users.digest /etc/cobbler/users.digest
	cp $(statepath)/http.conf /etc/httpd/conf.d/cobbler.conf
	find /var/lib/cobbler/triggers | xargs chmod +x
	chown -R apache /var/www/cobbler 
	chmod -R +x /var/www/cobbler/web
	chmod -R +x /var/www/cobbler/svc
	#-[ "$(statepath)" != "/" ] && rm -rf $(statepath)

completion:
	python mkbash.py

webtest: 
	make clean 
	make updatewui 
	make devinstall 
	make restartservices

restartservices:
	/sbin/service cobblerd restart
	/sbin/service httpd restart

sdist: clean updatewui
	python setup.py sdist

#messages: cobbler/*.py
#	xgettext -k_ -kN_ -o $(MESSAGESPOT) cobbler/*.py
#	sed -i'~' -e 's/SOME DESCRIPTIVE TITLE/cobbler/g' -e 's/YEAR THE PACKAGE'"'"'S COPYRIGHT HOLDER/2007 Red Hat, Inc. /g' -e 's/FIRST AUTHOR <EMAIL@ADDRESS>, YEAR/Michael DeHaan <mdehaan@redhat.com>, 2007/g' -e 's/PACKAGE VERSION/cobbler $(VERSION)-$(RELEASE)/g' -e 's/PACKAGE/cobbler/g' $(MESSAGESPOT)


rpms: clean updatewui manpage sdist
	mkdir -p rpm-build
	cp dist/*.gz rpm-build/
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-ba cobbler.spec

srpm: manpage sdist
	mkdir -p rpm-build
	cp dist/*.gz rpm-build/
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-bs --nodeps cobbler.spec

updatewui:
	cheetah-compile ./webui_templates/master.tmpl
	-(rm ./webui_templates/*.bak)
	mv ./webui_templates/master.py ./cobbler/webui

eraseconfig:
	-rm /var/lib/cobbler/distros*
	-rm /var/lib/cobbler/profiles*
	-rm /var/lib/cobbler/systems*
	-rm /var/lib/cobbler/repos*
	-rm /var/lib/cobbler/config/distros.d/*
	-rm /var/lib/cobbler/config/images.d/*
	-rm /var/lib/cobbler/config/profiles.d/*
	-rm /var/lib/cobbler/config/systems.d/*
	-rm /var/lib/cobbler/config/repos.d/*


graphviz:
	dot -Tpdf docs/cobbler.dot -o cobbler.pdf

