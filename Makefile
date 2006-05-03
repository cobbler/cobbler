all: clean test manpage install

clean:
	-(rm *.gz)
	-(rm *.rpm)
	-(rm -r koan-*)
	-(rm -rf ./dist)
	-(rm -rf ./build)
	-(rm MANIFEST)

manpage:
	pod2man --center="koan" --release="" koan.pod > koan.1
	-(\rm koan.1.gz)
	gzip koan.1

test:
	python tests/tests.py

install:
	python setup.py sdist
	cp dist/*.gz .
	rpmbuild --define "_topdir %(pwd)" --define "_builddir %{_topdir}" --define "_rpmdir %{_topdir}" --define "_srcrpmdir %{_topdir}" --define '_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm' --define "_specdir %{_topdir}" --define "_sourcedir  %{_topdir}" -ba koan.spec
