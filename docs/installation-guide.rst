***********************************
Install Guide
***********************************

Setting up and running `cobblerd` is not a easy task. Knowledge in Apache2 configuration (setting up SSL, virtual hosts,
and apache proxy module) is needed. Certificates and some server administration knowledge is required too.

Cobbler is available for installation in several different ways, through packaging systems for each distribution or
directly from source.

Cobbler has both definite and optional prerequisites, based on the features you'd like to use. This section documents
the definite prerequisites for both a basic installation and when building/installing from source.

Known packages by distros
#########################

This is the most convenient way and should be the default for most people. Production usage is advised only from these
four sources or from source with Git Tags.

- `Fedora 37 <https://src.fedoraproject.org/rpms/cobbler>`_ - ``dnf install cobbler``
- `CentOS 8 <https://src.fedoraproject.org/rpms/cobbler>`_:
    - ``dnf install epel-release``
    - ``dnf module enable cobbler``
    - ``dnf install cobbler``
- `openSUSE Tumbleweed <https://software.opensuse.org/package/cobbler>`_ - ``zypper in cobbler``
- `openSUSE Leap 15.x <https://software.opensuse.org/package/cobbler>`_ - ``zypper in cobbler``

.. _install-prerequisites:

Prerequisites
#############

Packages
========

Please note that installing any of the packages here via a package manager (such as dnf/yum or apt) can and will require
a large number of ancillary packages, which we do not document here. The package definition should automatically pull
these packages in and install them along with Cobbler, however it is always best to verify these requirements have been
met prior to installing Cobbler or any of its components.

First and foremost, Cobbler requires Python 3. When installing from distribution
packages, the dependency solver pulls the required libraries automatically. The
lists below document the packages so you can validate a manual or source based
installation. Package names reflect the native repositories of each platform.

DNF based distributions (Fedora, RHEL, CentOS Stream, Rocky, AlmaLinux)
----------------------------------------------------------------------

**Required packages**

- ``httpd`` (or another HTTP proxy supporting reverse proxy)
- ``tftp-server``
- ``createrepo_c``
- ``dnf-plugins-core``
- ``fence-agents`` (``fence-agents-all`` on RHEL 9 and newer)
- ``rsync``
- ``xorriso``
- ``dosfstools``
- ``mtools``
- ``python3-cheetah``
- ``python3-dns``
- ``python3-netaddr``
- ``python3-requests``
- ``python3-distro``
- ``python3-schema``
- ``python3-systemd``
- ``python3-gunicorn``
- ``python3-file-magic``
- ``python3-PyYAML``

**Recommended packages**

- ``syslinux``
- ``grub2-efi-x64`` and ``grub2-efi-ia32``
- ``logrotate``
- ``python3-librepo``
- ``bash-completion``

APT based distributions (Debian, Ubuntu)
----------------------------------------

**Required packages**

- ``apache2`` (or a compatible HTTP proxy)
- ``tftpd-hpa`` or ``atftpd``
- ``systemd``
- ``fence-agents``
- ``rsync``
- ``xorriso``
- ``python3`` (>= 3.6)
- ``python3-cheetah``
- ``python3-dnspython``
- ``python3-netaddr``
- ``python3-requests``
- ``python3-distro``
- ``python3-schema``
- ``python3-gunicorn``
- ``python3-yaml``

**Suggested packages**

- ``createrepo-c`` (``createrepo`` on older releases)
- ``logrotate``
- ``python3-librepo``

For mirror detection on apt based systems installing the ``python3-aptsources``
module is strongly recommended.

ZYpp based distributions (openSUSE Leap, openSUSE Tumbleweed, SLES)
-------------------------------------------------------------------

**Required packages**

- ``apache2``
- ``tftp``
- ``createrepo_c``
- ``fence-agents``
- ``rsync``
- ``xorriso``
- ``dosfstools``
- ``mtools``
- ``python311-Cheetah3`` (``python3-Cheetah3`` on older SLES)
- ``python311-dnspython``
- ``python311-netaddr``
- ``python311-requests``
- ``python311-distro``
- ``python311-schema``
- ``python311-systemd``
- ``python311-gunicorn``
- ``python311-file-magic``
- ``python311-PyYAML``

**Recommended packages**

- ``syslinux``
- ``grub2-x86_64-efi`` and ``grub2-i386-efi``
- ``logrotate``
- ``python311-librepo`` (``python3-librepo`` on Leap 15)
- ``bash-completion``

Feature specific dependencies
-----------------------------

The following packages are only needed when enabling the respective feature:

- ``python3-ldap`` (LDAP authentication; package name ``python311-ldap`` on
  openSUSE/SLES)
- ``python3-hivex`` and ``python3-pefile`` (Windows auto-installation support)
- ``wget`` or ``curl`` for fetching external resources
- ``koan`` when performing re-installs from existing systems

.. note::
   Not installing all required dependencies will lead to stacktraces in your
   Cobbler installation.

