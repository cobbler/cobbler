.. _settings-ref:

*****************
``settings.yaml``
*****************

auto_migrate_settings
#####################

If ``True`` Cobbler will auto migrate the settings file after upgrading from older versions. The current settings
are backed up in the same folder before the upgrade.

default: ``True``

allow_duplicate_hostnames
#########################

If ``True``, Cobbler will allow insertions of system records that duplicate the ``--dns-name`` information of other
system records. In general, this is undesirable and should be left False.

default: ``False``

allow_duplicate_ips
###################

If ``True``, Cobbler will allow insertions of system records that duplicate the IP address information of other system
records. In general, this is undesirable and should be left False.

default: ``False``

allow_duplicate_macs
####################

If ``True``, Cobbler will allow insertions of system records that duplicate the mac address information of other system
records. In general, this is undesirable.

default: ``False``

allow_dynamic_settings
######################

If ``True``, Cobbler will allow settings to be changed dynamically without a restart of the ``cobblerd`` daemon. You can
only change this variable by manually editing the settings file, and you MUST restart ``cobblerd`` after changing it.

default: ``False``

always_write_dhcp_entries
#########################

Always write DHCP entries, regardless if netboot is enabled.

default: ``False``

anamon_enabled
##############

By default, installs are *not* set to send installation logs to the Cobbler server. With ``anamon_enabled``, automatic
installation templates may use the ``pre_anamon`` snippet to allow remote live monitoring of their installations from
the Cobbler server. Installation logs will be stored under ``/var/log/cobbler/anamon/``.

.. note:: This does allow an XML-RPC call to send logs to this directory, without authentication, so enable only if you
          are ok with this limitation.

default: ``False``

auth_token_expiration
#####################

How long the authentication token is valid for, in seconds.

default: ``3600``

authn_pam_service
#################

If using ``authentication.pam`` under ``modules.authentication.module``, this can be configured to change the PAM
service authentication will be tested against.

default: ``"login"``

autoinstall
###########

If no autoinstall template is specified to profile add, use this template.

default: ``default.ks``

autoinstall_scheme
####################

This should contain the scheme over which the autoinstall-file is available.

This is setting does not setup your api for HTTPS, it just changes the way the url for your profiles and systems are
generated.

Choices:

- ``http``
- ``https``

default: ``http``

autoinstall_snippets_dir
########################

This is a directory of files that Cobbler uses to make templating easier. See the Wiki for more information. Changing
this directory should not be required.

default: ``/var/lib/cobbler/snippets``

autoinstall_templates_dir
#########################

This is a directory of files that Cobbler uses to make templating easier. See the Wiki for more information. Changing
this directory should not be required.

default: ``/var/lib/cobbler/templates``

bind_chroot_path
################

Set to path of bind chroot to create bind-chroot compatible bind configuration files.

default: ``""``

bind_master
###########

Set to the ip address of the master bind DNS server for creating secondary bind configuration files.

default: ``127.0.0.1``

bind_zonefile_path
##################

Set to path where zonefiles of bind/named server are located.

default: ``"@@bind_zonefiles@@"``

boot_loader_conf_template_dir
#############################

Location of templates used for boot loader config generation.

default: ``"/etc/cobbler/boot_loader_conf"``

bootloaders_dir
###############

A directory that "cobbler mkloaders" copies the built bootloaders into. "cobbler sync" searches for
bootloaders in this directory.

default: ``/var/lib/cobbler/loaders``

bootloaders_shim_folder
#######################

This `Python Glob <https://docs.python.org/3/library/glob.html>`_ will be responsible for finding the installed shim
folder. If you don't have shim installed this bootloader link will be skipped. If the Glob is not precise enough a
message will be logged and the link will also be skipped.

default: Depending on your distro. See values below.

* (open)SUSE: ``"/usr/share/efi/*/"``
* Debian/Ubuntu: ``"/usr/lib/shim/"``
* CentOS/Fedora: ``"/boot/efi/EFI/*/"``

bootloaders_shim_file
#####################

This is a `Python Regex <https://docs.python.org/3/library/re.html>`_ responsible for finding a single
match in all files found by the Python Glob in ``bootloaders_shim_folder``. If more or fewer files are found a message
will be logged.

