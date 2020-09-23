***********************************
Cobbler CLI
***********************************

This page contains a description for commands which can be used from the CLI.

.. Go Client: https://github.com/jtopjian/cobblerclient

General Principles
##################

This should just be a brief overview. For the detailed explanations please refer to
`Readthedocs <https://cobbler.readthedocs.io/>`_.

Distros, Profiles and Systems
=============================

Cobbler has a system of inheritance when it comes to managing the information you want to apply to a certain system.

Images
======

Repositories
============

Management Classes
==================

Deleting configuration entries
==============================

If you want to remove a specific object, use the remove command with the name that was used to add it.

.. code-block:: none

    cobbler distro|profile|system|repo|image|mgmtclass|package|file remove --name=string

Editing
=======

If you want to change a particular setting without doing an ``add`` again, use the ``edit`` command, using the same name
you gave when you added the item. Anything supplied in the parameter list will overwrite the settings in the existing
object, preserving settings not mentioned.

.. code-block:: none

    cobbler distro|profile|system|repo|image|mgmtclass|package|file edit --name=string [parameterlist]

Copying
=======

Objects can also be copied:

.. code-block:: none

    cobbler distro|profile|system|repo|image|mgmtclass|package|file copy --name=oldname --newname=newname

Renaming
========

Objects can also be renamed, as long as other objects don't reference them.

.. code-block:: none

    cobbler distro|profile|system|repo|image|mgmtclass|package|file rename --name=oldname --newname=newname

CLI-Commands
############

Short Usage: ``cobbler command [subcommand] [--arg1=value1] [--arg2=value2]``

Long Usage:

.. code-block:: shell

    cobbler <distro|profile|system|repo|image|mgmtclass|package|file> ... [add|edit|copy|get-autoinstall*|list|remove|rename|report] [options|--help]
    cobbler <aclsetup|buildiso|import|list|replicate|report|reposync|sync|validate-autoinstalls|version|signature|get-loaders|hardlink> [options|--help]

Cobbler distro
==============

This first step towards configuring what you want to install is to add a distribution record to Cobbler's configuration.

If there is an rsync mirror, DVD, NFS, or filesystem tree available that you would rather ``import`` instead, skip down
to the documentation about the ``import`` command. It's really a lot easier to follow the import workflow -- it only
requires waiting for the mirror content to be copied and/or scanned. Imported mirrors also save time during install
since they don't have to hit external install sources.

If you want to be explicit with distribution definition, however, here's how it works:

.. code-block:: shell

    $ cobbler distro add --name=string --kernel=path --initrd=path [--kopts=string] [--kopts-post=string] [--ksmeta=string] [--arch=i386|x86_64|ppc|ppc64] [--breed=redhat|debian|suse] [--template-files=string]

