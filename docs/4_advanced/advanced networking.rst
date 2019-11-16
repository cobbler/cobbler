.. _advanced-networking:

*******************
Advanced Networking
*******************

General
#######

This page details some of the networking tips and tricks in more detail, regarding what you can set on system records to
set up networking, without having to know a lot about kickstart/Anaconda.

These features include:

-   Arbitrary NIC naming (the interface is matched to a physical
    device using it's MAC address)
-   Configuring DNS nameserver addresses
-   Setting up NIC bonding
-   Defining for static routes
-   Support for VLANs

If you want to use any of these features, it's highly recommended
to add the MAC addresses for the interfaces you're using to Cobbler
for each system.

Arbitrary NIC naming
********************

You can give your network interface (almost) any name you like.

{% highlight bash %}
$ cobbler system edit --name=foo1.bar.local --interface=mgmt --mac=AA:BB:CC:DD:EE:F0
$ cobbler system edit --name=foo1.bar.local --interface=dmz --mac=AA:BB:CC:DD:EE:F1
{% endhighlight %}

The default interface is named eth0, but you don't have to call it that.

Note that you can't name your interface after a kernel module you're using. For example: if a NIC is called 'drbd', the
module drbd.ko would stop working. This is due to an "alias" line in /etc/modprobe.conf.

Name Servers
************

For static systems, the --name-servers parameter can be used to
specify a list of name servers to assign to the systems.

{% highlight bash %}
$ cobbler system edit --name=foo --interface=eth0 --mac=AA:BB:CC::DD:EE:FF --static=1 --name-servers="<ip1> <ip2>"
{% endhighlight %}

Static routes
*************

You can define static routes for a particular interface to use with --static-routes. The format of a static route is:

<code>
network/CIDR:gateway
</code>

So, for example to route the 192.168.1.0/24 network through 192.168.1.254:

{% highlight bash %}
$ cobbler system edit --name=foo --interface=eth0 --static-routes="192.168.1.0/24:192.168.1.254"
{% endhighlight %}

As with all lists in cobbler, the --static-routes list is space-separated so you can specify multiple static routes if
needed.

Kickstart Notes
***************

Three different networking [Snippets]({% link manuals/2.8.0/3/6_-_Snippets.md %}) must be present in your kickstart
files for this to work:

<pre>
pre_install_network_config
network_config
post_install_network_config
</pre>

The default kickstart templates (`/var/lib/cobbler/kickstart/sample\*.ks`) have these installed by default so they work
out of the box. Please use those files as a reference as to where to correctly include the $SNIPPET definitions.

Bonding
#######

Bonding is also known as trunking, or teaming. Different vendors use different names. It's used to join multiple
physical interfaces to one logical interface, for redundancy and/or performance.

You can set up a bond, to join interfaces eth0 and eth1 to a failover (active-backup) interface bond0 as follows:

{% highlight bash %}
$ cobbler system edit --name=foo --interface=eth0 --mac=AA:BB:CC:DD:EE:F0 --interface-type=bond_slave --interface-master=bond0
$ cobbler system edit --name=foo --interface=eth1 --mac=AA:BB:CC:DD:EE:F1 --interface-type=bond_slave --interface-master=bond0
$ cobbler system edit --name=foo --interface=bond0 --interface-type=bond --bonding-opts="miimon=100 mode=1" --ip-address=192.168.1.100 --netmask=255.255.255.0
{% endhighlight %}

You can specify any bonding options you would like, so please read the kernel documentation if you are unfamiliar with
the various bonding modes Linux can support.

Notes About Bonding Syntax
**************************

The methodology to create bonds was changed in 2.2.x with the introduction of bridged interface support. The
**--bonding** and **--bonding-master** options have since been deprecated and are now an alias to **--interface-type**
and **--interface-master**, respectively.

Likewise, the master/slave options have been deprecated in favor of bond/bond_slave. Cobbler will continue to read
system objects that have those fields set, but when the object is edited and saved back to disk they will be converted
to the new format transparently.

VLANs
#####

You can now add VLAN tags to interfaces from Cobbler. In this case we have two VLANs on eth0: 10 and 20. The default
VLAN (untagged traffic) is not used:

{% highlight bash %}
$ cobbler system edit --name=foo3.bar.local --interface=eth0 --mac=AA:BB:CC:DD:EE:F0 --static=1
$ cobbler system edit --name=foo3.bar.local --interface=eth0.10 --static=1 --ip-address=10.0.10.5 --subnet=255.255.255.0
$ cobbler system edit --name=foo3.bar.local --interface=eth0.20 --static=1 --ip-address=10.0.20.5 --subnet=255.255.255.0
{% endhighlight %}

**NOTE** You must install the vconfig package during the build process for this to work in the %post section of your
build.

Bridging
########

A bridge is a way to connect two Ethernet segments together in a protocol independent way. Packets are forwarded based
on Ethernet address, rather than IP address (like a router). Since forwarding is done at Layer 2, all protocols can go
transparently through a bridge. ([reference](http://www.linuxfoundation.org/collaborate/workgroups/networking/bridge)).

You can create a bridge in cobbler in the following way:

{% highlight bash %}
$ cobbler system edit --name=foo --interface=eth0 --mac=AA:BB:CC:DD:EE:F0 --interface-type=bridge_slave --interface-master=br0
$ cobbler system edit --name=foo --interface=eth1 --mac=AA:BB:CC:DD:EE:F1 --interface-type=bridge_slave --interface-master=br0
$ cobbler system edit --name=foo --interface=br0 --interface-type=bridge --bridge-opts="stp=no" --ip-address=192.168.1.100 --netmask=255.255.255.0
{% endhighlight %}

You can specify any bridging options you would like, so please read the brctl manpage for details if you are unfamiliar
with bridging.

**NOTE** You must install the bridge-utils package during the build process for this to work in the %post section of
your build.

Bonded Bridging
###############

Some situations, such as virtualization hosts, require more redundancy in their bridging setups. In this case, 2.8.0
introduced a new interface type - the bonded_bridge_slave. This is an interface that is a bond master to one or more
physical interfaces, and is itself a bridged slave interface.

You can create a bonded_bridge_slave in cobbler in the following way:

{% highlight bash %}
$ cobbler system edit --name=foo --interface=eth0 --mac=AA:BB:CC:DD:EE:F0 \
                      --interface-type=bond_slave --interface-master=bond0
$ cobbler system edit --name=foo --interface=eth1 --mac=AA:BB:CC:DD:EE:F1 \
                      --interface-type=bond_slave --interface-master=bond0
$ cobbler system edit --name=foo --interface=bond0 --interface-type=bonded_bridge_slave \
                      --bonding-opts="miimon=100 mode=1" --interface-master=br0
$ cobbler system edit --name=foo --interface=br0 --interface-type=bridge \
                      --bridge-opts="stp=no" --ip-address=192.168.1.100 \
                      --netmask=255.255.255.0 --static=1
{% endhighlight %}

**NOTE** Please reference the [Advanced Networking - Bonding]({% link manuals/2.8.0/4/1/1_-_Bonding.md %}) and
[Advanced Networking - Bridging]({% link manuals/2.8.0/4/1/3_-_Bridging.md %}) sections for requirements specific to
each of these interface types.
