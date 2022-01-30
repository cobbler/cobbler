***************************
GRUB and everything related
***************************

The directory ``/var/lib/cobbler/grub_config`` contains GRUB boot loader (version 2.02) configuration files.

The directory structure is exactly synced (e.g. via ``cobbler sync``) to the TFTP (or http/www for http network boot)
directory and must be kept as is.

Additional dependencies
#######################

If you wish to generate GRUB2 bootloaders in the EFI format please install the dependencies according to the arches you
wish to boot with your Cobbler installation: ``grub2-ARCH-efi-modules``.

The command "cobbler mkloaders"
###############################

This command can create a bootable GRUB2 bootloader in the EFI format. Thus it collects all modules and creates a
bootable GRUB2 bootloader. The folder where this is executed is not relevant.

To build GRUB bootloaders for other architectures install the packages and then execute the command against the newly
installed directories. openSUSE has enabled you to do this but other distros may not decide to do this. If your distro
does not enable you to do this you need to enable yourself for this. For this you need advanced GRUB knowledge, thus
this is not part of the tutorial.

This command must be ran after every GRUB2 package update.

The command can be manipulated by changing the settings of Cobbler. The following are being used:

* bootloaders_dir
* grub2_mod_dir
* bootloaders_formats
* bootloaders_modules
* syslinux_dir
* syslinux_memdisk_folder
* syslinux_pxelinux_folder
* bootloaders_shim_folder
* bootloaders_shim_file
* bootloaders_ipxe_folder

Current workflow
################

#. Check the settings for above mentioned keys.
#. Create a bootable grubx64.efi loader via ``cobbler mkloaders``
#. In ``/etc/cobbler/settings.yaml`` ``grubconfig_dir`` has to be set to ``/var/lib/cobbler/grub_config``
#. ``cobbler sync`` automatically populates the GRUB configuration directory now in the TFTP root folder
#. On your DHCP server, point option 67 (``filename``) to ``grubx64.efi`` (assuming you have configured the other
   options already)

When you want to use cloud init with the new subiquity installer in Ubuntu 20.04, please keep in mind that the nocloud
source has to be quoted in GRUB, otherwise it won't work. For syslinux however, the nocloud source mustn't be quoted!
That said, currently you can't use cloud init profiles for Ubuntu 20.04 simultaneously in both Syslinux and GRUB.

IMPORTANT FILES
###############

config/grub
===========

``grub.cfg``
++++++++++++

This file in the main TFTP directory is a fallback for broken firmware. Normally GRUB should already set the prefix to
the directory where it has been loaded from (GRUB subdirectory in our case). It is known for (specific versions?) KVM
and ppc64le that GRUB may end up loading this as first ``grub.cfg``. We simply set ``prefix="grub"`` and manually load
the main config file ``grub/grub.cfg``.

``grub/grub.cfg``
+++++++++++++++++

This is the main entry point for all architectures. We always load this config file.

``grub/grub/local_*.cfg``
+++++++++++++++++++++++++

This are the architecture specific config files providing local (hard disk) boot entries. These may need adjusting over
the time, depending how distributions name their ``*.efi`` executable for local boot.

``grub/grub/system/*``
++++++++++++++++++++++

Empty directory where Cobbler will sync machine specific configuration (typically setting local boot or an
(auto-)install menu entry). These are named after the mac address of a machine, e.g.: ``grub/system/52:54:00:42:07:04``
This config file is tried to be loaded from the main ``grub.cfg``.

``grub/grub/system_link.*``
+++++++++++++++++++++++++++

Empty directory where Cobbler will create symlinks, named after the Cobbler name of the machine and it links to above
described mac address file in ``../system/${mac}`` This is only for easier reading and debugging of machine specific
GRUB settings.


/var/lib/cobbler/loaders
========================

This directory holds network bootloaders (or links to them) and is also synced to ``/srv/tftp`` root directory 1 to 1.

It creates GRUB executables for each installed grub2-$arch via: ``grub2-mkimage`` and links in the corresponding GRUB2
modules and other supported bootloaders (``pxelinux.0``, ...)

If you have installed e.g. a new GRUB or Syslinux version, you should re-run ``cobbler mkloaders`` to build new GRUB
executables. For other, static or already compiled/linked bootloaders like, shim, ``pxelinux.0`` or a precompiled,
signed ``grub.efi`` executable, it is enough to call ``cobbler sync`` now (we store links to these now).

The GRUB specific files generated/linked via ``cobbler mkloaders`` are also described here:

``.cobbler_postun_cleanup``
+++++++++++++++++++++++++++

Filled up with generated ``grub2-mkimage`` binaries and created links.

This is needed in ``postun`` ``cobbler.spec`` section to remove things again. This is the only, not synced file.

``grub/grub.0``
+++++++++++++++

- 32 bit PXE (x86 legacy) GRUB executable.
- ``grub2-mkimage`` generated.
- This can/should be used instead of ``pxelinux.0``. You then get the full grub boot process.
- The bootloader is named ``grub.0``, because ``pxelinux.0`` can chain boot this grub executable via network. But it
  (or specific versions?) wants bootloaders with a filename ending on ``.0``.

``grub/{grubaa64.efi,grub.ppc64le,grubx64.efi}``
++++++++++++++++++++++++++++++++++++++++++++++++

Also ``grub2-mkimage`` generated, architecture specific GRUB executables. These, can directly be network booted on the
corresponding/matching architecture. Please have a look at the ``dhcpd.conf`` template for getting an idea how
architecture differing (via DHCP request network packets) works.

On ``grub-${arch}`` package updates, please call ``cobbler mkloaders`` to get up-to-date executables. The names of these
executables are derived from GRUB2 sources. These are the default names as they should get generated on all
distributions by default. These map to ``${grub-cpu}-${grub-platform}`` as seen below the modules directory structure.
Unfortunately this does not map 1 to 1.

``grub/{arm64-efi,i386-pc,powerpc-ieee1275,x86_64-efi}``
++++++++++++++++++++++++++++++++++++++++++++++++++++++++

Links to architecture specific GRUB modules. From these ``grub2-mkimage`` generates above executables.

These directories (where the links point to) have to be named exactly like this. GRUB may download missing/needed
modules from ``/srv/tftp/${prefix}/${grub-cpu}-${grub-platform}`` on the fly as needed.

E.g. using the ``grub.cfg`` command: hello, will end up in downloading ``hello.mod`` then doing automatically an
``insmod hello``...

``grub/{grub.efi,shim.efi}``
++++++++++++++++++++++++++++

- Links to precompiled from distribution provided and signed shim and GRUB EFI executables.
- By default ``shim.efi`` is used in UEFI (x86 at least) case.
- ``shim.efi`` automatically tries to load ``grub.efi``.
- Module loading via network using a signed ``grub.efi`` loader, does not work.
- All GRUB modules need ``grub.cfg`` and later sourced config files must be present in the signed ``grub.efi``
  executable.
- For example the "tr" GRUB module was not part of SLES 12 and therefore the reforming of the ``${mac}`` address to the
  previous ``pxelinux.0`` style, e.g.: ``52:54:00:42:56:58`` -> ``01-52-54-00-42-56-58`` does not work. But this is
  overhead anyway, so we now use the plain mac address as filenames for system specific grub configuration.
