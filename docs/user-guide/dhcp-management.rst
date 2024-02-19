.. _dhcp-management:

***************
DHCP Management
***************

Cobbler can optionally help you manage DHCP server. This feature is off by default.

Choose either ``modules.dhcp.module: "managers.isc"`` or ``modules.dhcp.module: "managers.dnsmasq"`` in the settings. For this
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