***********************************
Release Notes for Cobbler 3.0.0
***********************************

Enhancements
++++++++++++

* Use new dracut ip option for configuring static interfaces (koan).
* Add a whitelist of directories in order to persist a ``cobbler sync``.
* Add proxy support for get-loaders, signature update and reposync.
* Add initial support for DJBDNS.
* Enable external YUM repo mirroring through a proxy server.
* DHCP configuration now also supports the per interface gateway setting.
* A new interface_type ``BMC`` was added which also can be managed with DHCP.
* Yaboot was updated to 1.3.17.
* Add ability to have per-profile/per-system ``next_server`` values (#1196).
* Add ``--graphics`` option to Koan.
* Improved input validation and error handling.
* Support ``virtio26`` for generic QEMU fallback in Koan.
* Debian network config: add support for tagged vlan only bonding interfaces.
* Documentation has been converted into rST and is now included with the source tree.
* Integrated pyflakes into the build system and resolved hundreds of issues.
* Integrated pep8 (coding style) into the build system and resolved thousands of issues.
* Add a new field to the system type ``ipv6_prefix`` (#203).
* Minor update to CSS; make better use of screen (tables) (cobbler-web).
* Add support for an empty system status.
* If ``dns-name`` is specified, set it as DHCP hostname in preference to the ``hostname`` field.
* Allow user to choose whether or not to delete item(s) recursively (cobbler-web).
* Set ksdevice kernel option to MAC address for ppc systems as bootif is not used by yaboot.
* Return to list of snippets/kickstarts when snippet/kickstart is saved (cobbler-web).
* Layout in snippet/kickstart edit form has been improved (cobbler-web).
* Better handling of copy/remove actions for subprofiles (API and cobbler-web).
* Make kickstart selectable from a pulldown list in cobbler-web (#991).

Bugfixes
++++++++

* Changed Apache configuration directory in Ubuntu 14.04 (#1208).
* build_reporting no longer fails with an empty string in ignorelist (#1248).
* Kickstart repo statement, filter invalid values: ``gpgcheck``, ``gpgkey`` and ``enabled`` (#323).
* Several improvements to Debian/Ubuntu packaging.
* Some class/method names have been changed to make the code more intuitive for developers.
* Remove ``root=`` argument in Koan when using grubby and replace-self to avoid booting the current OS.
* Exit with an error if the cobblerd executable can't be found (#1108, #1135).
* Fix cobbler sync bug by xmlrpclib returning NoneType object.
* Dont send the Puppet environment when system status is empty (#560).
* Cobbler-web kept only the most recent interface change (#687).
* Fix broken gitdate, gitstamp values in ``/etc/cobbler/version``.
* Prevent disappearing profiles after cobblerd restart (#1030).
* Add missing icons to cobbler_web/content (#679).
* cobbler-ext-nodes was broken with ``mgmt_classes`` defined at the profile level (#790).
* Properly name the VLAN interface in the manual page.
* Fix wrong address of the Free Software Foundation.
* Remove legacy (EL5/6) cruft from the RPM specfile.
* Koan: use the print function instead of the print statement.
* Minor improvement to LDAP configuration (#217).
* Improvements to the unittest framework.
* Removed several unused functions from utils.
* List of authors is now automagically generated.

Upgrade notes
+++++++++++++

* Support for LDAP configuration through Koan has been removed.
* Support for redhat_management (Spacewalk/Satelite) has been moved to contrib. Users of this functionality should
  checkout contrib/redhat-management/README.
* Monit support has been removed; you really need to use a CMS to manage your services.
* Support for remote kickstart templates and files been removed (eg. kickstart=http://).
* All object names are now validated like that of the system object.
* The use of ``parent`` and ``distro`` on subprofiles are now mutually exclusive.
* Support for s390/s390x has been removed.
* Support for ia64 (Itanium) has been removed.
* Support for the MySQL backend has been removed.
* Support for deprecated fieldnames (``subnet``, ``bonding_master``, ``bonding``) has been removed.
* Cobbler now requires python 2.7 and Koan now requires python 2.6.
* Red Hat specific default kernel options have been removed from the settings file.
* Support for Func integration has been moved to contrib. Users of this functionality should checkout
  contrib/func/README.
* Deprecated Koan LiveCD: moved to contrib.

