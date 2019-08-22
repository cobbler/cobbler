***********************************
Cobbler Configuration
***********************************

There are two main settings files: settings and modules.conf. Both files can be found under ``/etc/cobbler/`` and both are
written in YAML.

settings
##################

allow_duplicate_hostnames
=========================
if 1, cobbler will allow insertions of system records that duplicate the ``--dns-name`` information of other system records.
In general, this is undesirable and should be left 0.

default: ``0``

allow_duplicate_ips
===================
if 1, cobbler will allow insertions of system records that duplicate the ip address information of other system records.
In general, this is undesirable and should be left 0.

default: ``0``

allow_duplicate_macs
====================
If 1, cobbler will allow insertions of system records that duplicate the mac address information of other system
records. In general, this is undesirable.

default: ``0``

allow_dynamic_settings
======================
If 1, cobbler will allow settings to be changed dynamically without a restart of the cobblerd daemon. You can only
change this variable by manually editing the settings file, and you MUST restart cobblerd after changing it.

default: ``0``

anamon_enabled
==============
By default, installs are *not* set to send installation logs to the cobbler server. With ``anamon_enabled``, automatic
installation templates may use the ``pre_anamon`` snippet to allow remote live monitoring of their installations from
the cobbler server. Installation logs will be stored under ``/var/log/cobbler/anamon/``.

**Note**: This does allow an xmlrpc call to send logs to this directory, without authentication, so enable only if you
are ok with this limitation.

default: ``0``

authn_pam_service
=================
If using authn_pam in the ``modules.conf``, this can be configured to change the PAM service authentication will be
tested against.

default: ``"login"``

auth_token_expiration
=====================
How long the authentication token is valid for, in seconds.

default: ``3600``

autoinstall_snippets_dir
========================
This is a directory of files that cobbler uses to make templating easier. See the Wiki for more information. Changing
this directory should not be required.

default: ``/var/lib/cobbler/snippets``

autoinstall_templates_dir
=========================
This is a directory of files that cobbler uses to make templating easier. See the Wiki for more information. Changing
this directory should not be required.

default: ``/var/lib/cobbler/templates``

boot_loader_conf_template_dir
=============================
Location of templates used for boot loader config generation.

default: ``"/etc/cobbler/boot_loader_conf"``

build_reporting_*
=================
Email out a report when cobbler finishes installing a system.

- enabled: set to 1 to turn this feature on
- sender: optional
- email: which addresses to email
- smtp_server: used to specify another server for an MTA
- subject: use the default subject unless overridden

defaults:

.. code-block:: none

    build_reporting_enabled: 0
    build_reporting_sender: ""
    build_reporting_email: [ 'root@localhost' ]
    build_reporting_smtp_server: "localhost"
    build_reporting_subject: ""
    build_reporting_ignorelist: [ "" ]

cheetah_import_whitelist
========================
Cheetah-language autoinstall templates can import Python modules. while this is a useful feature, it is not safe to
allow them to import anything they want. This whitelists which modules can be imported through Cheetah. Users can expand
this as needed but should never allow modules such as subprocess or those that allow access to the filesystem as Cheetah
templates are evaluated by cobblerd as code.

default:
 - "random"
 - "re"
 - "time"
 - "netaddr"

createrepo_flags
================
Default createrepo_flags to use for new repositories. If you have ``createrepo >= 0.4.10``, consider
``-c cache --update -C``, which can dramatically improve your ``cobbler reposync`` time. ``-s sha`` enables working with
Fedora repos from F11/F12 from EL-4 or EL-5 without python-hashlib installed (which is not available on EL-4)

default: ``"-c cache -s sha"``

default_autoinstall
===================
If no autoinstall template is specified to profile add, use this template.

default: ``/var/lib/cobbler/autoinstall_templates/default.ks``

default_name_*
==============
Configure all installed systems to use these nameservers by default unless defined differently in the profile. For DHCP
configurations you probably do /not/ want to supply this.

defaults:

.. code-block:: none

    default_name_servers: []
    default_name_servers_search: []

default_ownership
=================
if using the ``authz_ownership`` module (see the Wiki), objects created without specifying an owner are assigned to this
owner and/or group. Can be a comma seperated list.

default:
 - "admin"

default_password_crypted
========================
Cobbler has various sample automatic installation templates stored in ``/var/lib/cobbler/autoinstall_templates/``. This
controls what install (root) password is set up for those systems that reference this variable. The factory default is
"cobbler" and cobbler check will warn if this is not changed. The simplest way to change the password is to run
``openssl passwd -1`` and put the output between the ``""``.

