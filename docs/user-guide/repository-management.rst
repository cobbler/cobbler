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

.. note:: For Debian/Ubuntu (``apt``-breed) imports in particular, importing a full DVD or netinst ISO pulls in an
   *unsigned* package pool that later needs an unsafe trust workaround to install from. See
   `Air-gapped Debian/APT installs`_ below for why, and for the recommended alternative.

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

Air-gapped Debian/APT installs
###############################

A genuinely air-gapped (no route to the internet or to any other signed Debian/Ubuntu mirror, for the whole
duration of the install) unattended install of an ``apt``-breed distro is a **netboot kernel+initrd** paired with a
**real, properly-signed package mirror** served locally -- not a package pool extracted from install media. This
section explains why that distinction matters and how to set it up.

``netboot.tar.gz`` versus the DVD/netinst ISO
==============================================

Debian and Ubuntu ship two very different kinds of install media, and ``cobbler import`` will happily import either
one -- but only one of them is suitable for a trust-correct air-gapped install:

* ``netboot.tar.gz`` (and the equivalent small netboot directory inside a netinst ISO) contains **only** the
  installer bootstrap: a kernel, an initrd, and the PXE/GRUB chainload files. It carries no ``pool/``, no ``dists/``,
  and no package content of any kind -- there is nothing in it to sign or trust in the first place. Every actual
  package the installer needs (including Debian Installer's own udebs) is fetched live, at install time, from
  wherever the installer's mirror settings point it.
* A full DVD ISO (or a netinst ISO's own embedded packages) genuinely bundles a real package pool (``pool/``) and
  APT metadata (``dists/``) alongside that same installer bootstrap. Debian has **never** shipped
  ``Release.gpg``/``InRelease`` on any of its install media, DVD included -- physical possession of the disc is the
  trust model there (``APT::Authentication::TrustCDROM``), not a cryptographic signature over ``dists/``. Once that
  package pool is copied out onto a PXE server's disk by ``cobbler import`` and served back out over plain HTTP, it
  is unavoidably unsigned: nothing was lost or broken in the copy, an unsigned pool is simply what a DVD ISO's
  package content always was.

``cobbler import`` does not distinguish between the two cases: it recursively copies whatever it finds under the
mounted/extracted source into ``distro_mirror/<name>/``. Point it at a DVD ISO and the full, unsigned ``pool/`` and
``dists/`` come along for the ride; point it at just a netboot tree and only the kernel and initrd are imported,
since there is nothing else there to copy.

Why ``allow_unauthenticated`` is not a safe fix
================================================

Installing from a DVD-derived, unsigned local package pool over plain HTTP makes the installer's own ``apt``
reject the repository's ``Release``/``InRelease`` file outright. The usual workaround -- setting
``d-i debian-installer/allow_unauthenticated boolean true`` (and/or ``apt-setup/allow_unauthenticated``) in the
preseed/kernel command line -- does make the installer proceed, but **it does not just relax repository-level
trust**: it disables *package-level* signature checking for the entire install, i.e. ``apt``/``dpkg`` will install
any package regardless of whether its individual signature can be verified at all. This is a materially larger
trust hole than it sounds like from the option's own name, and it has to stay set for every single install done
against that tree, not just once. Treat it as a workaround to be removed, not as a supported configuration.

The recommended path: pair the netboot installer with a mirrored ``cobbler repo``
==================================================================================

The preferred setup keeps ``cobbler import`` limited to the small netboot kernel+initrd (no unsigned package pool
ever gets imported at all), and serves the real packages from a separate, genuinely signed mirror that Cobbler
itself manages and syncs while still connected to the internet. Once synced, the mirror is served entirely from
local disk -- no further network access is needed at install time, and the installer's ``apt`` validates it through
the completely standard trust path (the real Debian/Ubuntu archive signing key, already present in every system's
``debian-archive-keyring``), with **no** ``allow_unauthenticated``/insecure-repository flag of any kind.

``cobbler import`` already creates the repo item for you: every Debian or Ubuntu import automatically creates a
matching ``cobbler repo`` item (``apt_repo_adder()`` in ``cobbler/modules/managers/import_signatures.py``) pointing
at the real upstream archive, with the correct breed-specific ``apt.components`` (``main contrib non-free
non-free-firmware`` for Debian, ``main restricted universe multiverse`` for Ubuntu) and ``apt.dists``
(``<suite> <suite>-updates <suite>-security``) already filled in. This repo item is deliberately left with
``mirror_locally`` set to ``False`` -- an automatic import is not the place to silently commit an administrator to
a potentially tens-of-GB ``debmirror`` pull -- so it starts out as accurate, ready-to-use reference metadata only.
To actually sync it locally, opt in explicitly:

.. code-block:: shell

    cobbler-cli repo edit --name=<distro-name> --mirror-locally
    cobbler reposync --only=<distro-name>

(the ``--mirror-locally`` flag on ``cobbler-cli repo edit`` is equivalent to setting the ``Repo`` item's
``mirror_locally`` property to ``True`` through the Python API). Point the system's/profile's software-source
configuration at the resulting local mirror, served at ``/cobbler/repo_mirror/<distro-name>/`` on Cobbler's own HTTP
server, instead of a real internet mirror, and the install will complete with no outbound network access at all.

Sizing a minimal mirror with ``debmirror --include``/``--exclude``
====================================================================

Mirroring an entire ``main``+``non-free-firmware`` suite can easily run to tens of gigabytes. If only a known,
bounded set of packages is actually needed (for example, exactly the packages a known-good install already pulled
in), ``cobbler reposync``'s apt-breed sync (``apt_sync()`` in ``cobbler/actions/reposync.py``) forwards any extra
flags set on the repo item's ``yumopts`` straight through to the underlying ``debmirror`` invocation, so
``--include``/``--exclude`` filtering can be used to keep the mirror small:

.. code-block:: shell

    cobbler-cli repo edit --name=<distro-name> --yumopts="--exclude=.,--include=/(?:package-one_|package-two_).*"

There are two real gotchas with ``debmirror``'s (and the underlying ``rsync``-style) ``--include``/``--exclude``
semantics that are easy to get wrong:

* **``--include`` is not a standalone whitelist.** It only *rescues* files that would otherwise be matched by an
  ``--exclude`` pattern. Passing ``--include`` alone, with no ``--exclude``, leaves the implicit "not excluded"
  default in effect for everything else, and ``debmirror`` will still mirror the entire suite. Always pair
  ``--include`` with a catch-all ``--exclude=.`` (matching any non-empty filename) so the ``--include`` patterns
  are the only things that actually get pulled.
* **The pattern is matched against the full pool-relative ``Filename:`` path, not the basename.** Every real
  ``Packages`` file entry looks like ``pool/<component>/<letter>/<source-package>/<binary-package>_<version>_<arch>.deb``,
  not just the trailing file name. A pattern anchored to match a package name at the very start of the string
  (``^package-one_...``) will therefore match nothing at all, since every real entry starts with ``pool/...``.
  Anchor on the path separator instead (``/package-one_...``), matching immediately after the final ``/``.

Test any include/exclude pattern against the real ``Packages``/``Packages.gz`` file for the suite being mirrored
before running a real sync, to confirm it matches the expected number of packages and isn't accidentally falling
back to mirroring everything.
