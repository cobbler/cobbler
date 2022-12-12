Boot CD
#######

Cobbler can build all of it's profiles into a bootable CD image using the ``cobbler buildiso`` command. This allows for
PXE-menu like bring up of bare metal in environments where PXE is not possible. Another more advanced method is described
in the Koan manpage, though this method is easier and sufficient for most applications.

.. _dhcp-management:

DHCP Management
===============

Cobbler can optionally help you manage DHCP server. This feature is off by default.

Choose either ``modules.dhcp.module: "managers.isc"`` or ``modules.dhcp.module: "dnsmasq"`` in the settings. For this
setting to take effect ``manage_dhcp: true`` and at least one of ``manage_dhcp_v4`` or ``manage_dhcp_v6`` must be also
set to ``true``.

This allows DHCP to be managed via "cobbler system add" commands, when you specify the mac address and IP address for
systems you add into Cobbler.

Depending on your choice, Cobbler will use ``/etc/cobbler/dhcpd.template`` or ``/etc/cobbler/dnsmasq.template`` as a
starting point. This file must be user edited for the user's particular networking environment. Read the file and
understand how the particular app (ISC dhcpd or dnsmasq) work before proceeding.

If you already have DHCP configuration data that you would like to preserve (say DHCP was manually configured earlier),
insert the relevant portions of it into the template file, as running ``cobbler sync`` will overwrite your previous
configuration.

By default, the DHCP configuration file will be updated each time ``cobbler sync`` is run, and not until then, so it is
important to remember to use ``cobbler sync`` when using this feature.

If omapi_enabled is set to 1 in ``/etc/cobbler/settings.yaml``, the need to sync when adding new system records can be
eliminated. However, the OMAPI feature is experimental and is not recommended for most users.

.. _dns-management:

DNS configuration management
============================

Cobbler can optionally manage DNS configuration using BIND and dnsmasq.

Choose either ``modules.dns.module: "managers.bind"`` or ``modules.dns.module: "managers.dnsmasq"`` in the settings. To
enable the choice enable ``manage_dns`` in the settings.

You may also choose ``modules.dns.module: "managers.ndjbdns"`` as a management engine for DNS. For this the DNS server
tools of D.J. Bernstein need to be installed. For more information please refer to `<https://cr.yp.to/djbdns.html>`_

This feature is off by default. If using BIND, you must define the zones to be managed with the options
``manage_forward_zones`` and ``manage_reverse_zones``.

If using BIND, Cobbler will use ``/etc/cobbler/named.template`` and ``/etc/cobbler/zone.template`` as a starting point
for the ``named.conf`` and individual zone files, respectively. You may drop zone-specific template files in
``/etc/cobbler/zone_templates/name-of-zone`` which will override the default. These files must be user edited for the
user's particular networking environment. Read the file and understand how BIND works before proceeding.

If using dnsmasq, the template is ``/etc/cobbler/dnsmasq.template``. Read this file and understand how dnsmasq works
before proceeding.

If using ndjbdns, the template is ``/etc/cobbler/ndjbdns.template``. Read the file and understand how ndjbdns works
before proceeding.

All managed files (whether zone files and ``named.conf`` for BIND, or ``dnsmasq.conf`` for dnsmasq) will be updated each
time ``cobbler sync`` is run, and not until then, so it is important to remember to use ``cobbler sync`` when using this
feature.
