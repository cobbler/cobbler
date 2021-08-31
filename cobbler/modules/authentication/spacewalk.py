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

from cobbler.cexceptions import CX
from cobbler.utils import log_exc
from xmlrpc.client import ServerProxy, Error


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "authn"


def __looks_like_a_token(password) -> bool:
    """
    What spacewalk sends us could be an internal token or it could be a password if it's long and lowercase hex, it's
    /likely/ a token, and we should try to treat it as a token first, if not, we should treat it as a password.  All of
    this code is there to avoid extra XMLRPC calls, which are slow.

    A password gets detected as a token if it is lowercase and under 45 characters.

    :param password: The password which is possibly a token.
    :return: True if it is possibly a token or False otherwise.
    """

    return password.lower() == password and len(password) > 45


def __check_auth_token(xmlrpc_client, api_handle, username, password):
    """
    This checks if the auth token is valid.

    :param xmlrpc_client: The xmlrpc client to check access for.
    :param api_handle: The api instance to retrieve settings of.
    :param username: The username to try.
    :param password: The password to try.
    :return: In any error case this will return 0. Otherwise the return value of the API which should be 1.
    """
    # If the token is not a token this will raise an exception rather than return an integer.
    try:
        return xmlrpc_client.auth.checkAuthToken(username, password)
    except Error:
        logger = api_handle.logger
        logger.error("Error while checking authentication token.")
        log_exc()
        return False


def __check_user_login(xmlrpc_client, api_handle, user_enabled: bool, username, password) -> bool:
    """
    This actually performs the login to spacewalk.

    :param xmlrpc_client: The xmlrpc client bound to the target spacewalk instance.
    :param api_handle: The api instance to retrieve settings of.
    :param user_enabled: Weather we allow Spacewalk users to log in or not.
    :param username: The username to log in.
    :param password: The password to log in.
    :return: True if users are allowed to log in and he is of the role ``config_admin`` or ``org_admin``.
    """
    try:
        session = xmlrpc_client.auth.login(username, password)
        # login success by username, role must also match and user_enabled needs to be true.
        roles = xmlrpc_client.user.listRoles(session, username)
        if user_enabled and ("config_admin" in roles or "org_admin" in roles):
            return True
    except Error:
        logger = api_handle.logger
        logger.error("Error while checking user authentication data.")
        log_exc()
    return False


def authenticate(api_handle, username: str, password: str) -> bool:
    """
    Validate a username/password combo. This will pass the username and password back to Spacewalk to see if this
    authentication request is valid.

    See also: https://github.com/uyuni-project/uyuni/blob/master/java/code/src/com/redhat/rhn/frontend/xmlrpc/auth/AuthHandler.java#L133

    :param api_handle: The api instance to retrieve settings of.
    :param username: The username to authenticate against spacewalk/uyuni/SUSE Manager
    :param password: The password to authenticate against spacewalk/uyuni/SUSE Manager
    :return: True if it succeeded, False otherwise.
    :raises CX: Raised in case ``api_handle`` is missing.
    """

    if api_handle is None:
        raise CX("api_handle required. Please don't call this without it.")
    server = api_handle.settings().redhat_management_server
    user_enabled = api_handle.settings().redhat_management_permissive

    spacewalk_url = "https://%s/rpc/api" % server
    with ServerProxy(spacewalk_url, verbose=True) as client:
        if username == 'taskomatic_user' or __looks_like_a_token(password):
            # The tokens are lowercase hex, but a password can also be lowercase hex, so we have to try it as both a
            # token and then a password if we are unsure. We do it this way to be faster but also to avoid any login
            # failed stuff in the logs that we don't need to send.

            # Problem at this point, 0xdeadbeef is valid as a token but if that fails, it's also a valid password, so we
            # must try auth system #2

            if __check_auth_token(client, api_handle, username, password) != 1:
                return __check_user_login(client, api_handle, user_enabled, username, password)
            return True
        # It's an older version of spacewalk, so just try the username/pass.
        # OR: We know for sure it's not a token because it's not lowercase hex.
        return __check_user_login(client, api_handle, user_enabled, username, password)