default: Depending on your distro. See values below.

* (open)SUSE: ``"shim\.efi"``
* Debian/Ubuntu: ``"shim*.efi.signed"``
* CentOS/Fedora: ``"shim*.efi"``

secure_boot_grub_folder
=======================

This `Python Glob <https://docs.python.org/3/library/glob.html>`_ is responsible for finding the installed secure
boot bootloader folders. If the Glob is not precise enough a message will be logged and the link will also be skipped.

This glob is only used for grub formats that use the ``use_secure_boot_grub`` property.

default: Depending on your distro. See values below.

* (open)SUSE: ``"/usr/share/efi/*/"``
* Debian/Ubuntu: ``"/usr/lib/shim/"``
* CentOS/Fedora: ``"/boot/efi/EFI/*/"``

secure_boot_grub_file
=====================

This is a `Python Regex <https://docs.python.org/3/library/re.html>`_ responsible to finding a single
match for the secure boot grub bootloader in all files found by the ``secure_boot_grub_folder`` glob.

This regex is only used for grub formats that use the ``use_secure_boot_grub`` property.

default: Depending on your distro. See values below.

* (open)SUSE: ``"grub\.efi"``
* Debian/Ubuntu: ``"grub[a-zA-Z0-9]*\.efi"``
* CentOS/Fedora: ``"grub\.efi"``

grub2_mod_dir
#############

The directory where Cobbler looks for GRUB modules that are required for "cobbler mkloaders".

default: Depends on your distribution. See values below.

* (open)SUSE: ``"/usr/share/grub2"``
* Debian/Ubuntu: ``"/usr/lib/grub"``
* CentOS/Fedora: ``"/usr/lib/grub"``

syslinux_dir
############

The directory where Cobbler looks for syslinux modules that are required for "cobbler mkloaders".

default: Depends on your distribution. See values below.

* (open)SUSE: ``"/usr/share/syslinux"``
* Debian/Ubuntu: ``"/usr/lib/syslinux/modules/bios/"``
* CentOS/Fedora: ``"/usr/share/syslinux"``

bootloaders_modules
###################

A list of all modules "cobbler mkloaders" includes when building grub loaders.
Typically, a grub loader uses the modules for PXE or HTTP Boot.

default: Omited for readablity, please refer to the `settings.yaml` file in our GitHub repository.

bootloaders_formats
###################

This is a mapping that has the following structure:

.. code:: yaml

   <loader name>:
      binary_name: filename
      extra_modules:
        - extra-module
      mod_dir: <different folder name then loader name>
      use_secure_boot_grub: True

The keys ``extra_modules``, ``mod_dir`` and ``use_secure_boot_grub`` are optional. Under normal circumstances this
setting does not need adjustments.

default: Omited for readablity, please refer to the `settings.yaml` file in our GitHub repository.

grubconfig_dir
##############

The location where Cobbler searches for GRUB configuration files.

default: ``/var/lib/cobbler/grub_config``

build_reporting_*
#################

Email out a report when Cobbler finishes installing a system.

- enabled: Set to ``true`` to turn this feature on
- email: Which addresses to email
- ignorelist: A list of prefixes that defines mail topics that should not be sent.
- sender: Optional
- smtp_server: Used to specify another server for an MTA.
- subject: Use the default subject unless overridden.

defaults:

.. code-block:: yaml

   build_reporting_enabled: false
   build_reporting_sender: ""
   build_reporting_email: [ 'root@localhost' ]
   build_reporting_smtp_server: "localhost"
   build_reporting_subject: ""
   build_reporting_ignorelist: [ "" ]

buildisodir
###########

Used for caching the intermediate files for ISO-Building. You may want to use a SSD, a tmpfs or something which does not
persist across reboots and can be easily thrown away but is also fast.

default: ``/var/cache/cobbler/buildiso``

cheetah_import_whitelist
########################

Cheetah-language autoinstall templates can import Python modules. while this is a useful feature, it is not safe to
allow them to import anything they want. This whitelists which modules can be imported through Cheetah. Users can expand
this as needed but should never allow modules such as subprocess or those that allow access to the filesystem as Cheetah
templates are evaluated by ``cobblerd`` as code.

