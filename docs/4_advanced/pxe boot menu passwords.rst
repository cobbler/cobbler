***********************
PXE boot-menu passwords
***********************

How to create a PXE boot menu password
######################################

There are two different levels of password:

MENU MASTER PASSWD passwd: Sets a master password. This password can be used to boot any menu entry, and is required for
the [Tab] and [Esc] keys to work.

MENU PASSWD passwd: (Only valid after a LABEL statement.) Sets a password on this menu entry.  "passwd" can be either a
cleartext password or a SHA-1 encrypted password; use the included Perl script "sha1pass" to encrypt passwords.
(Obviously, if you don't encrypt your passwords they will not be very secure at all.)

If you are using passwords, you want to make sure you also use the settings "NOESCAPE 1", "PROMPT 0", and either set
"ALLOWOPTIONS 0" or use a master password (see below.)

If passwd is an empty string, this menu entry can only be unlocked with the master password.

Creating the password hash
##########################

If you have sha1pass on your system (you probably don't, but it's supposed to come with syslinux) you can do:
``sha1pass mypassword``

If you do _not_ have sha1pass, you can use openssl to create the pasword (the hashes appear to be compatible):
``openssl passwd -1 -salt sXiKzkus mypassword``

Files to edit
#############

* for master menu password: ``/etc/cobbler/pxe/pxedefault.template``
* for individual entries: ``/etc/cobbler/pxe/pxeprofile.template``

Sample usage
############

In this example, the master menu password will be used for all the entries (because the profile entry is blank). I have
not looked into a way to dynamically set a different password based on the profile variables yet.

.. code-block:: bash

    pxedefault.template:

        DEFAULT menu
        PROMPT 0
        MENU TITLE Cobbler | http://github.com/cobbler
        MENU MASTER PASSWD $1$sXiKzkus$haDZ9JpVrRHBznY5OxB82.

        TIMEOUT 200
        TOTALTIMEOUT 6000
        ONTIMEOUT $pxe_timeout_profile

        LABEL local
                MENU LABEL (local)
                MENU DEFAULT
                LOCALBOOT 0

        $pxe_menu_items

        MENU end


    pxeprofile.template:

        LABEL $profile_name
                MENU PASSWD
                kernel $kernel_path
                $menu_label
                $append_line
                ipappend 2

References
##########

* ``/usr/share/doc/syslinux*/syslinux.doc``
* ``/usr/share/doc/syslinux*/README.menu``
