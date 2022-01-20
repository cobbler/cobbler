*********************
Repository Management
*********************

General
#######

This has already been covered a good bit in the command reference section, for details see: :ref:`cobbler-cli-reposync`

Yum repository management is an optional feature and is not required to provision through Cobbler. However, if Cobbler
is configured to mirror certain repositories, this feature can be used to associate profiles with those repositories.
Systems installed under those profiles will be autoconfigured to use these repository mirrors in ``/etc/yum.repos.d``,
and if supported (Fedora Core 6 and later), these repositories can be leveraged within Anaconda.

This can be useful if

#. you have a large install base, or
#. you want fast installation and upgrades for your systems, or
#. have some extra software not in a standard repository but want provisioned systems to know about that repository.

Make sure there is plenty of space in Cobbler's webdir, which defaults to ``/var/www/cobbler``.

.. code-block:: shell

    cobbler reposync [--only=ONLY] [--tries=N] [--no-fail]

``cobbler reposync`` is used to update repos known to Cobbler. The command is required to be executed prior to the first
provisioning of a system if Cobbler is configured as a mirror. If you just add repos and never run ``cobbler reposync``,
the content of the repos will be missing. This is probably a command you should include in a crontab. The configuration
is left up to the systems administrator.

.. note:: Mirroring can take a long time because of the amount of data being downloaded.

For those familiar with dnf's reposync, Cobbler's reposync is mostly a wrapper around the ``dnf reposync`` command.
use "cobbler reposync" to update Cobbler mirrors, as dnf's reposync does not perform all required steps. Also Cobbler
adds support for rsync and SSH locations, where as dnf's reposync only supports what yum supports (http/ftp).

If you want to update a certain repository, run:

.. code-block:: shell

    cobbler reposync --only="reponame1" ...

When updating repos by name, a repo will be updated even if it is set to be not updated during a regular reposync
operation (ex: ``cobbler repo edit --name=reponame1 --keep-updated=False``).

For distributions using dnf/yum Cobbler can act as a mirror and generate the ``.repo`` files for the core system
packages. This is only possible if the ``cobbler import`` command provided enough information. If this feature is
desirable, it can be turned on by setting ``yum_post_install_mirror`` to ``True`` in ``/etc/cobbler/settings.yaml`` (and
running ``cobbler sync``). You should not use this feature if machines are provisioned on a different VLAN/network than
production, or if you are provisioning laptops that will want to acquire updates on multiple networks.

The flags ``--tries=N`` (for example, ``--tries=3``) and ``--no-fail`` should likely be used when putting reposync on a
crontab. They ensure network glitches in one repo can be retried and also that a failure to synchronize one repo does
not stop other repositories from being synchronized.

Importing trees workflow
########################

Cobbler can auto-add distributions and profiles from remote sources, whether this is a filesystem path or an rsync
mirror. This can save a lot of time when setting up a new provisioning environment. Import is a feature that many users
will want to take advantage of, and is very simple to use.

After an import is run, Cobbler will try to detect the distribution type and automatically assign automatic installation
files. By default, it will provision the system by erasing the hard drive, setting up eth0 for DHCP, and using a default
password of "cobbler".  If this is undesirable, edit the automatic installation files in ``/etc/cobbler`` to do
something else or change the automatic installation setting after Cobbler creates the profile.

Mirrored content is saved automatically in ``/var/www/cobbler/distro_mirror``.

Examples:

* ``cobbler import --path=rsync://mirrorserver.example.com/path/ --name=fedora --arch=x86``
* ``cobbler import --path=root@192.168.1.10:/stuff --name=bar``
* ``cobbler import --path=/mnt/dvd --name=baz --arch=x86_64``
* ``cobbler import --path=/path/to/stuff --name=glorp``
* ``cobbler import --path=/path/where/filer/is/mounted --name=anyname --available-as=nfs://nfs.example.org:/where/mounted/``

Once imported, run a ``cobbler list`` or ``cobbler report`` to see what you've added.

By default, the rsync operations will exclude content of certain architectures, debug RPMs, and ISO images -- to change
what is excluded during an import, see ``/etc/cobbler/rsync.exclude``.

Note that all of the import commands will mirror install tree content into ``/var/www/cobbler`` unless a network
accessible location is given with ``--available-as``.  The option ``--available-as`` will be primarily used when
importing distros stored on an external NAS box, or potentially on another partition on the same machine that is already
accessible via HTTP or FTP.

For import methods using rsync, additional flags can be passed to rsync with the option ``--rsync-flags``.

Should you want to force the usage of a specific Cobbler automatic installation template for all profiles created by an
import, feed the option ``--autoinstall`` to import, to bypass the built-in automatic installation file
auto-detection.

Repository mirroring workflow
#############################

The following example shows:

 * How to set up a repo mirror for all enabled Cobbler host repositories and two additional repositories.
 * Create a profile that will auto install those repository configurations on provisioned systems using that profile.

.. code-block:: shell

    cobbler check
    # set up your cobbler distros here.
    cobbler autoadd
    cobbler repo add --mirror=http://mirrors.kernel.org/fedora/core/updates/6/i386/ --name=fc6i386updates
    cobbler repo add --mirror=http://mirrors.kernel.org/fedora/extras/6/i386/ --name=fc6i386extras
    cobbler reposync
    cobbler profile add --name=p1 --distro=existing_distro_name --autoinstall=/etc/cobbler/kickstart_fc6.ks --repos="fc6i386updates fc6i386extras"

Import Workflow
###############


This example shows:

* How to create a provisioning infrastructure from a distribution mirror or from ISO media.
* Create a default PXE configuration, so that by default systems will PXE boot into a fully automated install process
  for that distribution.

You can use a network rsync mirror, a mounted DVD location, or a tree you have available via a network filesystem.

Import knows how to autodetect the architecture of what is being imported. To make sure things are named
correctly, it's a good idea to specify ``--arch``. For instance, if you import a distribution named "fedora8"
from an x86_64 ISO, specify ``--arch=x86_64`` and the distro will be named "fedora8-x86_64"
automatically, and the right architecture field will also be set on the distribution object. If you are batch importing
an entire mirror (containing multiple distributions and arches), you don't have to do this. Cobbler will set the
names for things based on the paths it finds for you.

.. code-block:: shell

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
