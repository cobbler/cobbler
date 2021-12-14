.. _building-isos:

*************
Building ISOs
*************

Since Cobbler uses the systemd hardening option "PrivateTmp" you can't write or read files from your ``/tmp`` when you
run Cobbler via systemd as a service.

Per default this builds an ISO for all available systems and profiles.

If you want to generate multiple ISOs you need to execute this command multiple times (with different ``--iso`` names).

Under the hood
##############

Under the hood the tool "xorriso" is used. It is being executed in the "mkisofs" (the predecessor) compatibility mode.
Thus we don't execute "mkisofs" anymore. Please be aware of this when adding CLI options.

On the Python side we are executing the following command:

.. code::

   xorriso -as mkisofs $XORRISOFS_OPTS -isohybrid-mbr $ISOHDPFX_location -c isolinux/boot.cat \
     -b isolinux/isolinux.bin -no-emul-boot -boot-load-size 4 -boot-info-table -eltorito-alt-boot \
     -e $EFI_IMG_LOCATION -no-emul-boot -isohybrid-gpt-basdat -V \"Cobbler Install\" \
     -o $ISO $BUILDISODIR

Explanation what this command is doing:

.. code::

   xorriso -as mkisofs \
     -isohybrid-mbr /usr/share/syslinux/isohdpfx.bin \  # --> Makes the image MBR bootable and specifies the MBR File
     -c isolinux/boot.cat \                             # --> Boot Catalog -> Automatically created according to Syslinux wiki
     -b isolinux/isolinux.bin \                         # --> Boot file which is manipulated by mkisofs/xorriso
     -no-emul-boot \                                    # --> Does not run in emulated disk mode when being booted
     -boot-load-size 4 \                                # --> Size of 512 sectors to boot in no-emulation mode
     -boot-info-table \                                 # --> Store CD layout in the image
     -eltorito-alt-boot \                               # --> Allows to have more then one El Torito boot on a CD
     -e /var/lib/cobbler/loaders/grub/x64.efi \         # --> Boot image file which is EFI bootable, relative to root directory
     -no-emul-boot \                                    # --> See above
     -isohybrid-gpt-basdat \                            # --> Add GPT additionally to MBR
     -V "Cobbler Install" \                             # --> Name when the image is recognized by the OS
     -o /root/generated.iso \                           # --> Produced ISO file name and path
     /var/cache/cobbler/buildiso                        # --> Root directory for the build

Common options for building ISOs
################################

* ``--iso``: This defines the name of the built ISO. It defaults to ``autoinst.iso``.
* ``--buildisodir``: The temporary directory where Cobbler will build the ISO. If you have enough RAM to build the ISO
  you should really consider using a tmpfs for performance.
* ``--profiles``: Modify the profiles Cobbler builds ISOs for. If this is omitted, ISOs for all profiles will be built.
* ``--xorrisofs-opts``: The options which are passed to xorriso additionally to the above shown.

Building standalone ISOs
########################

have to provide the following parameters:

* ``--standalone``: If this flag is present, Cobbler will built a partly self-sufficient ISO.
* ``--airgapped``: If this flag is present, Cobbler will built a fully self-sufficient ISO.
* ``--distro``: Modify the distros Cobbler builds ISOs for. If this is omitted, ISOs for all distros will be built.
* ``--source``: The directory with the sources for the image.

Building net-installer ISOs
###########################

You have to provide the following parameters:

* ``--systems``: Filter the systems you want to build the ISO for.
* ``--exclude-dns``: Flag to add the nameservers (and other DNS information) to the append line or not.

Examples
########

Building exactly one network installer ISO for a specific profile (suitable for all underlying systems):

Building exactly one network installer ISO for a specific system:

Building exactly one airgapped installable ISO for a specific system:

Links with further information
##############################

* `xorriso homepage <https://www.gnu.org/software/xorriso/>`_
* `xorriso manpage <https://www.gnu.org/software/xorriso/man_1_xorriso.html>`_
* `mkisofs manpage <https://linux.die.net/man/8/mkisofs>`_