default:
 - ``random``
 - ``re``
 - ``time``
 - ``netaddr``

client_use_https
################

If set to ``True``, all commands to the API (not directly to the XML-RPC server) will go over HTTPS instead of plain
text. Be sure to change the ``http_port`` setting to the correct value for the web server.

default: ``False``

client_use_localhost
####################

If set to ``True``, all commands will be forced to use the localhost address instead of using the above value which can
force commands like ``cobbler sync`` to open a connection to a remote address if one is in the configuration and would
traceback.

default: ``False``

cobbler_master
##############

Used for replicating the Cobbler instance.

default: ``""``

convert_server_to_ip
####################

Convert hostnames to IP addresses (where possible) so DNS isn't a requirement for various tasks to work correctly.

default: ``False``

createrepo_flags
################

Default ``createrepo_flags`` to use for new repositories.

default: ``"--cachedir=cache --update"``

default_name_*
##############

Configure all installed systems to use these name servers by default unless defined differently in the profile. For DHCP
configurations you probably do **not** want to supply this.

defaults:

.. code-block:: yaml

   default_name_servers: []
   default_name_servers_search: []

default_ownership
#################

if using the ``authz_ownership`` module, objects created without specifying an owner are assigned to this owner and/or
group.

default:
 - ``admin``

default_password_crypted
########################

Cobbler has various sample automatic installation templates stored in ``/var/lib/cobbler/templates/``. This
controls what install (root) password is set up for those systems that reference this variable. The factory default is
"cobbler" and Cobbler check will warn if this is not changed. The simplest way to change the password is to run
``openssl passwd -1`` and put the output between the ``""``.

default: ``"$1$mF86/UHC$WvcIcX2t6crBz2onWxyac."``

default_template_type
#####################

The default template type to use in the absence of any other detected template. If you do not specify the template
with ``#template=<template_type>`` on the first line of your templates/snippets, Cobbler will assume try to use the
following template engine to parse the templates.

.. note:: Over time we will try to deprecate and remove Cheetah3 as a template engine. It is hard to package and there
          are fewer guides then with Jinja2. Making the templating independent of the engine is a task which complicates
          the code. Thus, please try to use Jinja2. We will try to support a seamless transition on a best-effort basis.

Current valid values are: ``cheetah``, ``jinja2``

default: ``"cheetah"``

default_virt_bridge
###################

For libvirt based installs in Koan, if no virt-bridge is specified, which bridge do we try?  For defauit libvirt NAT
nework use "virbr0".  For bridged networks, use bridge device name (e.g. "br0").  This can be overridden on a
per-profile basis or at the Koan command line though this saves typing to just set it here to the most common option.

default: ``virbr0``

default_virt_disk_driver
########################

The on-disk format for the virtualization disk.

default: ``raw``

dnsmasq_ethers_file
###################

The path to the ethers file used by the dnsmasq manager module. Note that if you change this path, you might have to reconfigure
external systems that also use the file. See ``man 5 ethers`` for more information about the file and its uses.

default: ``/etc/ethers``

dnsmasq_hosts_file
##################

The path to the hosts file used by the dnsmasq manager module.

default: ``/var/lib/cobbler/cobbler_hosts``

default_virt_file_size
######################

Use this as the default disk size for virt guests (GB).

default: ``5.0``

default_virt_ram
################

Use this as the default memory size for virt guests (MB).

default: ``512``

default_virt_type
#################

If Koan is invoked without ``--virt-type`` and no virt-type is set on the profile/system, what virtualization type
should be assumed?

Current valid values are:

- ``qemu``
- ``kvm``
- ``xenpv``
- ``xenfv``
- ``qemu``
- ``vmware``
- ``vmwarew``
- ``openvz``
- ``auto``

**NOTE**: this does not change what ``virt_type`` is chosen by import.

default: ``kvm``

enable_ipxe
###########

Enable iPXE booting? Enabling this option will cause Cobbler to copy the ``undionly.kpxe`` file to the TFTP root
directory, and if a profile/system is configured to boot via iPXE it will chain load off ``pxelinux.0``.

