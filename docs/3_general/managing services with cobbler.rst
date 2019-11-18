.. _managing-services-with-cobbler:

******************************
Managing Services with Cobbler
******************************

.. _manage-dhcp:

DHCP
####

You may want cobbler to manage the DHCP entries of its client systems. It currently supports either ISC DHCP or dnsmasq
(which, despite the name, supports DHCP). Cobbler can also be used to manage your DNS configuration (see
:ref:`manage-dns` for more details).

To use ISC, your ``/etc/cobbler/modules.conf`` should contain:

.. code-block:: yaml

    [dhcp]
    module = manage_isc

To use dnsmasq, it should contain:

.. code-block:: yaml

    [dns]
    module = manage_dnsmasq

    [dhcp]
    module = manage_dnsmasq

.. note:: Using dnsmasq for DHCP requires that you use it for DNS, even if you disable ``manage_dns`` in your
   :ref:`settings`. You should not try to mix the ISC module with the dnsmasq module.

You also need to enable such management; this is done in :ref:`settings`.

.. code-block:: yaml

    manage_dhcp: 1
    restart_dhcp: 1

The relevant software packages also need to be present; :ref:`cobbler-check` will
verify this.

When To Enable DHCP Management
==============================

DHCP is closely related to PXE-based installation. If you are maintaining a database of your systems and what they run,
it can make sense also to manage hostnames and IP addresses. Controlling DHCP from Cobbler can coordinate all this. This
capability is a good fit if you can control DHCP for a lab or datacenter and want to run DHCP from the same server where
you are running Cobbler. If you have an existing configuration of things that cobbler shouldn't be managing, you can
copy them into your ``/etc/cobbler/dhcp.template``.

The default behaviour is for cobbler **not** to manage your DHCP infrastructure. Make sure that in your existing
``dhcp.conf`` the next-server entry and filename information are correct to serve up ``pxelinux.0`` to the machines that
want it (for the case of bare metal installations over PXE).

Setting up
==========

ISC considerations
******************

The master DHCP file when run from cobbler is ``/etc/cobbler/dhcp.template``, not the more usual ``/etc/dhcpd.conf``.
Edit this template file to suit your environment; this is mainly just making sure that the DHCP information is correct.
Youcan also include anything you may have had from an existing setup.

DNSMASQ considerations
**********************

If using dnsmasq, the template file is ``/etc/cobbler/dnsmasq.template`` but it basically works as for ISC (above).
Remember that dnsmasq also provides DNS.

How It Works
============

Suppose the following command is given (where ``<profile name>`` is an existing profile in cobbler):

.. code-block:: bash

    $ cobbler system add --name=foo --profile=<profile name>
      --interface=eth0 --mac=AA:BB:CC:DD:EE:FF --ip-address=192.168.1.1

That will take the template file in ``/etc/cobbler/dhcp.template``, fill in the appropriate fields, and generate a
fuller configuration file ``/etc/dhcpd.conf`` that includes this machine, and ensures that when AA:BB:CC:DD:EE:FF asks
for an IP, it gets 192.168.1.1. The ``--ip-address=...`` specification is optional; DHCP can make dynamic assignments
within a configured range.

To make this active, run:

.. code-block:: bash

    $ cobbler sync

As noted in the :ref:`cobbler-sync` section, managing DHCP with the ISC module is one of the few times you will need to
use the full sync via ``cobbler sync``.

Itanium: additional requirements
********************************

Itanium-based systems are more complicated and special the other architectures, because their bootloader is not as
intelligent, and requires a "filename" value that references elilo, not pxelinux.

* When creating the distro object, make sure that ``--arch=ia64`` is specified.
* You need to create system objects, and the ``--mac-address`` argument is mandatory. (This is due to a deficiency in
  LILO where it will ask for an encoded IP address, but will not ask for a PXE configuration file based on the MAC
  address.)
* You need to specify the ``--ip-address=...`` value on system objects.
* In ``/etc/cobbler/settings``, you must (for now) choose ``dhcp_isc``.

Also, sometimes Itaniums tend to hang during net installs; the reasons are unknown.

ISC and OMAPI for dynamic DHCP updates
**************************************

OMAPI support for updating ISC DHCPD is actually not supported.  This was a buggy feature (we think OMAPI itself is
buggy) and apparently OMAPI is slated for removal in a future version of ISC dhcpd.

