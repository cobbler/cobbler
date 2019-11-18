.. _settings:

****************
Cobbler Settings
****************

Cobbler has many features, many of which are disabled out of the box for simplicity's sake. Various settings are used to
enable these features and to modify how they work, while other settings are used to provide default functionality to
base features (for example, the default encrypted password to use).

.. _dynamic-settings:

Dynamic Settings
################

Prior to Cobbler 2.4.0, any changes to ``/etc/cobbler/settings`` required a restart of the cobblerd daemon for those
changes to take affect. Now, with 2.4.0+, you can easily modify settings on the fly via the ``cobbler setting`` command.

Enabling Dynamic Settings
=========================

Dynamic settings are not enabled by default. In order to enable them, you must set "allow_dynamic_settings: 1" in
``/etc/cobbler/settings`` and restart cobblerd.

Caveats
=======

Over the years, the Cobbler settings file has grown organically, and as such has not always had consistent spacing
applied to the YAML entries it contains. In order to ensure that augeas can correctly rewrite the settings, you must run
the following sed command:

.. code-block:: bash

    $ sed -i 's/^[[:space:]]\+/ /' /etc/cobbler/settings

When dynamic settings are enabled, the ``cobbler check`` command will also print out this recommendation.

CLI Commands
************

Please see the :ref:`Dynamic Settings CLI Command <cobbler-command-setting>` section for details on the dynamic settings
commands.

Complete Settings List
######################

This page documents all settings ``/etc/cobbler/settings`` available for configuring both cobblerd and the cobbler CLI
command. Be sure to restart the cobblerd service after making changes to this file.

.. note:: The defaults shown here are noted via JSON syntax. The settings file is stored as YAML, so be sure to format
   it correctly or cobblerd and the CLI command will not work properly.

allow_duplicate_hostnames
=========================

* **type:** Boolean
* **default:** 0
* **Description:** If set, Cobbler will allow multiple systems to use the same FQDN for the ``--dns-name`` interface
  option. This field is used for system identification for things like configuration management integration, so take
  care when enabling it.

allow_duplicate_ips
===================

* **type:** Boolean
* **default:** 0
* **Description:** If set, Cobbler will allow multiple systems to use the same IP address for interfaces. If enabled,
  this could impact managed services like DHCP and DNS where multiple active systems conflict.

allow_duplicate_macs
====================

* **type:** Boolean
* **default:** 0
* **Description:** If set, Cobbler will allow multiple systems to use the same MAC address for interfaces. If enabled,
  this could impact managed services like DHCP and DNS where multiple active systems conflict.

allow_dynamic_settings
======================

* **type:** Boolean
* **default:** 0
* **Description:** If enabled, Cobbler will allow settings to be modified on the fly without a restart to the cobblerd
  daemon. Please reference the :ref:`Dynamic Settings <cobbler-command-setting>` section for more details.

anamon_enabled
==============

* **type:** Boolean
* **default:** 0
* **Description:** If set, anamon will be enabled during the Anaconda kickstart process. This is specific to Red Hat
  style kickstarts only.

Please refer to the :ref:`anaconda` section for more details.

bind_chroot_path
================

* **type:** String
* **default:** ""
* **Description:** This sets the path of the directory in which bind-chroot compatible configuration files will be
  created. In most situations, this should be automatically detected by default (set to an empty string).

Please refer to the :ref:`manage-dns` section for more details.

bind_master
===========

* **type:** String
* **default:** "127.0.0.1"
* **Description:** The bind master to use when creating slave DNS zones.

Please refer to the :ref:`manage-dns` section for more details.

build_reporting_email
=====================

* **type:** Array of Strings
* **default:** ['root@localhost']
* **Description:** A list of email addresses to send build reports to.

build_reporting_enabled
=======================

* **type:** Boolean
* **default:** 0
* **Description:** Setting this option enables build reporting emails.

build_reporting_sender
======================