default: ``False``

enable_menu
###########

Controls whether Cobbler will add each new profile entry to the default PXE boot menu. This can be over-ridden on a
per-profile basis when adding/editing profiles with ``--enable-menu=False/True``. Users should ordinarily leave this
setting enabled unless they are concerned with accidental reinstall from users who select an entry at the PXE boot
menu. Adding a password to the boot menus templates may also be a good solution to prevent unwanted reinstallations.

default: ``True``

http_port
#########

Change this port if Apache is not running plain text on port 80. Most people can leave this alone.

default: ``80``

iso_template_dir
################

Folder to search for the ISO templates. These will build the boot-menu of the built ISO.

default: ``/etc/cobbler/iso``

jinja2_includedir
#################

This is a directory of files that Cobbler uses to include files into Jinja2 templates. Per default this settings is
commented out.

default: ``/var/lib/cobbler/jinja2``

kernel_options
##############

Kernel options that should be present in every Cobbler installation. Kernel options can also be applied at the
distro/profile/system level.

default: ``{}``

ldap_*
######
Configuration options if using the authn_ldap module. See the Wiki for details. This can be ignored if you are not
using LDAP for WebUI/XML-RPC authentication.

defaults:

.. code-block:: yaml

   ldap_server: "ldap.example.com"
   ldap_base_dn: "DC=example,DC=com"
   ldap_port: 389
   ldap_tls: true
   ldap_anonymous_bind: true
   ldap_search_bind_dn: ''
   ldap_search_passwd: ''
   ldap_search_prefix: 'uid='
   ldap_tls_cacertdir: ''
   ldap_tls_cacertfile: ''
   ldap_tls_certfile: ''
   ldap_tls_keyfile: ''
   ldap_tls_reqcert: 'hard'
   ldap_tls_cipher_suite: ''

bind_manage_ipmi
################

When using the Bind9 DNS server, you can enable or disable if the BMCs should receive own DNS entries.

default: ``False``

manage_dhcp
###########

Set to ``True`` to enable Cobbler's DHCP management features. The choice of DHCP management engine is under
``modules.dhcp.module``.

default: ``True``

manage_dhcp_v4
##############

Set to ``true`` to enable DHCP IPv6 address configuration generation. This currently only works with manager.isc DHCP
module (isc dhcpd6 daemon). See ``modules.dhcp.module`` whether this isc module is chosen for dhcp generation.

default: ``False``

manage_dhcp_v6
##############

Set to ``true`` to enable DHCP IPv6 address configuration generation. This currently only works with manager.isc DHCP
module (isc dhcpd6 daemon). See ``modules.dhcp.module`` whether this isc module is chosen for dhcp generation.

default: ``False``

manage_dns
##########

Set to ``True`` to enable Cobbler's DNS management features. The choice of DNS management engine is under the key
``modules.dns.module``.

default: ``False``

manage_*_zones
##############

If using BIND (named) for DNS management in ``modules.dns.module`` and ``manage_dns`` is enabled (above), this
lists which zones are managed. See :ref:`dns-management` for more information.

defaults:

.. code-block:: yaml

   manage_forward_zones: []
   manage_reverse_zones: []

manage_genders
##############

Whether or not to manage the genders file. For more information on that visit:
`github.com/chaos/genders <https://github.com/chaos/genders>`_

default: ``False``

manage_rsync
############

Set to ``True`` to enable Cobbler's RSYNC management features.

default: ``False``

manage_tftpd
##############

Set to ``True`` to enable Cobbler's TFTP management features. The choice of TFTP management engine is under
``modules.tftpd.module``.

default: ``True``

mgmt_*
######

Cobbler has a feature that allows for integration with config management systems such as Puppet. The following
parameters work in conjunction with ``--mgmt-classes`` and are described in further detail at
:ref:`configuration-management`.

.. code-block:: YAML

   mgmt_classes: []
   mgmt_parameters:
       from_cobbler: true

next_server_v4
##############

If using Cobbler with ``manage_dhcp_v4``, put the IP address of the Cobbler server here so that PXE booting guests can find
it. If you do not set this correctly, this will be manifested in TFTP open timeouts.

