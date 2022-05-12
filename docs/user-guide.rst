***********************************
User Guide
***********************************

.. toctree::
   :maxdepth: 2

   Configuration Management Integrations <user-guide/configuration-management-integrations>
   Automatic Windows installation with Cobbler <user-guide/wingen>
   Extending Cobbler <user-guide/extending-cobbler>
   Terraform Provider for Cobbler <user-guide/terraform-provider>
   Building ISOs <user-guide/building-isos>
   GRUB and everything related <user-guide/grub>
   Repository Management <user-guide/repository-management>
   The TFTP Directory <user-guide/tftp>
   Internal Database <user-guide/internal-database>
   HTTP API <user-guide/http-api>


API
###
Cobbler also makes itself available as an XML-RPC API for use by higher level management software. Learn more at
https://cobbler.github.io

Triggers
########

Triggers provide a way to integrate Cobbler with arbitrary 3rd party software without modifying Cobbler's code. When
adding a distro, profile, system, or repo, all scripts in ``/var/lib/cobbler/triggers/add`` are executed for the
particular object type. Each particular file must be executable and it is executed with the name of the item being added
as a parameter. Deletions work similarly -- delete triggers live in ``/var/lib/cobbler/triggers/delete``. Order of
execution is arbitrary, and Cobbler does not ship with any triggers by default. There are also other kinds of triggers
-- these are described on the Cobbler Wiki. For larger configurations, triggers should be written in Python -- in which
case they are installed differently. This is also documented on the Wiki.

Images
######

Cobbler can help with booting images physically and virtually, though the usage of these commands varies substantially
by the type of image. Non-image based deployments are generally easier to work with and lead to more sustainable
infrastructure. Some manual use of other commands beyond of what is typically required of Cobbler may be needed to
prepare images for use with this feature.

.. _power-management:

Power Management
################

Cobbler contains a power management feature that allows the user to associate system records in Cobbler with the power
management configuration attached to them. This can ease installation by making it easy to reassign systems to new
operating systems and then reboot those systems.

Non-import (manual) workflow
############################

The following example uses a local kernel and initrd file (already downloaded), and shows how profiles would be created
using two different automatic installation files -- one for a web server configuration and one for a database server.
Then, a machine is assigned to each profile.

.. code-block:: shell

    cobbler check
    cobbler distro add --name=rhel4u3 --kernel=/dir1/vmlinuz --initrd=/dir1/initrd.img
    cobbler distro add --name=fc5 --kernel=/dir2/vmlinuz --initrd=/dir2/initrd.img
    cobbler profile add --name=fc5webservers --distro=fc5-i386 --autoinstall=/dir4/kick.ks --kernel-options="something_to_make_my_gfx_card_work=42 some_other_parameter=foo"
    cobbler profile add --name=rhel4u3dbservers --distro=rhel4u3 --autoinstall=/dir5/kick.ks
    cobbler system add --name=AA:BB:CC:DD:EE:FF --profile=fc5-webservers
    cobbler system add --name=AA:BB:CC:DD:EE:FE --profile=rhel4u3-dbservers
    cobbler report

Virtualization
##############

For Virt, be sure the distro uses the correct kernel (if paravirt) and follow similar steps as above, adding additional
parameters as desired:

.. code-block:: shell

    cobbler distro add --name=fc7virt [options...]

Specify reasonable values for the Virt image size (in GB) and RAM requirements (in MB):

.. code-block:: shell

    cobbler profile add --name=virtwebservers --distro=fc7virt --autoinstall=path --virt-file-size=10 --virt-ram=512 [...]

Define systems if desired. Koan can also provision based on the profile name.

.. code-block:: shell

    cobbler system add --name=AA:BB:CC:DD:EE:FE --profile=virtwebservers [...]

If you have just installed Cobbler, be sure that the `cobblerd` service is running and that port 25151 is unblocked.

See the manpage for Koan for the client side steps.

Autoinstallation
################

Automatic installation templating
=================================

The ``--autoinstall_meta`` options above require more explanation.

If and only if ``--autoinstall`` options reference filesystem URLs, ``--autoinstall-meta`` allows for templating of the automatic
installation files to achieve advanced functions.  If the ``--autoinstall-meta`` option for a profile read
``--autoinstall-meta="foo=7 bar=llama"``, anywhere in the automatic installation file where the string ``$bar`` appeared would be
replaced with the string "llama".

To apply these changes, ``cobbler sync`` must be run to generate custom automatic installation files for each
profile/system.

For NFS and HTTP automatic installation file URLs, the ``--autoinstall_meta`` options will have no effect. This is a
good reason to let Cobbler manage your automatic installation files, though the URL functionality is provided for
integration with legacy infrastructure, possibly including web apps that already generate automatic installation files.

Templated automatic files are processed by the templating program/package Cheetah, so anything you can do in a Cheetah
template can be done to an automatic installation template.  Learn more at https://cheetahtemplate.org/users_guide/intro.html

