***********************************
Web-Interface
***********************************

.. Community Web-UI: https://github.com/vanishcode/cobbler-ui-part
.. Community Dashboard: https://github.com/zhangchenchen/supervisors

Please be patient until we have time to rework this section or please file a PR for this section.

The standard login for the Web-UI can be read below. We would recommend to change this as soon as possible!

Username: ``cobbler``
Password: ``cobbler``

Old Release 2.8.x
#################

https://cobbler.readthedocs.io/en/release28/web-interface.html

Old Github-Wiki Entry
#####################

Most of the day-to-day actions in cobbler's command line can be performed in Cobbler's Web UI.

With the web user interface (WebUI), you can:

  * View all of the cobbler objects and the settings
  * Add and delete a system, distro, profile, or system
  * Run the equivalent of a ``cobbler sync``
  * Edit kickstart files (which must be in ``/etc/cobbler`` and ``/var/lib/cobbler/kickstarts``)

You cannnot (yet):

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

.. code-block:: none

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

.. code-block:: none

    [authentication]
    module = authn_configfile

    [authorization]
    module = authz_allowall

4. Change the password for the 'cobbler' username:

.. code-block:: none

      htdigest /etc/cobbler/users.digest "Cobbler" cobbler

5.  If this is not a new install, your Apache configuration for Cobbler might not be current.

.. code-block:: none

    cp /etc/httpd/conf.d/cobbler.conf.rpmnew /etc/httpd/conf.d/cobbler.conf

6.  Now restart Apache and Cobblerd

.. code-block:: none

    /sbin/service cobblerd restart
    /sbin/service httpd restart

7.  If you use SELinux, you may also need to set the following, so that the WebUI can connect with the [XMLRPC](XMLRPC):

.. code-block:: none

    setsebool -P httpd_can_network_connect true


Basic setup (2.2.x and higher)
==============================

In addition to the steps above, cobbler 2.2.x has a requirement for ``mod_wsgi`` which, when installed via EPEL, will be
disabled by default. Attempting to start httpd will result in:

.. code-block:: none

    Invalid command 'WSGIScriptAliasMatch', perhaps misspelled \
      or defined by a module not included in the server configuration

You can enable this module by editing ``/etc/httpd/conf.d/wsgi.conf`` and un-commenting the
"LoadModule wsgi_module modules/mod_wsgi.so" line.

Next steps
==========

It should be ready to go. From your web browser visit the URL on your bootserver that resembles:

.. code-block:: none

    https://bootserver.example.com/cobbler_web

and log in with the username (usually cobbler) and password that you set earlier.

Should you ever need to debug things, see the following log files:

.. code-block:: none

    /var/log/httpd/error_log
    /var/log/cobbler/cobbler.log

Further setup
=============

Cobbler authenticates all WebUI logins through ``cobblerd``, which uses a configurable authentication mechanism. You may
wish to adjust that for your environment. For instance, if in ``modules.conf`` above you choose to stay with the
authn_configfile module, you may want to add your system administrator usernames to the digest file:

.. code-block:: none

    htdigest /etc/cobbler/users.digest "Cobbler" <username>

You may also want to refine for authorization settings.

Rewrite Rule for secure-http
============================

To redirect access to the WebUI via https on an Apache webserver, you can use the following rewrite rule, probably at
the end of Apache's ``ssl.conf``:

.. code-block:: none

    ### Force SSL only on the WebUI
    <VirtualHost *:80>
        <LocationMatch "^/cobbler_web/*">
           RewriteEngine on
           RewriteRule ^(.*) https://%{SERVER_NAME}/%{REQUEST_URI} [R,L]
       </LocationMatch>
    </VirtualHost>