default: ``127.0.0.1``

next_server_v6
##############

If using Cobbler with ``manage_dhcp_v6``, put the IP address of the Cobbler server here so that PXE booting guests can find
it. If you do not set this correctly, this will be manifested in TFTP open timeouts.

default: ``::1``

nsupdate_enabled
################

This enables or disables the replacement (or removal) of records in the DNS zone for systems created (or removed) by
Cobbler.

.. note:: There are additional settings needed when enabling this. Due to the limited number of resources, this won't
          be done until 3.3.0. Thus please expect to run into troubles when enabling this setting.

default: ``False``

nsupdate_log
############

The logfile to document what records are added or removed in the DNS zone for systems.

.. note:: The functionality this settings is related to is currently not tested due to tech-debt. Please use it with
          caution. This note will be removed once we were able to look deeper into this functionality of Cobbler.

- Required: No
- Default: ``/var/log/cobbler/nsupdate.log``

nsupdate_tsig_algorithm
#######################

.. note:: The functionality this settings is related to is currently not tested due to tech-debt. Please use it with
          caution. This note will be removed once we were able to look deeper into this functionality of Cobbler.

- Required: No
- Default: ``hmac-sha512``

nsupdate_tsig_key
#################

.. note:: The functionality this settings is related to is currently not tested due to tech-debt. Please use it with
          caution. This note will be removed once we were able to look deeper into this functionality of Cobbler.

- Required: No
- Default: ``[]``

power_management_default_type
#############################

Settings for power management features. These settings are optional. See :ref:`power-management` to learn more.

Choices (refer to the `fence-agents project <https://github.com/ClusterLabs/fence-agents>`_ for a complete list):

- apc_snmp
- bladecenter
- bullpap
- drac
- ether_wake
- ilo
- integrity
- ipmilan
- ipmilanplus
- lpar
- rsa
- virsh
- wti

default: ``ipmilanplus``

proxies
#######

This key is used by Uyuni (or one of its derivatives) for the Proxy scenario. More information can be found
`here <https://www.uyuni-project.org/uyuni-docs/en/uyuni/installation-and-upgrade/uyuni-proxy-setup.html>`_

Cobbler only evaluates this if the key has a list of strings as value. An empty list means you don't have any proxies configured in your Uyuni setup.

default: ``[]``

proxy_url_ext
#############

External proxy which is used by the following commands: ``reposync``, ``signature update``

defaults:

.. code-block:: text

  http: http://192.168.1.1:8080
  https: https://192.168.1.1:8443

proxy_url_int
#############

Internal proxy which is used by systems to reach Cobbler for kickstarts.

e.g.: ``proxy_url_int: http://10.0.0.1:8080``

default: ``""``

puppet_auto_setup
#################

If enabled, this setting ensures that puppet is installed during machine provision, a client certificate is generated
and a certificate signing request is made with the puppet master server.

default: ``False``

puppet_parameterized_classes
############################

Choose whether to enable puppet parameterized classes or not. Puppet versions prior to 2.6.5 do not support parameters.

default: ``True``

puppet_server
#############

Choose a ``--server`` argument when running puppetd/puppet agent during autoinstall.

default: ``'puppet'``

puppet_version
##############

Let Cobbler know that you're using a newer version of puppet. Choose version 3 to use: 'puppet agent'; version 2 uses
status quo: 'puppetd'.

default: ``2``

puppetca_path
#############

Location of the puppet executable, used for revoking certificates.

default: ``"/usr/bin/puppet"``

pxe_just_once
#############

If this setting is set to ``True``, Cobbler systems that pxe boot will request at the end of their installation to
toggle the ``--netboot-enabled`` record in the Cobbler system record. This eliminates the potential for a PXE boot loop
if the system is set to PXE first in it's BIOS order. Enable this if PXE is first in your BIOS boot order, otherwise
leave this disabled. See the manpage for ``--netboot-enabled``.

default: ``True``

nopxe_with_triggers
###################

If this setting is set to ``True``, triggers will be executed when systems will request to toggle the
``--netboot-enabled`` record at the end of their installation.

