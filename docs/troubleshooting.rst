.. _troubleshooting:

*******************************************
Frequently Asked Trouble Shooting Questions
*******************************************

This section covers some questions that frequently come up in IRC, some of which are problems, and some of which are
things about Cobbler that are not really problems, but are things folks just ask questions about frequently...

See also :ref:`virtualization-troubleshooting` for virtualization specific questions.

General
#######

Most Common Things To Check
===========================

Have you run Cobbler check? What did it say? Is Cobbler and koan at the most recent released stable version? Is
cobblerd running? Have you tried restarting it if this is a recent upgrade or config change? If something isn't showing
up, have you restarted cobblerd and run ``cobbler sync`` after making changes to the config file? If you can't connect
or retrieve certain files, is Apache running, or have you restarted it after a new install? If there's a koan
connectivity problem, are there any firewalls blocking port ``25150``?

I am having a problem with importing repos
==========================================

Trick question! one does not run ``cobbler import`` on repos :) Install trees contain more data than repositories.
Install trees are for OS installation and are added using ``cobbler import`` or ``cobbler distro add`` if you want do
something more low level. Repositories are for things like updates and additional packages. Use ``cobbler repo add`` to
add these sources. If you accidentally import a repo URL (for instance using rsync), clean up
``/var/www/cobbler/ks_mirror/name_you_used`` to take care of it. Cobbler can't detect what you are importing in advance
before you copy it. Thankfully ``man cobbler`` gives plenty of good examples for each command, ``cobbler import`` and
``cobbler repo add`` and gives example URLs and syntaxes for both.

See also [Using Cobbler Import](Using Cobbler Import) and [Manage Yum Repos](Manage Yum Repos) for further information.

Why do the kickstart files in /etc/cobbler look strange?
========================================================

These are not actually kickstart files, they are kickstart file templates. See :ref:`kickstart-templating` for more
information.

How can I validate that my kickstarts are right before installing?
==================================================================

Try ``cobbler validateks``.

Can I feed normal kickstart files to --kickstart ?
==================================================

You can, but you need to escape any dollar signs (``$``) with (``\\$``) so the Cobbler templating engine doesn't eat
them. This is not too hard, use ``cobbler profile getks`` and ``cobbler system getks`` to make sure everything renders
correctly. Also ``\#raw ... \#endraw`` in Cheetah can be useful. More is documented on the :ref:`kickstart-templating`
page.

My kickstart file has problems
==============================

If it's not related to Cobbler's :ref:`kickstart-templating` engine, and it's more of "how do I do this
in pre/post", ``kickstart-list`` is excellent.

`Redhat Mailman/Kickstart-List  <https://www.redhat.com/mailman/listinfo/kickstart-list>`_

Otherwise, you are likely seeing a Cheetah syntax error. Learn more about Cheetah syntax at
`Cheetahtemplate/User Guide/Language <https://cheetahtemplate.org/users_guide/language.html>`_ for further information.

I'm running into the 255 character kernel options line limit
============================================================

This can be a problem. Adding a CNAME for your cobbler server that is accessible everywhere, such as "cobbler", or even
"boot" can save a lot of characters over hostname.xyz.acme-corp.internal.org. It will show up twice in the kernel
options line, once for the kickstart URL, and once for the kickstart URL. Save characters by not using FQDNs when
possible. The IP may also be shorter in some cases. Cobbler should try to remove optional kernel args in the event of
overflow (like syslog) but you still need to be careful.

(Newer kernels are supposed to not have this limit)

I'm getting PXE timeouts and my cobbler server is also a virtualized host and I'm using dnsmasq for DHCP
========================================================================================================

Libvirtd starts an instance of dnsmasq unrelated to the DHCP needed for cobbler to PXE -- it's just there for local
networking but can cause conflicts. If you want PXE to work, do not run libvirtd on the cobbler server, or use ISC dhcpd
instead. You can of course run libvirtd on any other guests in your management network, and if you don't need PXE
support, running libvirtd on the cobbler server is also fine.