default: ``"$1$mF86/UHC$WvcIcX2t6crBz2onWxyac."``

default_template_type
=====================
The default template type to use in the absence of any other detected template. If you do not specify the template
with ``#template=<template_type>`` on the first line of your templates/snippets, cobbler will assume try to use the
following template engine to parse the templates.

Current valid values are: cheetah, jinja2

default: ``"cheetah"``

default_virt_bridge
===================
For libvirt based installs in koan, if no virt-bridge is specified, which bridge do we try? For EL 4/5 hosts this should
be ``xenbr0``, for all versions of Fedora, try ``virbr0``. This can be overriden on a per-profile basis or at the koan
command line though this saves typing to just set it here to the most common option.

default: ``xenbr0``

default_virt_file_size
======================
Use this as the default disk size for virt guests (GB).

default: ``5``

default_virt_ram
================
Use this as the default memory size for virt guests (MB).

default: ``512``

default_virt_type
=================
If koan is invoked without ``--virt-type`` and no virt-type is set on the profile/system, what virtualization type
should be assumed?

Current valid values are: xenpv, xenfv, qemu, vmware

**NOTE**: this does not change what ``virt_type`` is chosen by import.

default: ``xenpv``

enable_gpxe
===========
Enable gPXE booting? Enabling this option will cause cobbler to copy the ``undionly.kpxe`` file to the tftp root
directory, and if a profile/system is configured to boot via gpxe it will chain load off ``pxelinux.0``.

default: ``0``

enable_menu
===========
Controls whether cobbler will add each new profile entry to the default PXE boot menu. This can be over-ridden on a
per-profile basis when adding/editing profiles with ``--enable-menu=0/1``. Users should ordinarily leave this setting
enabled unless they are concerned with accidental reinstalls from users who select an entry at the PXE boot menu. Adding
a password to the boot menus templates may also be a good solution to prevent unwanted reinstallations

default: ``1``

http_port
=========
Change this port if Apache is not running plaintext on port 80. Most people can leave this alone.

default: ``80``

kernel_options
==============
Kernel options that should be present in every cobbler installation. Kernel options can also be applied at the
distro/profile/system level.

default: ``{}``

ldap_*
======
Configuration options if using the authn_ldap module. See the the Wiki for details. This can be ignored if you are not
using LDAP for WebUI/XMLRPC authentication.

defaults:

.. code-block:: none

    ldap_server: "ldap.example.com"
    ldap_base_dn: "DC=example,DC=com"
    ldap_port: 389
    ldap_tls: 1
    ldap_anonymous_bind: 1
    ldap_search_bind_dn: ''
    ldap_search_passwd: ''
    ldap_search_prefix: 'uid='
    ldap_tls_cacertfile: ''
    ldap_tls_keyfile: ''
    ldap_tls_certfile: ''

mgmt_*
======
Cobbler has a feature that allows for integration with config management systems such as Puppet. The following
parameters work in conjunction with ``--mgmt-classes`` and are described in further detail at:
https://github.com/cobbler/cobbler/wiki/Using-cobbler-with-a-configuration-management-system

.. code-block:: Yaml

    mgmt_classes: []
    mgmt_parameters:
        from_cobbler: 1

puppet_auto_setup
=================
If enabled, this setting ensures that puppet is installed during machine provision, a client certificate is generated
and a certificate signing request is made with the puppet master server.

default: ``0``

sign_puppet_certs_automatically
===============================
When puppet starts on a system after installation it needs to have its certificate signed by the puppet master server.
Enabling the following feature will ensure that the puppet server signs the certificate after installation if the puppet
master server is running on the same machine as cobbler. This requires ``puppet_auto_setup`` above to be enabled.

default: ``0``

puppetca_path
=============
Location of the puppet executable, used for revoking certificates.

default: ``"/usr/bin/puppet"``

remove_old_puppet_certs_automatically
=====================================
When a puppet managed machine is reinstalled it is necessary to remove the puppet certificate from the puppet master
server before a new certificate is signed (see above). Enabling the following feature will ensure that the certificate
for the machine to be installed is removed from the puppet master server if the puppet master server is running on the
same machine as cobbler. This requires ``puppet_auto_setup`` above to be enabled

default: ``0``

