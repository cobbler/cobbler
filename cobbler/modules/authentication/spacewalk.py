"""
Authentication module that uses Spacewalk's auth system.
Any org_admin or kickstart_admin can get in.

Copyright 2007-2008, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""


from future import standard_library
standard_library.install_aliases()
import xmlrpc.client


def register():
    """
    The mandatory Cobbler module registration hook.
    """
    return "authn"


def __looks_like_a_token(password):
    """
    What spacewalk sends us could be an internal token or it could be a password if it's long and lowercase hex, it's
    /likely/ a token, and we should try to treat it as a token first, if not, we should treat it as a password.  All of
    this code is there to avoid extra XMLRPC calls, which are slow.

    :param password: The password which is possibly a token.
    :return: True if it is possibly a token or False otherwise.
    :rtype: bool
    """

    if password.lower() != password:
        # Tokens are always lowercase, this isn't a token.
        return False

    # We can't use binascii.unhexlify here as it's an "odd length string".
    # try:
    #    #data = binascii.unhexlify(password)
    #    return True # looks like a token, but we can't be sure
    # except:
    #    return False # definitely not a token

    return (len(password) > 45)


def authenticate(api_handle, username, password):
    """
    Validate a username/password combo, returning True/False

    This will pass the username and password back to Spacewalk to see if this authentication request is valid.

    See also: https://github.com/uyuni-project/uyuni/blob/bbbbbf537a1928c1922015c70322034a89b1cb9a/java/code/src/com/redhat/rhn/frontend/xmlrpc/auth/AuthHandler.java#L133

    :param api_handle: The api instance to retrieve settings of.
    :param username: The username to authenticate agains spacewalk/uyuni/SUSE Manager
    :param password: The password to authenticate agains spacewalk/uyuni/SUSE Manager
    :return: True if it succeeded, False otherwise.
    :rtype: bool
    """

    if api_handle is not None:
        server = api_handle.settings().redhat_management_server
        user_enabled = api_handle.settings().redhat_management_permissive
    else:
        server = "columbia.devel.redhat.com"
        user_enabled = True

    if server == "xmlrpc.rhn.redhat.com":
        # Emergency fail, don't bother RHN!
        return False

    spacewalk_url = "https://%s/rpc/api" % server
    client = xmlrpc.client.Server(spacewalk_url, verbose=0)

    if __looks_like_a_token(password) or username == 'taskomatic_user':
        # The tokens are lowercase hex, but a password can also be lowercase hex, so we have to try it as both a token
        # and then a password if we are unsure. We do it this way to be faster but also to avoid any login failed stuff
        # in the logs that we don't need to send.

        try:
            valid = client.auth.checkAuthToken(username, password)
        except:
            # If the token is not a token this will raise an exception rather than return an integer.
            valid = 0

        # Problem at this point, 0xdeadbeef is valid as a token but if that fails, it's also a valid password, so we
        # must try auth system #2

        if valid != 1:
            # First API code returns 1 on success the second uses exceptions for login failed.
            # So... token check failed, but maybe the username/password is just a simple username/pass!

            if user_enabled == 0:
                # this feature must be explicitly enabled.
                return False

            session = ""
            try:
                session = client.auth.login(username, password)
            except:
                # FIXME: Should log exceptions that are not excepted as we could detect spacewalk java errors here that
                #        are not login related.
                return False

            # login success by username, role must also match
            roles = client.user.listRoles(session, username)
            if not ("config_admin" in roles or "org_admin" in roles):
                return False

        return True

    else:
        # It's an older version of spacewalk, so just try the username/pass.
        # OR: We know for sure it's not a token because it's not lowercase hex.

        if user_enabled == 0:
            # this feature must be explicitly enabled.
            return False

        session = ""
        try:
            session = client.auth.login(username, password)
        except:
            return False

        # login success by username, role must also match
        roles = client.user.listRoles(session, username)
        if not ("config_admin" in roles or "org_admin" in roles):
            return False

        return True


if __name__ == "__main__":
    print((authenticate(None, "admin", "redhat")))
