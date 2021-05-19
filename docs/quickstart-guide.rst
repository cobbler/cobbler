**********
Quickstart
**********

Cobbler can be a somewhat complex system to get started with, due to the wide variety of technologies it is designed to
manage, but it does support a great deal of functionality immediately after installation with little to no customization
needed. Before getting started with Cobbler, you should have a good working knowledge of PXE as well as the automated
installation methodology of your chosen distribution(s).

We will assume you have successfully installed Cobbler, please refer to the
:doc:`Installation Guide </installation-guide>` for instructions for your specific operating system. Finally, this part
guide will focus only on the CLI application.


Preparing your OS
#################

SELinux
=======

Before getting started with Cobbler, it may be convenient to either disable SELinux or set it to "permissive" mode,
especially if you are unfamiliar with SELinux troubleshooting or modifying SELinux policy. Cobbler constantly evolves to
assist in managing new system technologies, and the policy that ships with your OS can sometimes lag behind the
feature-set we provide, resulting in AVC denials that break Cobbler's functionality.

Firewall
========
TBD


Changing settings
#################

Before starting the `cobblerd` service, there are a few things you should modify.

Settings are stored in ``/etc/cobbler/settings.yaml``. This file is a YAML formatted data file, so be sure to take care
when editing this file as an incorrectly formatted file will prevent `cobblerd` from running.


Default encrypted password
==========================

This setting controls the root password that is set for new systems during the handsoff installation.

.. code::

    default_password_crypted: "$1$bfI7WLZz$PxXetL97LkScqJFxnW7KS1"

You should modify this by running the following command and inserting the output into the above string (be sure to save
the quote marks):

.. code-block:: shell

    $ openssl passwd -1


Server and next_server
======================

The ``server`` option sets the IP that will be used for the address of the Cobbler server. **DO NOT** use 0.0.0.0, as it
is not the listening address. This should be set to the IP you want hosts that are being built to contact the Cobbler
server on for such protocols as HTTP and TFTP.

.. code::

    server: 127.0.0.1

The ``next_server`` option is used for DHCP/PXE as the IP of the TFTP server from which network boot files are
downloaded. Usually, this will be the same IP as the server setting.

.. code::

    next_server: 127.0.0.1


DHCP management and DHCP server template
########################################

In order to PXE boot, you need a DHCP server to hand out addresses and direct the booting system to the TFTP server
where it can download the network boot files. Cobbler can manage this for you, via the ``manage_dhcp`` setting:

.. code::

    manage_dhcp: 0

Change that setting to 1 so Cobbler will generate the ``dhcpd.conf`` file based on the ``dhcp.template`` that is
included with Cobbler. This template will most likely need to be modified as well, based on your network settings:

.. code-block:: shell

    $ vi /etc/cobbler/dhcp.template

For most uses, you'll only need to modify this block:

.. code::

    subnet 192.168.1.0 netmask 255.255.255.0 {
        option routers             192.168.1.1;
        option domain-name-servers 192.168.1.210,192.168.1.211;
        option subnet-mask         255.255.255.0;
        filename                   "/pxelinux.0";
        default-lease-time         21600;
        max-lease-time             43200;
        next-server                $next_server_v4;
    }

No matter what, make sure you do not modify the ``next-server $next_server_v4;`` line, as that is how the next server
setting is pulled into the configuration. This file is a cheetah template, so be sure not to modify anything starting
after this line:

.. code::

    #for dhcp_tag in $dhcp_tags.keys():

Completely going through the ``dhcpd.conf`` configuration syntax is beyond the scope of this document, but for more
information see the man page for more details:

.. code-block:: shell

    $ man dhcpd.conf


Notes on files and directories
##############################

Cobbler makes heavy use of the ``/var`` directory. The ``/var/www/cobbler/distro_mirror`` directory is where all of the
distribution and repository files are copied, so you will need 5-10GB of free space per distribution you wish to import.

If you have installed Cobbler onto a system that has very little free space in the partition containing ``/var``, please
read the :ref:`relocating-your-installation` section of the Installation Guide to learn how you can relocate your
installation properly.


Starting and enabling the Cobbler service
#########################################

Once you have updated your settings, you're ready to start the service:

.. code-block:: shell

    $ systemctl start cobblerd.service
    $ systemctl enable cobblerd.service
    $ systemctl status cobblerd.service

If everything has gone well, you should see output from the status command like this:

.. code-block:: shell

    cobblerd.service - Cobbler Helper Daemon
        Loaded: loaded (/lib/systemd/system/cobblerd.service; enabled)
          Active: active (running) since Sun, 17 Jun 2012 13:01:28 -0500; 1min 44s ago
        Main PID: 1234 (cobblerd)
          CGroup: name=systemd:/system/cobblerd.service
                  └ 1234 /usr/bin/python /usr/bin/cobblerd -F


Checking for problems and your first sync
#########################################

Now that the `cobblerd` service is up and running, it's time to check for problems. Cobbler's check command will make some
suggestions, but it is important to remember that these are mainly only suggestions and probably aren't critical for
basic functionality. If you are running iptables or SELinux, it is important to review any messages concerning those that
check may report.

.. code-block:: shell

    $ cobbler check
    The following are potential configuration items that you may want to fix:

    1. ....
    2. ....

Restart `cobblerd` and then run ``cobbler sync`` to apply changes.

If you decide to follow any of the suggestions, such as installing extra packages, making configuration changes, etc.,
be sure to restart the `cobblerd` service as it suggests so the changes are applied.

Once you are done reviewing the output of ``cobbler check``, it is time to synchronize things for the first time. This
is not critical, but a failure to properly sync at this point can reveal a configuration problem.

