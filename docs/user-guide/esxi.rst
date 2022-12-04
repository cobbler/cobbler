*************************************
VMware ESXi installation with cobbler
*************************************

**What works** (DHCPv4):

* BIOS PXE install (via syslinux-3.86 ``pxelinux.0`` and ``mboot.c32``)
* BIOS iPXE install (via ipxe ``undionly.kpxe`` chainloading syslinux-3.86 ``pxelinux.0``)
* UEFI PXE install (via ESXi UEFI bootloader ``mboot.efi`` )
* UEFI iPXE install (via ipxe ``snponly.efi`` chainloading ESXi UEFI bootloader ``mboot.efi``)

**What does not work**:

* using DHCPv6 to install ESXi.
* UEFI firmware HTTP install
* Profile boot menus

Installation Quickstart guide
#############################

This quickstart guide will assume default settings.

Provide cobbler with ESXi bootloaders
=====================================

* For a BIOS firmware PXE install, you will need ``pxelinux.0`` from syslinux version 3.86
* For a UEFI firmware PXE install, you will need the ``efi/boot/bootx64.efi`` file from the ESXi installer ISO image
  copied as ``mboot.efi``

iPXE booting is documented later. Note that this step will only need to be run once.

.. code-block:: console

    # STEP 1: Create esxi dir in cobbler bootloaders_dir
    mkdir /var/lib/cobbler/loaders/esxi

    # STEP 2: If installing from BIOS firmware, pxelinux.0 from syslinux version 3.86 is needed
    curl https://mirrors.edge.kernel.org/pub/linux/utils/boot/syslinux/3.xx/syslinux-3.86.tar.gz | tar -zx -C /tmp
    cp /tmp/syslinux-3.86/core/pxelinux.0 /var/lib/cobbler/loaders/esxi/

    # STEP 3: If installing from UEFI firmware, copy efi/boot/bootx64.efi as mboot.efi
    # try using your latest ESXi ISO for compatibility
    mount -t iso9660 VMware-VMvisor-Installer-7.0U3d-19482537.x86_64.iso /mnt
    cp /mnt/efi/boot/bootx64.efi /var/lib/cobbler/loaders/esxi/mboot.efi
    umount /mnt

    # STEP 4: sync cobbler so bootloaders are copied to tftpboot location
    cobbler sync


Import an ESXi distro
========================

.. code-block:: console

    mount -t iso9660 /srv/VMware-VMvisor-Installer-7.0U3d-19482537.x86_64.iso /mnt
    cobbler import --name=esxiv70U3d --path=/mnt --arch=x86_64

Import will detect the breed as ``vmware`` and os-version as ``esxi70``; it will create a distro named ``esxiv70U3d-x86_64``
and a profile with the same ``esxiv70U3d-x86_64`` name.

Add a system
============

Now add a system with the previously created profile

.. code-block:: console

    cobbler system add --name some-esxi-host --profile esxiv70U3d-x86_64 --netboot-enabled=true \
        --interface="vmnic0" --mac-address="01:23:45:67:89:ab" --dns-name=some-esxi-host.localdomain

.. warning::
    Note that you **must** provide a MAC address for the ESXi system in order to be provisioned via cobbler

Entries in the ``/etc/dhcp/dhcpd.conf`` file should have been generated for system ``some-esxi-host``.

 .. code-block::

    # group for Cobbler DHCP tag: default
    group {
        ...
        host some-esxi-host.localdomain-vmnic0 {
            hardware ethernet 01:23:45:67:89:ab;
            option host-name "some-esxi-host.localdomain";
            if option system-arch = 00:07 or option system-arch = 00:09 {
                filename = "esxi/system/01-01-23-45-67-89-ab/mboot.efi";
            } else {
                filename = "esxi/pxelinux.0";
            }
            next-server 192.168.1.1;
        }
        ...
    }

You should now be able to pxe boot your system (BIOS or UEFI firmware) and install ESXi.

Providing Cobbler the ESXi bootloaders
######################################

ESXi own bootloader is available on `github <https://github.com/vmware/esx-boot>`_; this guides uses the ESXi install ISO as an
easier way to provide cobbler with the ESXi bootloaders, instead of compiling from source.

.. note::
    ESXi **does not support GRUB**; you can find the details on this
    `VMware community thread <https://communities.vmware.com/t5/ESXi-Discussions/Has-anyone-been-able-to-invoke-the-VMware-BOOTX64-efi-from-a/td-p/2194918>`_;
    (useful comments from the esx-boot author TimMann).

ESXi provides network bootloaders for:

