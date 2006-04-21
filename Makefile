all: manpage

manpage:
	pod2man --center="koan" --release="" koan.pod > koan.1
	-(\rm koan.1.gz)
	gzip koan.1
	cp -f koan.1.gz /usr/share/man/man1

install:
	echo "(install not implemented)"