default: ``True``

redhat_management_permissive
############################

If using ``modules.authentication.module: "authentication.spacewalk"`` in the settings to let Cobbler authenticate
against Satellite/Spacewalk's auth system, by default it will not allow per user access into Cobbler Web and Cobbler
XML-RPC. In order to permit this, the following setting must be enabled HOWEVER doing so will permit all
Spacewalk/Satellite users of certain types to edit all of Cobbler's configuration. these roles are: ``config_admin``
and ``org_admin``. Users should turn this on only if they want this behavior and do not have a cross-multi-org
separation concern. If you have a single org in your satellite, it's probably safe to turn this on and then you can use
CobblerWeb alongside a Satellite install.

default: ``False``

redhat_management_server
########################

This setting is only used by the code that supports using Uyuni/SUSE Manager/Spacewalk/Satellite authentication within Cobbler Web and
Cobbler XML-RPC.

default: ``"xmlrpc.rhn.redhat.com"``

uyuni_authentication_endpoint
#################################

This setting is only used by the code that supports using uyuni/SUSE Manager authentication within Cobbler Web and Cobbler XMLRPC.
This is the endpoint for uyuni/SUSE Manager authentication: if empty redhat_management_server will be used.

e.g.: ``uyuni_authentication_endpoint: http://localhost``

default: ``""``

redhat_management_key
#####################

Specify the default Red Hat authorization key to use to register system. If left blank, no registration will be
attempted. Similarly you can set the ``--redhat-management-key`` to blank on any system to keep it from trying to
register.

default: ``""``

redhat_management_org
#####################

Specify the default Red Hat organization ID to use to register system.  Used in combination with
redhat_management_key above.

default: ``""``

redhat_management_user
######################

Specify the default Red Hat user to use to register system. If left blank, no registration will be
attempted. Similarly you can set the ``--redhat-management-user`` to blank on any system to keep it from trying to
register.

default: ``""``

redhat_management_password
##########################

Specify the default Red Hat password to use to register system.  Used in combination with
redhat_management_user above.

default: ``""``

register_new_installs
#####################

If set to ``True``, allows ``/usr/bin/cobbler-register`` (part of the Koan package) to be used to remotely add new
Cobbler system records to Cobbler. This effectively allows for registration of new hardware from system records.

default: ``False``

remove_old_puppet_certs_automatically
#####################################

When a puppet managed machine is reinstalled it is necessary to remove the puppet certificate from the puppet master
server before a new certificate is signed (see above). Enabling the following feature will ensure that the certificate
for the machine to be installed is removed from the puppet master server if the puppet master server is running on the
same machine as Cobbler. This requires ``puppet_auto_setup`` above to be enabled

default: ``False``

replicate_repo_rsync_options
############################

Replication rsync options for repos set to override default value of ``-avzH``.

default: ``"-avzH"``

replicate_rsync_options
#######################

replication rsync options for distros, autoinstalls, snippets set to override default value of ``-avzH``.

default: ``"-avzH"``

reposync_flags
##############

Flags to use for yum's reposync. If your version of yum reposync does not support some options, you may need to remove
that options.

default: ``"--newest-only --delete --refresh --remote-time"``

reposync_rsync_flags
####################
Flags to use for rysync's reposync. If archive mode (-a,--archive) is used then createrepo is not run after the rsync as
it pulls down the repodata as well. This allows older OS's to mirror modular repos using rsync.

default: ``"-rltDv --copy-unsafe-links"``

restart_*
#########

When DHCP and DNS management are enabled, ``cobbler sync`` can automatically restart those services to apply changes.
The exception for this is if using ISC for DHCP, then OMAPI eliminates the need for a restart. ``omapi``, however, is
experimental and not recommended for most configurations. If DHCP and DNS are going to be managed, but hosted on a box
that is not on this server, disable restarts here and write some other script to ensure that the config files get
copied/rsynced to the destination box. This can be done by modifying the restart services trigger. Note that if
``manage_dhcp`` and ``manage_dns`` are disabled, the respective parameter will have no effect. Most users should not
need to change this.

defaults:

