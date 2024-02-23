.. _dns-management:

**************
DNS management
**************

Cobbler can optionally manage DNS configuration using BIND and dnsmasq.

Choose either ``module = managers.bind`` or ``module = managers.dnsmasq`` in ``/etc/cobbler/modules.conf`` and then
enable ``manage_dns`` in ``/etc/cobbler/settings.yaml``.

You may also choose ``module = managers.ndjbdns`` as a management engine for DNS. For this the DNS server tools of
D.J. Bernstein need to be installed. For more information please refer to `<https://cr.yp.to/djbdns.html>`_

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