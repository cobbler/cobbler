.. _ubuntu_autoinstall:

******************************************
Ubuntu cloud-init autoinstall with Cobbler
******************************************

Supported installation options:

* UEFI PXE install (via grub2 grubx64.efi and tftp)
* BIOS PXE install (via grub2 grub.0 and tftp)

Installation Quickstart guide
#############################

Mount and import the supported Ubuntu LTS server installation media:

.. code-block:: shell

    mount -t iso9660 -o loop,ro ubuntu-24.04.1-live-server-amd64.iso /mnt/ubuntu
    cobbler import --name Ubuntu24 --path /mnt/Ubuntu

Unlike other distros/breeds, Ubuntu 20.04 and later "server netboot" and "autoinstall" have a requirement beyond the usual kernel+initrd; the full, live ISO is downloaded immediately after boot on the PXE client to proceed with installations, so copy the live installer to the corresponding ``distro_mirror`` directory for the distro:

* The live installer MUST be named ``media.iso`` as specified by the default ``kernel_options`` for supported Ubuntu versions (see ``distro_signatures.json``).

.. code:: shell

    cp ubuntu-24.04.1-live-server-amd64.iso /var/www/cobbler/distro_mirror/Ubuntu24/media.iso

At this point, the new Ubuntu ``cobbler profile`` should be set to autoinstall and available on the generic BIOS and EFI GRUB2 menus

The ``cobbler system`` functions are nearly identical to other distros, with some exceptions/limitations in the default autoinstall included with cobbler

* no support for IPv6
* no support for bridged or teamed NICs

References & Resources
======================

* `how-to-netboot-the-server-installer-on-amd64 <https://documentation.ubuntu.com/server/how-to/installation/how-to-netboot-the-server-installer-on-amd64/>`_
* `kernel-cloud-config-url-configuration <https://docs.cloud-init.io/en/latest/explanation/kernel-command-line.html#kernel-cloud-config-url-configuration>`_
* `intro-to-autoinstall <https://canonical-subiquity.readthedocs-hosted.com/en/latest/intro-to-autoinstall.html>`_
* `providing-autoinstall <https://canonical-subiquity.readthedocs-hosted.com/en/latest/tutorial/providing-autoinstall.html#providing-autoinstall>`_
* `creating-autoinstall-configuration <https://canonical-subiquity.readthedocs-hosted.com/en/latest/tutorial/creating-autoinstall-configuration.html>`_
* `cloud-init-autoinstall-interaction <https://canonical-subiquity.readthedocs-hosted.com/en/latest/explanation/cloudinit-autoinstall-interaction.html>`_
* `autoinstall-quickstart <https://canonical-subiquity.readthedocs-hosted.com/en/latest/howto/autoinstall-quickstart.html>`_
* `autoinstall-reference <https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html>`_
* `creating-autoinstall-configuration <https://canonical-subiquity.readthedocs-hosted.com/en/latest/tutorial/creating-autoinstall-configuration.html>`_
* `netbooting-the-live-server-installer <https://discourse.ubuntu.com/t/netbooting-the-live-server-installer/14510>`_
* `netplan-yaml <https://netplan.readthedocs.io/en/latest/netplan-yaml/>`_
* `cloud-config-data <https://docs.cloud-init.io/en/latest/explanation/format.html#cloud-config-data>`_
* `cloud-init reference <https://docs.cloud-init.io/en/latest/reference/modules.html>`_
* `cloud-init examples <https://docs.cloud-init.io/en/latest/reference/examples.html#yaml-examples>`_

