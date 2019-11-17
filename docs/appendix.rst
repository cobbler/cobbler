********
Appendix
********

S390 Support
############

Introduction
============

Cobbler includes support for provisioning Linux on virtualized guests under z/VM, the System z hypervisor.

Quickstart Guide
================

To begin, you need to first configure a Cobbler server. Cobbler can be run on any Linux system accessible by the
mainframe, including an x86 system or another System z guest. This server's primary responsibility is to host the Linux
install tree(s) remotely, and maintain information about clients accessing it. For detailed instructions on configuring
the Cobbler server read the Cobbler manual.

We will assume static networking is used for System z guests.

After the Cobbler server is running, and you have imported at least one s390x install tree, you can customize the
default kickstart template. Cobbler provides a sample kickstart template that you can start with called
``/var/lib/cobbler/kickstarts/sample.ks``. You will want to copy this sample, and modify it by adding the following
snippet in ``%post``:

.. code-block:: bash

    $SNIPPET('post_s390_reboot')

Next, it's time to add a system to Cobbler. Unlike traditional PXE, where unknown clients are identified by MAC
address, zPXE uses the z/VM user ID to distinguish systems. For example, to add a system with z/VM user ID ''z01'':

.. code-block:: bash

    cobbler system add --name z01 \
    --hostname=z01.example.com --ip-address=10.10.10.100 --subnet=10.10.10.255 --netmask=255.255.255.0 \
    --name-servers=10.10.10.1 --name-servers-search=example.com:example2.com \
    --gateway=10.10.10.254 --kopts="LAYER2=0 NETTYPE=qeth PORTNO=0 cms=None \
    HOSTNAME=z01.example.com IPADDR=10.10.10.100 SUBCHANNELS=0.0.0600,0.0.0601,0.0.0602 \
    MTU=1500 BROADCAST=10.10.10.255 SEARCHDNS=example.com:example2.com \
    NETMASK=255.255.255.0 DNS=10.10.10.1 PORTNAME=UNASSIGNED \
    DASD=100-101,200 GATEWAY=10.10.10.254 NETWORK=10.10.10.0"


Most of the options to ``cobbler system add`` are self explanatory network parameters. They are fully explained in the
cobbler man page (see ``man cobbler``). The ``--kopts`` option is used to specify System z specific kernel options
needed by the installer. These are the same parameters found in the PARM or CONF file of a traditional installation, and
in fact will be placed into a PARM file used by zPXE. For any parameters not specified with ``--kopts``, the installer
will prompt you during kickstart in the 3270 console. For a truly non-interactive installation, make sure to specify at
least the parameters listed above.

Now that you've added a system to Cobbler, it's time to configure zPXE, the Cobbler-specific System z PXE emulator
client, which ships with Cobbler. zPXE is designed to replace PROFILE EXEC for a System z guest. Alternatively, you can
simply call ZPXE EXEC from your existing PROFILE EXEC. The following example assumes the z/VM FTP server is running;
however, you can also FTP from z/VM to the cobbler server. Transfer zpxe.rexx to z/VM:

.. code-block:: bash

    # cd /var/lib/cobbler
    # ftp zvm.example.com
    ==> ascii
    ==> put zpxe.rexx zpxe.exec
    ==> bye


Next, logon to z/VM, and backup the current PROFILE EXEC and rename ZPXE EXEC:

.. code-block:: bash

    ==> rename profile exec a = execback =
    ==> rename zpxe exec a profile = =


Finally, you need to create a ZPXE CONF to specify the cobbler server hostname, as well as the default disk to IPL. Use
xedit to create this file. It has only two lines.

.. code-block:: bash

    ==> xedit zpxe conf a

    00000 * * * Top of File * * *
    00001 HOST example.server.com
    00002 IPLDISK 100
    00003 * * * End of File * * *

zPXE is now configured. The client will attempt to contact the server at each logon. If there is a system record
available, and it is set to be reinstalled, zPXE will download the necessary files and begin the kickstart.

To schedule an install, run the following command on the cobbler server:

.. code-block:: bash

    cobbler system edit --name z01 --netboot-enabled 1 --profile RHEL-5-Server-U1-s390x


Internals: How It Works
=======================