+----------------+-----------------------------------------------------------------------------------------------------+
| Name           | Description                                                                                         |
+================+=====================================================================================================+
| name           | a string identifying the distribution, this should be something like ``rhel6``.                     |
+----------------+-----------------------------------------------------------------------------------------------------+
| kernel         | An absolute filesystem path to a kernel image.                                                      |
+----------------+-----------------------------------------------------------------------------------------------------+
| initrd         | An absolute filesystem path to a initrd image.                                                      |
+----------------+-----------------------------------------------------------------------------------------------------+
| remote-boot-   | A URL pointing to the installation initrd of a distribution. If the bootloader has this support,    |
| kernel         | it will directly download the kernel from this URL, instead of the directory of the TFTP client.    |
|                | Note: The kernel (or initrd below) will still be copied into the image directory of the TFTP server.|
|                | The above kernel parameter is still needed (e.g. to build iso images, etc.).                        |
|                | The advantage of letting the boot loader retrieve the kernel/initrd directly is the support of      |
|                | changing/updated distributions. E.g. openSUSE Tumbleweed is updated on the fly and if Cobbler would |
|                | copy/cache the kernel/initrd in the TFTP directory, you would get a "kernel does not match          |
|                | distribution" (or similar) error when trying to install.                                            |
+----------------+-----------------------------------------------------------------------------------------------------+
| remote-boot-   | See remote-boot-kernel above.                                                                       |
| initrd         |                                                                                                     |
+----------------+-----------------------------------------------------------------------------------------------------+
| kopts          | Sets kernel command-line arguments that the distro, and profiles/systems depending on it, will use. |
|                | To remove a kernel argument that may be added by a higher Cobbler object (or in the global          |
|                | settings), you can prefix it with a ``!``.                                                          |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | Example: ``--kopts="foo=bar baz=3 asdf !gulp"``                                                     |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | This example passes the arguments ``foo=bar baz=3 asdf`` but will make sure ``gulp`` is not passed  |
|                | even if it was requested at a level higher up in the Cobbler configuration.                         |
+----------------+-----------------------------------------------------------------------------------------------------+
| kopts-post     | This is just like ``--kopts``, though it governs kernel options on the installed OS, as opposed to  |
|                | kernel options fed to the installer. The syntax is exactly the same. This requires some special     |
|                | snippets to be found in your automatic installation template in order for this to work. Automatic   |
|                | installation templating is described later on in this document.                                     |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | Example: ``noapic``                                                                                 |
+----------------+-----------------------------------------------------------------------------------------------------+
| arch           | Sets the architecture for the PXE bootloader and also controls how Koan's ``--replace-self`` option |
|                | will operate.                                                                                       |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | The default setting (``standard``) will use ``pxelinux``. Set to ``ppc`` and ``ppc64`` to use       |
|                | ``yaboot``.                                                                                         |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | ``x86`` and ``x86_64`` effectively do the same thing as standard.                                   |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | If you perform a ``cobbler import``, the arch field will be auto-assigned.                          |
+----------------+-----------------------------------------------------------------------------------------------------+
| ksmeta         | This is an advanced feature that sets automatic installation template variables to substitute, thus |
|                | enabling those files to be treated as templates. Templates are powered using Cheetah and are        |
|                | described further along in this manpage as well as on the Cobbler Wiki.                             |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | Example: ``--ksmeta="foo=bar baz=3 asdf"``                                                          |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | See the section on "Kickstart Templating" for further information.                                  |
+----------------+-----------------------------------------------------------------------------------------------------+
| breed          | Controls how various physical and virtual parameters, including kernel arguments for automatic      |
|                | installation, are to be treated. Defaults to ``redhat``, which is a suitable value for Fedora and   |
|                | CentOS as well. It means anything Red Hat based.                                                    |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | There is limited experimental support for specifying "debian", "ubuntu", or "suse", which treats the|
|                | automatic installation template file as a preseed/autoyast file format and changes the kernel       |
|                | arguments appropriately. Support for other types of distributions is possible in the future. See the|
|                | Wiki for the latest information about support for these distributions.                              |
+----------------+-----------------------------------------------------------------------------------------------------+
|                | The file used for the answer file, regardless of the breed setting, is the value used for           |
|                | ``--autoinst`` when creating the profile.                                                           |
+----------------+-----------------------------------------------------------------------------------------------------+
| os-version     | Generally this field can be ignored. It is intended to alter some hardware setup for virtualized    |
|                | instances when provisioning guests with Koan. The valid options for ``--os-version`` vary depending |
|                | on what is specified for ``--breed``. If you specify an invalid option, the error message will      |
|                | contain a list of valid OS versions that can be used. If you don't know the OS version or it does   |
|                | not appear in the list, omitting this argument or using ``other`` should be perfectly fine. If you  |
|                | don't encounter any problems with virtualized instances, this option can be safely ignored.         |
+----------------+-----------------------------------------------------------------------------------------------------+
| owners         | Users with small sites and a limited number of admins can probably ignore this option.  All Cobbler |
|                | objects (distros, profiles, systems, and repos) can take a --owners parameter to specify what       |
|                | Cobbler users can edit particular objects.This only applies to the Cobbler WebUI and XML-RPC        |
|                | interface, not the "cobbler" command line tool run from the shell. Furthermore, this is only        |
|                | respected by the ``authz_ownership`` module which must be enabled in ``/etc/cobbler/modules.conf``. |
|                | The value for ``--owners`` is a space separated list of users and groups as specified in            |
|                | ``/etc/cobbler/users.conf``. For more information see the users.conf file as well as the Cobbler    |
|                | Wiki. In the default Cobbler configuration, this value is completely ignored, as is ``users.conf``. |
+----------------+-----------------------------------------------------------------------------------------------------+
| template-files | This feature allows Cobbler to be used as a configuration management system. The argument is a space|
|                | delimited string of ``key=value`` pairs. Each key is the path to a template file, each value is the |
|                | path to install the file on the system. This is described in further detail on the Cobbler Wiki and |
|                | is implemented using special code in the post install. Koan also can retrieve these files from a    |
|                | Cobbler server on demand, effectively allowing Cobbler to function as a lightweight templated       |
|                | configuration management system.                                                                    |
+----------------+-----------------------------------------------------------------------------------------------------+

Cobbler profile
===============

A profile associates a distribution to additional specialized options, such as a installation automation file. Profiles
are the core unit of provisioning and at least one profile must exist for every distribution to be provisioned. A
profile might represent, for instance, a web server or desktop configuration. In this way, profiles define a role to be
performed.

.. code-block:: shell

    $ cobbler profile add --name=string --distro=string [--autoinst=path] [--kopts=string] [--ksmeta=string] [--name-servers=string] [--name-servers-search=string] [--virt-file-size=gigabytes] [--virt-ram=megabytes] [--virt-type=string] [--virt-cpus=integer] [--virt-path=string] [--virt-bridge=string] [--server] [--parent=profile] [--filename=string]

Arguments are the same as listed for distributions, save for the removal of "arch" and "breed", and with the additions
listed below:

+---------------------+------------------------------------------------------------------------------------------------+
| Name                | Description                                                                                    |
+=====================+================================================================================================+
| name                | A descriptive name. This could be something like ``rhel5webservers`` or ``f9desktops``.        |
+---------------------+------------------------------------------------------------------------------------------------+
| distro              | The name of a previously defined Cobbler distribution. This value is required.                 |
+---------------------+------------------------------------------------------------------------------------------------+
| autoinst            | Local filesystem path to a automatic installation file, the file must reside under             |
|                     | ``/var/lib/cobbler/autoinstall_templates``                                                     |
+---------------------+------------------------------------------------------------------------------------------------+
| name-servers        | If your nameservers are not provided by DHCP, you can specify a space separated list of        |
|                     | addresses here to configure each of the installed nodes to use them (provided the automatic    |
|                     | installation files used are installed on a per-system basis). Users with DHCP setups should not|
|                     | need to use this option. This is available to set in profiles to avoid having to set it        |
|                     | repeatedly for each system record.                                                             |
+---------------------+------------------------------------------------------------------------------------------------+
| name-servers-search | You can specify a space separated list of domain names to configure each of the installed nodes|
|                     | to use them as domain search path.  This is available to set in profiles to avoid having to set|
|                     | it repeatedly for each system record.                                                          |
+---------------------+------------------------------------------------------------------------------------------------+
| virt-file-size      | (Virt-only) How large the disk image should be in Gigabytes. The default is 5. This can be a   |
|                     | comma separated list (ex: ``5,6,7``) to allow for multiple disks of different sizes depending  |
|                     | on what is given to ``--virt-path``. This should be input as a integer or decimal value without|
|                     | units.                                                                                         |
+---------------------+------------------------------------------------------------------------------------------------+
| virt-ram            | (Virt-only) How many megabytes of RAM to consume. The default is 512 MB. This should be input  |
|                     | as an integer without units.                                                                   |
+---------------------+------------------------------------------------------------------------------------------------+
| virt-type           | (Virt-only) Koan can install images using either Xen paravirt (``xenpv``) or QEMU/KVM          |
|                     | (``qemu``). Choose one or the other strings to specify, or values will default to attempting to|
|                     | find a compatible installation type on the client system("auto"). See the "Koan" manpage for   |
|                     | more documentation. The default ``--virt-type`` can be configured in the Cobbler settings file |
|                     | such that this parameter does not have to be provided. Other virtualization types are          |
|                     | supported, for information on those options (such as VMware), see the Cobbler Wiki.            |
+---------------------+------------------------------------------------------------------------------------------------+
| virt-cpus           | (Virt-only) How many virtual CPUs should Koan give the virtual machine? The default is 1. This |
|                     | is an integer.                                                                                 |
+---------------------+------------------------------------------------------------------------------------------------+
| virt-path           | (Virt-only) Where to store the virtual image on the host system. Except for advanced cases,    |
|                     | this parameter can usually be omitted. For disk images, the value is usually an absolute path  |
|                     | to an existing directory with an optional filename component. There is support for specifying  |
|                     | partitions ``/dev/sda4`` or volume groups ``VolGroup00``, etc.                                 |
+---------------------+------------------------------------------------------------------------------------------------+
|                     | For multiple disks, separate the values with commas such as ``VolGroup00,VolGroup00`` or       |
|                     | ``/dev/sda4,/dev/sda5``. Both those examples would create two disks for the VM.                |
+---------------------+------------------------------------------------------------------------------------------------+
| virt-bridge         | (Virt-only) This specifies the default bridge to use for all systems defined under this        |
|                     | profile. If not specified, it will assume the default value in the Cobbler settings file, which|
|                     | as shipped in the RPM is ``xenbr0``. If using KVM, this is most likely not correct. You may    |
|                     | want to override this setting in the system object. Bridge settings are important as they      |
|                     | define how outside networking will reach the guest. For more information on bridge setup, see  |
|                     | the Cobbler Wiki, where there is a section describing Koan usage.                              |
+---------------------+------------------------------------------------------------------------------------------------+
| repos               | This is a space delimited list of all the repos (created with ``cobbler repo add`` and updated |
|                     | with ``cobbler reposync``)that this profile can make use of during automated installation. For |
|                     | example, an example might be ``--repos="fc6i386updates fc6i386extras"`` if the profile wants to|
|                     | access these two mirrors that are already mirrored on the Cobbler server. Repo management is   |
|                     | described in greater depth later in the manpage.                                               |
+---------------------+------------------------------------------------------------------------------------------------+
| parent              | This is an advanced feature.                                                                   |
+---------------------+------------------------------------------------------------------------------------------------+
|                     | Profiles may inherit from other profiles in lieu of specifying ``--distro``. Inherited profiles|
|                     | will override any settings specified in their parent, with the exception of ``--ksmeta``       |
|                     | (templating) and ``--kopts`` (kernel options), which will be blended together.                 |
+---------------------+------------------------------------------------------------------------------------------------+
|                     | Example: If profile A has ``--kopts="x=7 y=2"``, B inherits from A, and B has                  |
|                     | ``--kopts="x=9 z=2"``, the actual kernel options that will be used for B are ``x=9 y=2 z=2``.  |
+---------------------+------------------------------------------------------------------------------------------------+
|                     | Example: If profile B has ``--virt-ram=256`` and A has ``--virt-ram=512``, profile B will use  |
|                     | the value 256.                                                                                 |
+---------------------+------------------------------------------------------------------------------------------------+
|                     | Example: If profile A has a ``--virt-file-size=5`` and B does not specify a size, B will use   |
|                     | the value from A.                                                                              |
+---------------------+------------------------------------------------------------------------------------------------+
| server              | This parameter should be useful only in select circumstances. If machines are on a subnet that |
|                     | cannot access the Cobbler server using the name/IP as configured in the Cobbler settings file, |
|                     | use this parameter to override that servername. See also ``--dhcp-tag`` for configuring the    |
|                     | next server and DHCP information of the system if you are also using Cobbler to help manage    |
|                     | your DHCP configuration.                                                                       |
+---------------------+------------------------------------------------------------------------------------------------+
| filename            | This parameter can be used to select the bootloader for network boot. If specified, this must  |
|                     | be a path relative to the TFTP servers root directory. (e.g. grub/grubx64.efi)                 |
|                     | For most use cases the default bootloader is correct and this can be omitted                   |
+---------------------+------------------------------------------------------------------------------------------------+

