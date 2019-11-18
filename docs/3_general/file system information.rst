***********************
File System Information
***********************

A typical Cobbler install looks something as follows. Note that in general Cobbler manages its own directories. Editing
templates and configuration files is intended. Deleting directories will result in very loud alarms. Please do not ask
for help if you decide to delete core directories or move them around.

See :ref:`relocating-cobbler` if you have space problems.

/var/log/cobbler
################

All Cobbler logs go here. Cobbler does not dump to ``/var/log/messages``, though other system services relating to
netbooting do.

/var/www/cobbler
################

This is a Cobbler owned and managed directory for serving up various content that we need to serve up via http. Further
selected details are below. As tempting as it is to self-garden this directory, do not do so. Manage it using the
"cobbler" command or the Cobbler web app.

/var/www/cobbler/web/
=====================

Here is where the ``mod_python`` web interface and supporting service scripts live for Cobbler pre 2.0

/var/www/cobbler/webui/
=======================

Here is where content for the (pre 2.0) webapp lives that is not a template. Web templates for all versions live in
``/usr/share/cobbler``.

/var/www/cobbler/aux/
=====================

This is used to serve up certain scripts to anaconda, such as anamon (See :ref:`anaconda` for more information on
anamon).

/var/www/cobbler/svc/
=====================

This is where the ``mod_wsgi`` script for Cobbler lives.

/var/www/cobbler/images/
========================

Kernel and initrd files are copied/symlinked here for usage by koan.

/var/www/cobbler/ks_mirror/
============================

Install trees are copied here.

/var/www/cobbler/repo_mirror/
=============================

Cobbler repo objects (i.e. yum, apt-mirror) are copied here.

/var/lib/cobbler/
#################

This is the main data directory for Cobbler. See individual descriptions of subdirectories below.

/var/lib/cobbler/config/
========================

Here Cobbler stores configuration files that it creates when you make or edit Cobbler objects. If you are using
``serializer_catalog`` in ``modules.conf``, these will exist in various "``.d``" directories under this main directory.

/var/lib/cobbler/backups/
=========================

This is a backup of the config directory created on RPM upgrades. The configuration format is intended to be forward
compatible (i.e. upgrades without user intervention are supported) though this file is kept around in case something
goes wrong during an install (though it never should, it never hurts to be safe).

/var/lib/cobbler/kickstarts/
============================

This is where Cobbler's shipped kickstart templates are stored. You may also keep yours here if you like. If you want to
edit kickstarts in the web application this is the recommended place for them. Though other distributions may have
templates that are not explicitly 'kickstarts', we also keep them here.

/var/lib/cobbler/snippets/
==========================

This is where Cobbler keeps snippet files, which are pieces of text that can be reused between multiple kickstarts.

/var/lib/cobbler/triggers/
==========================

Various user-scripts to extend Cobbler to perform certain actions can be dropped into subdirectories of this directory.
See the :ref:`triggers` section for more information.

/usr/share/cobbler/web
######################

This is where the cobbler-web package (for Cobbler 2.0 and later) lives. It is a Django app.

/etc/cobbler/
#############

- **cobbler.conf** - Cobbler's most important config file. Self-explanatory with comments, in YAML format.
- **modules.conf** - auxilliary config file. controls Cobbler security, and what DHCP/DNS engine is attached, see
  :ref:`modules` for developer-level details, and also Security Overview. This file is in an INI-style format that can
  be read by the ConfigParser class.
- **users.digest** - if using the digest authorization module this is where your web app username/passwords live. Refer
  to the :ref:`web-interface` section for more info.

/etc/cobbler/power
==================

Here we keep the templates for the various power management modules Cobbler supports. Please refer to the
:ref:`power-management` section for more details on configuring power management features.

/etc/cobbler/pxe
================

Various templates related to netboot installation, not neccessarily "pxe".

/etc/cobbler/zone_templates
===========================

If the chosen DNS management module for DNS is BIND, this directory is where templates for each zone file live. dnsmasq
does not use this directory.

/etc/cobbler/reporting
======================

Templates for various reporting related functions of Cobbler, most notably the new system email feature in Cobbler 1.5
and later.

/usr/lib/python${VERSION}/site-packages/cobbler/
################################################

The source code to Cobbler lives here. If you have multiple versions of python installed, make sure Cobbler is in the
site-packages directory for the correct python version (you can use symlinks to make it available to multiple versions).

/usr/lib/python${VERSION}/site-packages/cobbler/modules/
========================================================

This is a directory where modules can be dropped to extend Cobbler without modifying the core. See :ref:`modules` for
more information.
