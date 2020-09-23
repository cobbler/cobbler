***********************************
User Guide
***********************************

.. toctree::
   :maxdepth: 2

   Web User Interface <user-guide/web-interface>
   Configuration Management Integrations <user-guide/configuration-management-integrations>


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

.. code-block:: none

    cobbler check
    cobbler distro add --name=rhel4u3 --kernel=/dir1/vmlinuz --initrd=/dir1/initrd.img
    cobbler distro add --name=fc5 --kernel=/dir2/vmlinuz --initrd=/dir2/initrd.img
    cobbler profile add --name=fc5webservers --distro=fc5-i386 --autoinst=/dir4/kick.ks --kopts="something_to_make_my_gfx_card_work=42 some_other_parameter=foo"
    cobbler profile add --name=rhel4u3dbservers --distro=rhel4u3 --autoinst=/dir5/kick.ks
    cobbler system add --name=AA:BB:CC:DD:EE:FF --profile=fc5-webservers
    cobbler system add --name=AA:BB:CC:DD:EE:FE --profile=rhel4u3-dbservers
    cobbler report

Repository Management
#####################

REPO MANAGEMENT
===============

This has already been covered a good bit in the command reference section.

Yum repository management is an optional feature, and is not required to provision through Cobbler. However, if Cobbler
is configured to mirror certain repositories, it can then be used to associate profiles with those repositories. Systems
installed under those profiles will then be autoconfigured to use these repository mirrors in ``/etc/yum.repos.d``, and
if supported (Fedora Core 6 and later) these repositories can be leveraged even within Anaconda.  This can be useful if
(A) you have a large install base, (B) you want fast installation and upgrades for your systems, or (C) have some extra
software not in a standard repository but want provisioned systems to know about that repository.

Make sure there is plenty of space in Cobbler's webdir, which defaults to ``/var/www/cobbler``.

.. code-block:: none

    cobbler reposync [--only=ONLY] [--tries=N] [--no-fail]

Cobbler reposync is the command to use to update repos as configured with "cobbler repo add".  Mirroring
can take a long time, and usage of Cobbler reposync prior to usage is needed to ensure provisioned systems have the
files they need to actually use the mirrored repositories.  If you just add repos and never run "cobbler reposync", the
repos will never be mirrored.  This is probably a command you would want to put on a crontab, though the frequency of
that crontab and where the output goes is left up to the systems administrator.

For those familiar with dnf's reposync, Cobbler's reposync is (in most uses) a wrapper around the dnf reposync command.  Please
use "cobbler reposync" to update Cobbler mirrors, as dnf's reposync does not perform all required steps. Also Cobbler
adds support for rsync and SSH locations, where as dnf's reposync only supports what yum supports (http/ftp).

If you ever want to update a certain repository you can run:

.. code-block:: none

    cobbler reposync --only="reponame1" ...

When updating repos by name, a repo will be updated even if it is set to be not updated during a regular reposync
operation (ex: cobbler repo edit --name=reponame1 --keep-updated=0).

Note that if a Cobbler import provides enough information to use the boot server as a yum mirror for core packages,
Cobbler can set up automatic installation files to use the Cobbler server as a mirror instead of the outside world. If
this feature is desirable, it can be turned on by setting yum_post_install_mirror to 1 in /etc/settings (and running
"cobbler sync").  You should not use this feature if machines are provisioned on a different VLAN/network than
production, or if you are provisioning laptops that will want to acquire updates on multiple networks.

The flags ``--tries=N`` (for example, ``--tries=3``) and ``--no-fail`` should likely be used when putting reposync on a
crontab. They ensure network glitches in one repo can be retried and also that a failure to synchronize one repo does
not stop other repositories from being synchronized.

Importing trees
===============

Cobbler can auto-add distributions and profiles from remote sources, whether this is a filesystem path or an rsync
mirror. This can save a lot of time when setting up a new provisioning environment. Import is a feature that many users
will want to take advantage of, and is very simple to use.