Static IPs
**********

Lots of users will deploy with DHCP for PXE purposes and then use the Anaconda installer or other mechanism to configure
static networking.  For this, you do not need to use this DHCP Management feature. Instead you can configure your DHCP
to provide a dynamic range, and configure the static addresses by other mechanisms.

For instance ``cobbler system ...`` can set each interface. Cobbler's default :ref:`snippets` will handle the rest.

Alternatively, if your site uses a :ref:`config-management` system, that might be suitable for such configuration.

If You Don't Have Any DHCP
**************************

If you don't have any DHCP at all, you can't PXE, and you can ignore this feature, but you can still take advantage of
:ref:`buildiso` for bare metal installations. This is also good for installing machines on different networks that might
not have a next-server configured.

.. _manage-dns:

DNS
###

You may want cobbler to manage the DNS entries of its client systems. Cobbler can do so automatically by using
templates. It currently supports either dnsmasq (which also provides DHCP) or BIND. Cobbler also has the ability to
handle :ref:`manage-dhcp`.

To use BIND, your ``/etc/cobbler/modules.conf`` should contain:

.. code-block:: yaml

    [dns]
    module = manage_bind

    [dhcp]
    module = manage_isc

To use dnsmasq, it should contain:

.. code-block:: yaml

    [dns]
    module = manage_dnsmasq

    [dhcp]
    module = manage_dnsmasq

You should not try to mix these.

You also need to enable such management; this is done in ``/etc/cobbler/settings``:

.. code-block:: yaml

    manage_dns: 1

    restart_dns: 1

The relevant software packages also need to be present; ``cobbler check`` will verify this.

General considerations
======================

* Your maintenance is performed on template files. These do not take effect until a ``cobbler sync`` has been performed
  to generate the run-time data files.
* The serial number on the generated zone files is the cobbler server's UNIX epoch time, that is, seconds since
  1970-01-01 00:00:00 UTC. If, very unusually, your server's time gets reset backwards, your new zone serial number
  could have a smaller number than previously, and the zones will not propagate.

BIND considerations
===================

In ``/etc/cobbler/settings`` you will need entries resembling the following:

.. code-block:: bash

    manage_forward_zones: ['foo.example.com', 'bar.foo.example.com']

    manage_reverse_zones: ['10.0.0', '192.168', '172.16.123']

Note that the reverse zones are in simple IP ordering, not in BIND-style "0.0.10.in-addr.arpa".

(??? CIDR for non-octet netmask ???)

Restricting Zone Scope
**********************

DNS hostnames will be put into their "best fit" zone.  Continuing the above illustration, example hosts would be placed
as follows:

* ``baz.bar.foo.example.com`` as host ``baz`` in zone ``bar.foo.example.com``
* ``fie.foo.example.com`` as host ``fie`` in ``foo.example.com``
* ``badsub.oops.foo.example.com`` as host ``badsub.oops`` in ``foo.example.com``

Default and zone-specific templating
************************************

Cobbler will use ``/etc/cobbler/bind.template`` and ``/etc/cobbler/zone.template`` as a starting point for BIND's
``named.conf`` and individual zone files, respectively.  You may drop zone-specific template files into the directory
``/etc/cobbler/zone_templates/`` which will override the default.  For example, if you have a zone ``foo.example.com``,
you may create ``/etc/cobbler/zone_templates/foo.example.com`` which will be used in lieu of the default
``/etc/cobbbler/zone.template`` when generating that zone. This can be useful to define zone-specific records such as
MX, CNAME, SRV, and TXT.

All template files must be user edited for the local networking environment.  Read the file and understand how BIND
works before proceeding.

BIND's `named.conf` file and all zone files will be updated only when "cobbler sync" is run, so it is important to
remember to use it.

Other
*****

Note that your client's system interfaces _must_ have a ``--dns-name`` set to be considered for inclusion in the zone
files. If ``cobbler system report`` shows that your ``--dns-name`` is unset, it can be set by:

.. code-block:: bash

    cobbler system edit --name=foo.example.com --dns-name=foo.example.com

You can set a different such name per interface and each will get its own respective DNS entry.

DNSMASQ considerations
======================

You should review and adjust the contents of ``/etc/cobbler/dnsmasq.template``.

.. _manage-rsync:

rsync
#####

.. _managing-tftp:

TFTP
####
