MESSAGESPOT=po/messages.pot

all: rpms

clean:
	-rm -f pod2htm*.tmp
	-rm -f cobbler*.gz cobbler*.rpm MANIFEST
	-rm -rf cobbler-* dist build
	-rm -rf *~
	-rm -rf rpm-build/

manpage:
	pod2man --center="cobbler" --release="" ./docs/cobbler.pod | gzip -c > ./docs/cobbler.1.gz
	pod2html ./docs/cobbler.pod > ./docs/cobbler.html
 
test: install
	python tests/tests.py
	-rm -rf /tmp/_cobbler-*

build: clean updatewui messages
	python setup.py build -f

install: clean manpage
	python setup.py install -f

sdist: clean messages updatewui
	python setup.py sdist

messages: cobbler/*.py
	xgettext -k_ -kN_ -o $(MESSAGESPOT) cobbler/*.py
	sed -i'~' -e 's/SOME DESCRIPTIVE TITLE/cobbler/g' -e 's/YEAR THE PACKAGE'"'"'S COPYRIGHT HOLDER/2007 Red Hat, Inc. /g' -e 's/FIRST AUTHOR <EMAIL@ADDRESS>, YEAR/Michael DeHaan <mdehaan@redhat.com>, 2007/g' -e 's/PACKAGE VERSION/cobbler $(VERSION)-$(RELEASE)/g' -e 's/PACKAGE/cobbler/g' $(MESSAGESPOT)


rpms: manpage sdist
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