* **type:** String
* **default:** ""
* **Description:** The email address to use as the sender of a build report email (optional).

build_reporting_smtp_server
===========================

* **type:** String
* **default:** "localhost"
* **Description:** The SMTP server to use for build report emails.

build_reporting_subject
=======================

* **type:** String
* **default:** ""
* **Description:** This setting allows you to override the default auto-generated subject lines for build report emails.

build_reporting_to_address
==========================

* **type:** String
* **default:** ""
* **Description:** Not currently used.

buildisodir
===========

* **type:** String
* **default:** "/var/cache/cobbler/buildiso"
* **Description:** The default directory to use as scratch space when building an ISO via Cobbler. This can be
  overridden on the command line.

Please refer to the :ref:`Build ISO <buildiso>` section for more details.

cheetah_import_whitelist
========================

* **type:** Array of Strings
* **default:** ['random', 're', 'time']
* **Description:** This setting creates a whitelist of python modules that can be imported in a template.

This is a security issue, as allowing certain python modules would allow users to create templates that overwrite system
files (ie. the os module) or execute shell commands (ie. the subprocess module). Make sure you understand the
capabilities a python module has before adding them to this whitelist.

client_use_localhost
====================

* **type:** Boolean
* **default:** 0
* **Description:** If enabled, all commands will be forced to use the localhost address instead of the "server" setting.
  The cobbler client command can be used to manage remote cobblerd instances, so enabling this option would force all
  cobbler commands to operate locally only.

cobbler_master
==============

* **type:** String
* **default:** ""
* **Description:** The default server to pull from when using the replicate command.

Please refer to the :ref:`replication` section for more details.

consoles
========

* **type:** String
* **default:** "/var/consoles"
* **Description:** The path to the directory containing system consoles, used primarily for clearing logs and messages.

createrepo_flags
================

* **type:** String
* **default:** "-c cache -s sha --update"
* **Description:** Default options to use for the createrepo command when creating new repositories during a reposync.

If you have ``createrepo >= 0.4.10``, consider ``-c cache --update -C``, which can dramatically improve your
``cobbler reposync`` time. ``-s sha`` enables working with Fedora repos from F11/F12 from EL-4 or EL-5 without
``python-hashlib`` installed (which is not available on EL-4)

Please refer to the :ref:`package-management` section for more details.

default_deployment_method
=========================

* **type:** String
* **default:** "ssh"
* **Description:** Not currently used.

default_kickstart
=================

* **type:** String
* **default:** "/var/lib/cobbler/kickstarts/default.ks"
* **Description:** The default kickstart file to use if no other is specified. This option is effectively deprecated, as
  the default kickstart to use is now specified in the distro signatures configuration file. Please see the
  :ref:`distro-signatures` section for more details.

default_name_servers
====================

* **type:** Array of Strings
* **default:** []
* **Description:** A list of name servers to assign to all systems and profiles that are built. This will be used both
  pre and post install.

default_name_servers_search
===========================

* **type:** Array of Strings
* **default:** []
* **Description:** A list of domains to search by default. This will be inserted into the resolv.conf file.

default_ownership
=================

* **type:** Array of Strings
* **default:** ['admin']
* **Description:** A list of owners to assign to newly created objects. This is used only for Web UI authorization.

Please refer to the :ref:`web-authorization` section for more details.

default_password_crypted
========================

* **type:** String
* **default:** "$1$wrWZXfa7$Ts7jMmpdZkTlu0lSx1A/I/" (cobbler)
* **Description:** The default hashed password to use in kickstarts. The default value is "cobbler" (hashed).

To generate a new hashed password, use the following command: ``$ openssl passwd -1``

Be sure to enclose the hash with quotation marks.

default_template_type
=====================

* **type:** String
* **default:** "cheetah"
* **Description:** The default template type to use when parsing kickstarts and snippets. The default template type is
  Cheetah, and changing this value will currently break all snippets and templates currently shipped with Cobbler.

