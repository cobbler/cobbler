Install Guide
-------------

Setting up and running cobblerd is not a easy task. Knowledge in apache configuration (setting up ssl, virtual hosts, apache module and wsgi) is needed. Certificates and some server administration knowledge is required too.

Cobbler is available for installation in several different ways, through packaging systems for each distribution or directly from source.

Cobbler has both definite and optional prerequisites, based on the features you'd like to use. This section documents the definite prerequisites for both a basic installation and when building/installing from source.


Prerequisites
+++++++++++++

Packages
========

Please note that installing any of the packages here via a package manager (such as yum or apt) can and will require a large number of ancilary packages, which we do not document here. The package definition should automatically pull these packages in and install them along with Cobbler, however it is always best to verify these requirements have been met prior to installing cobbler or any of its components.

First and foremost, Cobbler requires Python. Any version over 2.7 should work. Cobbler also requires the installation of the following packages:

* createrepo
* httpd / apache2
* mkisofs / genisoimage
* mod_wsgi / libapache2-mod-wsgi
* mod_ssl / libapache2-mod-ssl
* python-cheetah
* python-netaddr
* python-simplejson
* python-urlgrabber
* PyYAML / python-yaml
* rsync
* syslinux
* tftp-server / atftpd
* yum-utils

Cobbler-web only has one other requirement besides Cobbler itself:

* Django / python-django

Koan can be installed apart from Cobbler, and has only the following requirement (besides python itself of course):

* python-simplejson

Source
======

Installation from source requires the following additional software:

* git
* make
* python-devel
* python-cheetah
* openssl


Installation
++++++++++++

Cobbler is available for installation for many Linux variants through their native packaging systems. However, the Cobbler project also provides packages for all supported distributions which is the preferred method of installation.

Supported packages
==================

Fedora
######

First, get the Cobbler repo file:

.. code-block:: none

    # cd /etc/yum.repos.d
    # curl -o cobbler30.repo http://download.opensuse.org/repositories/home:/libertas-ict:/cobbler30/Fedora_20/home:libertas-ict:cobbler30.repo
    # yum update


Then install Cobbler:

.. code-block:: none

    # yum install cobbler cobbler-web


RHEL / CentOS
#############

Make sure you have the EPEL repository enabled on your system:

.. code-block:: none

    # yum repolist
    Loaded plugins: fastestmirror
    Loading mirror speeds from cached hostfile
     * base: centos.mirror.triple-it.nl
     * epel: mirror.i3d.net
     * extras: centos.mirror.triple-it.nl
     * updates: mirror.amsiohosting.net
    repo id                       repo name                                                    status
    !base/7/x86_64                CentOS-7 - Base                                              8,465
    !epel/x86_64                  Extra Packages for Enterprise Linux 7 - x86_64               5,709
    !extras/7/x86_64              CentOS-7 - Extras                                            30
    !updates/7/x86_64             CentOS-7 - Updates                                           705
    repolist: 14,909


Then, get the Cobbler repo file:

.. code-block:: none

    # cd /etc/yum.repos.d
    # curl -o cobbler30.repo http://download.opensuse.org/repositories/home:/libertas-ict:/cobbler30/CentOS_CentOS-7/home:libertas-ict:cobbler30.repo
    # yum update


Then install Cobbler:

.. code-block:: none

    # yum install cobbler cobbler-web


openSUSE
########

TBD
http://download.opensuse.org/repositories/home:/libertas-ict:/cobbler30/openSUSE_13.1/home:libertas-ict:cobbler30.repo





Debian
######

TBD

http://download.opensuse.org/repositories/home:/libertas-ict:/cobbler30/Debian_7.0/

Ubuntu
######

TBD

http://download.opensuse.org/repositories/home:/libertas-ict:/cobbler30/xUbuntu_14.04/


Packages from source
====================

It is also possible to build packages directly from the source tree.

RPM
###