* BIOS firmware (``mboot.c32``).
* UEFI firmware (``mboot.efi``).
* It is also possible to use iPXE (BIOS and UEFI), and then chainload the ESXi bootloaders.

A cobbler setup with all the ESXi bootloaders would look like:

.. code-block:: console

    cobbler:~ # ls -alh /var/lib/cobbler/loaders/esxi/
    total 488K
    drwxr-xr-x 2 root root 4.0K Jul 18 10:47 .
    drwxr-xr-x 4 root root 4.0K Jul 18 07:25 ..
    -r-xr-xr-x 1 root root 197K Jul 13 11:18 mboot.efi
    -rwxr-xr-x 1 root root  17K Jul 13 18:04 pxelinux.0
    -rw-r--r-- 1 root root 185K Jul 14 13:54 snponly.efi
    -rw-r--r-- 1 root root  72K Jul 18 07:26 undionly.pxe

Note that ``mboot.c32``, the esxi network bootloader for BIOS firmware, is not listed as it will be downloaded from the images/distro
directory in the tftp boot location.

Booting from BIOS firmware
==========================

.. note::
    As stated on VMware docs, *The ESXi boot loader for BIOS systems, mboot.c32, runs as a SYSLINUX plugin. VMware builds
    the mboot.c32 plugin to work with SYSLINUX version 3.86 and tests PXE booting only with that version. Other versions
    might be incompatible.*

SYSLINUX packages (all versions) can be found at `<https://mirrors.edge.kernel.org/pub/linux/utils/boot/syslinux/>`_.
While syslinux 4.x still worked for ESXi (as for example syslinux 4.05 on rhel7), latest syslinux 6.x is not compatible
with the ``mboot.c32`` plugin (as for example syslinux 6.04 on rhel8).

Providing cobbler with ``pxelinux.0`` from syslinux 3.86 is therefore needed to pxe boot the ESXi installer.
To avoid overwriting other ``pxelinux.0`` such as the provided via ``cobbler mkloaders`` command, version 3.86 should be placed
on the esxi directory of the `bootloaders_dir`.

The following code snippet shows how to provide cobbler with ``pxelinux.0`` from syslinux version 3.86:

.. code-block:: console

    # Create esxi dir in cobbler bootloaders_dir
    mkdir /var/lib/cobbler/loaders/esxi
    # Obtain syslinux version 3.86
    curl https://mirrors.edge.kernel.org/pub/linux/utils/boot/syslinux/3.xx/syslinux-3.86.tar.gz | tar -zx -C /tmp
    # Copy pxelinux.0
    cp /tmp/syslinux-3.86/core/pxelinux.0 /var/lib/cobbler/loaders/esxi/
    # sync cobbler to copy bootloaders to tftp root
    cobbler sync


During the network boot process:

* the DHCP server will provide the booting host with the IP address of the TFTP server
  and the location of filename ``esxi/pxelinux.0``.
* On the booting host (with MAC address ``01:23:45:67:89:ab``) , PXELINUX will request the file
  ``esxi/pxelinux.cfg/01-01-23-45-67-89-ab``
* that file will provide the kernel tftp path to ``mboot.c32`` (from the distro images link),
  and append the ``boot.cfg`` file for the host:

.. code-block:: console

    cobbler:~ # cat /var/lib/tftpboot/esxi/pxelinux.cfg/01-01-23-45-67-89-ab
    timeout 1
    prompt 0
    default some-esxi-host
    ontimeout some-esxi-host
    LABEL some-esxi-host
        MENU LABEL some-esxi-host
        kernel /images/esxiv70U3d-x86_64/mboot.c32
        append -c system/01-01-23-45-67-89-ab/boot.cfg
        ipappend 2


Booting from UEFI firmware
==========================

The ESXi UEFI bootloader can be found in the ESXi installation iso at ``efi/boot/bootx64.efi``. You will need to provide the
``bootx64.efi`` bootloader to cobbler, renamed as ``mboot.efi``, on the esxi directory of the `bootloaders_dir`.

.. note::
    As stated on VMware docs, *try to provide cobbler with the latest ESXi UEFI bootloader:
    Newer versions of mboot.efi can generally boot older versions of ESXi, but older versions of mboot.efi might be unable to boot
    newer versions of ESXi. If you plan to configure different hosts to boot different versions of the ESXi installer, use the
    mboot.efi from the newest version.*

The following code snippet shows how to provide cobbler with the ``mboot.efi`` bootloader:

