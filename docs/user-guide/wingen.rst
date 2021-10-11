.. _wingen:

*******************************************
Automatic Windows installation with Cobbler
*******************************************

One of the challenges for creating your own Windows network installation scenario with Cobbler is preparing the necessary files in a Linux environment. However, generating the necessary binaries can be greatly simplified by using the cobbler post trigger on the sync command. Below is an example of such a trigger, which prepares the necessary files for legacy BIOS mode boot. Boot to UEFI Mode with iPXE is simpler and can be implemented by replacing the first 2 steps and several others with creating an iPXE boot menu.

Trigger ``sync_post_wingen.py``:

- some of the files are created from standard ones (``pxeboot.n12``, ``bootmgr.exe``) by directly replacing one string with another directly in the binary
- in the process of changing the ``bootmgr.exe`` file, the checksum of the PE file will change and it needs to be recalculated. The trigger does this with ``python-pefile``
- ``python3-hivex`` is used to modify Windows boot configuration data (BCD). For pxelinux distro boot_loader in BCD, paths to ``winpe.wim`` and ``boot.sdi`` are generated as ``/images/<distro_name>``, and for iPXE with wimboot - ``\Boot``.
- uses ``wimlib-tools`` to replace ``startnet.cmd startup`` script in WIM image

Windows answer files (``autounattended.xml``) are generated using Cobbler templates, with all of its conditional code generation capabilities, depending on the Windows version, architecture (32 or 64 bit), installation profile, etc.

startup scripts for WIM images (startnet.cmd) and a script that is launched after OS installation (``post_install.cmd``) are also generated from templates

Post-installation actions such as installing additional software, etc., are performed using the Automatic Installation Template (``win.ks``).

A logically automatic network installation of Windows 7 and newer can be represented as follows:

PXE + Legacy BIOS Boot

.. code::

    Original files: pxeboot.n12 → bootmgr.exe → BCD → winpe.wim → startnet.cmd → autounattended.xml
    Cobbler profile 1: pxeboot.001 → boot001.exe → 001 → wi001.wim → startnet.cmd → autounatten001.xml → post_install.cmd profile_name
    ...

iPXE + UEFI Boot

.. code::

    Original files: ipxe-x86_64.efi → wimboot → bootmgr.exe → BCD → winpe.wim → startnet.cmd → autounattended.xml
    Cobbler profile 1: ipxe-x86_64.efi → wimboot → bootmgr.exe → 001 → wi001.wim → startnet.cmd → autounatten001.xml → post_install.cmd profile_name
    ...

For older versions (Windows XP, 2003) + RIS:

.. code::

    Original files: pxeboot.n12 → setupldr.exe → winnt.sif → post_install.cmd profile_name
    Cobbler profile <xxx>: pxeboot.<xxx> → setup<xxx>.exe → wi<xxx>.sif → post_install.cmd profile_name

Additional Windows metadata
===========================

Additional metadata for preparing Windows boot files can be passed through the ``--autoinstall-meta`` option for distro, profile or system.
The source files for Windows boot files should be located in the ``/var/www/cobbler/distro_mirror/<distro_name>/Boot`` directory. The trigger copies them to ``/var/lib/tftpboot/images/<distro_name>`` with the new names specified in the metadata and and changes their contents. The resulting files will be available via tftp and http.

The ``sync_post_wingen`` trigger uses the following set of metadata:

- kernel

    ``kernel`` in autoinstall-meta is only used if the boot kernel is ``pxeboot.n12`` (``--kernel=/path_to_kernel/pxeboot.n12`` in distro).
    In this case, the trigger copies the ``pxeboot.n12`` file into a file with a new name and replaces:
    - ``bootmgr.exe`` substring in it with the value passed through the ``bootmgr`` metadata key in case of using Micrisoft ADK/WAIK.
    - ``NTLDR`` substring in it with the value passed through the ``bootmgr`` metadata key in case of using Legacy RIS.
    Value of the ``kernel`` key in ``autoinstall-meta`` will be the actual first boot file.
    If ``--kernel=/path_to_kernel/wimboot`` is in distro, then ``kernel`` key is not used in ``autoinstall-meta``.

- bootmgr

    The bootmgr key value is passed the name of the second boot file in the Windows boot chain. The source file to create it can be:
    - ``bootmgr.exe`` in case of using Micrisoft ADK/WAIK
    - ``setupldr.exe`` for Legacy RIS

    Trigger copies the corresponding source file to a file with the name given by this key and replaces in it:
    - substring ``\Boot\BCD`` to ``\Boot\<bcd_value>``, where ``<bcd_value>`` is the metadata ``bcd`` key value for Micrisoft ADK/WAIK.
    - substring ``winnt.sif`` with the value passed through the ``answerfile`` metadata key in case of using Legacy RIS.

