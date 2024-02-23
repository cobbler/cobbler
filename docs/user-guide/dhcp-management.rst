.. _dhcp-management:

***************
DHCP Management
***************

Cobbler can optionally help you manage a DHCP server. This feature is disabled by default.

The following options are available for ``modules.dhcp.module``:

* ``"managers.isc"``
* ``"managers.dnsmasq"``

Set ``manage_dhcp: true`` and ``manage_dhcp_v4`` or ``manage_dhcp_v6`` to ``true`` for this setting to take effect.

This allows DHCP to be managed via "cobbler system add" commands, when you specify the MAC address and IP address for
systems you add into Cobbler.

You must configure the templates for your networking environment. Read the file and understand how
the particular app works before proceeding.

If you already have DHCP configuration data that you would like to preserve (such as DHCP that was manually configured earlier),
insert the relevant portions of it into the template file, as running ``cobbler sync`` will overwrite your previous
configuration.

By default, Cobbler updates the DHCP configuration file each time you run ``cobbler sync``.
Remember to use ``cobbler sync`` when you use this feature.

``isc`` DHCP
############

Helpful links:

* Website: https://www.isc.org/dhcp/
* Documentation: https://kb.isc.org/docs/aa-00333

Templates used during generation:

* ``/etc/cobbler/dhcp.template``
* ``/etc/cobbler/dhcp6.template``

``dnsmasq`` DHCP
################

Helpful links:

* Website: https://thekelleys.org.uk/dnsmasq/doc.html
* Documentation: https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html

Templates used during generation:

* ``/etc/cobbler/dnsmasq.template``

``Kea`` DHCP
############

Support for Kea is a not yet implemented feature request: https://github.com/cobbler/cobbler/issues/3609

Helpful links:

* Website https://www.isc.org/kea/
* Migration tool from isc: https://www.isc.org/dhcp_migration/
* Documentation: https://kea.readthedocs.io/en/latest/index.html
