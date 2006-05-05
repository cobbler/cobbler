clean:
	\rm -f cobbler*.gz cobbler*.rpm MANIFEST
	\rm -rf cobbler-* dist build

manpage:
	pod2man --center="cobbler" --release="" cobbler.pod | gzip -c > cobbler.1.gz

test:
	python tests/tests.py
	\rm -rf /tmp/_cobbler-*

install: clean manpage
	python setup.py sdist
	cp dist/*.gz .
	rpmbuild --define "_topdir %(pwd)" \
	--define "_builddir %{_topdir}" \
	--define "_rpmdir %{_topdir}" \
	--define "_srcrpmdir %{_topdir}" \
	--define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' \
	--define "_specdir %{_topdir}" \
	--define "_sourcedir  %{_topdir}" \
	-ba cobbler.spec
