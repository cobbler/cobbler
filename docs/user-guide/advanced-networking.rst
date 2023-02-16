Advanced networking
###################

First off, read the cobbler manpage for all the settings you can set on a system object.

This page details some of the networking tips and tricks in more detail, regarding what you can set on system records
to set up networking, without having to know a lot about kickstart/Anaconda.

These features include:

* Arbitrary NIC naming (the interface is matched to a physical device using it's MAC address)
* Configuring DNS nameserver addresses
* Setting up NIC bonding
* Defining for static routes
* Support for VLANs

If you want to use any of these features, it's highly recommended to add the MAC addresses for the interfaces you're
using to Cobbler for each system.

Arbitrary NIC naming
====================

You can give your network interface (almost) any name you like.

.. code-block::

    cobbler system edit --name=foo1.bar.local --interface=mgmt --mac=AA:BB:CC:DD:EE:F0]
    cobbler system edit --name=foo1.bar.local --interface=dmz --mac=AA:BB:CC:DD:EE:F1

The default interface is named ``default``, but you don't have to call it that.

Note that you can't name your interface after a kernel module you're using. For example: if a NIC is called ``drbd``,
the module ``drbd.ko`` would stop working. This is due to an "alias" line in ``/etc/modprobe.conf``.

Name Servers
============

For static systems, the ``--name-servers`` parameter can be used to
specify a list of name servers to assign to the systems.

.. code-block::

    cobbler system edit --name=foo --interface=eth0 --mac=AA:BB:CC::DD:EE:FF --static=1 --name-servers="<ip1> <ip2>"

DNS and DHCP Management
-----------------------

See [ManageDns](Dns Management) and [ManageDhcp](Dhcp Management) for how cobbler can help control your DHCP and DNS servers.

NIC bonding
===========

Bonding is also known as trunking, or teaming. Different vendors use different names. It's used to join multiple
physical interfaces to one logical interface, for redundancy and/or performance.

You can set up a bond, to join interfaces eth0 and ``eth1`` to a failover (active-backup) interface ``bond0`` as
follows:

.. code-block::

    cobbler system edit --name=foo2.bar.local --interface=eth0 --mac=AA:BB:CC:DD:EE:F0 --bonding=slave --bonding-master=bond0
    cobbler system edit --name=foo2.bar.local --interface=eth1 --mac=AA:BB:CC:DD:EE:F1 --bonding=slave --bonding-master=bond0
    cobbler system edit --name=foo2.bar.local --interface=bond0 --bonding=master --bonding-opts="miimon=100 mode=1"

Static routes
=============

You can define static routes for a particular interface to use with ``--static-routes``.

The format of a static route is: ``network/CIDR:gateway``

So, for example to route the ``192.168.1.0/24`` network through ``192.168.1.254``:

.. code-block::

    $ cobbler system edit --name=foo --interface=eth0 --static-routes="192.168.1.0/24:192.168.1.254"

As with all lists in cobbler, the ``--static-routes`` list is space-separated so you can specify multiple static routes
if needed.

VLANs
=====

You can now add VLAN tags to interfaces from Cobbler. In this case we have two VLANs on ``eth0``: 10 and 20. The default
VLAN (untagged traffic) is not used:

.. code-block::

    cobbler system edit --name=foo3.bar.local --interface=eth0 --mac=AA:BB:CC:DD:EE:F0 --static=1
    cobbler system edit --name=foo3.bar.local --interface=eth0.10 --static=1 --ip=10.0.10.5 --subnet=255.255.255.0
    cobbler system edit --name=foo3.bar.local --interface=eth0.20 --static=1 --ip=10.0.20.5 --subnet=255.255.255.0

You have to install the vconfig package for this to work.

Kickstart Notes
===============

Three different networking [Kickstart Snippets](Kickstart Snippets) must be present in your kickstart files for this to work:

* ``pre_install_network_config``
* ``network_config``
* ``post_install_network_config``

The default kickstart templates (``/var/lib/cobbler/kickstart/sample\*.ks``) have these installed by default so they
work out of the box.