Alternatively you can configure your DHCP server not to listen on all interfaces: dnsmasq run by libvirtd is configured
to listen on internal virbr0/192.168.122.1 only. For ISC dhcpd you can set in /etc/sysconfig/dhcpd:

.. code-block:: bash

    DHCPDARGS=eth0

For dnsmasq you can set in ``/etc/dnsmasq.conf``:

.. code-block:: bash

    interface=eth0
    except-interface=lo
    bind-interfaces

I'm having DHCP timeouts / DHCP is slow / etc
=============================================

See the Anaconda network troubleshooting page:
`Fedoraproject/Anaconda/Networkissues <https://fedoraproject.org/wiki/Anaconda/NetworkIssues>`_

This URL has "Fedora" in it, but applies equally to Red Hat and derivative distributions.

Cobblerd won't start
====================

cobblerd won't start and say:

.. code-block:: bash

    > Starting cobbler daemon: Traceback (most recent call last):
    >   File "/usr/bin/cobblerd", line 76, in main
    >     api = cobbler_api.BootAPI(is_cobblerd=True)
    >   File "/usr/lib/python2.6/site-packages/cobbler/api.py", line 127, in __init__
    >     module_loader.load_modules()
    >   File "/usr/lib/python2.6/site-packages/cobbler/module_loader.py", line 62, in load_modules
    >     blip =  __import__("modules.%s" % ( modname), globals(), locals(), [modname])
    >   File "/usr/lib/python2.6/site-packages/cobbler/modules/authn_pam.py", line 53, in <module>
    >     from ctypes import CDLL, POINTER, Structure, CFUNCTYPE, cast, pointer, sizeof
    >   File "/usr/lib64/python2.6/ctypes/__init__.py", line 546, in <module>
    >     CFUNCTYPE(c_int)(lambda: None)
    > MemoryError
    >                                                            [  OK  ]

Check your SELinux. Immediate fix is to disable selinux:

.. code-block:: bash

    setenforce 0

Debugging Cobbler Web
#####################

Most of the action in cobbler happens inside cobblerd, and the web server actually talks to it over XMLRPC.

Using epdb is probably the easiest way to debug things remotely.

Hints and tips: Redhat
######################

A collection of tips for using Cobbler to deploy and support Redhat-based machines, including CentOS, Fedora,
Scientific Linux, etc.

Rescue Mode
===========

Redhat-based systems offer a "rescue" mode, typically used for trying to analyse and recover after a major OS problem.
The usual way of doing this is booting from a DVD and selecting "rescue" mode at the relevant point. But it is also
possible to do this via Cobbler. Indeed, if the machine lacks a DVD drive, alternatives such as this are vital for
attempted rescue operations.

**RISK:**  _Because you are using this Cobbler deployment system that usually installs machines, there is the risk that
this procedure could overwrite the very machine you are attempting to rescue. So it is strongly recommended that, as
part of your normal workflow, you develop and periodically verify this procedure in a safe, non-production,
non-emergency environment._

The example below illustrates RHEL 5.6.  The detail may vary for other Redhat-like flavours.

Assumptions
***********

* Your target machine's Cobbler network deployment is supported by exactly one active DHCP server.
* Your deployed machines are already present in Cobbler for their earlier deployment purposes.
* A deployed machine's ``kopts`` setting field is usually null.
* A deployed machine's ``netboot-enabled`` setting is false outside deployment time.

Procedure
*********

As stated above: _verify this periodically, outside emergency times, in a non-production environment._

On the Cobbler server:

.. code-block:: bash

    cobbler system edit --name=sick-machine --kopts='rescue'
    cobbler system edit --name=sick-machine --netboot-enabled=true
    cobbler sync

As always, don't forget that ``cobbler sync``.

At the client "sick-machine", start a normal deployment-style network boot.  During this you should eventually see:

* Usual blue screen: ``Loading SCSI driver``.  There may be a couple of similar screens.
* Usual blue screen: ``Sending request for IP information for eth0...``.  (The exact value of that "eth0" is dependent
  on your machine.)
* Usual blue screen: repeat ``Sending request for IP...`` , but this time the header bar at the top should have
  ``Rescue Mode`` appended.
* Usual back-to-black: ``running anaconda`` and a couple of related lines.
* Blue screen with header bar ``Rescue`` and options "Continue", "Read-Only", "Skip".

In particular, if the second ``Sending request for IP...`` screen fails to say ``Rescue Mode``, it is strongly
recommended that you immediately abort the process to avoid the risk of overwriting the machine.

At this point you select whichever option is appropriate for your rescue and follow the Redhat rescue procedures.
(The detail is independent of, and beyond the scope of, this Cobbler procedure.)

When you have finished, on the Cobbler server nullify the rescue:

.. code-block:: bash

    cobbler system edit --name=sick-machine --kopts=''
    cobbler system edit --name=sick-machine --netboot-enabled=false
    cobbler sync

.. _virtualization-troubleshooting:

Frequently Asked Virtualization Trouble Shooting Questions
##########################################################

This section covers some questions that frequently come up in IRC, some of which are problems, and some of which are
things about Cobbler that are not really problems, but are things folks just ask questions about frequently... All
related to virtualization.

See also :ref:`troubleshooting` for general items.

Why don't I see this Xen distribution in my PXE menu?
=====================================================

There are two types of installer kernel/initrd pairs. There's a normal one (for all physical installations) and a Xen
paravirt one. If you ``cobbler import`` an install tree (say from a DVD image) and get some "xen" distributions, these
distributions will then not show up in your PXE menu -- just because Cobbler knows it's impossible to PXE boot them on
physical hardware.

If you want to install virtual guests, read ``man koan`` for details and also
https://koan.readthedocs.io/en/release28/installing-virtual-guests.html

If you want to install a physical host, use the standard distribution, the one without "xen" in the name. Instead, in
the ``%packages`` section of the kickstart, add the package named ``kernel-xen``.

This only applies for Xen, of course, if you are using KVM, it's simpler and there is only one installer kernel/initrd
pair to worry about -- the main one.

In recent versions of Fedora, the Xen kernels have merged again, so this is not a problem.

I'm having problems using Koan to install virtual guests
========================================================

If you use virt-type xenpv, make sure the profile you are installing uses a distro with "xen" in the name. These are the
paravirtualized versions of the installer kernel/initrd pair.

Make sure your host arch matches your guest arch.

If installing Xen and using virsh console or xm console, if you don't use ``--nogfx`` at one point the installer will
appear to hang. Most likely it did not, it switched over to using VNC which you can view with virt-manager. If you would
like to keep using the text console, use ``--nogfx`` instead. This does not apply to other virt types, only Xen.

There really aren't any KVM gotchas, other than making sure ``/dev/kvm`` is present (you need the right kernel module
installed on the host) otherwise things will install with qemu and appear to be very slow.

See also https://koan.readthedocs.io/en/release28/installing-virtual-guests.html

What Is This Strange Message From Xen?
======================================

.. code-block:: bash

    libvir: Xen error : Domain not found: xenUnifiedDomainLookupByUUID
    libvir: Xen error : Domain not found: xenUnifiedDomainLookupByName

If you see the above, it's not an error. These strange messages are perfectly normal and are coming from Xen as it's
looking for an existing domain. It does not come from Cobbler/koan and your installation will not be affected. We agree
they are confusing but they are not coming from Cobbler or Koan.

VirtualBox version 4+ won't PXE boot, DHCP logs show up nothing
===============================================================

If you setup cobbler all correctly and you are trying to network book with PXE and you receive this error right after
the VirtualBox POST:

.. code-block:: bash

    FATAL: No bootable medium found! System halted.

Be sure to install to install the VirtualBox Extensions Pack to enable PXE boot support.
