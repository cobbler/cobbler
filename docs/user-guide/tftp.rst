******************
The TFTP Directory
******************

For booting machines in a PXE and/or HTTP-Boot environment the TFTP directory is the most important directory. This
folder contains all static files required for booting a system.

The folder of this is dependant on your distro and can be changed in the Cobbler settings. The default should be
correctly set during the package build of your Linux distro or during the installation process (if you are use the
source installation).

Behaviour
#########

A good explanation of ``cobbler sync`` can be found here: :ref:`cli-cobbler-sync`

In the following we will examine the behaviour for the TFTP directory more in details.

#. ``cobbler sync`` is executed (we assume a full one for now).
#. The pre-sync triggers are executed.
#. If the following directories do not exist they are created:
    #. ``pxelinux.cfg``
    #. ``grub``
    #. ``images``
    #. ``ipxe``
    #. A symlink from ``grub/images`` to ``images``
#. The content of in above mentioned directories is being fully deleted.
#. All bootloaders are being copied
#. All kernel and initrds are being copied
#. All images (if created) are being copied
#. The PXE menu is being generated and written to disk
#. The post-sync triggers are being executed

.. note:: If you only sync DHCP, DNS or specific systems the order and actions might be slightly different.

.. warning:: A ``cobbler sync`` is not required. Due to the file copying of a lot of small files this is a very
             expensive operation. Under normal operation Cobbler should move the files automatically to the right
             places. Only use this command when you encounter problems.

Layout
######

This is how an example TFTP-Boot Directory could look like. In the following sections we will cover the details of the
files and folders.

.. code-block::

    cobbler:~ # ls -alh /srv/tftpboot/
    total 105M
    drwxr-xr-x 17 root   root  327 Dez 17 14:29 .
    drwxr-xr-x  4 root   root   44 Mär  3  2021 ..
    drwxr-xr-x  8 root   root 4,0K Nov 18 14:30 grub
    -rw-r--r--  1 root   root  429 Okt 21 16:13 grub.cfg
    drwxr-xr-x 36 root   root 4,0K Jan 10 14:20 images
    -rw-r--r--  1 root   root  96M Jan 28  2021 initrd
    drwxr-xr-x  2 root   root   26 Dez  1 15:12 ipxe
    -rw-r--r--  1 root   root 8,6M Jan 28  2021 linux
    -rw-r--r--  1 root   root  26K Mär 17  2021 memdisk
    -rw-r--r--  1 root   root  54K Mär 17  2021 menu.c32
    drwxr-xr-x  2 root   root   24 Dez 11  2020 others
    -rw-r--r--  1 root   root  26K Mär 17  2021 pxelinux.0
    drwxr-xr-x  2 root   root  20K Jan 17 13:02 pxelinux.cfg


All files or folders not covered by below explanations are specific to the environment the directory listing was taken
from. Those files should not be touched by Cobbler and should survive even a ``cobbler sync``.

* ``tftpboot/grub/``: Contains the GRUB bootloaders and additional configuration not covered by ``tftpboot/grub.cfg``.
  If available this directory will also contain the ``shim.efi`` file.
* ``tftpboot/grub/system``: Normally contains the GRUB config for the MAC in the filename.

.. note:: In case Cobbler is not able to find a MAC for the interface it tries to generate an entry for, it applies
          a fallback strategy. First it tries the IP address. If that was not successful, it finally uses the name if no
          IP address is known to Cobbler.

* ``tftpboot/grub.cfg``: Rescue config file which serves as a pointer on the client side because the error message shows
  that this is the wrong location for the ``grub.cfg`` file. GRUB should always try to load ``tftpboot/grub/grub.cfg``.
* ``tftpboot/images/<distro>/``: Contains always the kernel and initrd of the distro you add to Cobbler. During a
  ``cobbler sync`` all folder with distros will be deleted and the structure will be recreated by the paths saved in the
  ``kernel`` and ``initrd`` attributes in a Cobbler distro item.
* ``tftpboot/ipxe/default.ipxe``: Cobbler will generate the iPXE menu for you. This is the file where all menu entries
  will be stored. It will be overwritten regularly by either a change in a distro or by the command ``cobbler sync``.
* ``tftpboot/pxelinux.0``: The binary for executing the pxelinux bootloader. This is taken from your system at
  ``cobbler sync`` time.
* ``tftpboot/pxelinux.cfg``: Normally this directory contains two types of files
    #. The configuration for each system where the file name is the MAC of the system.
    #. The file named ``default`` which is used for all PXE Clients not known by MAC address.

.. note:: In case Cobbler is not able to find a MAC for the interface it tries to generate an entry for, it falls back
          first to the IP and finally uses the name if no IP is known to Cobbler.
