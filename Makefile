all: manpage

manpage:
	pod2man --center="bootconf" --release="" bootconf.pod > bootconf.1
	-(\rm bootconf.1.gz)
	gzip bootconf.1
	cp -f bootconf.1.gz /usr/share/man/man1

install:
	echo "(install not implemented)"