.. code-block:: YAML

   restart_dns: true
   restart_dhcp: true

run_install_triggers
####################

Install triggers are scripts in ``/var/lib/cobbler/triggers/install`` that are triggered in autoinstall pre and post
sections. Any executable script in those directories is run. They can be used to send email or perform other actions.
They are currently run as root so if you do not need this functionality you can disable it, though this will also
disable ``cobbler status`` which uses a logging trigger to audit install progress.

default: ``true``

scm_track_*
###########

enables a trigger which version controls all changes to ``/var/lib/cobbler`` when add, edit, or sync events are
performed. This can be used to revert to previous database versions, generate RSS feeds, or for other auditing or backup
purposes. Git and Mercurial are currently supported, but Git is the recommend SCM for use with this feature.

default:

.. code-block:: YAML

   scm_track_enabled: false
   scm_track_mode: "git"
   scm_track_author: "cobbler <cobbler@localhost>"
   scm_push_script: "/bin/true"

serializer_pretty_json
######################

Sort and indent JSON output to make it more human-readable.

default: ``False``

server
######

This is the address of the Cobbler server -- as it is used by systems during the install process, it must be the address
or hostname of the system as those systems can see the server. if you have a server that appears differently to
different subnets (dual homed, etc), you need to read the ``--server-override`` section of the manpage for how that
works.

default: ``127.0.0.1``

sign_puppet_certs_automatically
###############################

When puppet starts on a system after installation it needs to have its certificate signed by the puppet master server.
Enabling the following feature will ensure that the puppet server signs the certificate after installation if the puppet
master server is running on the same machine as Cobbler. This requires ``puppet_auto_setup`` above to be enabled.

default: ``false``

signature_path
##############

The ``cobbler import`` workflow is powered by this file. Its location can be set with this config option.

default: ``/var/lib/cobbler/distro_signatures.json``

signature_url
#############

Updates to the signatures may happen more often then we have releases. To enable you to import new version we provide
the most up to date signatures we offer on this like. You may host this file for yourself and adjust it for your needs.

default: ``https://cobbler.github.io/libcobblersignatures/data/v2/distro_signatures.json``

tftpboot_location
#################

This variable contains the location of the tftpboot directory. If this directory is not present Cobbler does not start.

Default: ``/srv/tftpboot``

virt_auto_boot
##############

Should new profiles for virtual machines default to auto booting with the physical host when the physical host reboots?
This can be overridden on each profile or system object.

default: ``true``

webdir
######

Cobbler's web directory.  Don't change this setting -- see the Wiki on "relocating your Cobbler install" if your /var partition
is not large enough.

default: ``@@webroot@@/cobbler``

webdir_whitelist
################

Directories that will not get wiped and recreated on a ``cobbler sync``.

default:

.. code-block:: yaml

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

windows_enabled
###############

Set to true to enable the generation of Windows boot files in Cobbler.

default: ``False``

For more information see :ref:`wingen`.

windows_template_dir
####################

Location of templates used for Windows.

default: ``/etc/cobbler/windows``

For more information see :ref:`wingen`.

samba_distro_share
##################

Samba share name for distros

default: ``DISTRO``

For more information see :ref:`wingen`.

xmlrpc_port
###########

Cobbler's public XML-RPC listens on this port. Change this only if absolutely needed, as you'll have to start supplying
a new port option to Koan if it is not the default.

default: ``25151``

yum_distro_priority
###################

The default yum priority for all the distros. This is only used if yum-priorities plugin is used. 1 is the maximum
value. Tweak with caution.

default: ``true``

yum_post_install_mirror
#######################

``cobbler repo add`` commands set Cobbler up with repository information that can be used during autoinstall and is
automatically set up in the Cobbler autoinstall templates. By default, these are only available at install time. To
make these repositories usable on installed systems (since Cobbler makes a very convenient mirror) set this to ``True``.
Most users can safely set this to ``True``. Users who have a dual homed Cobbler server, or are installing laptops that
will not always have access to the Cobbler server may wish to leave this as ``False``. In that case, the Cobbler
mirrored yum repos are still accessible at ``http://cobbler.example.org/cblr/repo_mirror`` and YUM configuration can
still be done manually. This is just a shortcut.

