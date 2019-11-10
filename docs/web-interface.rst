*************
Web Interface
*************

This section of the manual covers the Cobbler Web Interface. With the web user interface (WebUI), you can:

  * View all of the cobbler objects and the settings
  * Add and delete a system, distro, profile, or system
  * Run the equivalent of a "cobbler sync"
  * Edit kickstart files (which must be in `/etc/cobbler` and `/var/lib/cobbler/kickstarts`)

You cannnot (yet):

  * Auto-Import media
  * Do a "cobbler validateks"

The WebUI is intended to be self-explanatory and contains tips and explanations for nearly every field you can edit. It
also contains links to additional documentation, including the Cobbler manpage documentation in HTML format.

Basic Setup
###########

1.  You must have installed the cobbler-web package

2.  Your `/etc/cobbler/modules.conf` should look something like this:

    [authentication]
    module = authn_configfile

    [authorization]
    module = authz_allowall

3. Change the password for the 'cobbler' username:

      htdigest /etc/cobbler/users.digest "Cobbler" cobbler

4.  If this is not a new install, your Apache configuration for Cobbler might not be current.

    cp /etc/httpd/conf.d/cobbler.conf.rpmnew /etc/httpd/conf.d/cobbler.conf

5.  Now restart Apache and Cobblerd

    /sbin/service cobblerd restart
    /sbin/service httpd restart

6.  If you use SELinux, you may also need to set the following, so that the WebUI can connect with the [XMLRPC](XMLRPC):

    setsebool -P httpd_can_network_connect true


Basic setup (2.2.x and higher)
##############################

In addition to the steps above, cobbler 2.2.x has a requirement for `mod_wsgi` which, when installed via EPEL, will be
disabled by default. Attempting to start httpd will result in:

    Invalid command 'WSGIScriptAliasMatch', perhaps misspelled \
      or defined by a module not included in the server configuration

You can enable this module by editing `/etc/httpd/conf.d/wsgi.conf` and un-commenting the
"LoadModule wsgi_module modules/mod_wsgi.so" line.

Next steps
==========

It should be ready to go.  From your web browser visit the URL on your bootserver that resembles:

    https://bootserver.example.com/cobbler_web

and log in with the username (usually cobbler) and password that you set earlier.

Should you ever need to debug things, see the following log files:

    /var/log/httpd/error_log
    /var/log/cobbler/cobbler.log

Further setup
=============

Cobbler authenticates all WebUI logins through `cobblerd`, which uses a configurable authentication mechanism. You may
wish to adjust that for your environment.  For instance, if in `modules.conf` above you choose to stay with the
authn_configfile module, you may want to add your system administrator usernames to the digest file:

    htdigest /etc/cobbler/users.digest "Cobbler" <username>

You may also want to refine for authorization settings.

Rewrite Rule for secure-http
============================

To redirect access to the WebUI via https on an Apache webserver, you can use the following rewrite rule, probably at
the end of Apache's `ssl.conf`:

    ### Force SSL only on the WebUI
    <VirtualHost *:80>
        <LocationMatch "^/cobbler/web/*">
           RewriteEngine on
           RewriteRule ^(.*) https://%{SERVER_NAME}/%{REQUEST_URI} [R,L]
       </LocationMatch>
    </VirtualHost>
