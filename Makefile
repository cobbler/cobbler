all: manpage

manpage:
	pod2man --center="cobbler" --release="" cobbler.pod > cobbler.1
	-(\rm cobbler.1.gz)
	gzip cobbler.1
	cp -f cobbler.1.gz /usr/share/man/man1

install:
	echo "(install not implemented)"
