#MESSAGESPOT=po/messages.pot

all: rpms

clean:
	-rm -f pod2htm*.tmp
	-rm -f cobbler*.gz cobbler*.rpm MANIFEST
	-rm -rf cobbler-* dist build
	-rm -rf *~
	-rm -rf rpm-build/
	#-rm -f docs/cobbler.1.gz
	#-rm -f docs/cobbler.html
	#-rm -f po/messages.pot*

manpage:
	pod2man --center="cobbler" --release="" ./docs/cobbler.pod | gzip -c > ./docs/cobbler.1.gz
	pod2html ./docs/cobbler.pod > ./docs/cobbler.html
 
test: devinstall
	-rm -rf /tmp/cobbler_test_bak
	mkdir -p /tmp/cobbler_test_bak
	cp /etc/cobbler/settings /tmp/cobbler_test_bak/settings
	cp /etc/cobbler/modules.conf /tmp/cobbler_test_bak/modules.conf
	cp -a /var/lib/cobbler/config  /tmp/cobbler_test_bak/config
	python tests/tests.py
	-rm -rf /var/lib/cobbler/config
	-rm /etc/cobbler/settings
	-rm /etc/cobbler/modules.conf
	cp -a /tmp/cobbler_test_bak/config /var/lib/cobbler/
	cp /tmp/cobbler_test_bak/settings /etc/cobbler/settings
	cp /tmp/cobbler_test_bak/modules.conf /etc/cobbler/modules.conf

test2:
	python tests/multi.py	

build: clean updatewui
	python setup.py build -f

install: clean manpage
	python setup.py install -f

devinstall:
	-cp /etc/cobbler/settings /tmp/cobbler_settings
	-cp /etc/cobbler/modules.conf /tmp/cobbler_modules.conf
	-cp /etc/httpd/conf.d/cobbler.conf /tmp/cobbler_http.conf
	-cp /etc/cobbler/acls.conf /tmp/cobbler_acls.conf
	-cp /etc/cobbler/users.conf /tmp/cobbler_users.conf
	-cp /etc/cobbler/users.digest /tmp/cobbler_users.digest
	make install
	-cp /tmp/cobbler_settings /etc/cobbler/settings
	-cp /tmp/cobbler_modules.conf /etc/cobbler/modules.conf
	-cp /tmp/cobbler_users.conf /etc/cobbler/users.conf
	-cp /tmp/cobbler_acls.conf /etc/cobbler/acls.conf
	-cp /tmp/cobbler_users.digest /etc/cobbler/users.digest
	-cp /tmp/cobbler_http.conf /etc/httpd/conf.d/cobbler.conf
	find /var/lib/cobbler/triggers | xargs chmod +x
	chown -R apache /var/www/cobbler 
	chmod -R +x /var/www/cobbler/web
	chmod -R +x /var/www/cobbler/svc
	-rm -rf /tmp/cobbler_*

completion:
	python mkbash.py

webtest: updatewui devinstall
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