Now let's take a look at how zPXE works. First, it defines a 50 MB VDISK, which is large enough to hold a kernel and
initial RAMdisk, and enough free space to convert both files to 80-character width fixed record length. Since VDISK is
used, zPXE does not require any writeable space on the user's 191(A) disk. This makes it possible to use zPXE as a
read-only PROFILE EXEC shared among many users.

Next, the client uses the z/VM TFTP client to contact the server specified in ZPXE CONF. It attempts to retrieve, in the
following order:

1. /s390x/s_systemname, if found, the following files will be downloaded:
    * /s390x/s_systemname_parm
    * /s390x/s_systemname_conf
2. /s390x/profile_list

When netboot is enabled on the cobbler server, it places a file called ``s_systemname`` (where ``systemname`` is a z/VM
user ID) into ``/var/lib/tftpboot/s390x/`` which contains the following lines:

.. code-block:: bash

    /images/RHEL-5-Server-U3-s390x/kernel.img
    /images/RHEL-5-Server-U3-s390x/initrd.img
    ks=http://cobbler.example.com/cblr/svc/op/ks/system/z01

The file parameter file (``s_systemname_parm``) is intended for kernel options, and may also contain network-specific
information for the guest. The config file (``s_systemname_conf``) is intended for CMS specific configuration. It is
currently unused, as the parm file contains everything necessary for install. However, it is maintained as a placeholder
for additional functionality.

A sample parameter file looks like this:

.. code-block:: bash

    LAYER2=0 NETTYPE=qeth PORTNO=0 ip=False MTU=1500
    SEARCHDNS=search.example.com DNS=192.168.5.1 GATEWAY=192.168.5.254
    DASD=100-101,200 NETWORK=192.168.5.0 RUNKS=1 cmdline root=/dev/ram0
    HOSTNAME=server.example.com IPADDR=192.168.5.2
    SUBCHANNELS=0.0.0600,0.0.0601,0.0.0602 BROADCAST=192.168.5.255
    NETMASK=255.255.255.0 PORTNAME=UNASSIGNED ramdisk_size=40000 ro cms

NOTE: The parameter file has several restrictions on content.  The most notable restrictions are listed below. For a
complete list of restrictions, refer to
`Redhat Access <https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/5/html/installation_guide/s1-s390-steps-vm>`_.

* The parameter file should contain no more than 80 characters per line.
* The VM reader has a limit of 11 lines for the parameter file (for a total of 880 characters).

If there is no system record available on the server, or if netboot is not enabled, zPXE will attempt to retrieve the
file ``profile_list``, containing a list of all available install trees. These are presented in the form of a menu which
is displayed at each logon. If a profile is chosen, zPXE downloads the appropriate kernel and initial RAMdisk and begins
the installation. Note that since these are generic profiles, there is no network-specific information available for
this guest, so you will be prompted for this information in the 3270 console during installation.

If you press Enter at the menu without choosing a profile, zPXE will IPL the default disk specified in ZPXE CONF. If the
guest is XAUTOLOG'd (logged on disconnected by another user), zPXE will check for the presence of a system record. If
not found, the default disk is IPL'd with no profile list shown.

Power PC support
################

Cobbler includes support for provisioning Linux on PowerPC systems. This document will address how cobbler PowerPC
support differs from cobbler support for more common architectures, including i386 and x86_64.

Setup
=====

Support for network booting PowerPC systems is much like support for network booting x86 systems using PXE. However,
since PXE is not available for PowerPC, `yaboot <http://yaboot.ozlabs.org>`_ is used to network boot your PowerPC
systems. To start, you must adjust the boot device order on your system so that a network device is first. On x86-based
architectures, this configuration change would be accomplished by entering the BIOS. However,
`Open Firmware <https://en.wikipedia.org/wiki/Open_Firmware>`_ is often used in place of a BIOS on PowerPC platforms.
Different PowerPC platforms offer different methods for accessing Open Firmware. The common procedures are outlined at
`Open Firmware (Access) <https://en.wikipedia.org/wiki/Open_Firmware#Access>`_. The following example demonstrates
updating the boot device order.

Once at an Open Firmware prompt, to display current device aliases use the ``devalias`` command. For example:

.. code-block:: bash

    0 > devalias
    ibm,sp              /vdevice/IBM,sp@4000
    disk                /pci@800000020000002/pci@2,4/pci1069,b166@1/scsi@1/sd@5,0
    network             /pci@800000020000002/pci@2/ethernet@1
    net                 /pci@800000020000002/pci@2/ethernet@1
    network1            /pci@800000020000002/pci@2/ethernet@1,1
    scsi                /pci@800000020000002/pci@2,4/pci1069,b166@1/scsi@0
    nvram               /vdevice/nvram@4002
    rtc                 /vdevice/rtc@4001
    screen              /vdevice/vty@30000000
     ok

To display the current boot device order, use the ``printenv`` command. For example:

.. code-block:: bash

    0 > printenv boot-device
    -------------- Partition: common -------- Signature: 0x70 ---------------
    boot-device              /pci@800000020000002/pci@2,3/ide@1/disk@0 /pci@800000020000002/pci@2,4/pci1069,b166@1/scsi@1/sd@5,0
     ok

To add the device with alias **network** as the first boot device, use the ``setenv`` command. For example:

.. code-block:: bash

    0 > setenv boot-device network /pci@800000020000002/pci@2,3/ide@1/disk@0 /pci@800000020000002/pci@2,4/pci1069,b166@1/scsi@1/sd@5,0

Your system is now configured to boot off of the device with alias **network** as the first boot device. Should booting
off this device fail, your system will fallback to the next device listed in the **boot-device** Open Firmware settings.

System-based configuration
==========================

To begin, you need to first configure a Cobbler server. Cobbler can be run on any Linux system accessible by the your
PowerPC system, including an x86 system, or another PowerPC system. This server's primary responsibility is to host the
Linux install tree(s) remotely, and maintain information about clients accessing it. For detailed instructions on
configuring the Cobbler server, see the manual.

Next, it's time to add a system to cobbler. The following command will add a system named *ibm-505-lp1* to cobbler. Note
that the cobbler profile specified (*F-11-GOLD-ppc64*) must already exist.

.. code-block:: bash

    cobbler system add --name ibm-505-lp1 --hostname ibm-505-lp1.example.com \
      --profile F-11-GOLD-ppc64 --kopts "console=hvc0 serial" \
      --interface 0 --mac 00:11:25:7e:28:64

Most of the options to cobbler system add are self explanatory network parameters. They are fully explained in the
cobbler man page (see man cobbler). The ``--kopts`` option is used to specify any system-specific kernel options
required for this system. These will vary depending on the nature of the system and connectivity. In the example above,
I chose to redirect console output to a device called *hvc0* which is a specific console device available in some
virtualized guest environments (including KVM and PowerPC virtual guests).

In the example above, only one MAC address was specified. If network booting from additional devices is desired, you may
wish to add more MAC addresses to your system configuration in cobbler. The following commands demonstrate adding
additional MAC addresses:

.. code-block:: bash

    cobbler system edit --name ibm-505-lp1 --interface 1 --mac 00:11:25:7e:28:65
    cobbler system edit --name ibm-505-lp1 --interface 2 --mac 00:0d:60:b9:6b:c8

<div class="alert alert-info alert-block"><b>Note:</b> Providing a MAC address is required for proper network boot</div>
support using yaboot.

Profile-based configuration
===========================

Profile-based network installations using yaboot are not available at this time. OpenFirmware is only able to load a
bootloader into memory once. Once, yaboot is loaded into memory from a network location, you are not able to exit and
load an on-disk yaboot. Additionally, yaboot requires specific device locations in order to properly boot. At this time
there is no *local* boot target as there are in PXE configuration files.

Troubleshooting
===============

OpenFirmware Ping test
**********************

If available, some PowerPC systems offer a management interface available from the boot menu or accessible from
OpenFirmware directly. On IBM PowerPC systems, this interface is called SMS.

To enter SMS while your IBM PowerPC system is booting, press *1* when prompted during boot up. A sample boot screen is
shown below:

.. code-block:: bash

    IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM
    IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM
    IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM
    IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM IBM

              1 = SMS Menu                          5 = Default Boot List
              8 = Open Firmware Prompt              6 = Stored Boot List


         Memory      Keyboard     Network     SCSI

To enter SMS from an OpenFirmware prompt, type:

.. code-block:: bash

    dev /packages/gui obe

Once you've entered the SMS, you should see an option menu similar to:

.. code-block:: bash

     SMS 1.6 (c) Copyright IBM Corp. 2000,2005 All rights reserved.
    -------------------------------------------------------------------------------
     Main Menu
     1.   Select Language
     2.   Setup Remote IPL (Initial Program Load)
     3.   Change SCSI Settings
     4.   Select Console
     5.   Select Boot Options

To perform the ping test:

1.  Select `Setup Remote IPL`
2.  Select the appropriate network device to use

.. code-block:: bash

        -------------------------------------------------------------------------------
         NIC Adapters
              Device                          Location Code                 Hardware
                                                                            Address
         1.  Port 1 - IBM 2 PORT 10/100/100  U789F.001.AAA0060-P1-T1  0011257e2864
         2.  Port 2 - IBM 2 PORT 10/100/100  U789F.001.AAA0060-P1-T2  0011257e2865

3.  Select `IP Parameters`

.. code-block:: bash

        -------------------------------------------------------------------------------
         Network Parameters
        Port 1 - IBM 2 PORT 10/100/1000 Base-TX PCI-X Adapter: U789F.001.AAA0060-P1-T1
         1.   IP Parameters
         2.   Adapter Configuration
         3.   Ping Test
         4.   Advanced Setup: BOOTP

4.  Enter your local network settings

.. code-block:: bash

        -------------------------------------------------------------------------------
         IP Parameters
        Port 1 - IBM 2 PORT 10/100/1000 Base-TX PCI-X Adapter: U789F.001.AAA0060-P1-T1
         1.   Client IP Address                    [0.0.0.0]
         2.   Server IP Address                    [0.0.0.0]
         3.   Gateway IP Address                   [0.0.0.0]
         4.   Subnet Mask                          [0.0.0.0]

5.  When complete, press `Esc`, and select `Ping Test`

The results of this test will confirm whether your network settings are functioning properly.

Confirm Cobbler Settings
************************

Is your system configured to netboot? Confirm this by using the following command:

.. code-block:: bash

    # cobbler system report --name ibm-505-lp1 | grep netboot
    netboot enabled?      : True

Confirm Cobbler Configuration Files
***********************************

Cobbler stores network boot information for each MAC address associated with a system. When a PowerPC system is
configured for netbooting, a cobbler will create the following two files inside the tftp root directory:

- ``ppc/01-<MAC\_ADDRESS\> - symlink to the ../yaboot``
- ``etc/01-<MAC\_ADDRESS\> - a yaboot.conf configuration``

Confirm that the expected boot and configuration files exist for each MAC address. A sample configuration is noted below:

.. code-block:: bash

    # for MAC in $(cobbler system report --name ibm-505-lp1 | grep mac | gawk '{print $4}' | tr ':' '-');
    do
        ls /var/lib/tftpboot/{ppc,etc}/01-$MAC ;
    done
    /var/lib/tftpboot/etc/01-00-11-25-7e-28-64
    /var/lib/tftpboot/ppc/01-00-11-25-7e-28-64
    /var/lib/tftpboot/etc/01-00-11-25-7e-28-65
    /var/lib/tftpboot/ppc/01-00-11-25-7e-28-65
    /var/lib/tftpboot/etc/01-00-0d-60-b9-6b-c8
    /var/lib/tftpboot/ppc/01-00-0d-60-b9-6b-c8

Confirm Permissions
*******************

Be sure that SELinux file context's and file permissions are correct. SELinux file context information can be reset
according to your system policy by issuing the following command:

.. code-block:: bash

    # restorecon -R -v /var/lib/tftpboot

To identify any additional permissions issues, monitor the system log file ``/var/log/messages`` and the SELinux audit
log ``/var/log/audit/audit.log`` while attempting to netboot your system.

Latest yaboot?
**************

Network boot support requires a fairly recent yaboot. The yaboot included in cobbler-1.4.x may not support booting
recent Fedora derived distributions. Before reporting a bug, try updating to the latest yaboot binary. The latest yaboot
binary is available from Fedora rawhide at LINK-DEAD.

References
==========

* Additional OpenFirmware information available at LINK-DEAD.

.. _tips-for-thn:

Tips for RHN
############

If you're deploying RHEL, there are a few extra kickstart and Cobbler tricks you can employ to make provisioning a snap,
all consolidated in one place...

Importing
=========

Download the DVD ISO's for RHN hosted. Then use ``cobbler import`` to import the ISO's to get an install tree.

Registering To RHN
==================