.. code-block:: none

    $ make rpms
    ... (lots of output) ...
    Wrote: /path/to/cobbler/rpm-build/cobbler-3.0.0-1.fc20.src.rpm
    Wrote: /path/to/cobbler/rpm-build/cobbler-3.0.0-1.fc20.noarch.rpm
    Wrote: /path/to/cobbler/rpm-build/koan-3.0.0-1.fc20.noarch.rpm
    Wrote: /path/to/cobbler/rpm-build/cobbler-web-3.0.0-1.fc20.noarch.rpm

As you can see, an RPM is output for each component of Cobbler, as well as a source RPM. This command was run on a system running Fedora 20, hence the fc20 in the RPM name - this will be different based on the distribution you're running.

DEB
###

To install cobbler from source on Debian Squeeze, the following steps need to be made:

.. code-block:: none

    $ apt-get install make
    $ apt-get install git
    $ apt-get install python-yaml
    $ apt-get install python-cheetah
    $ apt-get install python-netaddr
    $ apt-get install python-simplejson
    $ apt-get install python-urlgrabber
    $ apt-get install libapache2-mod-wsgi
    $ apt-get install python-django
    $ apt-get install atftpd

    $ a2enmod proxy
    $ a2enmod proxy_http
    $ a2enmod rewrite

    $ ln -s /usr/local/lib/python2.6/dist-packages/cobbler /usr/lib/python2.6/dist-packages/
    $ ln -s /srv/tftp /var/lib/tftpboot

    $ chown www-data /var/lib/cobbler/webui_sessions

Change all ``/var/www/cobbler`` in ``/etc/apache2/conf.d/cobbler.conf`` to ``/usr/share/cobbler/webroot/``
Init script:
- add Required-Stop line
- path needs to be ``/usr/local/...`` or fix the install location


Source
======

The latest source code is available through git:

.. code-block:: none

    $ git clone https://github.com/cobbler/cobbler.git

    $ cd cobbler
    $ git checkout release30

The release30 branch corresponds to the official release version for the 3.0.x series. The master branch is the development series, and always uses an odd number for the minor version (for example, 3.1.0).

When building from source, make sure you have the correct prerequisites. Once they are, you can install Cobbler with the following command:

.. code-block:: none

    $ make install

This command will rewrite all configuration files on your system if you have an existing installation of Cobbler (whether it was installed via packages or from an older source tree). To preserve your existing configuration files, snippets and automatic installation files, run this command:

.. code-block:: none

    $ make devinstall

To install the Cobbler web GUI, use this command:

.. code-block:: none

    $ make webtest

This will do a full install, not just the web GUI. ``make webtest`` is a wrapper around ``make devinstall``, so your configuration files will also be saved when running this command.


Relocating your installation
++++++++++++++++++++++++++++

Often folks don't have a very large ``/var`` partition, which is what Cobbler uses by default for mirroring install trees and the like.

You'll notice you can reconfigure the webdir location just by going into ``/etc/cobbler/settings``, but it's not the best way to do things -- especially as the packaging process does include some files and directories in the stock path. This means that, for upgrades and the like, you'll be breaking things somewhat. Rather than attempting to reconfigure Cobbler, your Apache configuration, your file permissions, and your SELinux rules, the recommended course of action is very simple.

1. Copy everything you have already in ``/var/www/cobbler`` to another location -- for instance, ``/opt/cobbler_data``
2. Now just create a symlink or bind mount at ``/var/www/cobbler`` that points to ``/opt/cobbler_data``.

Done. You're up and running.

If you decided to access Cobbler's data store over NFS (not recommended) you really want to mount NFS on ``/var/www/cobbler`` with SELinux context passed in as a parameter to mount versus the symlink. You may also have to deal with problems related to rootsquash. However if you are making a mirror of a Cobbler server for a multi-site setup, mounting read only is ok there.

Also Note: ``/var/lib/cobbler`` can not live on NFS, as this interferes with locking ("flock") Cobbler does around it's storage files.