After an import is run, Cobbler will try to detect the distribution type and automatically assign automatic installation
files. By default, it will provision the system by erasing the hard drive, setting up eth0 for DHCP, and using a default
password of "cobbler".  If this is undesirable, edit the automatic installation files in ``/etc/cobbler`` to do
something else or change the automatic installation setting after Cobbler creates the profile.

Mirrored content is saved automatically in ``/var/www/cobbler/distro_mirror``.

Example 1: ``cobbler import --path=rsync://mirrorserver.example.com/path/ --name=fedora --arch=x86``

Example 2: ``cobbler import --path=root@192.168.1.10:/stuff --name=bar``

Example 3: ``cobbler import --path=/mnt/dvd --name=baz --arch=x86_64``

Example 4: ``cobbler import --path=/path/to/stuff --name=glorp``

Example 5: ``cobbler import --path=/path/where/filer/is/mounted --name=anyname --available-as=nfs://nfs.example.org:/where/mounted/``

Once imported, run a ``cobbler list`` or ``cobbler report`` to see what you've added.

By default, the rsync operations will exclude content of certain architectures, debug RPMs, and ISO images -- to change
what is excluded during an import, see ``/etc/cobbler/rsync.exclude``.

Note that all of the import commands will mirror install tree content into ``/var/www/cobbler`` unless a network
accessible location is given with ``--available-as``.  --available-as will be primarily used when importing distros
stored on an external NAS box, or potentially on another partition on the same machine that is already accessible via
``http://`` or ``ftp://``.

For import methods using rsync, additional flags can be passed to rsync with the option ``--rsync-flags``.

Should you want to force the usage of a specific Cobbler automatic installation template for all profiles created by an
import, you can feed the option ``--autoinst`` to import, to bypass the built-in automatic installation file
auto-detection.

Repository mirroring workflow
=============================

The following example shows how to set up a repo mirror for all enabled Cobbler host repositories and two additional repositories,
and create a profile that will auto install those repository configurations on provisioned systems using that profile.

.. code-block:: none

    cobbler check
    # set up your cobbler distros here.
    cobbler autoadd
    cobbler repo add --mirror=http://mirrors.kernel.org/fedora/core/updates/6/i386/ --name=fc6i386updates
    cobbler repo add --mirror=http://mirrors.kernel.org/fedora/extras/6/i386/ --name=fc6i386extras
    cobbler reposync
    cobbler profile add --name=p1 --distro=existing_distro_name --autoinst=/etc/cobbler/kickstart_fc6.ks --repos="fc6i386updates fc6i386extras"

Import Workflow
===============

Import is a very useful command that makes starting out with Cobbler very quick and easy.

This example shows how to create a provisioning infrastructure from a distribution mirror or DVD ISO. Then a default PXE
configuration is created, so that by default systems will PXE boot into a fully automated install process for that
distribution.

You can use a network rsync mirror, a mounted DVD location, or a tree you have available via a network filesystem.

Import knows how to autodetect the architecture of what is being imported, though to make sure things are named
correctly, it's always a good idea to specify ``--arch``. For instance, if you import a distribution named "fedora8"
from an ISO, and it's an x86_64 ISO, specify ``--arch=x86_64`` and the distro will be named "fedora8-x86_64"
automatically, and the right architecture field will also be set on the distribution object. If you are batch importing
an entire mirror (containing multiple distributions and arches), you don't have to do this, as Cobbler will set the
names for things based on the paths it finds.

.. code-block:: none

    cobbler check
    cobbler import --path=rsync://yourfavoritemirror.com/rhel/5/os/x86_64 --name=rhel5 --arch=x86_64
    # OR
    cobbler import --path=/mnt/dvd --name=rhel5 --arch=x86_64
    # OR (using an external NAS box without mirroring)
    cobbler import --path=/path/where/filer/is/mounted --name=anyname --available-as=nfs://nfs.example.org:/where/mounted/
    # wait for mirror to rsync...
    cobbler report
    cobbler system add --name=default --profile=name_of_a_profile1
    cobbler system add --name=AA:BB:CC:DD:EE:FF --profile=name_of_a_profile2
    cobbler sync