Cobbler system
==============

System records map a piece of hardware (or a virtual machine) with the Cobbler profile to be assigned to run on it. This
may be thought of as choosing a role for a specific system.

Note that if provisioning via Koan and PXE menus alone, it is not required to create system records in Cobbler, though
they are useful when system specific customizations are required. One such customization would be defining the MAC
address. If there is a specific role intended for a given machine, system records should be created for it.

System commands have a wider variety of control offered over network details. In order to use these to the fullest
possible extent, the automatic installation template used by Cobbler must contain certain automatic installation
snippets (sections of code specifically written for Cobbler to make these values become reality). Compare your automatic
installation templates with the stock ones in /var/lib/cobbler/autoinstall_templates if you have upgraded, to make sure
you can take advantage of all options to their fullest potential. If you are a new Cobbler user, base your automatic
installation templates off of these templates.

Read more about networking setup at: https://cobbler.readthedocs.io/en/release28/4_advanced/advanced%20networking.html

Example:

.. code-block:: bash

    $ cobbler system add --name=string --profile=string [--mac=macaddress] [--ip-address=ipaddress] [--hostname=hostname] [--kopts=string] [--ksmeta=string] [--autoinst=path] [--netboot-enabled=Y/N] [--server=string] [--gateway=string] [--dns-name=string] [--static-routes=string] [--power-address=string] [--power-type=string] [--power-user=string] [--power-pass=string] [--power-id=string]

Adds a Cobbler System to the configuration. Arguments are specified as per "profile add" with the following changes:

+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| Name                                                          | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
+===============================================================+======================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================================+
| name                                                          | The system name works like the name option for other commands.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | If the name looks like a MAC address or an IP, the name will implicitly be used for either --mac or --ip of the first interface, respectively. However, it's usually better to give a descriptive name -- don't rely on this behavior.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | A system created with name "default" has special semantics. If a default system object exists, it sets all undefined systems to PXE to a specific profile.  Without a "default" system name created, PXE will fall through to local boot for unconfigured systems.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | When using "default" name, don't specify any other arguments than --profile ... they won't be used.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| mac                                                           | Specifying a mac address via --mac allows the system object to boot directly to a specific profile via PXE, bypassing Cobbler's PXE menu.  If the name of the Cobbler system already looks like a mac address, this is inferred from the system name and does not need to be specified.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | MAC addresses have the format AA:BB:CC:DD:EE:FF. It's highly recommended to register your MAC-addresses in Cobbler if you're using static addressing with multiple interfaces, or if you are using any of the advanced networking features like bonding, bridges or VLANs.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Cobbler does contain a feature (enabled in /etc/cobbler/settings) that can automatically add new system records when it finds profiles being provisioned on hardware it has seen before.  This may help if you do not have a report of all the MAC addresses in your datacenter/lab configuration.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ip-address                                                    | If Cobbler is configured to generate a DHCP configuration (see advanced section), use this setting to define a specific IP for this system in DHCP.  Leaving off this parameter will result in no DHCP management for this particular system.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Example: --ip-address=192.168.1.50                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | If DHCP management is disabled and the interface is labelled --static=1, this setting will be used for static IP configuration.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Special feature: To control the default PXE behavior for an entire subnet, this field can also be passed in using CIDR notation.  If --ip is CIDR, do not specify any other arguments other than --name and --profile.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | When using the CIDR notation trick, don't specify any arguments other than --name and --profile... they won't be used.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| dns-name                                                      | If using the DNS management feature (see advanced section -- Cobbler supports auto-setup of BIND and dnsmasq), use this to define a hostname for the system to receive from DNS.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Example: --dns-name=mycomputer.example.com                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | This is a per-interface parameter.  If you have multiple interfaces, it may be different for each interface, for example, assume a DMZ / dual-homed setup.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| gateway and netmask                                           | If you are using static IP configurations and the interface is flagged --static=1, these will be applied.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Netmask is a per-interface parameter. Because of the way gateway is stored on the installed OS, gateway is a global parameter. You may use --static-routes for per-interface customizations if required.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| if-gateway                                                    | If you are using static IP configurations and have multiple interfaces, use this to define different gateway for each interface.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | This is a per-interface setting.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| hostname                                                      | This field corresponds to the hostname set in a systems /etc/sysconfig/network file.  This has no bearing on DNS, even when manage_dns is enabled.  Use --dns-name instead for that feature.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | This parameter is assigned once per system, it is not a per-interface setting.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| power-address, power-type, power-user, power-pass, power-id   | Cobbler contains features that enable integration with power management for easier installation, reinstallation, and management of machines in a datacenter environment.  These parameters are described online at :ref:`power-management`. If you have a power-managed datacenter/lab setup, usage of these features may be something you are interested in.                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| static                                                        | Indicates that this interface is statically configured.  Many fields (such as gateway/netmask) will not be used unless this field is enabled.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | This is a per-interface setting.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| static-routes                                                 | This is a space delimited list of ip/mask:gateway routing information in that format. Most systems will not need this information.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | This is a per-interface setting.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| virt-bridge                                                   | (Virt-only) While --virt-bridge is present in the profile object (see above), here it works on an interface by interface basis. For instance it would be possible to have --virt-bridge0=xenbr0 and --virt-bridge1=xenbr1. If not specified in Cobbler for each interface, Koan will use the value as specified in the profile for each interface, which may not always be what is intended, but will be sufficient in most cases.                                                                                                                                                                                                                                                                                                                                                                                   |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | This is a per-interface setting.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| autoinst                                                      | While it is recommended that the --autoinst parameter is only used within for the "profile add" command, there are limited scenarios when an install base switching to Cobbler may have legacy automatic installation files created on aper-system basis (one automatic installation file for each system, nothing shared) and may not want to immediately make use of the Cobbler templating system. This allows specifying a automatic installation file for use on a per-system basis. Creation of a parent profile is still required.  If the automatic installation file is a filesystem location, it will still be treated as a Cobbler template.                                                                                                                                                              |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| netboot-enabled                                               | If set false, the system will be provisionable through Koan but not through standard PXE. This will allow the system to fall back to default PXE boot behavior without deleting the Cobbler system object. The default value allows PXE. Cobbler contains a PXE boot loop prevention feature (pxe_just_once, can be enabled in /etc/cobbler/settings) that can automatically trip off this value after a system gets done installing. This can prevent installs from appearing in an endless loop when the system is set to PXE first in the BIOS order.                                                                                                                                                                                                                                                             |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| repos-enabled                                                 | If set true, Koan can reconfigure repositories after installation. This is described further on the Cobbler Wiki,https://github.com/cobbler/cobbler/wiki/Manage-yum-repos.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| dhcp-tag                                                      | If you are setting up a PXE environment with multiple subnets/gateways, and are using Cobbler to manage a DHCP configuration, you will probably want to use this option. If not, it can be ignored.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | By default, the dhcp tag for all systems is "default" and means that in the DHCP template files the systems will expand out where $insert_cobbler_systems_definitions is found in the DHCP template. However, you may want certain systems to expand out in other places in the DHCP config file.  Setting --dhcp-tag=subnet2 for instance, will cause that system to expand out where $insert_cobbler_system_definitions_subnet2 is found, allowing you to insert directives to specify different subnets (or other parameters) before the DHCP configuration entries for those particular systems.                                                                                                                                                                                                                 |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | This is described further on the Cobbler Wiki.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| interface                                                     | By default flags like --ip, --mac, --dhcp-tag, --dns-name, --netmask, --virt-bridge, and --static-routes operate on the first network interface defined for a system (eth0). However, Cobbler supports an arbitrary number of interfaces. Using--interface=eth1 for instance, will allow creating and editing of a second interface.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Interface naming notes:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Additional interfaces can be specified (for example: eth1, or any name you like, as long as it does not conflict with any reserved names such as kernel module names) for use with the edit command. Defining VLANs this way is also supported, of you want to add VLAN 5 on interface eth0, simply name your interface eth0.5.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Example:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | cobbler system edit --name=foo --ip-address=192.168.1.50 --mac=AA:BB:CC:DD:EE:A0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | cobbler system edit --name=foo --interface=eth0 --ip-address=192.168.1.51 --mac=AA:BB:CC:DD:EE:A1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | cobbler system report foo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Interfaces can be deleted using the --delete-interface option.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Example:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | cobbler system edit --name=foo --interface=eth2 --delete-interface                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| interface-type, interface-master and bonding-opts/bridge-opts | One of the other advanced networking features supported by Cobbler is NIC bonding, bridging and BMC. You can use this to bond multiple physical network interfaces to one single logical interface to reduce single points of failure in your network, to create bridged interfaces for things like tunnels and virtual machine networks, or to manage BMC interface by DHCP. Supported values for the --interface-type parameter are "bond", "bond_slave", "bridge", "bridge_slave","bonded_bridge_slave" and "bmc".  If one of the "_slave" options is specified, you also need to define the master-interface for this bond using --interface-master=INTERFACE. Bonding and bridge options for the master-interface may be specified using --bonding-opts="foo=1 bar=2" or --bridge-opts="foo=1 bar=2".           |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Example:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | cobbler system edit --name=foo --interface=eth0 --mac=AA:BB:CC:DD:EE:00 --interface-type=bond_slave --interface-master=bond0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | cobbler system edit --name=foo --interface=eth1 --mac=AA:BB:CC:DD:EE:01 --interface-type=bond_slave --interface-master=bond0                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | cobbler system edit --name=foo --interface=bond0 --interface-type=bond --bonding-opts="mode=active-backup miimon=100" --ip-address=192.168.0.63 --netmask=255.255.255.0 --gateway=192.168.0.1 --static=1                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | More information about networking setup is available at https://github.com/cobbler/cobbler/wiki/Advanced-networking                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | To review what networking configuration you have for any object, run "cobbler system report" at any time:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | Example:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|                                                               | cobbler system report --name=foo                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
+---------------------------------------------------------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+

Cobbler repo
============

Repository mirroring allows Cobbler to mirror not only install trees ("cobbler import" does this for you) but also
optional packages, 3rd party content, and even updates. Mirroring all of this content locally on your network will
result in faster, more up-to-date installations and faster updates. If you are only provisioning a home setup, this will
probably be overkill, though it can be very useful for larger setups (labs, datacenters, etc).