Please refer to the :ref:`alternative-template-formats` section for more details.

default_virt_bridge
===================

* **type:** String
* **default:** "xenbr0"
* **Description:** The default bridge to assign virtual interfaces to.

default_virt_disk_driver
========================

* **type:** String
* **default:** "raw"
* **Description:** The default disk driver to use for virtual disks. Older versions of ``python-virtinst`` do not
  support changing this at build time, so this option will be ignored in those cases.

default_virt_file_size
======================

* **type:** Integer
* **default:** 5
* **Description:** The default size (in gigabytes) to use for new virtual disks.

default_virt_ram
================

* **type:** Integer
* **default:** 512
* **Description:** The default size (in megabytes) of RAM to assign to new virtual machines.

default_virt_type
=================

* **type:** String
* **default:** "xenpv"
* **Description:** The default virtualization type to use for virtual machines created with the koan utility.

Please refer to the https://koan.readthedocs.io/ section for more details.

enable_gpxe
===========

* **type:** Boolean
* **default:** 0
* **Description:** If set, Cobbler will enable the use of gPXE.

Please refer to the :ref:`using-gpxe` section for more details.

enable_menu
===========

* **type:** Boolean
* **default:** 1
* **Description:** If set, Cobbler will add each new profile entry to the default PXE boot menu. This can be overridden
  on a per-profile basis when adding/editing profiles with ``--enable-menu=0/1``. Users should ordinarily leave this
  setting enabled unless they are concerned with accidental reinstalls from users who select an entry at the PXE boot
  menu. Adding a password to the boot menus templates may also be a good solution to prevent unwanted reinstallations.

func_auto_setup
===============

* **type:** Boolean
* **default:** 0
* **Description:** If set, Cobbler will install and configure Func. This makes sure each installed machine is set up to
  use func out of the box, which is a powerful way to script and control remote machines.

Please refer to the :ref:`config-management-func` section for more details.

func_master
===========

* **type:** String
* **default:** "overlord.example.org"
* **Description:** The Func master server (overlord) to use by default.

Please refer to the :ref:`config-management-func` section for more details.

http_port
=========

* **type:** String
* **default:** "80"
* **Description:** The port on which Apache is listening. Only change this if your instance of Apache is listening on a
  different port (for example: 8080).

isc_set_host_name
=================

* **type:** Boolean
* **default:** 0
* **Description:** Not currently used.

iso_template_dir
================

* **type:** String
* **default:** "/etc/cobbler/iso"
* **Description:** The directory containing the buildiso.template, which is a SYSLINUX style configuration file for use
  in the buildiso process.

Please refer to the :ref:`buildiso` section for more details.

kerberos_realm
==============

* **type:** String
* **default:** "EXAMPLE.COM"
* **Description:** Not currently used (all kerberos configuration must currently be done manually).

Please refer to the :ref:`kerberos` section for more details.

kernel_options
==============

* **type:** Dictionary
* **default:** {'ksdevice': 'bootif', 'lang': ' ', 'text': '~'}
* **Description:** A dictionary of key/value pairs that will be added to the kernel command line during the installation
  only (post-installation options are specified at the distro/profile/etc. object level).

By default, each key/value pair will be show up as key=value in the kernel command line. Setting the value for a given
key to '~' (tilde) will cause the option to be printed by itself with no '='.

.. note:: The kernel command line has a maximum character limitation of 256 characters. Cobbler will print a warning if
   you exceed this limit.

kernel_options_s390x
====================

* **type:** Dictionary
* **default:** {'vnc': '~', 'ip': False, 'RUNKS': 1, 'ramdisk_size': 40000, 'ro': '~', 'root': '/dev/ram0'}
* **Description:** Same as the kernel_options setting, but specific to s390x architectures.

ldap_anonymous_bind
===================