.. code-block:: console

    # Create esxi dir in cobbler bootloaders_dir
    mkdir /var/lib/cobbler/loaders/esxi
    # mount your latest ESXi ISO for compatibility
    # example here is VMware-VMvisor-Installer-7.0U3d-19482537.x86_64.iso
    mount -t iso9660 VMware-VMvisor-Installer-7.0U3d-19482537.x86_64.iso /mnt
    # copy to bootloaders_dir/esxi and rename file to mboot.efi
    cp /mnt/efi/boot/bootx64.efi /var/lib/cobbler/loaders/esxi/mboot.efi
    # umount and sync cobbler
    umount /mnt
    cobbler sync

* During the network process, for a system with MAC address ``01:23:45:67:89:ab``, the DHCP server will provide the booting host
  with the IP address of the TFTP server and the location of filename ``esxi/system/01-01-23-45-67-89-ab/mboot.efi``.
* Then ``mboot.efi`` will try to download the ``boot.cfg`` file from the same location: ``esxi/system/01-01-23-45-67-89-ab/boot.cfg``

Booting from iPXE
=================

iPXE can be used to boot the ESXi installer:

* For BIOS firmware, iPXE works chainloading the syslinux ``pxelinux.0`` (from version 3.86). We need to provide cobbbler the
  iPXE ``undionly.kpxe`` driver renamed as ``undionly.pxe`` for consistency with the naming in cobbler.
* For UEFI firmware, iPXE works chainloading the ESXi UEFI bootloader (``mboot.efi``). We need to provide cobbler the iPXE
  ``snponly.efi``. driver.

.. note::
    As iPXE will chainload ``pxelinux.0`` (syslinux version 3.86) for BIOS and ``mboot.efi`` for UEFI,
    you already need to have provided cobbler previously with both.


Some distros already provide a compiled binary of undionly.kpxe and snponly.efi files. This snippet is valid for rhel8 and derivates:

.. code-block:: console

    # This is an example valid for rhel8 and derivates.
    # install ipxe-bootimgs-x86
    dnf -y install ipxe-bootimgs-x86
    # copy undionly.kpxe to bootloaders_dir/esxi and rename file to undionly.pxe
    cp /usr/share/ipxe/undionly.kpxe /var/lib/cobbler/loaders/esxi/undionly.pxe
    # copy ipxe-snponly-x86_64.efi to bootloaders_dir/esxi and rename file to snponly.pxe
    cp /usr/share/ipxe/ipxe-snponly-x86_64.efi /var/lib/cobbler/loaders/esxi/snponly.efi
    # sync cobbler to copy bootloaders to tftp root
    cobbler sync

Another option is obtaining the binaries from source ipxe:

.. code-block:: console

    # obtain source ipxe
    git clone https://github.com/ipxe/ipxe.git
    cd ipxe/src
    # make undionly.kpxe
    make bin/undionly.kpxe
    # copy undionly.kpxe to bootloaders_dir/esxi and rename file to undionly.pxe
    cp bin/undionly.kpxe /var/lib/cobbler/loaders/esxi/undionly.pxe
    # make snponly.efi
    make bin-x86_64-efi/snponly.efi
    # copy snponly.efi to bootloaders_dir/esxi
    cp bin-x86_64-efi/snponly.efi /var/lib/cobbler/loaders/esxi/
    # sync cobbler so bottloaders are copied to tftpboot location
    cobbler sync


iPXE boot can be enabled on a profile or system basis.

.. code-block:: console

    cobbler system edit --name some-esxi-host --enable-ipxe=true

After enabling iPXE, you shoud see a different DHCP configuration for the host.

.. code-block::

    ...
    # group for Cobbler DHCP tag: default
    group {
    ...
        host some-esxi-host.localdomain-vmnic0 {
            hardware ethernet 01:23:45:67:89:ab;
            option host-name "some-esxi-host.localdomain";
            if option system-arch = 00:07 or option system-arch = 00:09 {
                if exists user-class and option user-class = "iPXE" {
                    filename = "esxi/system/01-01-23-45-67-89-ab/mboot.efi";
                } else {
                    filename = "esxi/snponly.efi";
                }
            } else {
                if exists user-class and option user-class = "iPXE" {
                    filename = "esxi/pxelinux.0";
                } else {
                    filename = "esxi/undionly.pxe";
               }
            }
            next-server 192.168.1.1;
        }
    ...
    }

Booting from UEFI HTTP
======================

This is not currently supported.

The boot.cfg file
#################

.. note::
    As stated on VMware docs, *the boot loader configuration file boot.cfg specifies the kernel, the kernel options, and the boot modules that the mboot.c32
    or mboot.efi boot loader uses in an ESXi installation. The boot.cfg file is provided in the ESXi installer. You can modify the
    kernelopt line of the boot.cfg file to specify the location of an installation script or to pass other boot options.*

