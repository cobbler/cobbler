all: rpms

clean:
	-rm -f koan*.gz koan*.html koan*.rpm MANIFEST
	-rm -rf koan-* dist build
	-rm -rf rpm-build
	-rm -rf *~ *.pyc *.pyo *.tmp

manpage:
	pod2man --center="koan" --release= koan.pod | gzip -c > koan.1.gz
	pod2html koan.pod > koan.html

test:
	python tests/tests.py

build: clean
	python setup.py build -f

install: build manpage
	python setup.py install -f

sdist: manpage
	python setup.py sdist

rpms:  sdist
	mkdir -p rpm-build
	cp dist/*.gz rpm-build/
	rpmbuild --define "_topdir %(pwd)/rpm-build" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-ba koan.spec

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
	-bs --nodeps koan.spec



