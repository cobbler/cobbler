all: manpage

manpage:
	pod2man bootconf.pod > bootconf.1
	gzip bootconf.1
	cp bootconf.1.gz /usr/share/man/man1

install:
	echo "(install not implemented)"
