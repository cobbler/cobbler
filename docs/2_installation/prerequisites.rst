*************
Prerequisites
*************

Cobbler has both definite and optional prerequisites, based on the features you'd like to use. This section documents
the definite prerequisites for both a basic installation and when building/installing from source. Please see the
[Managing Services With Cobbler]({% link manuals/2.8.0/3/4_-_Managing_Services_With_Cobbler.md %}) section for details
on the prerequisites for managing services, and other sections may make note of other package requirements.

Please note that installing any of the packages here via a package manager (such as yum or apt) can and will require a
large number of ancilary packages, which we do not document here. The package definition should automatically pull these
packages in and install them along with cobbler, however it is always best to verify these requirements have been met
prior to installing cobbler or any of its components.

## Cobbler/Cobblerd

First and foremost, cobbler requires Python. Any version over 2.6 should work. Cobbler also requires the installation of
the following packages:

* createrepo
* httpd (apache2 for Debian/Ubuntu)
* mkisofs
* mod_wsgi (libapache2-mod-wsgi for Debian/Ubuntu)
* mod_ssl (libapache2-mod-ssl)
* python-cheetah
* python-netaddr
* python-simplejson
* python-urlgrabber
* PyYAML (python-yaml for Debian/Ubuntu)
* rsync
* syslinux
* tftp-server (atftpd for Debian/Ubuntu, though others _may_ work)
* yum-utils

## Cobbler-Web

Cobbler web only has one other requirement besides cobbler itself:

* Django (python-django for Debian/Ubuntu)


## Koan

Koan can be installed apart from cobblerd, and has only the following requirement (besides python itself of course):

* python-simplejson

## Source Prerequisites

Installation from source requires the following additional packages:

* git
* make
* python-devel
* python-setuptools
* python-cheetah
* openssl