default: ``True``

yumdownloader_flags
###################

Flags to use for yumdownloader. Not all versions may support ``--resolve``.

default: ``"--resolve"``

modules
#######

If you have own custom modules which are not shipped with Cobbler directly you may have additional sections here.

authentication
==============

module
------

This settings decides the login mechanism is being used to log users

Choices:

- authentication.denyall    -- No one
- authentication.configfile -- Use /etc/cobbler/users.digest (default)
- authentication.passthru   -- Ask Apache to handle it (used for kerberos)
- authentication.ldap       -- Authenticate against LDAP
- authentication.spacewalk  -- Ask Spacewalk/Satellite (experimental)
- authentication.pam        -- Use PAM facilities
- (user supplied)  -- You may write your own module

.. note:: A new web interface is in the making. At the moment we do not have any documentation, yet.

default: ``authentication.configfile``

hash_algorithm
--------------

This parameter has currently only a meaning when the option ``authentication.configfile`` is used.
The parameter decides what hashfunction algorithm is used for checking the passwords.

Choices:

- blake2b
- blake2s
- sha3_512
- sha3_384
- sha3_256
- sha3_224
- shake_128
- shake_256

default: ``sha3_512``

authorization
=============

module
------

Once a user has been cleared by the WebUI/XML-RPC, what can they do?

Choices:

- authorization.allowall   -- full access for all authenticated users (default)
- authorization.ownership  -- use users.conf, but add object ownership semantics
- (user supplied)  -- you may write your own module

.. warning:: If you want to further restrict Cobbler with ACLs for various groups, pick ``authorization.ownership``.
             ``authorization.allowall`` does not support ACLs. Configuration file does but does not support object
             ownership which is useful as an additional layer of control.

.. note:: A new web interface is in the making. At the moment we do not have any documentation, yet.

default: ``authorization.allowall``

dns
===

module
------

Chooses the DNS management engine if ``manage_dns`` is enabled in the settings, which is off by default.

Choices:

- managers.bind    -- default, uses BIND/named
- managers.dnsmasq -- uses dnsmasq, also must select dnsmasq for DHCP below
- managers.ndjbdns -- uses ndjbdns

.. note:: More configuration is still required in ``/etc/cobbler``

For more information see :ref:`dns-management`.

default: ``managers.bind``

dhcp
====

module
------

Chooses the DHCP management engine if ``manage_dhcp`` is enabled in the settings, which is off by default.

Choices:

- managers.isc     -- default, uses ISC dhcpd
- managers.dnsmasq -- uses dnsmasq, also must select dnsmasq for DNS above

.. note:: More configuration is still required in ``/etc/cobbler``

For more information see :ref:`dhcp-management`.

default: ``managers.isc``

tftpd
=====

module
------

Chooses the TFTP management engine if ``manage_tftpd`` is enabled in ``/etc/cobbler/settings.yaml``, which is **on** by
default.

Choices:

- managers.in_tftpd -- default, uses the system's TFTP server

default: ``managers.in_tftpd``

serializers
===========

module
------

This decided where Cobbler stores the item data that is being entered into the application.

Choices:

* serializers.file
* serializers.mongodb
* serializers.sqlite

default: ``serializers.file``

mongodb
=======

host
----

The host where MongoDB is running.

default: ``localhost``

port
----

The port where MongoDB is running.

default: ``27017``

cache_enabled
#############

If set to ``True``, allows the results of some internal operations to be cached, but may slow down editing of objects.

default: ``False``

lazy_start
##########

Set to ``True`` to speed up the start of the Cobbler. When storing collections as files, the directory with the names
of the collection elements will be scanned without reading and parsing the files themselves. In the case of storing
collections in the database, a projection query is made that includes only the names of the collection elements.
The first time an attribute of an element other than a name is accessed, a full read of all other attributes will be
performed, and a recursive full read of all elements on which this element depends. At startup, a background task is
also launched, which, when idle, fills in all the properties of the elements of the collections.
Suitable for configurations with a large number of elements placed on a slow device (HDD, network).

default: ``False``
