"""
Authentication module that uses ldap
Settings in /etc/cobbler/authn_ldap.conf
Choice of authentication module is in /etc/cobbler/modules.conf
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

# We need to ignore this due to the ldap bindings not being type annotated and also a C library at the same time.
# pylint: disable=no-member

import traceback
from typing import TYPE_CHECKING

from cobbler import enums
from cobbler.cexceptions import CX

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authn"
    """

    return "authn"


def authenticate(api_handle: "CobblerAPI", username: str, password: str) -> bool:
    """
    Validate an LDAP bind, returning whether the authentication was successful or not.

    :param api_handle: The api instance to resolve settings.
    :param username: The username to authenticate.
    :param password: The password to authenticate.
    :return: True if the ldap server authentication was a success, otherwise false.
    :raises CX: Raised in case the LDAP search bind credentials are missing in the settings.
    """

    if not password:
        return False
    import ldap  # type: ignore

    server = api_handle.settings().ldap_server
    basedn = api_handle.settings().ldap_base_dn
    port = str(api_handle.settings().ldap_port)
    prefix = api_handle.settings().ldap_search_prefix

    # Support for LDAP client certificates
    tls = api_handle.settings().ldap_tls
    tls_cacertdir = api_handle.settings().ldap_tls_cacertfile
    tls_cacertfile = api_handle.settings().ldap_tls_cacertfile
    tls_keyfile = api_handle.settings().ldap_tls_keyfile
    tls_certfile = api_handle.settings().ldap_tls_certfile
    tls_cipher_suite = api_handle.settings().ldap_tls_cipher_suite
    tls_reqcert = api_handle.settings().ldap_tls_reqcert

    # allow multiple servers split by a space
    if server.find(" "):
        servers = server.split()
    else:
        servers = [server]

    # to get ldap working with Active Directory
    ldap.set_option(ldap.OPT_REFERRALS, 0)  # type: ignore

    uri = ""
    for server in servers:
        # form our ldap uri based on connection port
        if port == "389":
            uri += "ldap://" + server
        elif port == "636":
            uri += "ldaps://" + server
        elif port == "3269":
            uri += "ldaps://" + f"{server}:{port}"
        else:
            uri += "ldap://" + f"{server}:{port}"
        uri += " "

    uri = uri.strip()

    # connect to LDAP host
    directory = ldap.initialize(uri)  # type: ignore

    if port in ("636", "3269"):
        ldaps_tls = ldap
    else:
        ldaps_tls = directory

    if tls or port in ("636", "3269"):
        if tls_cacertdir:
            ldaps_tls.set_option(ldap.OPT_X_TLS_CACERTDIR, tls_cacertdir)  # type: ignore
        if tls_cacertfile:
            ldaps_tls.set_option(ldap.OPT_X_TLS_CACERTFILE, tls_cacertfile)  # type: ignore
        if tls_keyfile:
            ldaps_tls.set_option(ldap.OPT_X_TLS_KEYFILE, tls_keyfile)  # type: ignore
        if tls_certfile:
            ldaps_tls.set_option(ldap.OPT_X_TLS_CERTFILE, tls_certfile)  # type: ignore
        if tls_reqcert:
            req_cert: enums.TlsRequireCert = enums.TlsRequireCert.to_enum(tls_reqcert)
            reqcert_types = {  # type: ignore
                enums.TlsRequireCert.NEVER: ldap.OPT_X_TLS_NEVER,  # type: ignore
                enums.TlsRequireCert.ALLOW: ldap.OPT_X_TLS_ALLOW,  # type: ignore
                enums.TlsRequireCert.DEMAND: ldap.OPT_X_TLS_DEMAND,  # type: ignore
                enums.TlsRequireCert.HARD: ldap.OPT_X_TLS_HARD,  # type: ignore
            }
            ldaps_tls.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, reqcert_types[req_cert])  # type: ignore
        if tls_cipher_suite:
            ldaps_tls.set_option(ldap.OPT_X_TLS_CIPHER_SUITE, tls_cipher_suite)  # type: ignore

    # start_tls if tls is 'on', 'true' or 'yes' and we're not already using old-SSL
    if port not in ("636", "3269"):
        if tls:
            try:
                directory.set_option(ldap.OPT_X_TLS_NEWCTX, 0)  # type: ignore
                directory.start_tls_s()
            except Exception:
                traceback.print_exc()
                return False
    else:
        ldap.set_option(ldap.OPT_X_TLS_NEWCTX, 0)  # type: ignore

    # if we're not allowed to search anonymously, grok the search bind settings and attempt to bind
    if not api_handle.settings().ldap_anonymous_bind:
        searchdn = api_handle.settings().ldap_search_bind_dn
        searchpw = api_handle.settings().ldap_search_passwd

        if searchdn == "" or searchpw == "":
            raise CX("Missing search bind settings")

        try:
            directory.simple_bind_s(searchdn, searchpw)  # type: ignore
        except Exception:
            traceback.print_exc()
            return False

    # perform a subtree search in basedn to find the full dn of the user
    # TODO: what if username is a CN?  maybe it goes into the config file as well?
    ldap_filter = prefix + username
    result = directory.search_s(basedn, ldap.SCOPE_SUBTREE, ldap_filter, [])  # type: ignore
    if result:
        for ldap_dn, _ in result:  # type: ignore
            # username _should_ be unique so we should only have one result ignore entry; we don't need it
            pass
    else:
        return False

    try:
        # attempt to bind as the user
        directory.simple_bind_s(ldap_dn, password)  # type: ignore
        directory.unbind()
        return True
    except Exception:
        # traceback.print_exc()
        return False
