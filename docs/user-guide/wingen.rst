.. _wingen:

*********************************
Windows installation with Cobbler
*********************************

Supported installation options:

* UEFI iPXE install (via ipxe-shimx64.efi, ipxe.efi and wimboot tftp/http)
* BIOS iPXE install (via ipxe undionly.kpxe and wimboot tftp/http)
* BIOS PXE install (via syslinux pxelinux.0, linux.c32 and wimboot tftp/http)
* BIOS PXE install (via grub2 grub.0 and wimboot tftp/http)
* BIOS PXE install (via windows pxeboot.n12)

Installation Quickstart guide
#############################

* ``dnf install python3-pefile python3-hivex wimlib-utils``
* enable Windows support in settings ``/etc/cobbler/settings.d/windows.settings``:

.. code::

    windows_enabled: true

* Share ``/var/www/cobbler`` via Samba:

.. code-block::

    vi /etc/samba/smb.conf
            [DISTRO]
            path = /var/www/cobbler
            guest ok = yes
            browseable = yes
            public = yes
            writeable = no
            printable = no

* import the Windows distro:

.. code:: shell

    cobbler import --name=win11 --path=/mnt

This command will determine the version and architecture of the Windows distribution, extract the files ``pxeboot.n12``, ``bootmgr.exe``, ``winpe.wim``
from the distro into the ``/var/www/cobbler/distro_mirror/win11/boot`` and create a distro and profile named ``win11-x86_64``.

Customization winpe.wim
=======================

For customization winpe.win you need ADK for Windows.

.. code::

    Start -> Apps -> Windows Kits -> Deployment and Imaging Tools Environment

You can use either ``winpe.wim`` obtained either as a result of cobbler import, or take it from ADK:

.. code:: shell

    copype.cmd <amd64|x86|arm> c:\winpe

If necessary, add drivers to the image:

.. code-block:: shell

    dism /mount-wim /wimfile:media\sources\boot.wim /index:1 /mountdir:mount
    dism /image:mount /add-driver /driver:D:\NetKVM\w11\amd64
    dism /image:mount /add-driver /driver:D:\viostor\w11\amd64
    dism /unmount-wim /mountdir:mount /commit

Copy the resulting WinPE image from Windows to the ``/var/www/cobbler/distro_mirror/win11/boot`` directory of the distro.

UEFI Secure Boot (SB)
#####################

For SB you can use ``ipxe-shimx64.efi`` (unsigned), ``ipxe.efi`` (unsigned) and ``wimboot`` (signed with a Microsoft key).
Therefore, in this case, we will need our own keys in order to sign ``ipxe-shimx64.efi``, ``ipxe.efi`` and computer fimware with them.

Creating Secure Boot Keys
=========================

.. code-block:: shell

    export NAME="DEMO"
    openssl req -new -x509 -newkey rsa:2048 -subj "/CN=$NAME PK/" -keyout PK.key \
            -out PK.crt -days 3650 -nodes -sha256
    openssl req -new -x509 -newkey rsa:2048 -subj "/CN=$NAME KEK/" -keyout KEK.key \
            -out KEK.crt -days 3650 -nodes -sha256
    openssl req -new -x509 -newkey rsa:2048 -subj "/CN=$NAME DB/" -keyout DB.key \
            -out DB.crt -days 3650 -nodes -sha256

    export GUID=`python3 -c 'import uuid; print(str(uuid.uuid1()))'`
    echo $GUID > myGUID.txt

Provide cobbler with bootloaders
================================

.. code-block:: shell

    wget https://github.com/ipxe/shim/releases/download/ipxe-15.7/ipxe-shimx64.efi
    wget https://boot.ipxe.org/ipxe.iso
    wget https://github.com/ipxe/wimboot/releases/latest/download/wimboot -P /var/lib/cobbler/loaders

    mkdir -p /mnt/{cdrom,disk}
    mount -o loop,ro ipxe.iso /mnt/cdrom
    mount -o loop,ro /mnt/cdrom/esp.img /mnt/disk

Signing EFI Binaries and replacing keys in firmware
===================================================

Signing the bootloaders:

.. code-block:: shell

    sbsign --key DB.key --cert DB.crt --output /var/lib/cobbler/loaders/ipxe-shimx64.efi ipxe-shimx64.efi
    sbsign --key DB.key --cert DB.crt --output /var/lib/cobbler/loaders/ipxe.efi /mnt/disk/EFI/BOOT/BOOTX64.EFI
    cobbler sync

Sign the computer firmware with your keys. For VM it can be done like this:

.. code-block:: shell

    rpm -ql python3-virt-firmware | grep '\.pem$'
        /usr/lib/python3.9/site-packages/virt/firmware/certs/CentOSSecureBootCA2.pem
        /usr/lib/python3.9/site-packages/virt/firmware/certs/CentOSSecureBootCAkey1.pem
        /usr/lib/python3.9/site-packages/virt/firmware/certs/MicrosoftCorporationKEKCA2011.pem
        /usr/lib/python3.9/site-packages/virt/firmware/certs/MicrosoftCorporationUEFICA2011.pem
        /usr/lib/python3.9/site-packages/virt/firmware/certs/MicrosoftWindowsProductionPCA2011.pem
        /usr/lib/python3.9/site-packages/virt/firmware/certs/RedHatSecureBootCA3.pem
        /usr/lib/python3.9/site-packages/virt/firmware/certs/RedHatSecureBootCA5.pem
        /usr/lib/python3.9/site-packages/virt/firmware/certs/RedHatSecureBootCA6.pem
        /usr/lib/python3.9/site-packages/virt/firmware/certs/RedHatSecureBootPKKEKkey1.pem
        /usr/lib/python3.9/site-packages/virt/firmware/certs/fedoraca-20200709.pem

    virt-fw-vars \
        --input /usr/share/edk2/ovmf/OVMF_VARS.fd \
        --output /var/lib/libvirt/qemu/nvram/win11_VARS.fd \
        --set-pk  ${GUID} PK.crt \
        --add-kek ${GUID} KEK.crt \
        --add-kek 77fa9abd-0359-4d32-bd60-28f4e78f784b /usr/lib/python3.9/site-packages/virt/firmware/certs/MicrosoftCorporationKEKCA2011.pem \
        --add-db  ${GUID} DB.crt \
        --add-db  77fa9abd-0359-4d32-bd60-28f4e78f784b /usr/lib/python3.9/site-packages/virt/firmware/certs/MicrosoftWindowsProductionPCA2011.pem \
        --add-db  77fa9abd-0359-4d32-bd60-28f4e78f784b /usr/lib/python3.9/site-packages/virt/firmware/certs/MicrosoftCorporationUEFICA2011.pem

Booting from UEFI iPXE HTTP
###########################

Change ``dhcpd.conf`` to use ``ipxe-shimx64.efi``:

.. code-block::

     class "pxeclients" {
          match if substring (option vendor-class-identifier, 0, 9) = "PXEClient";
          next-server 192.168.126.1;

          if exists user-class and option user-class = "iPXE" {
              filename "/ipxe/default.ipxe";
          }
          # UEFI-64-1
          else if option system-arch = 00:07 {
              filename "ipxe-shimx64.efi";
          }

The HTTP protocol is used by default in the profile created with the ``cobbler import`` command:

.. code-block:: shell

    cobbler profile report --name=win11-x86_64 | grep Metadata
        Automatic Installation Metadata :
            {'kernel': 'http://@@http_server@@/images/win11-x86_64/wimboot',
             'bootmgr': 'bootmgr.exe',
             'bcd': 'bcd',
             'winpe': 'winpe.wim',
             'answerfile': 'autounattended.xml',
             'post_install_script': 'post_install.cmd'}

.. code-block:: shell

    cat /var/lib/tftpboot/ipxe/default.ipxe
    :win11-x86_64
    kernel http://192.168.124.1/images/win11-x86_64/wimboot
    initrd --name boot.sdi  http://192.168.124.1/cobbler/images/win11-x86_64/boot.sdi boot.sdi
    initrd --name bootmgr.exe  http://192.168.124.1/cobbler/images/win11-x86_64/bootmgr.exe bootmgr.exe
    initrd --name bcd  http://192.168.124.1/cobbler/images/win11-x86_64/bcd bcd
    initrd --name winpe.wim  http://192.168.124.1/cobbler/images/win11-x86_64/winpe.wim winpe.wim

Booting from BIOS firmware
##########################

Booting from BIOS iPXE (via ipxe undionly.kpxe and wimboot tftp/http)
=====================================================================

Change ``dhcpd.conf`` to use ``undionly.kpxe``:

.. code-block::

     class "pxeclients" {
          match if substring (option vendor-class-identifier, 0, 9) = "PXEClient";
          next-server 192.168.126.1;

          if exists user-class and option user-class = "iPXE" {
              filename "/ipxe/default.ipxe";
          }
          else if option system-arch = 00:00 {
              filename "undionly.pxe";
          }

Import distro

.. code:: shell

    cobbler import --name=win10 --path=/mnt

By default, an EFI partition is created for the profile ``win10-x86_64`` in the answerfile, and for BIOS boot we can create a profile with ``uefi=False`` in the metadata:

.. code:: shell

    cobbler profile copy \
        --name=win10-x86_64 \
        --newname=win10-bios-pxe-wimboot-http-x86_64 \
        --autoinstall-meta="kernel=http://@@http_server@@/images/win10-x86_64/wimboot bootmgr=bootmg2.exe bcd=bc2 winpe=winp2.wim answerfile=autounattende2.xml uefi=False"
    cobbler sync

If you do not want to use the HTTP protocol, you can either change an existing profile or create a new one with ``kernel=wimboot`` in the metadata:

.. code:: shell

    cobbler profile copy \
        --name=win10-x86_64
        --newname=win10-bios-ipxe-wimboot-tftp-x86_64 \
        --autoinstall-meta="kernel=wimboot bootmgr=bootmg3.exe bcd=bc3 winpe=winp3.wim answerfile=autounattende3.xml uefi=False"
    cobbler sync

.. code:: shell

    cat /var/lib/tftpboot/ipxe/default.ipxe
    :win10-bios-ipxe-wimboot-tftp-x86_64
    kernel /images/win10-x86_64/wimboot
    initrd --name boot.sdi  /images/win10-x86_64/boot.sdi boot.sdi
    initrd --name bootmgr.exe  /images/win10-x86_64/bootmg3.exe bootmgr.exe
    initrd --name bcd  /images/win10-x86_64/bc3 bcd
    initrd --name winp3.wim  /images/win10-x86_64/winp3.wim winp3.wim
    boot

Booting from BIOS PXE (via syslinux pxelinux.0, linux.c32 and wimboot tftp/http)
=================================================================================

The ``win10-bios-pxe-wimboot-http-x86_64`` and ``win10-bios-ipxe-wimboot-tftp-x86_64`` profiles created earlier are suitable for this boot method.
You just need to change ``dhcpd.conf`` to boot via ``pxelinux.0``.

.. code-block::

     class "pxeclients" {
          match if substring (option vendor-class-identifier, 0, 9) = "PXEClient";
          next-server 192.168.126.1;

          if exists user-class and option user-class = "iPXE" {
              filename "/ipxe/default.ipxe";
          }
          else if option system-arch = 00:00 {
              filename "pxelinux.0";
          }

.. code-block:: shell

    cat /var/lib/tftpboot/pxelinux.cfg/default
    LABEL win10-bios-ipxe-wimboot-tftp-x86_64
        MENU LABEL win10-bios-ipxe-wimboot-tftp-x86_64
        kernel linux.c32
        append /images/win10-x86_64/wimboot initrdfile=/images/win10-x86_64/boot.sdi@boot.sdi initrdfile=/images/win10-x86_64/bootmg3.exe@bootmgr.exe initrdfile=/images/win10-x86_64/bc3@bcd initrdfile=/images/win10-x86_64/winp3.wim@winp3.wim
    LABEL win10-bios-pxe-wimboot-http-x86_64
        MENU LABEL win10-bios-pxe-wimboot-http-x86_64
        kernel linux.c32
        append http://192.168.124.1/images/win10-x86_64/wimboot initrdfile=http://192.168.124.1/cobbler/images/win10-x86_64/boot.sdi@boot.sdi initrdfile=http://192.168.124.1/cobbler/images/win10-x86_64/bootmg2.exe@bootmgr.exe initrdfile=http://192.168.124.1/cobbler/images/win10-x86_64/bc2@bcd initrdfile=http://192.168.124.1/cobbler/images/win10-x86_64/winp2.wim@winp2.wim


Booting from BIOS PXE (via grub2 grub.0 and wimboot tftp/http)
==============================================================

The ``win10-bios-pxe-wimboot-http-x86_64`` and ``win10-bios-ipxe-wimboot-tftp-x86_64`` profiles created earlier also suitable for this boot method.
You just need to change ``dhcpd.conf`` to boot via ``grub/grub.0``.

.. code-block::

     class "pxeclients" {
          match if substring (option vendor-class-identifier, 0, 9) = "PXEClient";
          next-server 192.168.126.1;

          if exists user-class and option user-class = "iPXE" {
              filename "/ipxe/default.ipxe";
          }
          else if option system-arch = 00:00 {
              filename "grub/grub.0";
          }

.. code-block:: shell

    cat /var/lib/tftpboot/grub/x86_64_menu_items.cfg
    menuentry 'win10-bios-ipxe-wimboot-tftp-x86_64' --class gnu-linux --class gnu --class os {
      echo 'Loading kernel ...'
      clinux /images/win10-x86_64/wimboot
      echo 'Loading initial ramdisk ...'
      cinitrd  newc:boot.sdi:/images/win10-x86_64/boot.sdi newc:bootmgr.exe:/images/win10-x86_64/bootmg3.exe newc:bcd:/images/win10-x86_64/bc3 newc:winp3.wim:/images/win10-x86_64/winp3.wim
      echo '...done'
    }
    menuentry 'win10-bios-pxe-wimboot-http-x86_64' --class gnu-linux --class gnu --class os {
      echo 'Loading kernel ...'
      clinux (http,192.168.124.1)/images/win10-x86_64/wimboot
      echo 'Loading initial ramdisk ...'
      cinitrd  newc:boot.sdi:(http,192.168.124.1)/cobbler/images/win10-x86_64/boot.sdi newc:bootmgr.exe:(http,192.168.124.1)/cobbler/images/win10-x86_64/bootmg2.exe newc:bcd:(http,192.168.124.1)/cobbler/images/win10-x86_64/bc2 newc:winp2.wim:(http,192.168.124.1)/cobbler/images/win10-x86_64/winp2.wim
      echo '...done'
    }

Booting from  BIOS PXE install (via windows pxeboot.n12)
========================================================

This is the only boot method that does not require ``wimboot``.
Booting can be done via syslinux (pxelinux.0) or ipxe (undionly.kpxe).

Create a file ``/etc/tftpd.rules``:

.. code-block::

    rg	\\					/ # Convert backslashes to slashes
    r	(boot1e.\.exe)				/images/win10-x86_64/\1
    r	(/Boot/)(1E.)				/images/win10-x86_64/\2

Change the tftp service

.. code-block:: shell

    cp /usr/lib/systemd/system/tftp.service /etc/systemd/system

Replace the line in the ``/etc/systemd/system/tftp.service``

.. code-block::

    ExecStart=/usr/sbin/in.tftpd -s /var/lib/tftpboot
        to:
    ExecStart=/usr/sbin/in.tftpd -m /etc/tftpd.rules -s /var/lib/tftpboot

Restart the tftp:

.. code-block:: shell

    systemctl daemon-reload
    systemctl restart tftp

Create a new profile

.. code-block:: shell

    cobbler profile copy \
        --name=win10-x86_64 \
        --newname=win10-bios-syslinux-tftp-x86_64 \
        --autoinstall-meta="kernel=win10a.0 bootmgr=boot1ea.exe bcd=1Ea winpe=winp5.wim answerfile=autounattende5.xml uefi=False"
    cobbler sync

Boot entries were created for this profile:

.. code-block:: shell

    cat /var/lib/tftpboot/pxelinux.cfg/default
    LABEL win10-bios-syslinux-tftp-x86_64
        MENU LABEL win10-bios-syslinux-tftp-x86_64
        kernel /images/win10-x86_64/win10a.0

    cat /var/lib/tftpboot/ipxe/default.ipxe
    :win10-bios-syslinux-tftp-x86_64
    kernel /images/win10-x86_64/win10a.0
    initrd /images/win10-x86_64/boot.sdi
    boot

Additional Windows metadata
###########################

Additional metadata for preparing Windows boot files can be passed through the ``--autoinstall-meta`` option for distro, profile or system.
The source files for Windows boot files should be located in the ``/var/www/cobbler/distro_mirror/<distro_name>/Boot`` directory.
The trigger copies them to ``/var/lib/tftpboot/images/<distro_name>`` with the new names specified in the metadata and and changes their contents.
The resulting files will be available via tftp and http.

The ``sync_post_wingen`` trigger uses the following set of metadata:

* kernel

    ``kernel`` in autoinstall-meta is only used if the boot kernel is ``pxeboot.n12`` (``--kernel=/path_to_kernel/pxeboot.n12`` in distro).
    In this case, the trigger copies the ``pxeboot.n12`` file into a file with a new name and replaces:

    - ``bootmgr.exe`` substring in it with the value passed through the ``bootmgr`` metadata key in case of using Micrisoft ADK.
    - ``NTLDR`` substring in it with the value passed through the ``bootmgr`` metadata key in case of using Legacy RIS.

    Value of the ``kernel`` key in ``autoinstall-meta`` will be the actual first boot file.
    If ``--kernel=/path_to_kernel/wimboot`` is in distro, then ``kernel`` key is not used in ``autoinstall-meta``.

* bootmgr

    The bootmgr key value is passed the name of the second boot file in the Windows boot chain. The source file to create it can be:

    - ``bootmgr.exe`` in case of using Micrisoft ADK
    - ``setupldr.exe`` for Legacy RIS

    Trigger copies the corresponding source file to a file with the name given by this key and replaces in it:

    - substring ``\Boot\BCD`` to ``\Boot\<bcd_value>``, where ``<bcd_value>`` is the metadata ``bcd`` key value for Micrisoft ADK.
    - substring ``winnt.sif`` with the value passed through the ``answerfile`` metadata key in case of using Legacy RIS.

* bcd

    This key is used to pass the value of the ``BCD`` file name in case of using Micrisoft ADK. Any ``BCD`` file from the Windows distribution can be used as a source for this file.
    The trigger copies it, then removes all boot information from the copy and adds new data from the ``initrd`` value of the distro and the value passed through the ``winpe`` metadata key.

* winpe

    This metadata key allows you to specify the name of the WinPE image. The image is copied by the cp utility trigger with the ``--reflink=auto`` option,
    which allows to reduce copying time and the size of the disk space on CoW file systems.
    In the copy of the file, the tribger changes the ``/Windows/System32/startnet.cmd`` script to the script generated from the ``startnet.template`` template.

* answerfile

    This is the name of the answer file for the Windows installation. This file is generated from the ``answerfile.template`` template and is used in:

    - ``startnet.cmd`` to start WinPE installation
    - the file name is written to the binary file ``setupldr.exe`` for RIS

* post_install_script

    This is the name of the script to run immediately after the Windows installation completes.
    The script is specified in the Windows answer file. All the necessary completing the installation actions can be performed directly in this script,
    or it can be used to get and start additional steps from ``http://<server>/cblr/svc/op/autoinstall/<profile|system>/name``.
    To make this script available after the installation is complete, the trigger creates it in ``/var/www/cobbler/distro_mirror/<distro_name>/$OEM$/$1`` from the ``post_inst_cmd.template`` template.

Legacy Windows XP and Windows 2003 Server
#########################################

- WinPE 3.0 and winboot can be used to install legacy versions of Windows. ``startnet.template`` contains the code for starting such an installation via ``winnt32.exe``.

  - copy ``bootmgr.exe``, ``bcd``, ``boot.sdi`` from Windows 7 and ``winpe.wim`` from WAIK to the ``/var/www/cobbler/distro_mirror/WinXp_EN-i386/boot``

.. code-block:: shell

    cobbler distro add --name=WinXp_EN-i386 \
    --kernel=/var/lib/tftpboot/wimboot \
    --initrd=/var/www/cobbler/distro_mirror/WinXp_EN-i386/boot/boot.sdi \
    --remote-boot-kernel=http://@@http_server@@/cobbler/images/@@distro_name@@/wimboot \
    --remote-boot-initrd=http://@@http_server@@/cobbler/images/@@distro_name@@/boot.sdi \
    --arch=i386 --breed=windows --os-version=xp \
    --boot-loaders=ipxe --autoinstall-meta='clean_disk'

    cobbler distro add --name=Win2k3-Server_EN-x64 \
    --kernel=/var/lib/tftpboot/wimboot \
    --initrd=/var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/boot/boot.sdi \
    --remote-boot-kernel=http://@@http_server@@/cobbler/images/@@distro_name@@/wimboot \
    --remote-boot-initrd=http://@@http_server@@/cobbler/images/@@distro_name@@/boot.sdi \
    --arch=x86_64 --breed=windows --os-version=2003 \
    --boot-loaders=ipxe --autoinstall-meta='clean_disk'

    cobbler profile add --name=WinXp_EN-i386 --distro=WinXp_EN-i386 --autoinstall=win.ks \
    --autoinstall-meta='bootmgr=bootxea.exe bcd=XEa winpe=winpe.wim answerfile=wine0.sif post_install_script=post_install.cmd'

    cobbler profile add --name=Win2k3-Server_EN-x64 --distro=Win2k3-Server_EN-x64 --autoinstall=win.ks \
    --autoinstall-meta='bootmgr=boot3ea.exe bcd=3Ea winpe=winpe.wim answerfile=wi2k3.sif post_install_script=post_install.cmd'

- WinPE 3.0 without ``winboot`` also can be used to install legacy versions of Windows.

  - copy ``pxeboot.n12``, ``bootmgr.exe``, ``bcd``, ``boot.sdi`` from Windows 7 and ``winpe.wim`` from WAIK to the ``/var/www/cobbler/distro_mirror/WinXp_EN-i386/boot``

.. code-block:: shell

    cobbler distro add --name=WinXp_EN-i386 \
    --kernel=/var/www/cobbler/distro_mirror/WinXp_EN-i386/boot/pxeboot.n12 \
    --initrd=/var/www/cobbler/distro_mirror/WinXp_EN-i386/boot/boot.sdi \
    --arch=i386 --breed=windows --os-version=xp \
    --autoinstall-meta='clean_disk'

    cobbler distro add --name=Win2k3-Server_EN-x64 \
    --kernel=/var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/boot/pxeboot.n12 \
    --initrd=/var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/boot/boot.sdi \
    --arch=x86_64 --breed=windows --os-version=2003 \
    --autoinstall-meta='clean_disk'

    cobbler profile add --name=WinXp_EN-i386 --distro=WinXp_EN-i386 --autoinstall=win.ks \
    --autoinstall-meta='kernel=wine0.0 bootmgr=bootxea.exe bcd=XEa winpe=winpe.wim answerfile=wine0.sif post_install_script=post_install.cmd'

    cobbler profile add --name=Win2k3-Server_EN-x64 --distro=Win2k3-Server_EN-x64 --autoinstall=win.ks \
    --autoinstall-meta='kernel=w2k0.0 bootmgr=boot3ea.exe bcd=3Ea winpe=winpe.wim answerfile=wi2k3.sif post_install_script=post_install.cmd'

- Although the ris-linux package is no longer supported, it also can still be used to install older Windows versions.

For example on Fedora 33:

.. code-block:: shell

    dnf install chkconfig python27
    dnf install ris-linux --releasever=24 --repo=updates,fedora
    dnf install python3-dnf-plugin-versionlock
    dnf versionlock add ris-linux
    sed -i -r 's/(python)/\12/g' /sbin/ris-linuxd
    sed -i -r 's/(\/winos\/inf)\//\1/g' /etc/sysconfig/ris-linuxd
    sed -i -r 's/(\/usr\/share\/ris-linux\/infparser.py)/python2 \1/g' /etc/rc.d/init.d/ris-linuxd
    sed -i 's/p = p + chr(252)/#&/g' /usr/share/ris-linux/binlsrv.py
    mkdir -p /var/lib/tftpboot/winos/inf

To support 64 bit distributions:

.. code-block:: shell

    cd /sbin
    ln -s ris-linux ris-linux64
    cd /etc/sysconfig
    cp ris-linuxd ris-linuxd64
    sed -i -r 's/(linuxd)/\164/g' ris-linuxd64
    sed -i -r 's/(inf)/\164/g' ris-linuxd64
    sed -i -r 's/(BINLSRV_OPTS=)/\1--port=4012/g' ris-linuxd64
    cd /etc/rc.d/init.d
    cp ris-linuxd ris-linuxd64
    sed -i -r 's/(linuxd)/\164/g' ris-linuxd64
    sed -i -e 's/RIS/RIS64/g' ris-linuxd64
    systemctl daemon-reload
    mkdir -p /var/lib/tftpboot/winos/inf64

copy the Windows network drivers to ``/var/lib/tftpboot/winos/inf[64]`` and start ``ris-linuxd[64]``:

.. code-block:: shell

    systemctl start ris-linuxd
    systemctl start ris-linuxd64

Preparing boot files for RIS and legacy Windows XP and Windows 2003 Server
==========================================================================

.. code-block:: shell

    dnf install cabextract
    cd /var/www/cobbler/distro_mirror/<distro_name>
    mkdir boot
    cp i386/ntdetect.com /var/lib/tftpboot
    cabextract -dboot i386/setupldr.ex_

If you need to install Windows 2003 Server in addition to Windows XP, then to avoid a conflict, you can rename the ``ntdetect.com`` file:

.. code-block:: shell

    mv /var/lib/tftpboot/ntdetect.com /var/lib/tftpboot/ntdetect.wxp
    sed -i -e 's/ntdetect\.com/ntdetect\.wxp/g' boot/setupldr.exe

    cp /var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/i386/ntdetect.com /var/lib/tftpboot/ntdetect.2k3
    sed -i -e 's/ntdetect\.com/ntdetect\.2k3/g' /var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/boot/setupldr.exe
    sed -bi "s/\x0F\xAB\x00\x00/\x0F\xAC\x00\x00/" /var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/boot/setupldr.exe

.. code-block:: shell

    cabextract -dboot i386/startrom.n1_
    mv Boot/startrom.n12 boot/pxeboot.n12
    touch boot/boot.sdi

Copy the required drivers to the ``i386``

.. code-block:: shell

    cobbler distro add --name=WinXp_EN-i386 \
    --kernel=/var/www/cobbler/distro_mirror/WinXp_EN-i386/boot/pxeboot.n12 \
    --initrd=/var/www/cobbler/distro_mirror/WinXp_EN-i386/boot/boot.sdi \
    --boot-files='@@local_img_path@@/i386/=@@web_img_path@@/i386/*.*' \
    --arch=i386 --breed=windows –os-version=xp

    cobbler distro add --name=Win2k3-Server_EN-x64 \
    --kernel=/var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/boot/pxeboot.n12 \
    --initrd=/var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/boot/boot.sdi \
    --boot-files='@@local_img_path@@/i386/=@@web_img_path@@/[ia][3m][8d]6*/*.*' \
    --arch=x86_64 --breed=windows --os-version=2003

    cobbler profile add --name=WinXp_EN-i386 --distro=WinXp_EN-i386 --autoinstall=win.ks \
    --autoinstall-meta='kernel=wine0.0 bootmgr=xple0 answerfile=wine0.sif'

    cobbler profile add --name=Win2k3-Server_EN-x64 --distro=Win2k3-Server_EN-x64 --autoinstall=win.ks \
    --autoinstall-meta='kernel=w2k0.0 bootmgr=w2k3l answerfile=wi2k3.sif'

Useful links
############

 `Managing EFI Boot Loaders for Linux: Controlling Secure Boot <https://www.rodsbooks.com/efi-bootloaders/controlling-sb.html>`_