* **type:** Boolean
* **default:** 1
* **Description:** If set, the LDAP authentication module will use an anonymous bind when connecting to the LDAP server.

Please refer to the :ref:`ldap` section for more details.

ldap_base_dn
============

* **type:** String
* **default:** "DC=example,DC=com"
* **Description:** The base DN to use for LDAP authentication.

Please refer to the :ref:`ldap` section for more details.

ldap_management_default_type
============================

* **type:** String
* **default:** "authconfig"
* **Description:** Not currently used.

Please refer to the :ref:`ldap` section for more details.

ldap_port
=========

* **type:** Integer
* **default:** 389
* **Description:** The port to use when connecting to the LDAP server. If TLS is enabled and this port is the default of
  389, cobbler will internally convert it to 636 for SSL.

Please refer to the :ref:`ldap` section for more details.

ldap_search_bind_dn
===================

* **type:** String
* **default:** ""
* **Description:** The DN to use for binding to the LDAP server for authentication, used only if
  ``ldap_anonymous_bind=0``.

Please refer to the :ref:`ldap` section for more details.

ldap_search_passwd
==================

* **type:** String
* **default:** ""
* **Description:** The password to use when binding to the LDA server for authentication, used only if
  ``ldap_anonymous_bind=0``.

Please refer to the :ref:`ldap` section for more details.

ldap_search_prefix
==================

* **type:** String
* **default:** "uid="
* **Description:** The prefix to use for searches when querying the LDAP server.

Please refer to the :ref:`ldap` section for more details.

ldap_server
===========

* **type:** Boolean
* **default:** "ldap.example.com"
* **Description:** The LDAP server to use for LDAP authentication.

Please refer to the :ref:`ldap` section for more details.

ldap_tls
========

* **type:** Boolean
* **default:** 1
* **Description:** If set, the LDAP authentication will occur over a SSL/TLS encrypted connection.

Please refer to the :ref:`ldap` section for more details.

ldap_tls_cacertfile
===================

* **type:** Boolean
* **default:** 1
* **Description:** The CA certificate file to use when using TLS encryption.

Please refer to the :ref:`ldap` section for more details.

ldap_tls_keyfile
================

* **type:** Boolean
* **default:** 1
* **Description:** The certificate key file to use when using TLS encryption.

Please refer to the :ref:`ldap` section for more details.

ldap_tls_certfile
=================

* **type:** Boolean
* **default:** 1
* **Description:** The certificate file to use when using TLS encryption.

Please refer to the :ref:`ldap` section for more details.

manage_dhcp
===========

* **type:** Boolean
* **default:** 0
* **Description:** If enabled, Cobbler will rewrite the dhcpd.conf file based on the template
  ``/etc/cobbler/dhcp.template``. If you are using static IP addresses for interfaces, you must enable this option so
  that static lease entries are written and available for the PXE phase of the installation.

Alternatively, if DNSMASQ is being used for DNS/DHCP, it will manage those configuration files.

Please refer to the :ref:`manage-dhcp` section for more details.

manage_dns
==========

* **type:** Boolean
* **default:** 0
* **Description:** If enabled, Cobbler will write the named.conf and BIND zone files based on templates and other
  settings.

Alternatively, if DNSMASQ is being used for DNS/DHCP, it will manage those configuration files.

Please refer to the :ref:`manage-dns` section for more details.

manage_forward_zones
====================

* **type:** List of Strings
* **default:** []
* **Description:** If enabled along with the manage_dns option, Cobbler will generate configurations for the
  forward-based zones specified in the list.

Please refer to the :ref:`manage-dns` section for more details.

manage_reverse_zones
====================

* **type:** List of Strings
* **default:** []
* **Description:** If enabled along with the ``manage_dns`` option, Cobbler will generate configurations for the
  reverse-based zones specified in the list.

Please refer to the :ref:`manage-dns` section for more details.

manage_rsync
============

