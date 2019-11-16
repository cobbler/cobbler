*******************
Configuration Files
*******************

Cobbler has many configuration files, however only a few typically need be modified for basic functionality:

Settings File
#############

The main settings file for cobbler is ``/etc/cobbler/settings``. Cobbler also supports :ref:`dynamic-settings`, so it is
no longer required to manually edit this file if this feature is enabled. This file is YAML-formatted, and with dynamic
settings enabled [Augeas](http://augeas.net/) is used to modify its contents.

Whether dynamic settings are enabled or not, if you directly edit this file you must restart cobblerd. When modified
with the dynamic settings CLI command or the web GUI, changes take affect immediately and do not require a restart.

Modules Configuration
#####################

Cobbler supports add-on modules, some of which can provide the same functionality (for instance, the
authentication/authorization modules discussed in the :ref:`web-authentication` section). Modules of this nature are
configured via the ``/etc/cobbler/modules.conf`` file, for example:

.. code-block:: yaml

    # dns:
    # chooses the DNS management engine if manage_dns is enabled
    # in /etc/cobbler/settings, which is off by default.
    # choices:
    #    manage_bind    -- default, uses BIND/named
    #    manage_dnsmasq -- uses dnsmasq, also must select dnsmasq for dhcp below

    [dns]
    module = manage_bind

As you can see above, this file has a typical INI-style syntax where sections are denoted with the `[` & `]` brackets
and entries are of the form ``key = value``.

Many of these sections are covered in the :ref:`managing-services-with-cobbler` and :ref:`web-authentication`
topics later in this manual. Please refer to those sections for further details on modifying this file.

As with the settings file, you must restart cobblerd after making changes to this file.
