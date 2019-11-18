******************
Distribution Notes
******************

Cobbler was originally written to support Fedora, Red Hat, and derivative distributions such as CentOS or Scientific
Linux. Cobbler now works for managing other environments, including mixed environments, occasionally with some
limitations. Debian/Ubuntu and SuSE support is quite strong, with patches coming in from developers working on those
distributions as well.

However, in some cases (especially for newer distribution versions), a little extra work may be required after an import
in order to make things work smoothly.

Nexenta
#######

Installing NexentaStor with Cobbler
===================================

The following steps outline the Nexenta install process when using Cobbler.

1) Assuming that Cobbler has been setup previously, verify that the signature file contains the entry for Nexenta:

.. code-block:: JSON

    {
        "nexenta": {
            "4": {
                "signatures":["boot"],
                "version_file": "platform",
                "version_file_regex": null,
                "supported_arches":["x86_64"],
                "supported_repo_breeds":["apt"],
                "kernel_file":"platform/i86pc/kernel/amd64/unix",
                "initrd_file":"platform/i86pc/amd64/miniroot",
                "isolinux_ok":false,
                "kernel_options":"",
                "kernel_options_post":"",
                "boot_files":[]
            }
        }
    }

2) Obtain a Nexenta iso from http://www.nexenta.com/corp/nexentastor-download and mount it:

.. code-block:: bash

    mkdir -p /mnt/nexenta4 && mnt /path/to/nexenta4.iso /mnt/nexenta4 -o loop`

3) Import the distribution into Cobbler:

.. code-block:: bash

    cobbler import --name=nexenta-4 --path=/mnt/nexenta4

Verify that a Nexenta distirbution is available via Cobbler: ``cobbler list`` Once the import is done, you can
unmount the ISO:

.. code-block:: bash

    sudo umount /mnt/nexenta4

4) Nexenta uses a PXE Grub executable different from other, linux-like systems. To install a Nexenta on a desired
   system, you have to specify the PXE Grub file for that system. This can be done by using either a MAC address, or a
   subnet definition in your DHCP configuration file. In ``/etc/cobbler/dhcp.template``:

.. code-block:: bash

    host test-1 {
        hardware ethernet 00:0C:29:10:B6:10;
        fixed-address 10.3.30.91;
        filename "boot/grub/pxegrub";
    }
    host test-2 {
        hardware ethernet 00:0c:29:d1:9c:26;
        fixed-address 10.3.30.97;
        filename "boot/grub/pxegrub";
    }

OR if you are installing only Nexenta on all machines on a subnet, you may use the subnet definition instead of host
definition in your dhcp config file.

.. note:: The path ``boot/grub/pxegrub`` is a hardcoded default in the Nexenta boot process.

5) In order the have unmanned installation, an installation profile must be created for each booted Nexenta system. The
   profiles are placed in ``/var/lib/cobbler/kickstarts/install_profiles``. Each profile should be a file with the
   filename ``machine.AACC003355FF`` where AA..FF stand for the mac address of the machine, without `:` (columns). The
   contents of each profile should look like the following:

.. code-block:: bash

    __PF_gateway="IP address" (required)
    __PF_nic_primary="NIC NAME" (required)
    __PF_dns_ip_1="IP address" (required)
    __PF_dns_ip_2="IP address" (optional)
    __PF_dns_ip_3="IP address" (optional)
    __PF_loghost="IP address" (optional)
    __PF_logport="Port Number" (optional)
    __PF_syspool_luns="list of space separated LUNs that will be used to create syspool" (required)
    __PF_syspool_spare="list of space separated LUNs that will be used as syspool spare" (optional)
    __PF_ipaddr_NIC_NAME="IP address" (NIC_NAME is the name of the target NIC e1000g0, ixgbe1, etc.) (required)
    __PF_netmask_NIC_NAME="NETMASK" (NIC_NAME is the name of the target NIC e1000g0, ixgbe1, etc.) (required)
    __PF_nlm_key="LICENSE KEY" (required)
    __PF_language="en" (used to choose localzation, but now only "en" is supported) (required)
    __PF_ssh_enable=1 (enable SSH, by default SSH is disabled) (optional)
    __PF_ssh_port="PORT where SSH server will wait for incoming connections" (optional)

6) Power on the hardware. NexentaStor should boot from this setup.

Hints & Notes
=============

This process has been tested with Cobbler Release 2.8.0 running on Ubuntu 12.04 LTS.

The install of Nexenta is automatic. That means that each machine to be booted with nexenta has to be configurated with
a profile in kickstarts/install_profiles directory. To boot Nexenta nodes manually, in the file
``/var/lib/tftpboot/boot/grub/menu.lst`` replace the line:

.. code-block:: bash

    kernel$ /images/nexenta-a-x86_64/platform/i86pc/kernel/amd64/unix -B iso_nfs_path=10.3.30.95:/var/www/cobbler/links/nexenta-a-x86_64,auto_install=1

With

.. code-block:: bash

    kernel$ /images/nexenta-a-x86_64/platform/i86pc/kernel/amd64/unix -B iso_nfs_path=10.3.30.95:/var/www/cobbler/links/nexenta-a-x86_64

If you are adding a new distro, don't forget to enable NFS access to it! NFS share must be configured on the boot
server. In particular, the directories in ``/var/www/cobbler/links/<distro-name>`` are exported. As an example, there is
a ``/etc/exports`` file:

.. code-block:: bash

    # /etc/exports: the access control list for filesystems which may be exported
    #    to NFS clients.  See exports(5).
    #
    # Example for NFSv2 and NFSv3:
    # /srv/homes       hostname1(rw,sync,no_subtree_check) hostname2(ro,sync,no_subtree_check)
    #
    # Example for NFSv4:
    # /srv/nfs4        gss/krb5i(rw,sync,fsid=0,crossmnt,no_subtree_check)
    # /srv/nfs4/homes  gss/krb5i(rw,sync,no_subtree_check)
    #
    /var/www/cobbler/links/nexenta-a-x86_64 *(ro,sync,no_subtree_check)
    /var/www/cobbler/links/<nexenta-distribution-name> *(ro,sync,no_subtree_check)

FreeBSD
#######

The following steps are required to enable FreeBSD support in Cobbler.

You can grab the patches and scripts from the following github repos:
`jsabo/cobbler_misc <git://github.com/jsabo/cobbler_misc.git>`_

