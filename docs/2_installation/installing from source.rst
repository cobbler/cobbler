**********************
Installing from Source
**********************

Cobbler is licensed under the General Public License (GPL), version 2 or later. You can download it, free of charge,
using the links below.

Latest Source
#############

The latest source code (it's all Python) is available through `git <https://github.com/cobbler/cobbler>`_.

Getting the Code
================

Clone the repo using git: `<git://github.com/cobbler/cobbler.git>`_ or https://github.com/cobbler/cobbler.git

.. code-block:: bash

    $ git clone PASTE URL HERE
    $ cd cobbler
    $ git checkout release28

.. note:: The release28 branch corresponds to the official release version for the 2.8.x series. The master branch is
   the development series, and always uses an odd number for the minor version (for example, 2.9.0).

Installing
##########

When building from source, make sure you have the correct :ref:`prerequisites`. Once they are, you can install
cobbler with the following command: ``make install``

This command will rewrite all configuration files on your system if you have an existing installation of Cobbler
(whether it was installed via packages or from an older source tree). To preserve your existing configuration files,
snippets and kickstarts, run this command: ``make devinstall``

To install the Cobbler web GUI, use this command: ``make webtest``

.. note:: This will do a full install, not just the web GUI. ``make webtest`` is a wrapper around ``make devinstall``,
   so your configuration files will also be saved when running this command.

Building Packages from Source (RPM)
===================================

It is also possible to build packages from the source file. Right now, only RPMs are supported, however we plan to add
support for building .deb files in the future as well.

To build RPMs from source, use this command:

.. code-block:: bash

    $ make rpms
    ... (lots of output) ...
    Wrote: /path/to/cobbler/rpm-build/cobbler-2.8.0-1.fc24.src.rpm
    Wrote: /path/to/cobbler/rpm-build/cobbler-2.8.0-1.fc24.noarch.rpm
    Wrote: /path/to/cobbler/rpm-build/koan-2.8.0-1.fc24.noarch.rpm
    Wrote: /path/to/cobbler/rpm-build/cobbler-web-2.8.0-1.fc24.noarch.rpm

As you can see, an RPM is output for each component of cobbler, as well as a source RPM. This command was run on a
system running Fedora 20, thus the fc20 in the RPM name - this will be different based on the distribution you're
running.

Building Packages from Source (DEB)
===================================

To install cobbler from source on Debian Squeeze, the following steps need to be made:

.. code-block:: bash

    $ apt-get install make # for build
    $ apt-get install git # for build
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

    $ a2ensite cobbler.conf

    $ ln -s /usr/local/lib/python2.6/dist-packages/cobbler /usr/lib/python2.6/dist-packages/
    $ ln -s /srv/tftp /var/lib/tftpboot

    $ chown www-data /var/lib/cobbler/webui_sessions

- Change all ``/var/www/cobbler`` in ``/etc/apache2/conf.d/cobbler.conf`` to ``/usr/share/cobbler/webroot/``
- init script
  - add Required-Stop line
  - path needs to be ``/usr/local/...`` or fix the install location
