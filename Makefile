all: manpage

manpage:
	pod2man --center="xen-net-install" --release="" xen-net-install.pod > xen-net-install.1
	-(\rm xen-net-install.1.gz)
	gzip xen-net-install.1
	cp -f xen-net-install.1.gz /usr/share/man/man1

install:
	echo "(install not implemented)"