* **type:** Boolean
* **default:** 0
* **Description:** If set, Cobbler will generate the ``rsyncd.conf`` configuration file. This is required if using a
  system running cobblerd as a replica master.

Please refer to the :ref:`replication` section for more details.

manage_tftpd
============

* **type:** Boolean
* **default:** 1
* **Description:** If set, Cobbler will copy files required for the PXE netboot process to the TFTPD root directory and
  will also generate PXE boot configuration files for systems and profiles.

Please refer to the :ref:`config-management` section for more details.

mgmt_classes
============

* **type:** List of Strings
* **default:** []
* **Description:** A default list of management class names to give all objects, for use with configuration management
  integration.

Please refer to the :ref:`config-management` section for
more details.

mgmt_parameters
===============

* **type:** Dictionary
* **default:** {'from_cobbler': 1}
* **Description:** A default list of management parameters to give all objects, for use with configuration management
  integration.

Please refer to the :ref:`config-management` section for more details.

next_server
===========

* **type:** String
* **default:** "127.0.0.1"
* **Description:** If manage_dhcp is enabled, this will be the default next-server value passed to systems that are PXE
  booting. This value can be overriden on a per-system basis via the ``--server`` option.

Please refer to the :ref:`multi-homed-cobbler-servers` section for more details.

power_management_default_type
=============================

* **type:** String
* **default:** "ipmitool"
* **Description:** The default power management type, when using Cobbler's power management feature.

Please refer to the :ref:`power-management` section for more details.

power_template_dir
==================

* **type:** String
* **default:** "/etc/cobbler/power"
* **Description:** The path to the directory containing templates that will be used for generating data sent to the
  various power management functions (typically provided by cluster fencing agents). As of 2.2.3, templates are no
  longer required for the default function of most fence agents.

Please refer to the :ref:`power-management` section for more details.

puppet_auto_setup
=================

* **type:** Boolean
* **default:** 0
* **Description:** If enabled, Cobbler will install and configure the
  `Puppet configuration management <https://puppet.com/solutions/configuration-management>`_ software on new systems.

Please refer to the :ref:`config-management-puppet` section for more details.

puppetca_path
=============

* **type:** String
* **default:** "/usr/sbin/puppetca"
* **Description:** The path to the puppetca command, which is used by cobbler to auto-register and cleanup Puppet CA
  certificates during the build process for new systems.

Please refer to the :ref:`config-management-puppet` section for more details.

pxe_just_once
=============

* **type:** Boolean
* **default:** 0
* **Description:** If enabled, Cobbler will set the netboot_enabled flag for systems to 0 when the build process is
  complete. This prevents systems from ending up in a PXE reboot/installation loop which can happen when PXE is set to
  the default boot option.

.. note:: This requires the use of the ``$SNIPPET('kickstart_done')`` in your %post (usually the last line of the
   ``%post`` script). This snippet is included in the ``sample*.ks`` files, so review those as a reference for use.

pxe_template_dir
================

* **type:** String
* **default:** "/etc/cobbler/pxe"
* **Description:** The directory containing the templates used for generating PXE boot configuration files, when
  ``manage_tftpd`` is enabled.

redhat_management_key
=====================

* **type:** String
* **default:** ""
* **Description:** The default RHN registration key to use with the included RHN/Satellite/Spacewalk registration
  scripts. This can be overridden on a per-object basis, for instance when you want to use different registration keys
  to place systems in different RHN channels, etc.

redhat_management_permissive
============================

* **type:** Boolean
* **default:** 0
* **Description:** If set, this will allow per-user access in the Web UI when using the ``authn_spacewalk`` module for
  authentication.

However, doing so will permit all Spacewalk/Satellite users with certain roles (``config_admin`` and ``org_admin``) to
edit all of cobbler's configuration. Users should turn this on only if they want this behavior and do not have a
cross-multi-org seperation concern. If you have a single org in your satellite, it's probably safe to turn this on to
enable the use of the Web UI alongside a Satellite install.