.. code-block:: shell

    $ cobbler sync
    task started: 2012-06-24_224243_sync
    task started (id=Sync, time=Sun Jun 24 22:42:43 2012)
    running pre-sync triggers
    ...
    rendering DHCP files
    generating /etc/dhcp/dhcpd.conf
    cleaning link caches
    running: find /var/lib/tftpboot/images/.link_cache -maxdepth 1 -type f -links 1 -exec rm -f '{}' ';'
    received on stdout:
    received on stderr:
    running post-sync triggers
    running python triggers from /var/lib/cobbler/triggers/sync/post/*
    running python trigger cobbler.modules.sync_post_restart_services
    running: dhcpd -t -q
    received on stdout:
    received on stderr:
    running: service dhcpd restart
    received on stdout:
    received on stderr:
    running shell triggers from /var/lib/cobbler/triggers/sync/post/*
    running python triggers from /var/lib/cobbler/triggers/change/*
    running python trigger cobbler.modules.scm_track
    running shell triggers from /var/lib/cobbler/triggers/change/*
    *** TASK COMPLETE ***

Assuming all went well and no errors were reported, you are ready to move on to the next step.


Importing your first distribution
#################################

Cobbler automates adding distributions and profiles via the ``cobbler import`` command. This command can (usually)
automatically detect the type and version of the distribution your importing and create (one or more) profiles with the
correct settings for you.


Download an ISO image
=====================

In order to import a distribution, you will need a DVD ISO for your distribution.

.. note::
   You must use a full DVD, and not a "Live CD" ISO. For this example, we'll be using the Fedora 17 x86_64 ISO.

.. warning::
   When running Cobbler via systemd, you cannot mount the ISO to ``/tmp`` or a sub-folder of it because we are using the
   option `Private Temporary Directory`, to enhance the security of our application.

Once this file is downloaded, mount it somewhere:

.. code-block:: shell

    $ mount -t iso9660 -o loop,ro /path/to/isos/Fedora-17-x86_64-DVD.iso /mnt


Run the import
==============

You are now ready to import the distribution. The name and path arguments are the only required options for import:

.. code-block:: shell

    $ cobbler import --name=fedora17 --arch=x86_64 --path=/mnt

The ``--arch`` option need not be specified, as it will normally be auto-detected. We're doing so in this example in
order to prevent multiple architectures from being found.


Listing objects
+++++++++++++++

If no errors were reported during the import, you can view details about the distros and profiles that were created
during the import.

.. code-block:: shell

    $ cobbler distro list
    $ cobbler profile list

The import command will typically create at least one distro/profile pair, which will have the same name as shown above.
In some cases (for instance when a Xen-based kernel is found), more than one distro/profile pair will be created.


Object details
++++++++++++++

The report command shows the details of objects in Cobbler:

.. code-block:: shell

    $ cobbler distro report --name=fedora17-x86_64
    Name                            : fedora17-x86_64
    Architecture                    : x86_64
    TFTP Boot Files                 : {}
    Breed                           : redhat
    Comment                         :
    Fetchable Files                 : {}
    Initrd                          : /var/www/cobbler/distro_mirror/fedora17-x86_64/images/pxeboot/initrd.img
    Kernel                          : /var/www/cobbler/distro_mirror/fedora17-x86_64/images/pxeboot/vmlinuz
    Kernel Options                  : {}
    Kernel Options (Post Install)   : {}
    Automatic Installation Template Metadata : {'tree': 'http://@@http_server@@/cblr/links/fedora17-x86_64'}
    Management Classes              : []
    OS Version                      : fedora17
    Owners                          : ['admin']
    Red Hat Management Key          : <<inherit>>
    Red Hat Management Server       : <<inherit>>
    Template Files                  : {}

As you can see above, the import command filled out quite a few fields automatically, such as the breed, OS version, and
initrd/kernel file locations. The "Automatic Installation Template Metadata" field (``--autoinstall_meta`` internally)
is used for miscellaneous variables, and contains the critical "tree" variable. This is used in the automated
installation templates to specify the URL where the installation files can be found.

Something else to note: some fields are set to ``<<inherit>>``. This means they will use either the default setting
(found in the settings file), or (in the case of profiles, sub-profiles, and systems) will use whatever is set in the
parent object.


Creating a system
+++++++++++++++++

Now that you have a distro and profile, you can create a system. Profiles can be used to PXE boot, but most of the
features in Cobbler revolve around system objects. The more information you give about a system, the more Cobbler will
do automatically for you.

First, we'll create a system object based on the profile that was created during the import. When creating a system, the
name and profile are the only two required fields:

.. code-block:: shell

    $ cobbler system add --name=test --profile=fedora17-x86_64
    $ cobbler system list
    test
    $ cobbler system report --name=test
    Name                           : test
    TFTP Boot Files                : {}
    Comment                        :
    Enable gPXE?                   : 0
    Fetchable Files                : {}
    Gateway                        :
    Hostname                       :
    Image                          :
    IPv6 Autoconfiguration         : False
    IPv6 Default Device            :
    Kernel Options                 : {}
    Kernel Options (Post Install)  : {}
    Automatic Installation Template: <<inherit>>
    Automatic Installation Template Metadata: {}
    Management Classes             : []
    Management Parameters          : <<inherit>>
    Name Servers                   : []
    Name Servers Search Path       : []
    Netboot Enabled                : True
    Owners                         : ['admin']
    Power Management Address       :
    Power Management ID            :
    Power Management Password      :
    Power Management Type          : ipmilanplus
    Power Management Username      :
    Profile                        : fedora17-x86_64
    Proxy                          : <<inherit>>
    Red Hat Management Key         : <<inherit>>
    Red Hat Management Server      : <<inherit>>
    Repos Enabled                  : False
    Server Override                : <<inherit>>
    Status                         : production
    Template Files                 : {}
    Virt Auto Boot                 : <<inherit>>
    Virt CPUs                      : <<inherit>>
    Virt Disk Driver Type          : <<inherit>>
    Virt File Size(GB)             : <<inherit>>
    Virt Path                      : <<inherit>>
    Virt RAM (MB)                  : <<inherit>>
    Virt Type                      : <<inherit>>

The primary reason for creating a system object is network configuration. When using profiles, you're limited to DHCP
interfaces, but with systems you can specify many more network configuration options.

So now we'll setup a single, simple interface in the ``192.168.1/24`` network:

.. code-block:: shell

    $ cobbler system edit --name=test --interface=eth0 --mac=00:11:22:AA:BB:CC --ip-address=192.168.1.100 --netmask=255.255.255.0 --static=1 --dns-name=test.mydomain.com

The default gateway isn't specified per-NIC, so just add that separately (along with the hostname):

.. code-block:: shell

    $ cobbler system edit --name=test --gateway=192.168.1.1 --hostname=test.mydomain.com

The ``--hostname`` field corresponds to the local system name and is returned by the ``hostname`` command. The
``--dns-name`` (which can be set per-NIC) should correspond to a DNS A-record tied to the IP of that interface.
Neither are required, but it is a good practice to specify both. Some advanced features (like configuration management)
rely on the ``--dns-name`` field for system record look-ups.

Whenever a system is edited, Cobbler executes what is known as a "lite sync", which regenerates critical files like the
PXE boot file in the TFTP root directory. One thing it will **NOT** do is execute service management actions, like
regenerating the ``dhcpd.conf`` and restarting the DHCP service. After adding a system with a static interface it is a
good idea to execute a full ``cobbler sync`` to ensure the dhcpd.conf file is rewritten with the correct static lease
and the service is bounced.