Koan can be installed apart from Cobbler. Please visit the
`Koan documentation <https://koan.readthedocs.io/en/latest/>`_ for details.

Source
======

.. note::
   Please be aware that on some distributions the python packages are named differently. On Debian based systems
   everything which is named ``something-devel`` is named ``something-dev`` there. Also please remember that the case of
   some packages is slightly different.

.. warning::
   Some distributions still have Python 2 available. It is your responsibility to adjust the package names to Python3.

Installation from source requires the following additional software:

- git
- make
- python3-devel (on Debian based distributions ``python3-dev``)
- python3-Sphinx
- python3-coverage
- openssl


Installation
############

Cobbler is available for installation for many Linux variants through their native packaging systems. However, the
Cobbler project also provides packages for all supported distributions which is the preferred method of installation.

Packages
========

We leave packaging to downstream; this means you have to check the repositories provided by your distribution vendor.
However we provide docker files for

- Fedora 37
- openSUSE Leap 15.6
- openSUSE Tumbleweed
- Rocky Linux 9
- Rocky Linux 10
- Debian 11 Bullseye
- Debian 12 Bookworm

which will give you packages which will work better then building from source yourself.

.. note:: If you have a close look at our ``docker`` folder you may see more folders and files but they are meant for
          testing or other purposes. Please ignore them, this page is always aligned and up to date.

.. note:: Rocky Linux 10 is missing python3-schema and as such building a native RPM will not be successful.

To build the packages you to need to execute the following in the root folder of the cloned repository:

- openSUSE Leap 15.6: ``./docker/rpms/build-and-install-rpms.sh opensuse-leap docker/rpms/opensuse_leap/openSUSE_Leap15.dockerfile``
- Fedora 37: ``./docker/rpms/build-and-install-rpms.sh fc41 docker/rpms/Fedora_41/Fedora41.dockerfile``
- Rocky Linux 9: ``./docker/rpms/build-and-install-rpms.sh rl9 docker/rpms/Rocky_Linux_9/Rocky_Linux_9.dockerfile``
- Rocky Linux 10: ``./docker/rpms/build-and-install-rpms.sh rl10 docker/rpms/Rocky_Linux_10/Rocky_Linux_10.dockerfile``
- Debian 11: ``./docker/debs/build-and-install-debs.sh deb11 docker/debs/Debian_11/Debian11.dockerfile``
- Debian 12: ``./docker/debs/build-and-install-debs.sh deb12 docker/debs/Debian_12/Debian12.dockerfile``

After executing the scripts you should have one folder owned by ``root`` which was created during the build. It is
either called ``rpm-build`` or ``deb-build``. In these directories you should find the built packages. They are
obviously unsigned and thus will generate warnings in relation to that fact.

Packages from source
====================

For some platforms it's also possible to build packages directly from the source tree.

RPM
###

.. code-block:: shell

    $ make rpms
    ... (lots of output) ...
    Wrote: /path/to/cobbler/rpm-build/cobbler-3.0.0-1.fc20.src.rpm
    Wrote: /path/to/cobbler/rpm-build/cobbler-3.0.0-1.fc20.noarch.rpm
    Wrote: /path/to/cobbler/rpm-build/koan-3.0.0-1.fc20.noarch.rpm
    Wrote: /path/to/cobbler/rpm-build/cobbler-web-3.0.0-1.fc20.noarch.rpm

As you can see, an RPM is output for each component of Cobbler, as well as a source RPM. This command was run on a
system running Fedora 20, hence the fc20 in the RPM name - this will be different based on the distribution you're
running.

DEB
###

To install Cobbler from source on a Debian-Based system, the following steps need to be made (tested on Debian Buster):

.. code-block:: shell

    $ a2enmod proxy
    $ a2enmod proxy_http
    $ a2enmod rewrite

    $ ln -s /srv/tftp /var/lib/tftpboot

    $ systemctl restart apache2
    $ make debs

Change all ``/var/www/cobbler`` in ``/etc/apache2/conf.d/cobbler.conf`` to ``/usr/share/cobbler/webroot/``
Init script:

- add Required-Stop line
- path needs to be ``/usr/local/...`` or fix the install location

Pip
###

While this installation method is not recommended, since Cobbler is a Python-Project, you can install Cobbler with
``pip`` (the Python Package manager). To do so please follow the following steps:

.. note::
   Cobbler will never be compatible with virtual environments that don't inherit from the system due to dependencies
   like ``dnf`` (`PyPi Link <https://pypi.org/project/dnf/>`_)

Additional dependencies needed for installation via pip:

- python-pip
- openldap2 (with devel and client subpackages)
- cyrus-sasl development headers

Installation process:

#. Please ensure that the system-level dependencies mentioned in :ref:`install-prerequisites` are available.
#. Ensure that additional system-level dependencies for pip-installation are available.
#. Install Pip (in case you haven't automatically done so)
#. Install Cobbler with pip: ``pip install --break-system-packages git+https://github.com/cobbler/cobbler.git``
#. Move all required files and folders into place with ``cobblerd setup``