This would not be possible without the help from Doug Kilpatrick. Thanks Doug!

Stuff to do once
================

* Install FreeBSD with full sources

  * Select "Standard" installation
  * Use entire disk
  * Install a standard MBR
  * Create a new slice and use the entire disk
  * Mount it at ``/``
  * Choose the "Developer" distribution

    * Full sources, binaries and doc but no games

  * Install from a FreeBSD CD/DVD
  * Setup networking to copy files back and forth
  * In the post install "Package Selection" scroll down and select shells

    * Install bash
    * ``chsh -s /usr/local/bin/bash username`` or ``vipw``

* Rebuild pxeboot with tftp support

.. code-block:: bash

    cd /sys/boot
    make clean
    make LOADER_TFTP_SUPPORT=yes
    make install

* Copy the pxeboot file to the Cobbler server.

Stuff to do every supported release
===================================

* Patch sysinstall with http install support
* The media location is hard coded in this patch and has to be updated every release. Just look for 8.X and change it.
  The standard sysinstall doesn't really support HTTP. This patch adds full http support to sysinstall.

.. code-block:: bash

    cd /usr
    patch -p0 < /root/http_install.patch

* Rebuild FreeBSD mfsroot: We'll use ``crunchgen`` to create the contents of /stand in a ramdisk image. Crunchgen
  creates a single statically linked binary that acts like different normal binaries depending on how it's called. We
  need to include ``fetch`` and a few other binaries. This is a multi step process.

