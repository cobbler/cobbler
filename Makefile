all: clean test manpage install

clean:
	@rm -f *.gz *.rpm MANIFEST
	@rm -rf cobbler-* dist build

manpage:
	pod2man --center="cobbler" --release="" cobbler.pod > cobbler.1
	@\rm -f cobbler.1.gz
	gzip cobbler.1

test:
	python tests/tests.py

install: clean
	python setup.py sdist
	cp dist/*.gz .
	rpmbuild --define "_topdir %(pwd)" --define "_builddir %{_topdir}" --define "_rpmdir %{_topdir}" --define "_srcrpmdir %{_topdir}" --define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' --define "_specdir %{_topdir}" --define "_sourcedir  %{_topdir}" -ba cobbler.spec