Please refer to the :ref:`web-authentication-spacewalk` section for more details.

redhat_management_server
========================

* **type:** String
* **default:** "xmlrpc.rhn.redhat.com"
* **Description:** The default RHN server to use for registration via the included RHN/Satellite/Spacewalk registration
  scripts as well as the ``authn_spacewalk`` authentication module.

Please refer to the :ref:`web-authentication-spacewalk` section for more details.

redhat_management_type
======================

* **type:** String
* **default:** "off"
* **Description:** When using a Red Hat management platform in addition to Cobbler, this option is used to speficy the
  type of RHN server being used:

.. code-block:: none

    "off"    : I'm not using Red Hat Network, Satellite, or Spacewalk
    "hosted" : I'm using Red Hat Network
    "site"   : I'm using Red Hat Satellite Server or Spacewalk

Please refer to the :ref:`tips-for-rhn` section for more details.

register_new_installs
=====================

* **type:** Boolean
* **default:** 0
* **Description:** If enabled, this allows ``/usr/bin/cobbler-register`` (part of the koan package) to be used to
  remotely add new cobbler system records to cobbler. This effectively allows for registration of new hardware from
  system records, even during the build process when building a system based only on a profile.

Please refer to the :ref:`auto-registration` section for more
details.

remove_old_puppet_certs_automatically
=====================================

* **type:** Boolean
* **default:** 0
* **Description:** If enabled when using Puppet integration, Cobbler can be triggered (through the use of snippets) to
  automatically remove CA certificates for a given FQDN. This prevents failed Puppet registrations when a conflicting
  cert already exists.

Please refer to the :ref:`config-management-puppet` section for more details.

replicate_rsync_options
=======================

* **type:** String
* **default:** "-avzH"
* **Description:** This setting is used to specify additional options that are passed to the rsync command during the
  replicate process.

Please refer to the :ref:`replication` section for more details.

reposync_flags
==============

* **type:** String
* **default:** "-l -n -d"
* **Description:** This setting is used to specify additional options that are passed to the reposync command during the
  reposync process. This is specific to yum, and is not used with apt or other repository types.

Please refer to the :ref:`reposync` section for more details.

restart_dhcp
============

* **type:** Boolean
* **default:** 1
* **Description:** If enabled, Cobbler will restart the dhcpd or dnsmasq daemon during a ``cobbler sync`` and after all
  configuration files have been generated. This will only happen when ``manage_dhcp`` is enabled.

Please refer to the :ref:`manage-dhcp` section for more details.

restart_dns
===========

* **type:** Boolean
* **default:** 1
* **Description:** If enabled, Cobbler will restart the named or dnsmasq daemon during a ``cobbler sync`` and after all
  configuration files have been generated. This will only happen when ``manage_dns`` is enabled.

Please refer to the :ref:`manage-dns` section for more details.

restart_xinetd
==============

* **type:** Boolean
* **default:** 1
* **Description:** If enabled, Cobbler will restart the xinetd daemon during a ``cobbler sync`` and after all
  configuration files have been generated.

Please refer to the :ref:`managing-tftp` section for more details.

run_install_triggers
====================

* **type:** Boolean
* **default:** 1
* **Description:** If disabled, no install triggers (whether old-style bash or newer python-based scripts) will be run.
  This is an easy way to lock down cobbler if this functionality is not desired, as these scripts are run as the root
  user and can present a security risk.

.. note:: Disabling this will break the ``cobbler status`` command, which relies on installation triggers to generate
   the start and stop times for the builds.

Please refer to the :ref:`triggers` section for more details.

scm_track_enabled
=================

* **type:** Boolean
* **default:** 0
* **Description:** If enabled, Cobbler will execute a trigger for all add/edit/sync events which uses the
  ``scm_track_mode`` option to revision control Cobbler's data objects.

Please refer to the :ref:`data-revision-control` section for more details.