- bcd

    This key is used to pass the value of the ``BCD`` file name in case of using Micrisoft ADK/WAIK. Any ``BCD`` file from the Windows distribution can be used as a source for this file. The trigger copies it, then removes all boot information from the copy and adds new data from the ``initrd`` value of the distro and the value passed through the ``winpe`` metadata key.

- winpe

    This metadata key allows you to specify the name of the WinPE image. The image is copied by the cp utility trigger with the ``--reflink=auto`` option, which allows to reduce copying time and the size of the disk space on CoW file systems.
    In the copy of the file, the tribger changes the ``/Windows/System32/startnet.cmd`` script to the script generated from the ``startnet.template`` template.

- answerfile

    This is the name of the answer file for the Windows installation. This file is generated from the ``answerfile.template`` template and is used in:
    - ``startnet.cmd`` to start WinPE installation
    - the file name is written to the binary file ``setupldr.exe`` for RIS

- post_install_script

    This is the name of the script to run immediately after the Windows installation completes. The script is specified in the Windows answer file. All the necessary completing the installation actions can be performed directly in this script, or it can be used to get and start additional steps from ``http://<server>/cblr/svc/op/autoinstall/<profile|system>/name``.
    To make this script available after the installation is complete, the trigger creates it in ``/var/www/cobbler/distro_mirror/<distro_name>/$OEM$/$1`` from the ``post_inst_cmd.template`` template.

The following metadata does not specify boot file names and is an example of using metadata to generate files from Cobbler templates.

- clean_disk

    The presence of this key in the metadata (regardless of its value) leads to the preliminary deletion of all data and the disk partition table before installing the OS.
    Used in the ``answerfile.template`` and also in ``startnet.template`` in Windows XP and Windows 2003 Server installations using WinPE.

Preparing for an unattended network installation of Windows
===========================================================

- ``dnf install python3-pefile python3-hivex wimlib-utils``
- enable Windows support in settings ``/etc/cobbler/settings.d/windows.settings``:

.. code::

    windows_enabled: true

- import the Windows distributions to ``/var/www/cobbler/distro_mirror``:

.. code::

    cobbler import --name=Win10_EN-x64 --path=/mnt

This command will determine the version and architecture of the Windows distribution, will extract the necessary boot files from the distribution and create a distro and profile named ``Win10_EN-x64``.

- For customization winpe.win you need
  - ADK for Windows 10 / 8.1

.. code::

    Start -> Apps -> Windows Kits -> Deployment and Imaging Tools Environment

or

  - WAIK for Windows 7

.. code::

    Start -> All Programs -> Microsoft Windows AIK -> Deployment Tools Command Prompt

.. code::

    copype.cmd <amd64|x86|arm> c:\winpe

After executing the command, the WinPE image will be located in ``.\winpe.wim`` for WAIK and in ``media\sources\boot.wim`` for ADK. You can use either it or replace it with the one that has been obtained as a result of the import of the Windows distribution.

  - If necessary, add drivers to the image

Example:

.. code-block:: shell

    dism /mount-wim /wimfile:media\sources\boot.wim /index:1 /mountdir:mount
    dism /image:mount /add-driver /driver:D:\NetKVM\w10\amd64
    dism /image:mount /add-driver /driver:D:\viostor\w10\amd64
    dism /unmount-wim /mountdir:mount /commit

- Copy the resulting WiNPE image from Windows to the ``boot`` directory of the distro
- Share ```/var/www/cobbler/distro_mirror``` via Samba:

.. code-block:: shell

    vi /etc/samba/smb.conf
            [DISTRO]
            path = /var/www/cobbler/distro_mirror
            guest ok = yes
            browseable = yes
            public = yes
            writeable = no
            printable = no


- You can use ``tftpd.rules`` to indicate the actual locations of the ``bootmgr.exe`` and ``BCD`` files generated by the trigger.

.. code-block:: shell

    cp /usr/lib/systemd/system/tftp.service /etc/systemd/system

Replace the line in the ``/etc/systemd/system/tftp.service``

.. code::

    ExecStart=/usr/sbin/in.tftpd -s /var/lib/tftpboot
        to:
    ExecStart=/usr/sbin/in.tftpd -m /etc/tftpd.rules -s /var/lib/tftpboot

Create a file ``/etc/tftpd.rules``:

.. code-block:: shell

    vi /etc/tftpd.rules
    rg	\\					/ # Convert backslashes to slashes
    r	(wine.\.sif)				/WinXp_EN-i386/\1
    r	(xple.)					/WinXp_EN-i386/\1

    r	(wi2k.\.sif)				/Win2k3-Server_EN-x64/\1
    r	(w2k3.)					/Win2k3-Server_EN-x64/\1

    r	(boot7e.\.exe)				/images/Win7_EN-x64/\1
    r	(/Boot/)(7E.)				/images/Win7_EN-x64/\2

    r	(boot28.\.exe)				/images/Win2k8-Server_EN-x64/\1
    r	(/Boot/)(28.)				/images/Win2k8-Server_EN-x64/\2

    r   (boot9r.\.exe)				/images/Win2019-Server_EN-x64/\1
    r   (/Boot/)(9r.)				/images/Win2019-Server_EN-x64/\2

    r	(boot6e.\.exe)				/images/Win2016-Server_EN-x64/\1
    r	(/Boot/)(6e.)				/images/Win2016-Server_EN-x64/\2

    r	(boot2e.\.exe)				/images/Win2012-Server_EN-x64/\1
    r	(/Boot/)(2e.)				/images/Win2012-Server_EN-x64/\2

    r	(boot81.\.exe)				/images/Win8_EN-x64/\1
    r	(/Boot/)(B8.)				/images/Win8_EN-x64/\2

    r	(boot1e.\.exe)				/images/Win10_EN-x64/\1
    r	(/Boot/)(1E.)				/images/Win10_EN-x64/\2

    r	(.*)(/WinXp...-i386/)(.*)		/images\2\L\3
    r	(.*)(/Win2k3-Server_EN-x64/)(.*)	/images\2\L\3

    r	(.*)(bootxea.exe)			/images/WinXp_EN-i386/\2
    r	(.*)(XEa)				/images/WinXp_EN-i386/\2

    r	(.*)(boot3ea.exe)			/images/Win2k3-Server_EN-x64/\2
    r	(.*)(3Ea)				/images/Win2k3-Server_EN-x64/\2

Final steps
===========

- Restart the services:

.. code-block:: shell

    systemctl daemon-reload
    systemctl restart tftp
    systemctl restart smb
    systemctl restart nmb

- add additional distros for PXE boot:

.. code-block:: shell

    cobbler distro add --name=Win10_EN-x64 \
    --kernel=/var/www/cobbler/distro_mirror/Win10_EN-x64/boot/pxeboot.n12 \
    --initrd=/var/www/cobbler/distro_mirror/Win10_EN-x64/boot/boot.sdi \
    --arch=x86_64 --breed=windows --os-version=10

or for iPXE:

.. code-block:: shell

    cobbler distro add --name=Win10_EN-x64 \
    --kernel=/var/lib/tftpboot/wimboot \
    --initrd=/var/www/cobbler/distro_mirror/Win10_EN-x64/boot/boot.sdi \
    --remote-boot-kernel=http://@@http_server@@/cobbler/images/@@distro_name@@/wimboot \
    --remote-boot-initrd=http://@@http_server@@/cobbler/images/@@distro_name@@/boot.sdi \
    --arch=x86_64 --breed=windows --os-version=10 \
    --boot-loaders=ipxe

- and additional profiles for PXE boot:

.. code-block:: shell

    cobbler profile add --name=Win10_EN-x64 --distro=Win10_EN-x64 --autoinstall=win.ks \
    --autoinstall-meta='kernel=win10a.0 bootmgr=boot1ea.exe bcd=1Ea winpe=winpe.wim answerfile=autounattended.xml'

    cobbler profile add --name=Win10-profile1 --parent=Win10_EN-x64 \
    --autoinstall-meta='kernel=win10b.0 bootmgr=boot1eb.exe bcd=1Eb winpe=winp1.wim answerfile=autounattende1.xml'

    cobbler profile add --name=Win10-profile2 --parent=Win10_EN-x64 \
    --autoinstall-meta='kernel=win10c.0 bootmgr=boot1ec.exe bcd=1Ec winpe=winp2.wim answerfile=autounattende2.xml'

The boot menu will look like this:

.. code-block:: shell

        LABEL Win10_EN-x64
                MENU LABEL Win10_EN-x64
                kernel /images/Win10_EN-x64/win10a.0
        LABEL Win10_EN-x64-profile1
                MENU LABEL Win10_EN-x64-profile1
                kernel /images/Win10_EN-x64/win10b.0
        LABEL Win10_EN-x64-profile1
                MENU LABEL Win10_EN-x64-profile2
                kernel /images/Win10_EN-x64/win10c.0

or for iPXE:

.. code-block:: shell

    cobbler profile add --name=Win10_EN-x64 --distro=Win10_EN-x64 --autoinstall=win.ks \
    --autoinstall-meta='bootmgr=boot1ea.exe bcd=1Ea winpe=winpe.wim answerfile=autounattended.xml' \
    --boot-loaders=ipxe

    cobbler profile add --name=Win10-profile1 --parent=Win10_EN-x64 \
    --autoinstall-meta='bootmgr=boot1eb.exe bcd=1Eb winpe=winp1.wim answerfile=autounattende1.xml' \
    --boot-loaders=ipxe

    cobbler profile add --name=Win10-profile2 --parent=Win10_EN-x64 \
    --autoinstall-meta='bootmgr=boot1ec.exe bcd=1Ec winpe=winp2.wim answerfile=autounattende2.xml' \
    --boot-loaders=ipxe