RHEL has a tool installed called rhnreg_ks that you may not be familiar with. It's what you call in the %post of a
kickstart file to make a system automatically register itself with Satellite or the RHN Hosted offering.

You may want to read up on rhnreg_ks for all the options it provides, but Cobbler ships with a snippet
("redhat_register") that can help you register systems. It should be in the ``/var/lib/cobbler/kickstarts/sample*.ks``
files by default, for you to look at. It is configured by various settings in ``/etc/cobbler/settings``.

Authenticating XMLRPC / Web users against Satellite / Spacewalk's API
=====================================================================

In ``/etc/cobbler/modules.conf``, if you are using authn_spacewalk for authentication, Cobbler can talk to Satellite
(5.3 and later) or Spacewalk for authentication. Authentication is cleared when users have the role "org_admin", or
"kickstart_admin" roles. Authorization can later be supplied via cobbler modules as normal, for example,
``authz_allowall`` (default) or ``authn_ownership``, but should probably be left as ``authz_allowall``.

See :ref:`customizable-security`

If you are using a copy of Cobbler that came bundled with Spacewalk or Satellite Server, don't change these settings, as
you will break Spacewalk/Satellite's ability to converse with Cobbler.

Installation Numbers
====================

See the section called "RHEL Keys" on the KickstartSnippets page. It's a useful way to store all of your install keys in
cobbler and use them automatically as needed.

Repository Mirroring
====================

Cobbler has limited/experimental support for mirroring RHN-channels, see the cobbler manpage for details. Basically you
just specify a ``cobbler repo add`` with the path "rhn://channel-name". This requires a version of yum-utils 1.0.4 or
later, installed on the cobbler boot server. Only the arch of the cobbler server can be mirrored. See ManageYumRepos.

If you require better mirroring support than what yum provides, please consider Red Hat Satellite Server.

Memtest
#######

If installed, cobbler will put an entry into all of your PXE menus allowing you to run memtest on physical systems
without making changes in Cobbler. This can be handy for some simple diagnostics.

Steps to get memtest to show up in your PXE menus:

.. code-block:: bash

    # yum install memtest86+
    # cobbler image add --name=memtest86+ --file=/path/to/memtest86+ --image-type=direct
    # cobbler sync

memtest will appear at the bottom of your menus after all of the profiles.

Targeted Memtesting
===================

However, if you already have a cobbler system record for the system, you can't get the menu. No problem!

.. code-block:: bash

    cobbler image add --name=foo --file=/path/to/memtest86 --image-type=direct
    cobbler system edit --name=bar --mac=AA:BB:CC:DD:EE:FF --image=foo --netboot-enabled=1

The system will boot to memtest until you put it back to it's original profile.

**CAUTION**: When restoring the system back from memtest, make sure you turn it's netboot flag /off/ if you have it set
to PXE first in the BIOS order, unless you want to reinstall the system!

.. code-block:: bash

    cobbler system edit --name=bar --profile=old_profile_name --netboot-enabled=0

Naturally if you **do** want to reinstall it after running memtest, just use ``--netboot-enabled=1``

.. _anaconda:

Anaconda Monitoring
###################

This page details the Anaconda Monitoring service available in cobbler. As anamon is rather distribution specific,
support for it is considered deprecated at this time.

History
=======

Prior to Cobbler 1.6, remote monitoring of installing systems was limited to distributions that accept the the boot
argument *syslog=*. While this is supported in RHEL-5 and newer Red Hat based distributions, it has several
shortcomings.

Reduces available kernel command-line length
********************************************

The kernel command-line has a limited amount of space, relying on *syslog=somehost.example.com* reduces available
argument space. Cobbler has smarts to not add the *syslog=* parameter if no space is available. But doing so disables
remote monitoring.

Only captures syslog
********************

The *syslog=* approach will only capture syslog-style messages. Any command-specific output (``/tmp/lvmout``,
``/tmp/ks-script``, ``/tmp/X.config``) or installation failure (``/tmp/anacdump.txt``) information is not sent.

Unsupported on older distros
****************************

While capturing syslog information is key for remote monitoring of installations, the
`anaconda <https://fedoraproject.org/wiki/Anaconda>`_ installer only supports sending syslog data for RHEL-5 and newer
distributions.

What is Anamon?
===============