Example with a minimal openSUSE Tumbleweed container:

.. code-block:: shell

   $ zypper in -y gcc git python3-devel fence-agents rsync syslinux python3-gunicorn createrepo_c ipmitool python3-gunicorn cyrus-sasl-devel python3-legacycrypt systemd-devel mtools dosfstools python3-pip openldap2-devel openldap2 openldap2-client
   $ pip install --break-system-packages git+https://github.com/cobbler/cobbler.git
   $ cobblerd setup

Multi-Build
###########

In the repository root there is a file called ``docker-compose.yml``. If you have ``docker-compose`` installed you may
use that to build packages for multiple distros on a single run. Just execute:

.. code-block:: shell

   $ docker-compose up -d

After some time all containers expect one should be exited and you should see two new folders owned by ``root`` called
``rpm-build`` and ``deb-build``. The leftover docker container is meant to be used for testing and playing, if you don't
require this playground you may just clean up with:

.. code-block:: shell

   $ docker-compose down

Source
######

.. warning:: Cobbler is not suited to be run outside of custom paths or being installed into a virtual environment. We
             are working hard to get there but it is not possible yet. If you try this and it works, please report to
             our GitHub repository and tell us what is left to support this conveniently.


Installation
============

The latest source code is available through git:

.. code-block:: shell

    $ git clone https://github.com/cobbler/cobbler.git
    $ cd cobbler

The release30 branch corresponds to the official release version for the 3.0.x series. The main branch is the
development series.

When building from source, make sure you have the correct prerequisites. The Makefile uses a script called
`distro_build_configs.sh` which sets the correct environment variables. Be sure to source it if you do not use the
Makefile.

If all prerequisites are met, you can install Cobbler with the following command:

.. code-block:: shell

    $ make install

This command will rewrite all configuration files on your system if you have an existing installation of Cobbler
(whether it was installed via packages or from an older source tree).

To preserve your existing configuration files, snippets and automatic installation files, run this command:

.. code-block:: shell

    $ make devinstall

To install Cobbler, finish the installation in any of both cases, use these steps:

#. Copy the systemd service file for `cobblerd` from ``/etc/cobbler/cobblerd.service`` to your systemd unit directory
   (``/etc/systemd/system``).
#. Install ``python3-gunicorn`` or the package responsible for your distro.
#. Take the systemd service file ``cobblerd-gunicorn-service`` and copy it into your unit directory.
#. Enable the proxy module of Apache2 (``a2enmod proxy`` or something similar) if not enabled.
#. Restart Apache, ``cobblerd`` and ``cobblerd-gunicorn``.

.. note:: Depending on your distributions FHS implementation you might need to adjust ``ExecStart`` from
          ``/usr/bin/cobblerd`` to ``/usr/local/bin/cobblerd`` in the ``cobblerd.service`` file.

Be advised that we don't copy the service file into the correct directory and that the path to the binary may be wrong
depending on the location of the binary on your system. Do this manually and then you should be good to go. The same is
valid for the Apache webserver config.

Uninstallation
==============

#. Stop the ``cobblerd`` and ``apache2`` daemon
#. Remove Cobbler related files from the following paths:

   #. ``/usr/lib/python3.x/site-packages/cobbler/``
   #. ``/etc/apache2/``
   #. ``/etc/cobbler/``
   #. ``/etc/systemd/system/``
   #. ``/usr/local/bin/``
   #. ``/var/lib/cobbler/``
   #. ``/var/log/cobbler/``

#. Do a ``systemctl daemon-reload``.

.. _relocating-your-installation:

Relocating your installation
############################

Often folks don't have a very large ``/var`` partition, which is what Cobbler uses by default for mirroring install
trees and the like.

You'll notice you can reconfigure the webdir location just by going into ``/etc/cobbler/settings.yaml``, but it's not
the best way to do things -- especially as the packaging process does include some files and directories in the stock
path. This means that, for upgrades and the like, you'll be breaking things somewhat. Rather than attempting to
reconfigure Cobbler, your Apache configuration, your file permissions, and your SELinux rules, the recommended course of
action is very simple.

1. Copy everything you have already in ``/var/www/cobbler`` to another location -- for instance, ``/opt/cobbler_data``
2. Now just create a symlink or bind mount at ``/var/www/cobbler`` that points to ``/opt/cobbler_data``.

Done. You're up and running.

If you decided to access Cobbler's data store over NFS (not recommended) you really want to mount NFS on
``/var/www/cobbler`` with SELinux context passed in as a parameter to mount versus the symlink. You may also have to
deal with problems related to rootsquash. However if you are making a mirror of a Cobbler server for a multi-site setup,
mounting read only is OK there.

Also Note: ``/var/lib/cobbler`` can not live on NFS, as this interferes with locking ("flock") Cobbler does around it's
storage files.