Cobbler will provide with boot.cfg configuration files from systems and profiles. They are generated via the ``bootcfg.template``.
You can obtain cobbler's boot.cfg file for a system and profile via HTTP API.

Example call for profile (modules shortened for readability)

.. code-block:: console

    cobbler:~ # curl http://localhost/cblr/svc/op/bootcfg/profile/esxiv70U3d-x86_64
    bootstate=0
    title=Loading ESXi installer
    prefix=/images/esxiv70U3d-x86_64
    kernel=b.b00
    kernelopt=runweasel  ks=http://10.4.144.14/cblr/svc/op/autoinstall/profile/esxiv70U3d-x86_64
    modules=jumpstrt.gz --- useropts.gz --- features.gz --- k.b00 --- uc_intel.b00 --- uc_amd.b00 --- uc_hygon.b00
    build=
    updated=0


Example call for system (modules shortened for readability). Note that as system is iPXE enabled, prefix is now an http location.

.. code-block:: console

    cobbler:~ # curl http://localhost/cblr/svc/op/bootcfg/system/some-esxi-host
    bootstate=0
    title=Loading ESXi installer
    prefix=http://10.4.144.14:80/cobbler/links/esxiv70U3d-x86_64
    kernel=b.b00
    kernelopt=runweasel  ks=http://10.4.144.14/cblr/svc/op/autoinstall/system/some-esxi-host
    modules=jumpstrt.gz --- useropts.gz --- features.gz --- k.b00 --- uc_intel.b00 --- uc_amd.b00 --- uc_hygon.b00
    build=
    updated=0


Kernel Options
==============

Kernel options can be added to profiles and to systems. Systems will inherit their profile kernel options.

Example adding a kernel option to profile and system, and the generated boot.cfg file:

.. code-block:: console

    cobbler:~ # cobbler profile edit --name esxiv70U3d-x86_64 --kernel-options="vlanid=203"
    cobbler:~ # cobbler system edit --name some-esxi-host --kernel-options="systemMediaSize=small"
    cobbler:~ # curl http://localhost/cblr/svc/op/bootcfg/system/some-esxi-host
    bootstate=0
    title=Loading ESXi installer
    prefix=http://10.4.144.14:80/cobbler/links/esxiv70U3d-x86_64
    kernel=b.b00
    kernelopt=runweasel vlanid=203 systemMediaSize=small  ks=http://10.4.144.14/cblr/svc/op/autoinstall/system/some-esxi-host
    modules=jumpstrt.gz --- useropts.gz --- features.gz --- k.b00 --- uc_intel.b00 --- uc_amd.b00 --- uc_hygon.b00
    build=
    updated=0


TFTP esxi directory
###################

On the tftp root directory, tree would look like:

.. code-block:: console

    cobbler:~ # tree /var/lib/tftpboot/esxi
    /var/lib/tftpboot/esxi
    ├── images -> ../images
    ├── mboot.efi
    ├── pxelinux.0
    ├── pxelinux.cfg -> ../pxelinux.cfg
    ├── snponly.efi
    ├── system
    │   ├── 01-01-23-45-67-89-ab
    │   │   ├── boot.cfg
    │   │   └── mboot.efi -> ../../mboot.efi
    │   └── 01-98-40-bb-c8-36-00
    │       ├── boot.cfg
    │       └── mboot.efi -> ../../mboot.efi
    └── undionly.pxe

The directory contains:

* Bootloaders and helper files (``pxelinux.0``, ``mboot.efi``, ``undionly.pxe``, ``snponly.efi``)
* Symlink from ``esxi/images`` to ``images``
* Symlink from ``esxi/pxelinux.cfg`` to ``pxelinux.cfg``
* Directory ``system``, with a subdirectory per system mac address. On each system/mac directory, the ``boot.cfg`` file and a
  symlink to ``mboot.efi``.


Useful links
############

* `VMware ESXi 7 Network Boot Install <https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.esxi.install.doc/GUID-44535B01-38CF-4E6D-862A-95EF5ACA3F03.html>`_
* `boot.cfg file description <https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.esxi.upgrade.doc/GUID-1DE4EC58-8665-4F14-9AB4-1C62297D866B.html>`_
* `ESXi boot options <https://docs.vmware.com/en/VMware-vSphere/7.0/com.vmware.esxi.upgrade.doc/GUID-9040F0B2-31B5-406C-9000-B02E8DA785D4.html>`_