puppet_server
=============
Choose a ``--server`` argument when running puppetd/puppet agent during autoinstall. This one is commented out by
default.

default: ``'puppet'``

puppet_version
==============
Let cobbler know that you're using a newer version of puppet. Choose version 3 to use: 'puppet agent'; version 2 uses
status quo: 'puppetd'. This one is commented out by default.

default: ``2``

puppet_parameterized_classes
============================
Choose whether to enable puppet parameterized classes or not. Puppet versions prior to 2.6.5 do not support parameters.
This one is commented out by default.

default: 1

manage_dhcp
===========
Set to 1 to enable Cobbler's DHCP management features. The choice of DHCP management engine is in
``/etc/cobbler/modules.conf``

default: ``0``

manage_dns
==========
Set to 1 to enable Cobbler's DNS management features. The choice of DNS mangement engine is in
``/etc/cobbler/modules.conf``

default: ``0``

bind_chroot_path
================
Set to path of bind chroot to create bind-chroot compatible bind configuration files. This should be automatically
detected.

default: ``""``

bind_master
===========
Set to the ip address of the master bind DNS server for creating secondary bind configuration files.

default: ``127.0.0.1``

manage_tftpd
==============
Set to 1 to enable Cobbler's TFTP management features. the choice of TFTP mangement engine is in
``/etc/cobbler/modules.conf``

default: ``1``

tftpboot_location
=================
This variable contains the location of the tftpboot directory. If this directory is not present cobbler does not start.

Default: ``/srv/tftpboot``

manage_rsync
============
Set to 1 to enable Cobbler's RSYNC management features.

default: ``0``