In order to overcome the above obstacles, the *syslog=* remote monitoring has been replaced by a python service called
**anamon** (Anaconda Monitor). Anamon is a python daemon (which runs inside the installer while it is installing) that
connects to the cobbler server via XMLRPC and uploads a pre-determined set of files. Anamon will continue monitoring
files for updates and send any new data to the cobbler server.

Using Anamon
============

To enable anamon for your Red Hat based distribution installations, edit */etc/cobbler/settings* and set:

.. code-block:: yaml

    anamon_enabled: 1

**NOTE:** Enabling anamon allows an xmlrpc call to send create and update log files in the anamon directory, without
authentication, so enable only if you are ok with this limitation. It could be potentially used by users to flood the
log files or fill up the server, which you probably don't want in an untrusted environment. However, even so, it may be
good for debugging complex installs.

You will also need to update your kickstart templates to include the following snippets.

.. code-block:: bash

    %pre
    $SNIPPET('pre_anamon')

Anamon can also send ``/var/log/messages`` and ``/var/log/boot.log`` once your provisioned system has booted. To also
enable post-install boot notification, you must enable the following snippet:

.. code-block:: bash

    %post
    $SNIPPET('post_anamon')

Where Is Information Saved?
===========================

All anamon logs are stored in a system-specific directory under ``/var/log/cobbler/anamon/systemname``. For example,

.. code-block:: bash

    $ ls /var/log/cobbler/anamon/vguest3
    anaconda.log  boot.log  dmesg  install.log  ks.cfg  lvmout.log  messages  sys.log

Older Distributions
===================

Anamon relies on a %pre installation script that uses a python *xmlrpc* library. The installation image used by
Red Hat Enterprise Linux 4 and older distributions for **http://** installs does not provide the needed python
libraries. There are several ways to get around this ...

1. Always perform a graphical or **vnc** install - installing graphically (or by vnc) forces anaconda to download the
   *stage2.img* that includes graphics support **and** the required python xmlrpc library.
2. Install your system over nfs - nfs installations will also use the *stage2.img* that includes python xmlrpc support
3. Install using an *updates.img* - Provide the missing xmlrpc library by building an updates.img for use during
   installation. To construct an *updates.img*, follow the steps below:

.. code-block:: bash

    $ dd if=/dev/zero of=updates.img bs=1k count=1440
    $ mke2fs updates.img
    $ tmpdir=`mktemp -d`
    $ mount -o loop updates.img $tmpdir
    $ mkdir $tmpdir/cobbler
    $ cp /usr/lib64/python2.3/xmlrpclib.* $tmpdir/cobbler
    $ cp /usr/lib64/python2.3/xmllib.* $tmpdir/cobbler
    $ cp /usr/lib64/python2.3/shlex.* $tmpdir/cobbler
    $ cp /usr/lib64/python2.3/lib-dynload/operator.* $tmpdir/cobbler
    $ umount $tmpdir
    $ rmdir $tmpdir

More information on building and using an *updates.img* is available from
`Anaconda Updates <https://fedoraproject.org/wiki/Anaconda/Updates>`_

System Retirement
#################

Using DBAN with Cobbler to automate system retirement

Introduction
============

The following method details using `DBAN <https://dban.org/>`_ with Cobbler to create a PXE boot image that
will securely wipe the disk of the system being retired. This could also be used if you are shipping a disk back to the
manufacturer and wanted to ensure all data is "securely" wiped.

Steps
=====

DBAN 2.2.6
**********

Retrieve the extra loader parts that DBAN 2.2.6 needs:

.. code-block:: bash

    cobbler get-loaders

Download DBAN:

.. code-block:: bash

    wget -O /tmp/dban-2.2.6_i586.iso http://prdownloads.sourceforge.net/dban/dban-2.2.6_i586.iso

Mount the ISO and copy the kernel image file and (optionally) the boot configuration file:

.. code-block:: bash

    mount -o loop,ro /tmp/dban-2.2.6_i586.iso /mnt
    mkdir -p /opt/cobbler/dban-2.2.6
    cp -p /mnt/dban.bzi /opt/cobbler/dban-2.2.6/
    cp -p /mnt/isolinux.cfg /opt/cobbler/dban-2.2.6/
    chmod -x /opt/cobbler/dban-2.2.6/*
    umount /mnt

Add the DBAN distro and profile to Cobbler.  Run sync to copy the loaders into place:

.. code-block:: bash

    cobbler distro add --name=DBAN-2.2.6-i586 --kernel=/opt/cobbler/dban-2.2.6/dban.bzi \
      --initrd=/opt/cobbler/dban-2.2.6/dban.bzi --kopts="nuke=dwipe silent"
    cobbler profile add --name=DBAN-2.2.6-i586 --distro=DBAN-2.2.6-i586
    cobbler sync

DBAN 1.0.7
**********

Download DBAN:

.. code-block:: bash

    wget -O /tmp/dban-1.0.7_i386.iso http://prdownloads.sourceforge.net/dban/dban-1.0.7_i386.iso

Mount the ISO and copy the floppy disk image file:

.. code-block:: bash

    mount -o loop,ro /tmp/dban-1.0.7_i386.iso /mnt
    cp -p /mnt/dban_1_0_7_i386.ima /tmp/
    umount /mnt

Mount the floppy disk image file and copy the kernel image file, initial ram disk, and (optionally) the boot
configuration file:

.. code-block:: bash

    mount -o loop,ro /tmp/dban_1_0_7_i386.ima /mnt
    mkdir -p /opt/cobbler/dban-1.0.7
    cp -p /mnt/initrd.gz /opt/cobbler/dban-1.0.7/
    cp -p /mnt/kernel.bzi /opt/cobbler/dban-1.0.7/
    cp -p /mnt/syslinux.cfg /opt/cobbler/dban-1.0.7/
    chmod -x /opt/cobbler/dban-1.0.7/*
    umount /mnt

Add the DBAN distro and profile to Cobbler:

.. code-block:: bash

    cobbler distro add --name=DBAN-1.0.7-i386 --kernel=/opt/cobbler/dban-1.0.7/kernel.bzi \
      --initrd=/opt/cobbler/dban-1.0.7/initrd.gz --kopts="root=/dev/ram0 init=/rc nuke=dwipe floppy=0,16,cmos"
    cobbler profile add --name=DBAN-1.0.7-i386 --distro=DBAN-1.0.7-i386

Test
====

1. Add a system to be destroyed:

.. code-block:: bash

    cobbler system add --name=00:15:c5:c0:05:58 --profile=DBAN-1.0.7-i386

2. Sync cobbler:

.. code-block:: bash

    cobbler sync

3. Boot the system via PXE. The DBAN menu will pop up. Select the drives and hit F10 to start the wipe.
4. Remove the system from this profile so that you don't accidentally boot and wipe in the future:

.. code-block:: bash

    cobbler system remove --name=00:15:c5:c0:05:58

Notes
=====

You can setup DBAN to autowipe the system in question by supplying the kernel option of ``nuke="dwipe --autonuke"``. We
are not doing it in this example because people sometimes only half-read things and it would suck to find out too late
that you'd wiped a system you didn't mean to.

It should go without saying that, while it might be a mildly fun prank, you shouldn't set this to be your default pxe
boot menu choice. You'll most likely get fired and/or beat up by your fellow employees.

If you do set this profile, it will show up as an option in the PXE menus. If this concerns you, set up a syslinux
password by editing the templates in ``/etc/cobbler`` to ensure no one walks up to a system and blitzes it
involuntarily. An option to keep a profile out of the PXE menu is doable if enough people request it or someone wants to
submit a patch...

Booting Live CD's
#################

Live CD's can be used for a variety of tasks. They might update firmware, run diagnostics, assist with cloning systems,
or just serve up a desktop environment.

With Cobbler
============

Somewhat unintuitively, LiveCD's are booted by transforming the CD ISO's to kernel+initrd files.

Take the livecd and install livecd-tools. You may need a recent Fedora to find livecd-tools. What we are about to do is
convert the live image to something that is PXEable. It will produce a kernel image and a VERY large initrd which
essentially contains the entire ISO. Once this is done it is PXE-bootable, but we still have to provide the right kernel
arguments.

.. code-block:: bash

    livecd-iso-to-pxeboot live-image.iso


This will produce a subdirectory in the current directory called ``./tftpboot``. You need to save the initrd and the
vmlinuz from this directory, and as a warning, the initrd is as big as the live image. Make sure you have space.

.. code-block:: bash

    mkdir -p /srv/livecd
    cp /path/to/cwd/tftpboot/vmlinuz0 /srv/livecd/vmlinuz0
    cp /path/to/cwd/tftpboot/initrd.img /srv/livecd/initrd.img
    cobbler distro add --name=liveF9 --kernel=/srv/livecd/vmlinuz0 --initrd=/srv/livecd/initrd.img


Now we must add some parameters to the kernel and create a dummy profile object. Note we are passing in some extra
kernel options and telling cobbler it doesn't need many of the default ones because it can save space. Be sure the
``/name-goes-here.iso`` part of the path matches up with the ISO you ran livecd-iso-to-pxeboot against exactly or the
booting will not be successful.

.. code-block:: bash

    cobbler distro edit --name=liveF9 --kopts='root=/f9live.iso rootfstype=iso9660 rootflags=loop !text !lang !ksdevice'
    cobbler profile add --name=liveF9 --distro=liveF9

At this point it will work as though it is a normal "profile", though it will boot the live image as opposed to an
installer image.

For instance, if we wanted to deploy the live image to all machines on a specific subnet we could do it as follows:

.. code-block:: bash

    cobbler system add --name=live_network --ip-address=123.45.00.00/24 --profile=liveF9

Or of course we could just deploy it to a specific system:

.. code-block:: bash

    cobbler system add --name=xyz --mac=AA:BB:CC:DD:EE:FF --profile=liveF9

And of course this will show up in the PXE menus automatically as well.

Notes
=====

When you boot this profile it will take a relatively long time (3-5 minutes?) and you will see a lot of dots printed on
the screen. This is expected behavior as it has to transfer a large amount of data.

Space Considerations
====================

The Live Images are very large. Cobbler will try to hardlink them if the vmlinuz/initrd files are on the same device,
but it cannot symlink because of the way TFTP (needed for PXE) requires a chroot environment. If your distro add command
takes a long time, this is because of the copy, please make sure you have the extra space in your TFTP boot directory's
partition (either ``/var/lib/tftpboot`` or ``/tftpboot`` depending on OS).

Troubleshooting
===============

If you boot into the live environment and it does not work right, most likely the rootflags and other parameters are
incorrect. Recheck them with "cobbler distro report --name=foo"

Clonezilla Integration
######################

Since many of us need to support non-linux systems in addition to Linux systems, some facility for support of these
systems is helpful - especially if your dhcp server is pointing pxe boots to your cobbler server. PXE booting a
clonezilla live CD as an option under cobbler provides a unified starting point for all system installation tasks.

Step-by-step (as of 2.2.2)
==========================

1. Download clonezilla live image from here here: `Clonezilla Download Page <https://clonezilla.org/downloads.php>`_.
   I used the ubuntu based "experimental" version because the Debian based clonezilla's don't have necessary network
   drivers for many Dell servers.
2. Unpack the zip file to a location on the machine, and run an add the distribution

.. code-block:: bash

    cobbler distro add  --name=clonezilla1-2-22-37 --arch=x86_64 --breed=other --os-version=other \
    --boot-files="'$img_path/filesystem.squashfs'='<path_to_your_folder>/live/filesystem.squashfs'" \
    --kernel=<path_to_your_folder>/live/vmlinuz --initrd=<path_to_your_folder>/live/initrd.img``
3. Set up the kickstart kernel options needed for booting to at least:

.. code-block:: bash

    nomodeset edd=on ocs_live_run=ocs-live-general ocs_live_keymap=NONE boot=live vga=788 noswap noprompt nosplash \
    ocs_live_batch=no ocs_live_extra_param ocs_lang=en_US.UTF-8 ocs_lang=None nolocales config
    fetch=tftp://<Your_TFTP_ServerIP>/images/<your_Profile_NAME>/filesystem.squashfs``

4. You should then be able to create a profile for the clonezilla distro and then add to the kernel options, and be able
   to customize the startup procedure from there using the clonezilla docs.
5. Run ``cobbler sync`` to set up the template for the systems you need.

Limitations and work needed
===========================

1. I've seen the download of the squashfs skipped on more than one occaision, resulting in a kernel panic. Not sure why
   this happens, but trying again fixes the problem (or could just be because I'm still experimenting too much).
2. Would be nice if clonezilla UI was integrated into cobbler somewhat (i.e. it knew the IP of the server saving the
   images and maybe had an ssh key so it could get access without a password).
3. **Still very experimental.**