.. code-block:: shell

    $ cobbler repo add --mirror=url --name=string [--rpmlist=list] [--creatrepo-flags=string] [--keep-updated=Y/N] [--priority=number] [--arch=string] [--mirror-locally=Y/N] [--breed=yum|rsync|rhn] [--mirror_type=baseurl|mirrorlist|metalink]

+------------------+---------------------------------------------------------------------------------------------------+
| Name             | Description                                                                                       |
+==================+===================================================================================================+
| mirror           | The address of the yum mirror. This can be an ``rsync://``-URL, an ssh location, or a ``http://`` |
|                  | or ``ftp://`` mirror location. Filesystem paths also work.                                        |
+------------------+---------------------------------------------------------------------------------------------------+
|                  | The mirror address should specify an exact repository to mirror -- just one architecture and just |
|                  | one distribution. If you have a separate repo to mirror for a different arch, add that repo       |
|                  | separately.                                                                                       |
+------------------+---------------------------------------------------------------------------------------------------+
|                  | Here's an example of what looks like a good URL:                                                  |
+------------------+---------------------------------------------------------------------------------------------------+
|                  | - ``rsync://yourmirror.example.com/fedora-linux-core/updates/6/i386`` (for rsync protocol)        |
|                  | - ``http://mirrors.kernel.org/fedora/extras/6/i386/`` (for http)                                  |
|                  | - ``user@yourmirror.example.com/fedora-linux-core/updates/6/i386``  (for SSH)                     |
+------------------+---------------------------------------------------------------------------------------------------+
|                  | Experimental support is also provided for mirroring RHN content when you need a fast local mirror.|
|                  | The mirror syntax for this is ``--mirror=rhn://channel-name`` and you must have entitlements for  |
|                  | this to work. This requires the Cobbler server to be installed on RHEL 5 or later. You will also  |
|                  | need a version of ``yum-utils`` equal or greater to 1.0.4.                                        |
+------------------+---------------------------------------------------------------------------------------------------+
| mirror_type      | The type of the yum mirror. This can be an ``baseurl``- list of URLs, ``mirrorlist`` - URL of     |
|                  | a mirrorlist, or a ``metalink`` - URL of a metalink. The defaults are ``baseurl``.                |
+------------------+---------------------------------------------------------------------------------------------------+
| name             | This name is used as the save location for the mirror. If the mirror represented, say, Fedora     |
|                  | Core 6 i386 updates, a good name would be ``fc6i386updates``. Again, be specific.                 |
+------------------+---------------------------------------------------------------------------------------------------+
|                  | This name corresponds with values given to the ``--repos`` parameter of ``cobbler profile add``.  |
|                  | If a profile has a ``--repos``-value that matches the name given here, that repo can be           |
|                  | automatically set up during provisioning (when supported) and installed systems will also use the |
|                  | boot server as a mirror (unless ``yum_post_install_mirror`` is disabled in the settings file). By |
|                  | default the provisioning server will act as a mirror to systems it installs, which may not be     |
|                  | desirable for laptop configurations, etc.                                                         |
+------------------+---------------------------------------------------------------------------------------------------+
|                  | Distros that can make use of yum repositories during automatic installation include FC6 and later,|
|                  | RHEL 5 and later, and derivative distributions.                                                   |
+------------------+---------------------------------------------------------------------------------------------------+
|                  | See the documentation on ``cobbler profile add`` for more information.                            |
+------------------+---------------------------------------------------------------------------------------------------+
| rpm-list         | By specifying a space-delimited list of package names for ``--rpm-list``, one can decide to mirror|
|                  | only a part of a repo (the list of packages given, plus dependencies). This may be helpful in     |
|                  | conserving time/space/bandwidth. For instance, when mirroring FC6 Extras, it may be desired to    |
|                  | mirror just Cobbler and Koan, and skip all of the game packages. To do this, use                  |
|                  | ``--rpm-list="cobbler koan"``.                                                                    |
+------------------+---------------------------------------------------------------------------------------------------+
|                  | This option only works for ``http://`` and ``ftp://`` repositories (as it is powered by           |
|                  | yumdownloader). It will be ignored for other mirror types, such as local paths and ``rsync://``   |
|                  | mirrors.                                                                                          |
+------------------+---------------------------------------------------------------------------------------------------+
| createrepo-flags | Specifies optional flags to feed into the createrepo tool, which is called when                   |
|                  | ``cobbler reposync`` is run for the given repository. The defaults are ``-c cache``.              |
+------------------+---------------------------------------------------------------------------------------------------+
| keep-updated     | Specifies that the named repository should not be updated during a normal "cobbler reposync". The |
|                  | repo may still be updated by name. The repo should be synced at least once before disabling this  |
|                  | feature. See "cobbler reposync" below.                                                            |
+------------------+---------------------------------------------------------------------------------------------------+
| mirror-locally   | When set to ``N``, specifies that this yum repo is to be referenced directly via automatic        |
|                  | installation files and not mirrored locally on the Cobbler server. Only ``http://`` and ``ftp://``|
|                  | mirror urls are supported when using ``--mirror-locally=N``, you cannot use filesystem URLs.      |
+------------------+---------------------------------------------------------------------------------------------------+
| priority         | Specifies the priority of the repository (the lower the number, the higher the priority), which   |
|                  | applies to installed machines using the repositories that also have the yum priorities plugin     |
|                  | installed. The default priority for the plugins 99, as is that of all Cobbler mirrored            |
|                  | repositories.                                                                                     |
+------------------+---------------------------------------------------------------------------------------------------+
| arch             | Specifies what architecture the repository should use. By default the current system arch (of the |
|                  | server) is used,which may not be desirable. Using this to override the default arch allows        |
|                  | mirroring of source repositories(using ``--arch=src``).                                           |
+------------------+---------------------------------------------------------------------------------------------------+
| yumopts          | Sets values for additional yum options that the repo should use on installed systems. For instance|
|                  | if a yum plugin takes a certain parameter "alpha" and "beta", use something like                  |
|                  | ``--yumopts="alpha=2 beta=3"``.                                                                   |
+------------------+---------------------------------------------------------------------------------------------------+
| breed            | Ordinarily Cobbler's repo system will understand what you mean without supplying this parameter,  |
|                  | though you can set it explicitly if needed.                                                       |
+------------------+---------------------------------------------------------------------------------------------------+

