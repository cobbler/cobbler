********
Advanced
********

This section of the manual covers the more advanced use cases for Cobbler, including methods for customizing and
extending cobbler without needing to write code.

PXE behaviour and tailoring
###########################

Menus
=====

Cobbler will automatically generate PXE menus for all profiles it has defined. Running ``cobbler sync`` is required to
generate and update these menus.

To access the menus, type "menu" at the "boot:" prompt while a system is PXE booting.  If nothing is typed, the network
boot will default to a local boot.  If "menu" is typed, the user can then choose and provision any cobbler profile the
system knows about.

If the association between a system (MAC address) and a profile is already known, it may be more useful to just use
"system add" commands and declare that relationship in cobbler; however many use cases will prefer having a PXE system,
especially when provisioning is done at the same time as installing new physical machines.

If this behavior is not desired, run ``cobbler system add --name=default --profile=plugh`` to default all PXE booting
machines to get a new copy of the profile "plugh". To go back to the menu system, run
``cobbler system remove --name=default`` and then "cobbler sync" to regenerate the menus.

When using PXE menu deployment exclusively, it is not neccessary to make cobbler system records, although the two can
easily be mixed.

Additionally, note that all files generated for the pxe menu configurations are templatable, so if you wish to change
the color scheme or equivalent, see the files in ``/etc/cobbler``.

Default boot behavior
=====================

If cobbler has no record of the system being booted, cobbler will configure PXE to boot to the contents of
`/etc/cobbler/default.pxe` which, if unmodified, will just fall through to the local boot process.

The recommended way to specify a different default cobbler profile to PXE boot is to create an explicit system named
"default".  This will cause `/etc/cobbler/default.pxe` to be ignored.

.. code-block:: bash

    cobbler system add --name=default --profile=boot_this

To restore the previous behavior remove that explicit "default" system:

.. code-block:: bash

    cobbler system remove --name=default

It is also possible to control the default behavior for a specific network:

.. code-block:: bash

    cobbler system add --name=network1 --ip-address=192.168.0.0/24 --profile=boot_this

Preventing boot loops
=====================

If your machines are set to PXE first in the boot order (ahead of hard drives), change the ``pxe_just_once`` flag in
``/etc/cobbler/settings`` to 1.  This will set the machines _not_ to PXE-boot on successive boots once they complete one
install. To re-enable PXE for a specific system, run the following command:

.. code-block:: bash

    cobbler system edit --name=name --netboot-enabled=1

Service Discovery (Avahi)
*************************

If the ``avahi-tools`` package is installed, ``cobblerd`` will broadcast it's presence on the network, allowing it to be
discovered by koan with the ``koan --server=DISCOVER`` parameter.

Repo Management
***************

This has already been covered a good bit in the command reference section.

Yum repository management is an optional feature, and is not required to provision through cobbler. However, if cobbler
is configured to mirror certain repositories, it can then be used to associate profiles with those repositories. Systems
installed under those profiles will then be autoconfigured to use these repository mirrors in ``/etc/yum.repos.d``, and
if supported (Fedora Core 6 and later) these repositories can be leveraged even within Anaconda. This can be useful if
(A) you have a large install base, (B) you want fast installation and upgrades for your systems, or (C) have some extra
software not in a standard repository but want provisioned systems to know about that repository.

Make sure there is plenty of space in cobbler's webdir, which defaults to ``/var/www/cobbler``.

.. code-block:: bash

    cobbler reposync [--tries=N] [--no-fail]

Cobbler reposync is the command to use to update repos as configured with ``cobbler repo add``. Mirroring can take a
long time, and usage of cobbler reposync prior to usage is needed to ensure provisioned systems have the files they need
to actually use the mirrored repositories. If you just add repos and never run ``cobbler reposync``, the repos will
never be mirrored. This is probably a command you would want to put on a crontab, though the frequency of that crontab
and where the output goes is left up to the systems administrator.

For those familiar with yum's reposync, cobbler's reposync is (in most uses) a wrapper around the yum command. Please
use ``cobbler reposync`` to update cobbler mirrors, as yum's reposync does not perform all required steps. Also cobbler
adds support for rsync and SSH locations, where as yum's reposync only supports what yum supports (http/ftp).

If you ever want to update a certain repository you can run:

.. code-block:: bash

    cobbler reposync --only="reponame1" ...

When updating repos by name, a repo will be updated even if it is set to be not updated during a regular reposync
operation (ex: ``cobbler repo edit --name=reponame1 --keep-updated=0``).

Note that if a cobbler import provides enough information to use the boot server as a yum mirror for core packages,
cobbler can set up kickstarts to use the cobbler server as a mirror instead of the outside world. If this feature is
desirable, it can be turned on by setting yum_post_install_mirror to 1 in ``/etc/cobbler/settings`` (and running
"cobbler sync").  You should not use this feature if machines are provisioned on a different VLAN/network than
production, or if you are provisioning laptops that will want to acquire updates on multiple networks.

The flags ``--tries=N`` (for example, ``--tries=3``) and ``--no-fail`` should likely be used when putting reposync on a
crontab. They ensure network glitches in one repo can be retried and also that a failure to synchronize one repo does
not stop other repositories from being synchronized.

Kickstart Tracking
##################

Cobbler knows how to keep track of the status of kickstarting machines.

.. code-block:: bash

    cobbler status

Using the status command will show when cobbler thinks a machine started kickstarting and when it finished, provided the
proper snippets are found in the kickstart template. This is a good way to track machines that may have gone interactive
(or stalled/crashed) during kickstarts.

Boot CD
#######

Cobbler can build all of its profiles into a bootable CD image using the ``cobbler buildiso`` command. This allows for
PXE-menu like bringup of bare metal in evnvironments where PXE is not possible. Another more advanced method is
described in the koan manpage, though this method is easier and sufficient for most applications.
