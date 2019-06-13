installdep:
	yum install -y grub2-efi-ia32-modules grub2-efi-x64-modules

buildloaders:
	grub2-mkstandalone -d /usr/lib/grub2/i386-efi/ --compress=xz -O i386-efi --modules="tftp net efinet linux part_gpt efifwsetup http" --locales= -o grub2-x86.efi
	grub2-mkstandalone -d /usr/lib/grub2/x86_64-efi/ --compress=xz -O x86_64-efi --modules="tftp net efinet linux part_gpt efifwsetup http" --locales= -o grubx64.efi
copyloaders:
	cp grub2-x86.efi /var/lib/cobbler/loaders/
	cp grub2-x86_64.efi /var/lib/cobbler/loaders/grub2-x86_64.efi

install: installdep buildloaders copyloaders
