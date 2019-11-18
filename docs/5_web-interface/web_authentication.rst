.. _web-authentication:

******************
Web Authentication
******************

Authentication controls who has access to your cobbler server. Controlling the details of what they can subsequently do
is covered by a second step, :ref:`web-authorization`.

Authentication is governed by a setting in the ``[authentication]`` section of ``/etc/cobbler/modules.conf``, whose
options are as follows:

Deny All (Default)
##################

.. code-block:: yaml

    [authentication]
    module = authn_denyall

This disables all external XMLRPC modifications, and also disables the Cobbler Web interface. Use this if you do not
want to allow any external access and do not want to use the web interface. This is the default setting in Cobbler for
new installations, forcing users to decide what sort of remote security they want to have, and is intended to make sure
they think about that decision, rather than having access on by default.

Digest
######

.. code-block:: yaml

    [authentication]
    module = authn_configfile

This option uses a simple digest file to hold username and password information. This is a great option if you do not
have a Kerberos or LDAP server to authenticate against and just want something simple.

Be sure to change your default password for the "cobbler" user as soon as you set this up:

.. code-block:: bash

    htdigest /etc/cobbler/users.digest "Cobbler" cobbler

You can add additional users:

.. code-block:: bash

    htdigest /etc/cobbler/users.digest "Cobbler" $username

You can also choose to delete the "cobbler" user from the file.

Digest authentication with Apache is no longer supported due to the fact that we have moved to a session/token based
authentication and form-based login scheme with the new Web UI. Unfortunately, digest authentication does not work with
this method, so we now recommend using PAM or one of the other authentication schemes.

.. _kerberos:

Defer to Apache / Kerberos
##########################

.. code-block:: yaml

    [authentication]
    module = authn_passthru

This option lets Apache do the authentication and Cobbler will defer to what it decides. This is how Cobbler implements
`RFC 4120 <https://tools.ietf.org/html/rfc4120>`_ support. This could be modified to use other mechanisms if so desired.

Do you want to authenticate users using Cobbler's Web UI against Kerberos? If so, this is for you.

You may also be interested in authenticating against LDAP instead -- see :ref:`ldap` -- though if you have Kerberos you
probably want to use Kerberos.

We assume you've already got the WebUI up and running and just want to kerberize it ... if not, see :ref:`web-interface`
first, then come back here.

Passthru
========

Passthru authentication has been added back to Cobbler Web as of version 2.8.0. Passthru authentication allows you to
setup your webserver to perform authentication and Cobbler Web will use the value of ``REMOTE_USER`` to determine
authorization. Using this authentication module disables the normal web form authentication which was added in Cobbler
Web 2.2.0. If you prefer to use web form authentication we recommend using PAM or one of the other authentication
schemes.

A common reason you might want to use Passthru authentication is to provide support for single sign on authentication
like Kerberos. An example of setting this up can be found DEAD-LINK.

Bonus
=====

These steps also work for kerberizing Cobbler XMLRPC transactions provided those URLs are the Apache proxied versions as
specified in ``/var/lib/cobbler/httpd.conf``

Configure the Authentication and Authorization Modes
====================================================

Edit ``/etc/cobbler/modules.conf``:

.. code-block:: yaml

    [authentication]
    module = authn_passthru

    [authorization]
    module = authz_allowall

Note that you may want to change the authorization later, see :ref:`web-authorization` for more info.

A Note About Security
=====================

The ``authn_passthru`` mode is only as secure as your Apache configuraton. If you make the Apache configuration permit
everyone now, everyone will have access. For this reason you may want to test your Apache config on a test path like
``/var/www/html/test`` first, before using those controls to replace your default cobbler controls.

Configure your `/etc/krb5.conf`
===============================

NOTE: This is based on my file which I created during testing. Your kerberos configuration could be rather different.