.. code-block:: shell

    $ cobbler repo autoadd

Add enabled yum repositories from ``dnf repolist --enabled`` list. The repository names are generated using the
<repo id>-<releasever>-<arch> pattern (ex: fedora-32-x86_64). Existing repositories with such names are not overwritten.

Cobbler image
=============

Example:

.. code-block:: shell

    $ cobbler image

cobbler mgmtclass
=================

Management classes allows Cobbler to function as an configuration management system. Cobbler currently supports the
following resource types:

1. Packages
2. Files

Resources are executed in the order listed above.

.. code-block:: shell

    $ cobbler mgmtclass add --name=string --comment=string [--packages=list] [--files=list]

+----------+-----------------------------------------------------------------------------------------------------------+
| Name     | Description                                                                                               |
+==========+===========================================================================================================+
| name     | The name of the mgmtclass. Use this name when adding a management class to a system, profile, or distro.  |
|          | To add a mgmtclass to an existing system use something like                                               |
|          | (``cobbler system edit --name="madhatter" --mgmt-classes="http mysql"``).                                 |
+----------+-----------------------------------------------------------------------------------------------------------+
| comment  | A comment that describes the functions of the management class.                                           |
+----------+-----------------------------------------------------------------------------------------------------------+
| packages | Specifies a list of package resources required by the management class.                                   |
+----------+-----------------------------------------------------------------------------------------------------------+
| files    | Specifies a list of file resources required by the management class.                                      |
+----------+-----------------------------------------------------------------------------------------------------------+


Cobbler package
===============

Package resources are managed using ``cobbler package add``

Actions:

+-----------+--------------------------------+
| Name      | Description                    |
+===========+================================+
| install   | Install the package. [Default] |
+-----------+--------------------------------+
| uninstall | Uninstall the package.         |
+-----------+--------------------------------+

Attributes:

+-----------+--------------------------------------------------------+
| Name      | Description                                            |
+===========+========================================================+
| installer | Which package manager to use, vaild options [rpm|yum]. |
+-----------+--------------------------------------------------------+
| version   | Which version of the package to install.               |
+-----------+--------------------------------------------------------+

Example:

.. code-block:: shell

    $ cobbler package add --name=string --comment=string [--action=install|uninstall] --installer=string [--version=string]

Cobbler file
============

Actions:

+--------+----------------------------+
| Name   | Description                |
+========+============================+
| create | Create the file. [Default] |
+--------+----------------------------+
| remove | Remove the file.           |
+--------+----------------------------+

Attributes:

+----------+--------------------------------+
| Name     | Description                    |
+==========+================================+
| mode     | Permission mode (as in chmod). |
+----------+--------------------------------+
| group    | The group owner of the file.   |
+----------+--------------------------------+
| user     | The user for the file.         |
+----------+--------------------------------+
| path     | The path for the file.         |
+----------+--------------------------------+
| template | The template for the file.     |
+----------+--------------------------------+

Example:

.. code-block:: shell

    $ cobbler file add --name=string --comment=string [--action=string] --mode=string --group=string --owner=string --path=string [--template=string]

cobbler aclsetup
================

Example:

.. code-block:: shell

    $ cobbler aclsetup

Cobbler buildiso
================

Example:

.. code-block:: shell

    $ cobbler buildiso

Cobbler import
==============

Example:

.. code-block:: shell

    $ cobbler import

Cobbler list
============

This list all the names grouped by type. Identically to ``cobbler report`` there are subcommands for most of the other
Cobbler commands. (Currently: distro, profile, system, repo, image, mgmtclass, package, file)

.. code-block:: shell

    $ cobbler list

Cobbler replicate
=================

Cobbler can replicate configurations from a master Cobbler server. Each Cobbler server is still expected to have a
locally relevant ``/etc/cobbler/cobbler.conf`` and ``modules.conf``, as these files are not synced.

This feature is intended for load-balancing, disaster-recovery, backup, or multiple geography support.

Cobbler can replicate data from a central server.