scm_track_mode
==============

* **type:** String
* **default:** "git"
* **Description:** If scm_track_enabled is set to true, Cobbler will use the source control method specified by this
  setting to revision control data objects. Currently, only "git" and "hg" are supported.

.. note:: Only data in ``/var/lib/cobbler`` is revision controlled.

Please refer to the :ref:`data-revision-control` section for more details.

serializer_pretty_json
======================

* **type:** Boolean
* **default:** 0
* **Description:** If enabled, Cobbler will "pretty-print" JSON files that are written to disk, including those for all
  data object types. By default, the JSON is condensed into a single line, which can make them a bit difficult to read.
  The trade-off is a slightly larger file per object (though this size difference is negligable).

server
======

* **type:** String
* **default:** "127.0.0.1"
* **Description:** This is the address of the cobbler server. As it is used by systems during the install process, it
  must be the address or hostname of the system as those systems can see the server. If you have a server that appears
  differently to different subnets (dual homed, etc), you can use the ``--server`` option to override this value.

This value is also used by the cobbler CLI command, unless the ``client_use_localhost`` setting is enabled.

Please refer to the :ref:`multi-homed-cobbler-servers` section for more details.

sign_puppet_certs_automatically
===============================

* **type:** Boolean
* **default:** 0
* **Description:** If enabled when using Puppet integration, Cobbler can be triggered (through the use of snippets) to
  automatically register CA certificates for a given FQDN, allowing puppet to be run during the ``%post`` section of the
  installation without issues.

Please refer to the :ref:`config-management-puppet` section for more details.

snippetsdir
===========

* **type:** String
* **default:** "/var/lib/cobbler/snippets"
* **Description:** The default directory containing Cobbler's snippets. Any snippet referenced by the ``$SNIPPET('')``
  call in a template must live under this directory, for security purposes. Snippets can be located in sub-directories
  here to aid in organization.

template_remote_kickstarts
==========================

* **type:** Boolean
* **default:** 0
* **Description:** If this option is enabled and a remote (non-local) kickstart file is specified for an object, Cobbler
  will fetch the file contents internally and serve a templated version of the file to the client. By default, Cobbler
  simply passes the remote URL directly to the client.

virt_auto_boot
==============

* **type:** Boolean
* **default:** 1
* **Description:** If enabled, any VM created by Koan will be set to start at boot time.

Please refer to the https://koan.readthedocs.io/ section for more details.

webdir
======

* **type:** String
* **default:** "/var/www/cobbler"
* **Description:** The directory in which Cobbler will write all of its distribution, repo, and other web-related data.

xmlrpc_port
===========

* **type:** Integer
* **default:** 25151
* **Description:** The port on which cobblerd will listen for XMLRPC connections, in connection with the
  address/hostname specified in the server setting.

The cobbler CLI command also relies upon this option for connecting to cobblerd unless the ``client_use_localhost``
setting is enabled.

yum_distro_priority
===================

* **type:** Integer
* **default:** 1
* **Description:** The default yum repo priority for repos managed by Cobbler. If different repos provide the same
  package name, the one with the lower priority will be used by default. The lower the priorty number, the higher the
  priority (1 is the highest priority).

This option is only valid for yum repos, and is not used for apt or other repo types.

Please refer to the :ref:`package-management` section for more details.

yum_post_install_mirror
=======================

* **type:** Boolean
* **default:** 1
* **Description:** If enabled, Cobbler will add yum.repos.d entries for all repos allocated to a system or profile. If
  disabled, these repos will only be used during the build process. Normally, this option should be left enabled unless
  you are using other configuration management systems to configure the repos in use after the build process is
  complete.

yumdownloader_flags
===================

* **type:** String
* **default:** "--resolve"
* **Description:** Extra flags for the yumdownloader command, which is used to pull down individual RPM files out of a
  yum repo.

Please refer to the :ref:`package-management` section for more details.