.. code-block:: yaml

    [logging]
     default = FILE:/var/log/krb5libs.log
     kdc = FILE:/var/log/krb5kdc.log
     admin_server = FILE:/var/log/kadmind.log

    [libdefaults]
     ticket_lifetime = 24000
     default_realm = EXAMPLE.COM
     dns_lookup_realm = false
     dns_lookup_kdc = false
     kdc_timesync = 0

    [realms]
     REDHAT.COM = {
      kdc = kdc.example.com:88
      admin_server = kerberos.example.com:749
      default_domain = example.com
     }

    [domain_realm]
     .example.com = EXAMPLE.COM
     example.com = EXAMPLE.COM

    [kdc]
     profile = /var/kerberos/krb5kdc/kdc.conf

    [pam]
     debug = false
     ticket_lifetime = 36000
     renew_lifetime = 36000
     forwardable = true
     krb4_convert = false


Modify your Apache configuration file
=====================================

There's a section in ``/etc/httpd/conf.d/cobbler.conf`` that controls access to ``/var/www/cobbler/web``. We are going
to modify that section. Replace that specific "Directory" section with:

(Note that for Cobbler >= 2.0, the path is actually ``/cobbler_web/``)

.. code-block:: bash

    LoadModule auth_kerb_module   modules/mod_auth_kerb.so

    <Directory "/var/www/cobbler/web/">
      SetHandler mod_python
      PythonHandler index
      PythonDebug on

      Order deny,allow
      Deny from all
      AuthType Kerberos
      AuthName "Kerberos Login"
      KrbMethodK5Passwd On
      KrbMethodNegotiate On
      KrbVerifyKDC Off
      KrbAuthRealms EXAMPLE.COM

      <Limit GET POST>
        require user \
          gooduser1@EXAMPLE.COM \
          gooduser2@EXAMPLE.COM
        Satisfy any
      </Limit>

    </Directory>

Note that the above example configuration can be tweaked any way you want, the idea is just that we are delegating
Kerberos authentication bits to Apache, and Apache will do the hard work for us.

Also note that the above information lacks KeyTab and Service Principal info for usage with the GSS API (so you don't
have to type passwords in). If you want to enable that, do so following whatever kerberos documentation you like --
Cobbler is just deferring to Apache for auth so you can do whatever you want. The above is just to get you started.

Restart Things And test
=======================

.. code-block:: bash

    /sbin/service cobblerd restart
    /sbin/service httpd restart

A Note About Usernames
======================

If entering usernames and passwords into prompts, use ``user@EXAMPLE.COM`` not "user".

If you are using one of the authorization mechanisms that uses ``/etc/cobbler/users.conf``, make sure these match and
that you do not use just the short form.

Customizations
==============

You may be interested in the [Web Authorization](Web Authorization) section to further control things. For instance you
can decide to let in the users above, but only allow certain users to access certain things. The authorization module
can be used independent of your choice of authentication modes.

A note about restarting cobblerd
================================

Cobblerd regenerates an internal token on restart (for security reasons), so if you restart cobblerd, you'll have to
close your browser to drop the session token and then try to login again. Generally you won't be restarting cobblerd
except when restarting machines and on upgrades, so this shouldn't be a problem.

.. _ldap:

LDAP
####

.. code-block:: yaml

    [authentication]
    module = authn_ldap

This option authenticates against `RFC 4511 <https://tools.ietf.org/html/rfc4511>`_ using parameters from
``/etc/cobbler/settings``. This is a direct connection to LDAP without relying on Apache.

By default, the Cobbler WebUI and Web services authenticate against a digest file. All users in the digest file are
"in". What if you want to authenticate against an external resource? Cobbler can do that too. These instructions can be
used to make it authenticate against LDAP instead.

For the purposes of these instructions, we are authenticating against a new source install of FreeIPA -- though any LDAP
install should work in the same manner.

Instructions
============

0. Install python-ldap: ``yum install python-ldap``

1. In ``/etc/cobbler/modules.conf`` change the authn/authz sections to look like:

.. code-block:: yaml

    [authentication]
    module = authn_ldap

    [authorization]
    module = authz_configfile


   The above specifies that you authenticating against LDAP and will list which LDAP users are valid by looking at
   ``/etc/cobbler/users.conf``.

2. In ``/etc/cobbler/settings``, set the following to appropriate values to configure the LDAP parts. The values below
   are examples that show us pointing to an LDAP server, which is not running on the cobbler box, for authentication.
   Note that authorization is seperate from authentication. We'll get to that later.

.. code-block:: bash

    ldap_server     : "grimlock.devel.redhat.com"
    ldap_base_dn    : "DC=devel,DC=redhat,DC=com"
    ldap_port       : 389
    ldap_tls        : 1

With Cobbler 1.3 and higher, you can add additional LDAP servers by separating the server names with a space in the
``ldap_server`` field.

3. Now we have to configure OpenLDAP to know about the cert of the LDAP server. You only have to do this once on the
   cobbler box, not on each client box.

.. code-block:: bash

    openssl s_client -connect servername:636

4. Copy everything between BEGIN and END in the above output to ``/etc/openldap/cacerts/ldap.pem``
5. Ensure that the CA certificate is correctly hashed

.. code-block:: bash

    cd /etc/openldap/cacerts
    ln -s ldap.pem $(openssl x509 -hash -noout -in ldap.pem).0

   On Red Hat and Fedora systems this can also be done using the cacertdir\_rehash command:

.. code-block:: bash

    cacertdir_rehash /etc/openldap/cacerts

6. Configure ``/etc/openldap/ldap.conf`` to include the following:

.. code-block:: bash

    TLS_CACERTDIR   /etc/openldap/cacerts
    TLS_REQCERT     allow

7. Edit ``/etc/cobbler/users.conf`` to include the list of users allowed access to cobbler resources. These must match
   names in  LDAP. The group names are just comments.

.. code-block:: yaml

    [dxs]
    mac = ""
    pete = ""
    jack = ""

8. Done! Cobbler now authenticates against ldap instead of the  digest file, and you can limit what users can edit
   things by changing the ``/etc/cobbler/users.conf`` file.

Troubleshooting LDAP
====================

The following trick lets you test your username/password combinations outside of the web app and may prove useful in
verifying that your LDAP configuration is correct. replace $VERSION with your python version, for instance 2.4 or 2.5,
etc.

.. code-block:: bash

    # cp /usr/lib/python$VERSION/site-packages/cobbler/demo_connect.py /tmp/demo_connect.py
    # python /tmp/demo_connect.py --user=username --pass=password

Just run the above and look at the output. You should see a traceback if problems are encountered, which may point to
problems in your configuration if you specified a valid username/password. Restart cobblerd after changing
``/etc/cobbler/settings`` (if you're not using :ref:`dynamic-settings`) in order for them to take effect.

.. _web-authentication-spacewalk:

Spacewalk
#########

.. code-block:: yaml

    [authentication]
    module = authn_spacewalk

This module allows Spacewalk to use its own specific authorization scheme to log into Cobbler, since Cobbler is a
software service used by Spacewalk.

There are settings in ``/etc/cobbler/settings`` to configure this, for instance redhat_management_permissive if set to 1
will enable users with admin rights in Spacewalk (or RHN Satellite Server) to access Cobbler web using the same
username/password combinations.

This module requires that the address of the Spacewalk/Satellite server is configured in ``/etc/cobbler/settings``
(``redhat_management_server``)

Testing
#######

.. code-block:: yaml

    [authentication]
    module = authn_testing

This is for development/debug only and should never be used in production systems. The user "testing/testing" is always
let in, and no other combinations are accepted.

User Supplied
#############

Copy the signature of any existing cobbler authentication :ref:`modules` to write your own that conforms to your
organization's specific security requirements. Then just reference that module name in ``/etc/cobbler/modules.conf``,
restart cobblerd, and you're good to go.

