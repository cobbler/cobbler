all: clean test manpage install

clean:
	-(rm *.gz)
	-(rm *.rpm)
	-(rm -r cobbler-*)
	-(rm -rf ./dist)
	-(rm -rf ./build)
	-(rm MANIFEST)

manpage:
	pod2man --center="cobbler" --release="" cobbler.pod > cobbler.1
	-(\rm cobbler.1.gz)
	gzip cobbler.1

test:
	python tests/tests.py

install:
	python setup.py sdist
	cp dist/*.gz .
	rpmbuild --define "_topdir %(pwd)" --define "_builddir %{_topdir}" --define "_rpmdir %{_topdir}" --define "_srcrpmdir %{_topdir}" --define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' --define "_specdir %{_topdir}" --define "_sourcedir  %{_topdir}" -ba cobbler.spec