Virtualization
##############

For Virt, be sure the distro uses the correct kernel (if paravirt) and follow similar steps as above, adding additional
parameters as desired:

.. code-block:: none

    cobbler distro add --name=fc7virt [options...]

Specify reasonable values for the Virt image size (in GB) and RAM requirements (in MB):

.. code-block:: none

    cobbler profile add --name=virtwebservers --distro=fc7virt --autoinst=path --virt-file-size=10 --virt-ram=512 [...]

Define systems if desired. Koan can also provision based on the profile name.

.. code-block:: none

    cobbler system add --name=AA:BB:CC:DD:EE:FE --profile=virtwebservers [...]

If you have just installed Cobbler, be sure that the `cobblerd` service is running and that port 25151 is unblocked.

See the manpage for Koan for the client side steps.

Autoinstallation
################

Automatic installation templating
=================================

The ``--autoinstall_meta`` options above require more explanation.

If and only if ``--autoinst`` options reference filesystem URLs, ``--ksmeta`` allows for templating of the automatic
installation files to achieve advanced functions.  If the ``--ksmeta`` option for a profile read
``--ksmeta="foo=7 bar=llama"``, anywhere in the automatic installation file where the string ``$bar`` appeared would be
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

.. code-block:: none

    cobbler system add --name=default --profile=boot_this
    cobbler system remove --name=default

As mentioned in earlier sections, it is also possible to control the default behavior for a specific network:

.. code-block:: none

    cobbler system add --name=network1 --ip-address=192.168.0.0/24 --profile=boot_this

PXE boot loop prevention
========================

If you have your machines set to PXE first in the boot order (ahead of hard drives), change the ``pxe_just_once`` flag
in ``/etc/cobbler/settings`` to 1. This will set the machines to not PXE on successive boots once they complete one
install. To re-enable PXE for a specific system, run the following command:

.. code-block:: none

    cobbler system edit --name=name --netboot-enabled=1

Automatic installation tracking
===============================

Cobbler knows how to keep track of the status of automatic installation of machines.

.. code-block:: none

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
``/etc/cobbler/modules.conf``.  Then set ``manage_dhcp=1`` in ``/etc/cobbler/settings``.

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

If omapi_enabled is set to 1 in ``/etc/cobbler/settings``, the need to sync when adding new system records can be
eliminated. However, the OMAPI feature is experimental and is not recommended for most users.

.. _dns-management:

DNS configuration management
============================

Cobbler can optionally manage DNS configuration using BIND and dnsmasq.

Choose either ``management = isc_and_bind`` or ``management = dnsmasq`` in ``/etc/cobbler/modules.conf`` and then enable
``manage_dns`` in ``/etc/cobbler/settings``.

This feature is off by default. If using BIND, you must define the zones to be managed with the options
``manage_forward_zones`` and ``manage_reverse_zones``.  (See the Wiki for more information on this).

If using BIND, Cobbler will use ``/etc/cobbler/named.template`` and ``/etc/cobbler/zone.template`` as a starting point
for the ``named.conf`` and individual zone files, respectively. You may drop zone-specific template files in
``/etc/cobbler/zone_templates/name-of-zone`` which will override the default. These files must be user edited for the
user's particular networking environment.  Read the file and understand how BIND works before proceeding.

If using dnsmasq, the template is ``/etc/cobbler/dnsmasq.template``. Read this file and understand how dnsmasq works
before proceeding.

All managed files (whether zone files and ``named.conf`` for BIND, or ``dnsmasq.conf`` for dnsmasq) will be updated each
time ``cobbler sync`` is run, and not until then, so it is important to remember to use ``cobbler sync`` when using this
feature.

Containerization
################

We have a test-image which you can find in the Cobbler repository and an old image made by the community:
https://github.com/osism/docker-cobbler
