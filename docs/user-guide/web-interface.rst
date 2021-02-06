.. _web-interface:

***********************************
Web-Interface
***********************************

.. Community Web-UI: https://github.com/vanishcode/cobbler-ui-part
.. Community Dashboard: https://github.com/zhangchenchen/supervisors

Please be patient until we have time to rework this section or please file a PR for this section.

The standard login for the WebUI can be read below. We would recommend to change this as soon as possible!

Username: ``cobbler``
Password: ``cobbler``

Old Release 2.8.x
#################

https://cobbler.readthedocs.io/en/release28/web-interface.html

Old GitHub-Wiki Entry
#####################

Most of the day-to-day actions in cobbler's command line can be performed in Cobbler's Web UI.

With the web user interface (WebUI), you can:

* View all of the cobbler objects and the settings
* Add and delete a system, distro, profile, or system
* Run the equivalent of a ``cobbler sync``
* Edit kickstart files (which must be in ``/etc/cobbler`` and ``/var/lib/cobbler/kickstarts``)

You cannot (yet):

* Auto-Import media
* Auto-Import a rsync mirror of install trees
* Do a ``cobbler reposync`` to mirror or update yum content
* Do a ``cobbler validateks``

The WebUI can be very good for day-to-day configuring activities, but the CLI is still required for basic bootstrapping
and certain other activities.

The WebUI is intended to be self-explanatory and contains tips and explanations for nearly every field you can edit. It
also contains links to additional documentation, including the Cobbler manpage documentation in HTML format.

Who logs in and what they can access is controlled by [Web Authentication](Web Authentication) and
[Web Authorization](Web Authorization). The default options are mostly good for getting started, but for safety reasons
the default authentication is "denyall" so you will at least need to address that.

Basic Setup
===========

1.  You must have installed the cobbler-web package

2.  Your ``/etc/httpd/conf.d/cobbler_web.conf`` should look something like this:

.. code::

        # This configuration file enables the cobbler web interface (django version)
        # Force everything to go to https
        RewriteEngine on
        RewriteCond %{HTTPS} off
        RewriteCond %{REQUEST_URI} ^/cobbler_web
        RewriteRule (.*) https://%{HTTP_HOST}%{REQUEST_URI}

        WSGIScriptAlias /cobbler_web /usr/share/cobbler/web/cobbler.wsgi

        # The following Directory Entry in Apache Configs solves 403 Forbidden errors.
        <Directory "/usr/share/cobbler/web">
          Order allow,deny
          Allow from all
        </Directory>

        # Display Cobbler Themes + Logo graphics.
        <Directory "/var/www/cobbler_webui_content">
        Order allow,deny
        Allow from all
        </Directory>

3.  Your ``/etc/cobbler/modules.conf`` should look something like this:

.. code::

    [authentication]
    module = authn_configfile

    [authorization]
    module = authz_allowall

4. You should change the password for the 'cobbler' username, see `Managing users.digest`_.

5.  If this is not a new install, your Apache configuration for Cobbler might not be current.

.. code-block:: shell

    cp /etc/httpd/conf.d/cobbler.conf.rpmnew /etc/httpd/conf.d/cobbler.conf

6.  Now restart Apache and ``cobblerd``.

.. code-block:: shell

    /sbin/service cobblerd restart
    /sbin/service httpd restart

7.  If you use SELinux, you may also need to set the following, so that the WebUI can connect with the [XMLRPC](XMLRPC):

.. code-block:: shell

    setsebool -P httpd_can_network_connect true


Basic setup (2.2.x and higher)
==============================

In addition to the steps above, cobbler 2.2.x has a requirement for ``mod_wsgi`` which, when installed via EPEL, will be
disabled by default. Attempting to start httpd will result in:

.. code::

    Invalid command 'WSGIScriptAliasMatch', perhaps misspelled \
      or defined by a module not included in the server configuration

You can enable this module by editing ``/etc/httpd/conf.d/wsgi.conf`` and un-commenting the
"LoadModule wsgi_module modules/mod_wsgi.so" line.

Next steps
==========

It should be ready to go. From your web browser visit the URL on your bootserver that resembles:

.. code::

    https://bootserver.example.com/cobbler_web

and log in with the username (usually cobbler) and password that you set earlier.

Should you ever need to debug things, see the following log files:

.. code::

    /var/log/httpd/error_log
    /var/log/cobbler/cobbler.log

Managing users.digest
=====================

Cobbler authenticates all WebUI logins through ``cobblerd``, which uses a configurable authentication mechanism. You may
wish to adjust that for your environment. For instance, if in ``modules.conf`` above you choose to stay with the
``authentication.configfile`` module, you may want to add your system administrator usernames to the digest file.

Because the generated password isn't supported by the ``htdigest`` command you have to generate the entries yourself, and
to generate the password hashes it is recommended to use either ``openssl`` or Python directly.

The entry format should be, where ``Cobbler`` is the realm:

.. code::

    username:realm:hash

Example using ``openssl 1.1.1`` or later:

.. code-block:: shell

    printf "foobar" | openssl dgst -sha3-512

It is possible with ``openssl`` to generate hashes for the following hash algorithms which are configurable: blake2b512,
blake2s256, shake128, shake256, sha3-224m sha3-256, sha3-384, sha3-512

Example using Python (using the python interactive shell):

.. code-block:: python

    import hashlib
    hashlib.sha3_512("<PASSWORD>".encode('utf-8')).hexdigest()

Python of course will always have all possible hash algorithms available which are valid in the context of Cobbler.

Both examples return the same result when executed with the same password. The file itself is structured according to
the following: ``<USERNAME>:<REALM>:<PASSWORDHASH>``. Normally ``<REALM>`` will be ``Cobbler``. Other values are
currently not valid. Please add the user, realm and passwordhash with your preferred editor. Normally there should be
no need to restart cobbler when a new user is added, removed or the password is changed. The authentication process
reads the file every time a user is authenticated.

You may also want to refine for authorization settings.

Before Cobbler 3.1.2 it was recommended to do edit the file ``users.digest`` with the following command. Since ``md5``
is not FIPS compatible from Cobbler 3.1.3 and onwards this is not possible anymore. The file was also just read once per
Cobbler start and thus a change of the data requires that Cobbler is restarted that it picks up these changes.

.. code-block:: shell

    htdigest /etc/cobbler/users.digest "Cobbler" <username>

Rewrite Rule for secure-http
============================

To redirect access to the WebUI via HTTPS on an Apache webserver, you can use the following rewrite rule, probably at
the end of Apache's ``ssl.conf``:

.. code::

    ### Force SSL only on the WebUI
    <VirtualHost *:80>
        <LocationMatch "^/cobbler_web/*">
           RewriteEngine on
           RewriteRule ^(.*) https://%{SERVER_NAME}/%{REQUEST_URI} [R,L]
       </LocationMatch>
    </VirtualHost>