.. code-block:: bash

    mkdir /tmp/bootcrunch
    cd /tmp/bootcrunch
    crunchgen -o /root/boot_crunch.conf
    make -f boot_crunch.mk

Once we've added our additional binaries we need to create a larger ramdisk.

* Create a new, larger ramdisk, and mount it.

.. code-block:: bash

    dd if=/dev/zero of=/tmp/mfsroot bs=1024 count=$((1024 * 5))
    dev0=`mdconfig -f /tmp/mfsroot`;newfs $dev0;mkdir /mnt/mfsroot_new;mount /dev/$dev0 /mnt/mfsroot_new

* Mount the standard installer's mfsroot

.. code-block:: bash

    mkdir /mnt/cdrom; mount -t cd9660 -o -e /dev/acd0 /mnt/cdrom
    cp /mnt/cdrom/boot/mfsroot.gz /tmp/mfsroot.old.gz
    gzip -d /tmp/mfsroot.old.gz; dev1=`mdconfig -f /tmp/mfsroot.old`
    mkdir /mnt/mfsroot_old; mount /dev/$dev1 /mnt/mfsroot_old

Copy everything from the old one to the new one. You'll be replacing the binaries, but it's simpler to just copy it
all over.

.. code-block:: bash

    (cd /mnt/mfsroot_old/; tar -cf - .) | (cd /mnt/mfsroot_new; tar -xf -)

Next copy over the new bootcrunch file and create all of the symlinks after removing the old binaries.

.. code-block:: bash

    cd /mnt/mfsroot_new/stand; rm -- *; cp /tmp/bootcrunch/boot_crunch ./
    for i in $(./boot_crunch 2>&1|grep -v usage);do if [ "$i" != "boot_crunch" ];then rm -f ./"$i";ln ./boot_crunch "$i";fi;done

Sysinstall uses install.cfg to start the install off. We've created a version of the install.cfg that uses fetch to pull
down another configuration file from the Cobbler server which allows us to dynamically control the install. install.cfg
uses a script called "doconfig.sh" to determine where the Cobbler installer is via the DHCP next-server field.

Copy both install.cfg and doconfig.sh into place.

.. code-block:: bash

    cp {install.cfg,doconfig.sh} /mnt/mfsroot_new/stand

Now just unmount the ramdisk and compress the file

.. code-block:: bash

    umount /mnt/mfsroot_new; umount /mnt/mfsroot_old
    mdconfig -d -u $dev0; mdconfig -d -u $dev1
    gzip /tmp/mfsroot

Copy the mfsroot.gz to the Cobbler server.

Stuff to do in Cobbler
======================

* Enable Cobbler's tftp server in modules.conf

.. code-block:: yaml

    [tftpd]
    module = manage_tftpd_py

* Mount the media

.. code-block:: bash

    mount /dev/cdrom /mnt

* Import the distro

.. code-block:: bash

    cobbler import --path=/mnt/ --name=freebsd-8.2-x86_64

* Copy the mfsroot.gz and the pxeboot.bs into the distro

.. code-block:: bash

    cp pxeboot.bs /var/www/cobbler/ks_mirror/freebsd-8.2-x86_64/boot/
    cp mfsroot.gz /var/www/cobbler/ks_mirror/freebsd-8.2-x86_64/boot/

* Configure a system to use the profile, turn on netboot, and off you go.

DHCP will tell the system to request ``pxelinux.0``, so it will. Pxelinux will request it's configuration file, which
will have ``pxeboot.bs`` as the "kernel". Pxelinux will request ``pxeboot.bs``, use the extention (``.bs``) to realize
it's another boot loader, and chain to it. Pxeboot will then request all the ``.rc``, ``.4th``, the kernel, and
``mfsroot.gz``. It will mount the ramdisk and start the installer. The installer will connect back to the Cobbler server
to fetch the ``install.cfg`` (the kickstart file), and do the install as instructed, rebooting at the end.
