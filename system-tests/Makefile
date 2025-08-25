listing:
	scripts/list-iso $(ISO) $(BREED) $(DISTRO)

images/dummy/bios-disk:
	scripts/create-dummy-initramfs $@

images/dummy/initramfs.gz:
	scripts/create-dummy-bios-disk $@

.PHONY: results listing
