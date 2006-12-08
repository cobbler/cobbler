all: rpm

clean:
	-rm -f koan*.gz koan*.rpm MANIFEST
	-rm -rf koan-* dist build

manpage:
	pod2man --center=koan --release= koan.pod | gzip -c > koan.1.gz
	pod2html koan.pod > koan.html

test:
	python tests/tests.py

rpm: clean manpage
	python setup.py sdist
	cp dist/*.gz .
	rpmbuild --define "_topdir %(pwd)" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-ba koan.spec

