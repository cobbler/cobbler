.. _dns-management:

**************
DNS management
**************

Cobbler can optionally manage DNS configuration. This feature is off by default.

The following options are available for ``modules.dns.module``:

* ``"managers.bind"``
* ``"managers.dnsmasq"``

For this setting to take effect ``manage_dns`` must be set to ``True``.

All managed files will be updated each time ``cobbler sync`` is run, and not until then, so it is important to remember
to use ``cobbler sync`` when using this feature.

bind DNS
########

If using BIND, you must define the zones to be managed with. This is done with two options

* ``manage_forward_zones``: This option is a list of domain names.
* ``manage_reverse_zones``: This option is a list of IP addresses.

While the built-in templates provide a good starting point for many environment, they may not be suitable for all
use-cases. As such, these files must be user edited for the user's particular networking environment. Read the files and
understand how BIND works before proceeding.

Helpful links:

* Website: https://www.isc.org/bind/
* Documentation: https://bind9.readthedocs.io/en/latest/#

Templates used during generation:

* ``named.conf``: A template with the tags ``named_primary`` and ``active``.
* ``secondary.conf``: A template with the tags ``named_secondary`` and ``active``.
* Default zone template: A template with the tags ``named_zone_default`` and ``active``.
* Specific zone template: A template with the tags ``named_zone_specifc`` and your DNS zone name (e.g. ``example.org``).

dnsmasq DNS
###########

Helpful links:

* Website: https://thekelleys.org.uk/dnsmasq/doc.html
* Docs: https://thekelleys.org.uk/dnsmasq/docs/dnsmasq-man.html

Templates used during generation:

* A template with the tags ``dnsmasq`` and ``active`` qualifies.

ndjbdns DNS
###########

If using ndjbdns, the template is ``/etc/cobbler/ndjbdns.template``. Read the file and understand how ndjbdns works
before proceeding.

For this the DNS server tools of D.J. Bernstein need to be installed.

Helpful links:

* Website: `<https://cr.yp.to/djbdns.html>`_

Templates used during generation:

* A template with the tags ``ndjbdns`` and ``active`` qualifies.
