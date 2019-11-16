*****************
Web Authorization
*****************

Authorization happens after users have been [authenticated](Web Authentication) and controls who is then allowed, or not
allowed, to perform certain specific operations in cobbler.

Note that this applies to the [Cobbler Web Interface](Cobbler web interface) and [XMLRPC](XmlRpc) only -- the local
cobbler instance can be modified with the command line tool "cobbler" as the root user, regardless of authorization
policy.

Authorization choices are set in the `[authorization]` section of `/etc/cobbler/modules.conf`, whose options are as
follows:

Allow All
#########

    [authorization]
    module = authz_allowall

This module permits any user who has passed through authorization successfully to do anything they need to do,
regardless of username.  This is a valid choice if you are authenticating against a source that only contains trusted
accounts, such as the digest authentication module.  But if you are authenticating against an entire company's LDAP
server or Kerberos server, however, this would be a poor choice.

Config File
###########

    [authorization]
    module = authz_configfile

This uses the simple file `/etc/cobbler/users.conf` to provide a list of what users can access the server. The format is
described below in a separate section. There are no semantics given to groups and any listed user can access cobbler to
make any changes requested. Users not in this file do not have access. An example use of this setting would be if you
wanted to [authenticate admins against Kerberos](Kerberos) but kerberos contained other passwords and you wanted to
allow only users present in your whitelist to be able to make changes.

.. _ownership:

Ownership
#########

    [authorization]
    module = authz_ownership

This is similar to authz_configfile but now enforces group dynamics. Each file in the users file (format described
below) belongs to a group.

The module keeps users from modifying distributions, profiles, or system records that they do not have access to. This
is a good choice if you are using cobbler in a large company, have multiple levels of administrators, or want to grant
access to users to control specific systems.

If a user is in a group named "admin" or "admins" they will be able to edit any object regardless of the ownership
information stored on that object in Cobbler.

Here's an example of storing ownership details in Cobbler:

     cobbler system edit --name=system-name --owner=dbagroup,pete,mac,jack

This policy is rather detailed, so see more at AuthorizationWithOwnership for the full details on how this works.

Other authorization controls
############################

User Supplied Module
====================

The above authentication systems aren't expected to work for everyone.

As with any CobblerModule, users can write their own, and if they wish, submit them to the mailing list for others to
use. This allows for developing even finer grained access control, or adapting cobbler to more custom/unusual
configurations.

Using something like authz_ownership as a base would probably provide a very good place to start.  If you develop
something interesting you think others may want to use for policy, sharing is greatly appreciated!

File Format
===========

The file `/etc/cobbler/users.conf` is there to configure alternative authentication modes for modules like
authz_ownership and authz_configfile.  In the default cobbler configuration (authz_allowall), this file is IGNORED, as
is indicated by the comments in the file.

Here's a sample file defining a few users and groups:

    [admins]
    admin = ""
    cobbler = ""
    mdehaan = ""

    [superlab]
    obiwan = ""
    luke = ""

    [basement]
    darth = ""


Note that how this file is used depends entirely on what you have in `/etc/cobbler/modules.conf` (as described above in
"Module Choices"). After changing this file, cobblerd must be restarted in order for the changes to take effect.

You'll note the values have the "equals quote quote" after them. These values are currently required, but ignored.
Basically they are reserved for later use.
