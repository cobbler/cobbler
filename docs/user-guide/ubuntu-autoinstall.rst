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

At this point, the new Ubuntu ``cobbler profile`` should be set to autoinstall and available on the generic BIOS and EFI GRUB2 menus, which will use the live installer by default as the source for installations, not the local cobbler ``distro_mirror``.

* This is due to the default cobbler autoinstall snippet ``cloud_config_apt``, which, when rendered, would resemble the below code-block

.. code-block:: yaml

      apt:
        preserve_sources_list: true
        mirror-selection:
          primary:
            - arches: [default]
              uri: http://server/cblr/links/Ubuntu24-casper-x86_64

* in order to install from the local repo hosted by cobbler (which was extracted during ``distro import``) the ``apt:`` section must disable some suites & components which are not included on the live ISO installer with the following settings:

.. code-block:: yaml

      apt:
        preserve_sources_list: true
        mirror-selection:
          primary:
            - arches: [default]
              uri: http://server/cblr/links/Ubuntu24-casper-x86_64
        disable_components: [restricted,multiverse]
        disable_suites: [backports,security,updates]

By default the resulting system will retain the apt configuration defined in the ``cloud-config`` autoinstall, so it may be necessary to add the appropriate official source mirrors/repos as a local (metadata-only) ``cobbler repo`` and assign them to the appropriate ``cobbler profile`` for use during and after installation

.. code-block:: shell

    cobbler repo add --name Ubuntu-Noble --mirror-locally false --breed apt --arch x86_64 --mirror http://us.archive.ubuntu.com/ubuntu --apt-components=main --apt-dists=noble
    cobbler profile edit --name Ubuntu24-casper-x86_64 --repos "Ubuntu-Noble"

* To retain the apt settings included on the live ISO installer (default Ubuntu official sources), the ``apt:`` section should include the ``preserve_sources_list: false`` option:

.. code-block:: yaml

      apt:
        preserve_sources_list: false
        mirror-selection:
          primary:
            - arches: [default]
              uri: http://server/cblr/links/Ubuntu24-casper-x86_64

The ``cobbler system`` functions are nearly identical to other distros, with some exceptions/limitations in the default autoinstall included with cobbler

* no support for IPv6
* no support for bridged or teamed NICs

Ubuntu 20.04 differences
========================

The ``mirror-selection`` options was not available in ubuntu 20.04, so the ``apt`` section should be changed to resemble the following instead:

* Additionally, the ``fallback: offline`` option was only available as of Ubuntu 22.04 LTS, so Ubuntu20.04 cannot install via PXE without a remote source mirror/repo, so be sure to use the public mirrors or ``disable_suites`` & ``disable_components`` options mentioned above. ( `release notes <https://discourse.ubuntu.com/t/jammy-jellyfish-release-notes/24668>`_ , `introduction <https://github.com/canonical/subiquity/commit/6c3ae3c6dda8020599b8bf1a772e834876541666>`_ )

.. code-block:: yaml

      apt:
        preserve_sources_list: true
        primary:
          - arches: [default]
            uri: http://server/cblr/links/Ubuntu24-casper-x86_64
        disable_components: [restricted,multiverse]
        disable_suites: [backports,security,updates]

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

