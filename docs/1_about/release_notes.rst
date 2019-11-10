*************
Release Notes
*************

2.8.0
#####

Deprecation warnings
====================

The following list of features have been deprecated and will *not* be available in Cobbler 3.0. Users depending on one
of these features should stick to the 2.8.x (LTS) series. If you'd like to maintain one of these features in 3.x and
beyond, then please reach out to the developers through GitHub or the mailinglist.

- MySQL backend
- CouchDB backend
- MongoDB backend
- Monit support
- Platforms: s390/s390x and ia64
- System field names: subnet, bonding_master, bonding
- Func integration
- Koan LiveCD
- Koan LDAP configuration
- redhat_management (Spacewalk/Satellite)
- Remote kickstart files/templates (other than on the Cobbler server)
- The concurrent use of ``parent`` and ``distro`` on subprofiles

Feature improvements
====================

- Signature updates: Fedora 24/25, Ubuntu 16.10, Virtuozzo 7
- Integrated ``pyflakes`` into the build system and fixed all reported issues
- Integrated Travis CI into the build system (``make qa``)
- Allow https method in repo management (\#1587)
- Add support for the ``ppc64le`` architecture
- Backport gpxe mac search argument
- Added support for fixed DHCP IPs when using vlan over bond
- Add support for Django 1.7.x and 1.8.x
- Add action name to cobbler action ``--help`` output

Bugfixes
========

- Added HOSTS_ALLOW acl in settings.py (CVE-2016-9014)
- Profile template logic seperated for grub and pxelinux formats
- Refer to system_name in grubsystem.template
- Add netmask and dhcp_tag to slave interfaces in ISC DHCP
- Koan now works with CentOS version numbers
- Fixes to pxesystem_esxi.template
- Move ``get-loaders`` to https transport
- Add default/timeout to grubsystem.template
- Anamon now actually waits on files that you specify with ``--watchfiles``
- Do not set interface["filename"] to /pxelinux.0 in manage_isc.py (\#1565)
- Allow the use of relative paths when importing a distro (\#1613)
- Fix /etc/xinetd.d/rsync check (\#1651)
- Exit with a appropiate message when signature file can't be parsed
- Handle cases where virt-install responds to ``--version`` on stderr (Koan)
- Fix mangling of kernel options in  edit profile command with ``--in-place``
- Several fixes to Koan regarding os-info-query and os-variants