When working with Cheetah, be sure to escape any shell macros that look like ``$(this)`` with something like
``\$(this)`` or errors may show up during the sync process.

The Cobbler Wiki also contains numerous Cheetah examples that should prove useful in using this feature.

Also useful is the following repository: https://github.com/FlossWare/cobbler

Automatic installation snippets
===============================

Anywhere a automatic installation template mentions ``SNIPPET::snippet_name``, the file named
``/var/lib/cobbler/snippets/snippet_name`` (if present) will be included automatically in the automatic installation
template. This serves as a way to recycle frequently used automatic installation snippets without duplication. Snippets
can contain templating variables, and the variables will be evaluated according to the profile and/or system as one
would expect.

Snippets can also be overridden for specific profile names or system names. This is described on the Cobbler Wiki.

Kickstart validation
====================

To check for potential errors in kickstarts, prior to installation, use ``cobbler validateks``. This function will check
all profile and system kickstarts for detectable errors. Since pykickstart is not future-Anaconda-version aware, there
may be some false positives. It should be noted that ``cobbler validateks`` runs on the rendered kickstart output, not
kickstart templates themselves.

Network Topics
##############

.. Z-PXE: https://github.com/beaker-project/zpxe

PXE Menus
=========

Cobbler will automatically generate PXE menus for all profiles it has defined. Running ``cobbler sync`` is required to
generate and update these menus.

To access the menus, type ``menu`` at the ``boot:`` prompt while a system is PXE booting. If nothing is typed, the
network boot will default to a local boot. If "menu" is typed, the user can then choose and provision any Cobbler
profile the system knows about.

If the association between a system (MAC address) and a profile is already known, it may be more useful to just use
``system add`` commands and declare that relationship in Cobbler; however many use cases will prefer having a PXE
system, especially when provisioning is done at the same time as installing new physical machines.

If this behavior is not desired, run ``cobbler system add --name=default --profile=plugh`` to default all PXE booting
machines to get a new copy of the profile ``plugh``. To go back to the menu system, run
``cobbler system remove --name=default`` and then ``cobbler sync`` to regenerate the menus.

When using PXE menu deployment exclusively, it is not necessary to make Cobbler system records, although the two can
easily be mixed.

Additionally, note that all files generated for the PXE menu configurations are templatable, so if you wish to change
the color scheme or equivalent, see the files in ``/etc/cobbler``.

Default PXE Boot behavior
=========================

What happens when PXE booting a system when Cobbler has no record of the system being booted?

By default, Cobbler will configure PXE to boot to the contents of ``/etc/cobbler/default.pxe``, which (if unmodified)
will just fall through to the local boot process. Administrators can modify this file if they like to change that
behavior.

An easy way to specify a default Cobbler profile to PXE boot is to create a system named ``default``. This will cause
``/etc/cobbler/default.pxe`` to be ignored. To restore the previous behavior do a ``cobbler system remove`` on the
``default`` system.

.. code-block:: shell

    cobbler system add --name=default --profile=boot_this
    cobbler system remove --name=default

As mentioned in earlier sections, it is also possible to control the default behavior for a specific network:

.. code-block:: shell

    cobbler system add --name=network1 --ip-address=192.168.0.0/24 --profile=boot_this

PXE boot loop prevention
========================

If you have your machines set to PXE first in the boot order (ahead of hard drives), change the ``pxe_just_once`` flag
in ``/etc/cobbler/settings.yaml`` to 1. This will set the machines to not PXE on successive boots once they complete one
install. To re-enable PXE for a specific system, run the following command:

.. code-block:: shell

    cobbler system edit --name=name --netboot-enabled=1

Automatic installation tracking
===============================

Cobbler knows how to keep track of the status of automatic installation of machines.

.. code-block:: shell

    cobbler status

Using the status command will show when Cobbler thinks a machine started automatic installation and when it finished,
provided the proper snippets are found in the automatic installation template. This is a good way to track machines that
may have gone interactive (or stalled/crashed) during automatic installation.

Boot CD
#######

Cobbler can build all of it's profiles into a bootable CD image using the ``cobbler buildiso`` command. This allows for
PXE-menu like bring up of bare metal in environments where PXE is not possible. Another more advanced method is described
in the Koan manpage, though this method is easier and sufficient for most applications.

.. _dhcp-management:

DHCP Management
===============

Cobbler can optionally help you manage DHCP server. This feature is off by default.

Choose either ``management = isc_and_bind`` in ``/etc/cobbler/dhcp.template`` or ``management = "dnsmasq"`` in
``/etc/cobbler/modules.conf``.  Then set ``manage_dhcp=1`` in ``/etc/cobbler/settings.yaml``.

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

Containerization
################

We have a test-image which you can find in the Cobbler repository and an old image made by the community:
https://github.com/osism/docker-cobbler


Web-Interface
#############

Please be patient until we have time with the 4.0.0 release to create a new web UI. The old Django based was preventing
needed change inside the internals in Cobbler.
