"""
Authentication module that uses /etc/cobbler/auth.conf
Choice of authentication module is in /etc/cobbler/modules.conf


PAM python code based on the pam_python code created by Chris AtLee:
https://atlee.ca/software/pam/

#-----------------------------------------------
pam_python (c) 2007 Chris AtLee <chris@atlee.ca>
Licensed under the MIT license:
https://www.opensource.org/licenses/mit-license.php

PAM module for python

Provides an authenticate function that will allow the caller to authenticate
a user against the Pluggable Authentication Modules (PAM) on the system.

Implemented using ctypes, so no compilation is necessary.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# FIXME: Move to the dedicated library python-pam


from ctypes import (
    CDLL,
    CFUNCTYPE,
    POINTER,
    Structure,
    c_char,
    c_char_p,
    c_int,
    c_uint,
    c_void_p,
    cast,
    pointer,
    sizeof,
)
from ctypes.util import find_library
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


LIBPAM = CDLL(find_library("pam"))
LIBC = CDLL(find_library("c"))

CALLOC = LIBC.calloc
CALLOC.restype = c_void_p
CALLOC.argtypes = [c_uint, c_uint]

STRDUP = LIBC.strdup
STRDUP.argstypes = [c_char_p]  # type: ignore
STRDUP.restype = POINTER(c_char)  # NOT c_char_p !!!!

# Various constants
PAM_PROMPT_ECHO_OFF = 1
PAM_PROMPT_ECHO_ON = 2
PAM_ERROR_MSG = 3
PAM_TEXT_INFO = 4


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "authn"


class PamHandle(Structure):
    """
    wrapper class for pam_handle_t
    """

    _fields_ = [("handle", c_void_p)]

    def __init__(self):
        Structure.__init__(self)
        self.handle = 0


class PamMessage(Structure):
    """
    wrapper class for pam_message structure
    """

    _fields_ = [("msg_style", c_int), ("msg", c_char_p)]

    def __repr__(self):
        return f"<PamMessage {self.msg_style:d} '{self.msg}'>"


class PamResponse(Structure):
    """
    wrapper class for pam_response structure
    """

    _fields_ = [("resp", c_char_p), ("resp_retcode", c_int)]

    def __repr__(self):
        return f"<PamResponse {self.resp_retcode:d} '{self.resp}'>"


CONV_FUNC = CFUNCTYPE(
    c_int, c_int, POINTER(POINTER(PamMessage)), POINTER(POINTER(PamResponse)), c_void_p
)


class PamConv(Structure):
    """
    wrapper class for pam_conv structure
    """

    _fields_ = [("conv", CONV_FUNC), ("appdata_ptr", c_void_p)]


PAM_START = LIBPAM.pam_start
PAM_START.restype = c_int
PAM_START.argtypes = [c_char_p, c_char_p, POINTER(PamConv), POINTER(PamHandle)]

PAM_AUTHENTICATE = LIBPAM.pam_authenticate
PAM_AUTHENTICATE.restype = c_int
PAM_AUTHENTICATE.argtypes = [PamHandle, c_int]

PAM_ACCT_MGMT = LIBPAM.pam_acct_mgmt
PAM_ACCT_MGMT.restype = c_int
PAM_ACCT_MGMT.argtypes = [PamHandle, c_int]


def authenticate(api_handle: "CobblerAPI", username: str, password: str) -> bool:
    """
    Validate PAM authentication, returning whether the authentication was successful or not.

    :param api_handle: Used for resolving the pam service name and getting the Logger.
    :param username: The username to log in with.
    :param password: The password to log in with.
    :returns: True if the given username and password authenticate for the given service. Otherwise False
    """

    @CONV_FUNC
    def my_conv(n_messages, messages, p_response, app_data):  # type: ignore
        """
        Simple conversation function that responds to any prompt where the echo is off with the supplied password
        """
        # Create an array of n_messages response objects
        addr = CALLOC(n_messages, sizeof(PamResponse))
        p_response[0] = cast(addr, POINTER(PamResponse))
        for i in range(n_messages):  # type: ignore
            if messages[i].contents.msg_style == PAM_PROMPT_ECHO_OFF:  # type: ignore
                pw_copy = STRDUP(password.encode())
                p_response.contents[i].resp = cast(pw_copy, c_char_p)  # type: ignore
                p_response.contents[i].resp_retcode = 0  # type: ignore
        return 0

    try:
        service = api_handle.settings().authn_pam_service
    except Exception:
        service = "login"

    api_handle.logger.debug(f"authn_pam: PAM service is {service}")

    handle = PamHandle()
    conv = PamConv(my_conv, 0)
    retval = PAM_START(
        service.encode(), username.encode(), pointer(conv), pointer(handle)
    )

    if retval != 0:
        # TODO: This is not an authentication error, something has gone wrong starting up PAM
        api_handle.logger.error("authn_pam: error initializing PAM library")
        return False

    retval = PAM_AUTHENTICATE(handle, 0)

    if retval == 0:
        retval = PAM_ACCT_MGMT(handle, 0)

    return retval == 0