Objects that need to be replicated should be specified with a pattern, such as ``--profiles="webservers* dbservers*"``
or ``--systems="*.example.org"``. All objects matched by the pattern, and all dependencies of those objects matched by
the pattern (recursively) will be transferred from the remote server to the central server. This is to say if you intend
to transfer ``*.example.org`` and the definition of the systems have not changed, but a profile above them has changed,
the changes to that profile will also be transferred.

In the case where objects are more recent on the local server, those changes will not be overridden locally.

Common data locations will be rsync'ed from the master server unless ``--omit-data`` is specified.

To delete objects that are no longer present on the master server, use ``--prune``.

**Warning**: This will delete all object types not present on the remote server from the local server, and is recursive.
If you use prune, it is best to manage Cobbler centrally and not expect changes made on the slave servers to be
preserved. It is not currently possible to just prune objects of a specific type.

Example:

.. code-block:: shell

    $ cobbler replicate --master=cobbler.example.org [--distros=pattern] [--profiles=pattern] [--systems=pattern] [--repos-pattern] [--images=pattern] [--prune] [--omit-data]

Cobbler report
=================

This lists all configuration which Cobbler can obtain from the saved data. There are also ``report`` subcommands for
most of the other Cobbler commands (currently: distro, profile, system, repo, image, mgmtclass, package, file).

.. code-block:: shell

    $ cobbler report --name=[object-name]

--name=[object-name]

Optional parameter which filters for object with the given name.

Cobbler reposync
================

Example:

.. code-block:: shell

    $ cobbler reposync [--only=ONLY] [--tries=TRIES] [--no-fail]

Cobbler reposync is the command to use to update repos as configured with ``cobbler repo add``. Mirroring can
take a long time, and usage of cobbler reposync prior to usage is needed to ensure provisioned systems have the
files they need to actually use the mirrored repositories. If you just add repos and never run ``cobbler reposync``,
the repos will never be mirrored. This is probably a command you would want to put on a crontab, though the
frequency of that crontab and where the output goes is left up to the systems administrator.

For those familiar with dnf’s reposync, cobbler’s reposync is (in most uses) a wrapper around the ``dnf reposync``
command. Please use ``cobbler reposync`` to update cobbler mirrors, as dnf’s reposync does not perform all required steps.
Also cobbler adds support for rsync and SSH locations, where as dnf’s reposync only supports what dnf supports
(http/ftp).

If you ever want to update a certain repository you can run:
``cobbler reposync --only="reponame1" ...``

When updating repos by name, a repo will be updated even if it is set to be not updated during a regular reposync
operation (ex: ``cobbler repo edit –name=reponame1 –keep-updated=0``).
Note that if a cobbler import provides enough information to use the boot server as a yum mirror for core packages,
cobbler can set up automatic installation files to use the cobbler server as a mirror instead of the outside world. If
this feature is desirable, it can be turned on by ``setting yum_post_install_mirror`` to 1 in /etc/settings (and running
``cobbler sync``). You should not use this feature if machines are provisioned on a different VLAN/network than
production, or if you are provisioning laptops that will want to acquire updates on multiple networks.

The flags --tries=N (for example, ``--tries=3``) and ``--no-fail`` should likely be used when putting re-posync on a crontab.
They ensure network glitches in one repo can be retried and also that a failure to synchronize
one repo does not stop other repositories from being synchronized.

Cobbler sync
============

The sync command is very important, though very often unnecessary for most situations. It's primary purpose is to force
a rewrite of all configuration files, distribution files in the TFTP root, and to restart managed services. So why is it
unnecessary? Because in most common situations (after an object is edited, for example), Cobbler executes what is known
as a "lite sync" which rewrites most critical files.

When is a full sync required? When you are using ``manage_dhcpd`` (Managing DHCP) with systems that use static leases.
In that case, a full sync is required to rewrite the ``dhcpd.conf`` file and to restart the dhcpd service.

Cobbler sync is used to repair or rebuild the contents ``/tftpboot`` or ``/var/www/cobbler`` when something has changed
behind the scenes. It brings the filesystem up to date with the configuration as understood by Cobbler.

Sync should be run whenever files in ``/var/lib/cobbler`` are manually edited (which is not recommended except for the
settings file) or when making changes to automatic installation files. In practice, this should not happen often, though
running sync too many times does not cause any adverse effects.

If using Cobbler to manage a DHCP and/or DNS server (see the advanced section of this manpage), sync does need to be run
after systems are added to regenerate and reload the DHCP/DNS configurations.

The sync process can also be kicked off from the web interface.

Example:

.. code-block:: shell

    $ cobbler sync

Cobbler validate-autoinstalls
=============================

Example:

.. code-block:: shell

    $ cobbler validate-autoinstalls

Cobbler version
===============

Example:

.. code-block:: shell

    $ cobbler version

Cobbler signature
=================

Example:

.. code-block:: shell

    $ cobbler signature

Cobbler get-loaders
===================

Example:

.. code-block:: shell

    $ cobbler get-loaders

Cobbler hardlink
================

Example:

.. code-block:: shell

    $ cobbler hardlink

EXIT_STATUS
###########

Cobbler's command line returns a zero for success and non-zero for failure.

Additional Help
###############

We have a Gitter Channel and you also can ask questions as GitHub issues. The IRC Channel on Freenode (#cobbler) is not
that active but sometimes there are people who can help you.

The way we would prefer are GitHub issues as they are easily searchable.
