************************
Installing from packages
************************

Cobbler is available for installation for many Linux variants through their native packaging systems.

The Cobbler project also provides packages: http://cobbler.github.io/downloads/2.8.x.html

Fedora
######

Cobbler is packaged and available through the Fedora packaging system, so you just need to install the packages with the
yum command: ``sudo yum install cobbler``

With Fedora's packaging system, new releases are held in a "testing" repository for a period of time to vet bugs. If you
would like to install the most up to date version of cobbler for Fedora (which may not be fully vetted for a production
environment), enable the -testing repo when installing or updating:

.. code-block:: bash

    $ sudo yum install --enablerepo=updates-testing cobbler
    # or
    $ sudo yum update --enablerepo=updates-testing cobbler

Once cobbler is installed, start and enable the service:

.. code-block:: bash

    $ systemctl start cobblerd.service
    $ systemctl enable cobblerd.service
    $ systemctl status cobblerd.service
    cobblerd.service - Cobbler Helper Daemon
          Loaded: loaded (/lib/systemd/system/cobblerd.service; enabled)
          Active: active (running) since Sun, 17 Jun 2012 13:01:28 -0500; 1min 44s ago
        Main PID: 1234 (cobblerd)
          CGroup: name=systemd:/system/cobblerd.service
              └ 1234 /usr/bin/python /usr/bin/cobblerd -F

And (re)start/enable Apache:

.. code-block:: bash

    $ systemctl start httpd.service
    $ systemctl enable httpd.service

RHEL and CentOS
###############

Cobbler is packaged for RHEL variants through the `Fedora EPEL <https://fedoraproject.org/wiki/EPEL>`_
(Extra Packages for Enterprise Linux) system. Follow the directions there to install the correct repo RPM for your RHEL
version and architecture. For example, on for a RHEL6.x x86_64 system:

.. code-block:: bash

    $ sudo rpm -Uvh http://download.fedoraproject.org/pub/epel/6/x86_64/epel-release-X-Y.noarch.rpm

Be sure to use the most recent X.Y version of the epel-release package. Once that is complete, simply use the yum
command to install the cobbler package: ``sudo yum install cobbler``

As noted above, new releases in the Fedora packaging system are held in a "testing" repository for a period of time to
vet bugs. If you would like to install the most up to date version of cobbler through EPEL (which may not be fully
vetted for a production environment), enable the -testing repo when installing or updating:

.. code-block:: bash

    $ sudo yum install --enablerepo=epel-testing cobbler
    # or
    $ sudo yum update --enablerepo=epel-testing cobbler

Once cobbler is installed, start and enable the service:

.. code-block:: bash

    $ service cobblerd start
    $ chkconfig cobblerd on

And (re)start/enable Apache:

.. code-block:: bash

    $ service httpd start
    $ service cobblerd on

openSUSE
########

Enable required apache modules (``/etc/sysconfig/apache2:APACHE_MODULES``)

.. code-block:: bash

    /usr/sbin/a2enmod proxy
    /usr/sbin/a2enmod proxy_http
    /usr/sbin/a2enmod proxy_connect
    /usr/sbin/a2enmod rewrite
    /usr/sbin/a2enmod ssl
    /usr/sbin/a2enmod wsgi
    /usr/sbin/a2enmod version
    /usr/sbin/a2enmod socache_shmcb (or whatever module you are using)

Setup SSL certificates in Apache (not documented here)

Enable required apache flag (``/etc/sysconfig/apache2:APACHE_SERVER_FLAGS``)

.. code-block:: bash

    /usr/sbin/a2enflag SSL

Make sure port 80 & 443 are opened in SuSEFirewall2 (not documented here)

Start/enable the apache2 and cobblerd services

.. code-block:: bash

    systemctl enable apache2.service
    systemctl enable cobblerd.service
    systemctl start apache2.service
    systemctl start cobblerd.service

Visit ``https://${CERTIFICATE_FQDN}/cobbler_web/``

Debian and Ubuntu
#################

TO BE DONE
