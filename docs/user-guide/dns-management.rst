.. _dns-management:

**************
DNS management
**************

Cobbler can optionally manage DNS configuration. This feature is disabled by default.

The following options are available for ``modules.dns.module``:

* ``"managers.bind"``
* ``"managers.dnsmasq"``

For this setting to take effect, ``manage_dns`` must be set to ``True``.

All managed files will be updated each time ``cobbler sync`` is run, and not until then, so it is important to remember
to use ``cobbler sync`` when using this feature.

`bind` DNS
##########

If using BIND, you must define the zones to be managed with. This is done with two options

* ``manage_forward_zones``: This option is a list of domain names.
* ``manage_reverse_zones``: This option is a list of IP addresses.

If using BIND, Cobbler will use ``/etc/cobbler/named.template`` and ``/etc/cobbler/zone.template`` as a starting point
for the ``named.conf`` and individual zone files, respectively. You may drop zone-specific template files in
``/etc/cobbler/zone_templates/<name-of-zone>`` which will override the default. These files must be edited manually by the user to fit the
user's particular networking environment. Read the file and understand how BIND works before proceeding.

Helpful links:

* Website: https://www.isc.org/bind/
* Documentation: https://bind9.readthedocs.io/en/latest/#

Templates used during generation:

* ``/etc/cobbler/named.template``
* ``/etc/cobbler/zone.template``
* ``/etc/cobbler/zone_templates/<name-of-zone>``

`dnsmasq` DNS
#############

If using dnsmasq, the template is ``/etc/cobbler/dnsmasq.template``. Read this file and understand how dnsmasq works
before proceeding.

Helpful links:

* Website: https://thekelleys.org.uk/dnsmasq/doc.html
* Docs: https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html

Templates used during generation:

* ``/etc/cobbler/dnsmasq.template``

`ndjbdns` DNS
#############

If using ndjbdns, the template is ``/etc/cobbler/ndjbdns.template``. Read the file and understand how ndjbdns works
before proceeding.

For this the DNS server tools of D.J. Bernstein need to be installed.

Helpful links:

* Website: `<https://cr.yp.to/djbdns.html>`_

Templates used during generation:

* ``/etc/cobbler/ndjbdns.template``