manage_*
========
If using BIND (named) for DNS management in ``/etc/cobbler/modules.conf`` and manage_dns is enabled (above), this lists
which zones are managed. See the Wiki (https://github.com/cobbler/cobbler/wiki/Dns-management) for more info

defaults:

.. code-block:: none

    manage_forward_zones: []
    manage_reverse_zones: []

next_server
===========
If using cobbler with ``manage_dhcp``, put the IP address of the cobbler server here so that PXE booting guests can find
it. If you do not set this correctly, this will be manifested in TFTP open timeouts.

default: ``127.0.0.1``

power_management_default_type
=============================
Settings for power management features. These settings are optional. See
https://github.com/cobbler/cobbler/wiki/Power-management to learn more.

Choices (refer to codes.py):

- apc_snmp
- bladecenter
- bullpap
- drac
- ether_wake
- ilo
- integrity
- ipmilan
- ipmitool
- lpar
- rsa
- virsh
- wti

default: ``ipmitool``

power_template_dir
==================
The commands used by the power management module are sourced from what directory?

default: ``"/etc/cobbler/power"``

pxe_just_once
=============
If this setting is set to 1, cobbler systems that pxe boot will request at the end of their installation to toggle the
``--netboot-enabled`` record in the cobbler system record. This eliminates the potential for a PXE boot loop if the
system is set to PXE first in it's BIOS order. Enable this if PXE is first in your BIOS boot order, otherwise leave this
disabled. See the manpage for ``--netboot-enabled``.

default: ``1``

nopxe_with_triggers
===================
If this setting is set to one, triggers will be executed when systems will request to toggle the ``--netboot-enabled``
record at the end of their installation.

default: ``1``

redhat_management_server
========================
This setting is only used by the code that supports using Spacewalk/Satellite authentication within Cobbler Web and
Cobbler XMLRPC.

default: ``"xmlrpc.rhn.redhat.com"``

redhat_management_permissive
============================
If using ``authn_spacewalk`` in ``modules.conf`` to let cobbler authenticate against Satellite/Spacewalk's auth system,
by default it will not allow per user access into Cobbler Web and Cobbler XMLRPC. In order to permit this, the following
setting must be enabled HOWEVER doing so will permit all Spacewalk/Satellite users of certain types to edit all of
cobbler's configuration. these roles are: ``config_admin`` and ``org_admin``. Users should turn this on only if they
want this behavior and do not have a cross-multi-org seperation concern. If you have a single org in your satellite,
it's probably safe to turn this on and then you can use CobblerWeb alongside a Satellite install.

default: ``0``

redhat_management_key
=====================
Specify the default Red Hat authorization key to use to register system. If left blank, no registration will be
attempted. Similarly you can set the ``--redhat-management-key`` to blank on any system to keep it from trying to
register.

default: ``""``

register_new_installs
=====================
If set to ``1``, allows ``/usr/bin/cobbler-register`` (part of the koan package) to be used to remotely add new cobbler
system records to cobbler. This effectively allows for registration of new hardware from system records.

default: ``0``

reposync_flags
==============
Flags to use for yum's reposync. If your version of yum reposync does not support ``-l``, you may need to remove that
option.

default: ``"-l -n -d"``

restart_*
=========
When DHCP and DNS management are enabled, ``cobbler sync`` can automatically restart those services to apply changes.
The exception for this is if using ISC for DHCP, then omapi eliminates the need for a restart. ``omapi``, however, is
experimental and not recommended for most configurations. If DHCP and DNS are going to be managed, but hosted on a box
that is not on this server, disable restarts here and write some other script to ensure that the config files get
copied/rsynced to the destination box. This can be done by modifying the restart services trigger. Note that if
``manage_dhcp`` and ``manage_dns`` are disabled, the respective parameter will have no effect. Most users should not
need to change this.

defaults:

.. code-block:: none

    restart_dns: 1
    restart_dhcp: 1

run_install_triggers
====================
Install triggers are scripts in ``/var/lib/cobbler/triggers/install`` that are triggered in autoinstall pre and post
sections. Any executable script in those directories is run. They can be used to send email or perform other actions.
They are currently run as root so if you do not need this functionality you can disable it, though this will also
disable ``cobbler status`` which uses a logging trigger to audit install progress.

default: ``1``

scm_track_*
===========
enables a trigger which version controls all changes to ``/var/lib/cobbler`` when add, edit, or sync events are
performed. This can be used to revert to previous database versions, generate RSS feeds, or for other auditing or backup
purposes. Git and Mercurial are currently supported, but Git is the recommend SCM for use with this feature.

default:

.. code-block:: none

    scm_track_enabled: 0
    scm_track_mode: "git"
    scm_track_author: "cobbler <cobbler@localhost>"
    scm_push_script: "/bin/true"

server
======
This is the address of the cobbler server -- as it is used by systems during the install process, it must be the address
or hostname of the system as those systems can see the server. if you have a server that appears differently to
different subnets (dual homed, etc), you need to read the ``--server-override`` section of the manpage for how that
works.

default: ``127.0.0.1``

client_use_localhost
====================
If set to 1, all commands will be forced to use the localhost address instead of using the above value which can force
commands like cobbler sync to open a connection to a remote address if one is in the configuration and would traceback.

default: ``0``

client_use_https
================
If set to 1, all commands to the API (not directly to the XMLRPC server) will go over HTTPS instead of plaintext. Be
sure to change the ``http_port`` setting to the correct value for the web server.

default: ``0``

virt_auto_boot
==============
Should new profiles for virtual machines default to auto booting with the physical host when the physical host reboots?
This can be overridden on each profile or system object.

default: ``1``

webdir
======
Cobbler's web directory.  Don't change this setting -- see the Wiki on "relocating your cobbler install" if your /var partition
is not large enough.

default: ``@@webroot@@/cobbler``

webdir_whitelist
================
Directories that will not get wiped and recreated on a ``cobbler sync``.

default:

.. code-block:: none

    webdir_whitelist:
      - misc
      - web
      - webui
      - localmirror
      - repo_mirror
      - distro_mirror
      - images
      - links
      - pub
      - repo_profile
      - repo_system
      - svc
      - rendered
      - .link_cache

xmlrpc_port
===========
Cobbler's public XMLRPC listens on this port. Change this only if absolutely needed, as you'll have to start supplying
a new port option to koan if it is not the default.

default: ``25151``

yum_post_install_mirror
=======================
``cobbler repo add`` commands set cobbler up with repository information that can be used during autoinstall and is
automatically set up in the cobbler autoinstall templates. By default, these are only available at install time. To
make these repositories usable on installed systems (since cobbler makes a very convenient mirror) set this to 1. Most
users can safely set this to 1. Users who have a dual homed cobbler server, or are installing laptops that will not
always have access to the cobbler server may wish to leave this as 0. In that case, the cobbler mirrored yum repos are
still accessible at ``http://cobbler.example.org/cblr/repo_mirror`` and yum configuration can still be done manually.
This is just a shortcut.

default: ``1``

yum_distro_priority
===================
The default yum priority for all the distros. This is only used if yum-priorities plugin is used. 1 is the maximum
value. Tweak with caution.

default: ``1``

yumdownloader_flags
===================
Flags to use for yumdownloader. Not all versions may support ``--resolve``.

default: ``"--resolve"``

serializer_pretty_json
======================
Sort and indent JSON output to make it more human-readable.

default: ``0``

replicate_rsync_options
=======================
replication rsync options for distros, autoinstalls, snippets set to override default value of ``-avzH``

default: ``"-avzH"``

replicate_repo_rsync_options
============================
Replication rsync options for repos set to override default value of ``-avzH``

default: ``"-avzH"``

always_write_dhcp_entries
=========================
Always write DHCP entries, regardless if netboot is enabled.

default: ``0``

proxy_url_ext:
==============
External proxy - used by: get-loaders, reposync, signature update. Per default commented out.

defaults:

.. code-block:: none

  http: http://192.168.1.1:8080
  https: https://192.168.1.1:8443

proxy_url_int
=============
Internal proxy - used by systems to reach cobbler for kickstarts.

E.g.: proxy_url_int: ``http://10.0.0.1:8080``

default: ``""``

jinja2_includedir
=================
This is a directory of files that cobbler uses to include files into Jinja2 templates. Per default this settings is
commented out.

default: ``/var/lib/cobbler/jinja2``

include
=======
Include other configuration snippets with this regular expresion.

default: ``[ "/etc/cobbler/settings.d/*.settings" ]``

modules.conf
############

If you have own custom modules which are not shipped with Cobbler directly you may have additional sections here.

authentication
==============
What users can log into the WebUI and Read-Write XMLRPC?

Choices:

- authn_denyall    -- no one (default)
- authn_configfile -- use /etc/cobbler/users.digest (for basic setups)
- authn_passthru   -- ask Apache to handle it (used for kerberos)
- authn_ldap       -- authenticate against LDAP
- authn_spacewalk  -- ask Spacewalk/Satellite (experimental)
- authn_pam        -- use PAM facilities
- authn_testing    -- username/password is always testing/testing (debug)
- (user supplied)  -- you may write your own module

WARNING: this is a security setting, do not choose an option blindly.

For more information:

- https://github.com/cobbler/cobbler/wiki/Cobbler-web-interface
- https://github.com/cobbler/cobbler/wiki/Security-overview
- https://github.com/cobbler/cobbler/wiki/Kerberos
- https://github.com/cobbler/cobbler/wiki/Ldap

default: ``authn_configfile``

authorization
=============
Once a user has been cleared by the WebUI/XMLRPC, what can they do?

Choices:

- authz_allowall   -- full access for all authneticated users (default)
- authz_ownership  -- use users.conf, but add object ownership semantics
- (user supplied)  -- you may write your own module

**WARNING**: this is a security setting, do not choose an option blindly.
If you want to further restrict cobbler with ACLs for various groups,
pick authz_ownership.  authz_allowall does not support ACLs.  configfile
does but does not support object ownership which is useful as an additional
layer of control.

For more information:

- https://github.com/cobbler/cobbler/wiki/Cobbler-web-interface
- https://github.com/cobbler/cobbler/wiki/Security-overview
- https://github.com/cobbler/cobbler/wiki/Web-authorization

default: ``authz_allowall``

dns
===
Chooses the DNS management engine if manage_dns is enabled in ``/etc/cobbler/settings``, which is off by default.

Choices:

- manage_bind    -- default, uses BIND/named
- manage_dnsmasq -- uses dnsmasq, also must select dnsmasq for dhcp below
- manage_ndjbdns -- uses ndjbdns

**NOTE**: More configuration is still required in ``/etc/cobbler``

For more information: https://github.com/cobbler/cobbler/wiki/Dns-management

default: ``manage_bind``

dhcp
====
Chooses the DHCP management engine if ``manage_dhcp`` is enabled in ``/etc/cobbler/settings``, which is off by default.

Choices:

- manage_isc     -- default, uses ISC dhcpd
- manage_dnsmasq -- uses dnsmasq, also must select dnsmasq for dns above

**NOTE**: More configuration is still required in ``/etc/cobbler``

For more information: https://github.com/cobbler/cobbler/wiki/Dhcp-management

default: ``manage_isc``

tftpd
=====
Chooses the TFTP management engine if manage_tftp is enabled in ``/etc/cobbler/settings``, which is ON by default.

Choices:

- manage_in_tftpd -- default, uses the system's tftp server
- manage_tftpd_py -- uses cobbler's tftp server

default: ``manage_in_tftpd``