The boot menu will look like this:

.. code-block:: shell

    :Win10_EN-x64
    kernel http://<http_server>/cobbler/images/Win10_EN-x64/wimboot
    initrd --name boot.sdi http://<http_server>/cobbler/images/Win10_EN-x64/boot.sdi boot.sdi
    initrd --name bootmgr.exe http://<http_server>/cobbler/images/Win10_EN-x64/boot1ea.exe bootmgr.exe
    initrd --name bcd http://<http_server>/cobbler/images/Win10_EN-x64/1Ea bcd
    initrd --name winpe.wim http://<http_server>/cobbler/images/Win10_EN-x64/winpe.wim winpe.wim
    boot

    :Win10_EN-x64-profile1
    kernel http://<http_server>/cobbler/images/Win10_EN-x64/wimboot
    initrd --name boot.sdi http://<http_server>/cobbler/images/Win10_EN-x64/boot.sdi boot.sdi
    initrd --name bootmgr.exe http://<http_server>/cobbler/images/Win10_EN-x64/boot1eb.exe bootmgr.exe
    initrd --name bcd http://<http_server>/cobbler/images/Win10_EN-x64/1Eb bcd
    initrd --name winpe.wim http://<http_server>/cobbler/images/Win10_EN-x64/winp1.wim winpe.wim
    boot

    :Win10_EN-x64-profile2
    kernel http://<http_server>/cobbler/images/Win10_EN-x64/wimboot
    initrd --name boot.sdi http://<http_server>/cobbler/images/Win10_EN-x64/boot.sdi boot.sdi
    initrd --name bootmgr.exe http://<http_server>/cobbler/images/Win10_EN-x64/boot1ec.exe bootmgr.exe
    initrd --name bcd http://<http_server>/cobbler/images/Win10_EN-x64/1Ec bcd
    initrd --name winpe.wim http://<http_server>/cobbler/images/Win10_EN-x64/winp2.wim winpe.wim
    boot

- cobbler sync

  - kernel from ``autoinstall-meta`` of profile or from ``kernel`` of distro property will be copied to ``/var/lib/tftpboot/<distro_name>``
  - if the kernel is ``pxeboot.n12``, then the ``bootmgr.exe`` substring is replaced in the copied copy of kernel with the value passed via ``bootmgr`` of the ``autoinstall-meta`` profile propery

- Install Windows

Legacy Windows XP and Windows 2003 Server
=========================================

- WinPE 3.0 and winboot can be used to install legacy versions of Windows. ``startnet.template`` contains the code for starting such an installation via ``winnt32.exe``.

  - copy ``bootmgr.exe``, ``bcd``, ``boot.sdi`` from Windows 7 and ``winpe.wim`` from WAIK to the ``/var/www/cobbler/distro_mirror/WinXp_EN-i386/boot``

.. code-block:: shell

    cobbler distro add --name=WinXp_EN-i386 \
    --kernel=/var/lib/tftpboot/wimboot \
    --initrd=/var/www/cobbler/distro_mirror/WinXp_EN-i386/boot/boot.sdi \
    --remote-boot-kernel=http://@@http_server@@/cobbler/images/@@distro_name@@/wimboot \
    --remote-boot-initrd=http://@@http_server@@/cobbler/images/@@distro_name@@/boot.sdi \
    --arch=i386 --breed=windows --os-version=XP \
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
    --arch=i386 --breed=windows --os-version=XP \
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
    --arch=i386 --breed=windows –os-version=XP

    cobbler distro add --name=Win2k3-Server_EN-x64 \
    --kernel=/var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/boot/pxeboot.n12 \
    --initrd=/var/www/cobbler/distro_mirror/Win2k3-Server_EN-x64/boot/boot.sdi \
    --boot-files='@@local_img_path@@/i386/=@@web_img_path@@/[ia][3m][8d]6*/*.*' \
    --arch=x86_64 --breed=windows --os-version=2003

    cobbler profile add --name=WinXp_EN-i386 --distro=WinXp_EN-i386 --autoinstall=win.ks \
    --autoinstall-meta='kernel=wine0.0 bootmgr=xple0 answerfile=wine0.sif'

    cobbler profile add --name=Win2k3-Server_EN-x64 --distro=Win2k3-Server_EN-x64 --autoinstall=win.ks \
    --autoinstall-meta='kernel=w2k0.0 bootmgr=w2k3l answerfile=wi2k3.sif'
