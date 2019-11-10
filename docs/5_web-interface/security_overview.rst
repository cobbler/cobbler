*****************
Security Overview
*****************

This section provides an overview of Cobbler's security model for the Web UI.

Why Customizable Security?
##########################

See also [Cobbler Web Interface](Cobbler web interface).

When manipulating cobbler remotely, either through the Web UI or the XMLRPC interface, different classes of users want
different authentication systems and different workflows. It would be wrong for Cobbler to enforce any specific workflow
on someone moving to Cobbler from their current systems, as it would limit where Cobbler can be deployed. So what
Cobbler does is make authentication and authorization extremely pluggable, while still shipping with some very
reasonable defaults.

The center of all of this revolves around a few settings in `/etc/cobbler/modules.conf`, for example:

    [authentication]
    module = authn_configfile

    [authorization]
    module = authn_allowall

The list of choices for each option is covered in depth at the links below.

Authentication
##############

The authentication setting determines what external source users are checked against to see if their passwords are
valid.

See [Authentication](Web Authentication).

The default setting is to deny XMLRPC access, so all users wanting remote/web access will need to pick their
authentication mode.

Authorization
#############

The authorization setting determines, for a user that has already passed authentication stages, what resources they have
access to in Cobbler.

See [Authorization](Web Authorization).

The default is to authorize all users that have cleared the authentication stage.
