"""
Authentication module that uses /etc/cobbler/auth.conf
Choice of authentication module is in /etc/cobbler/modules.conf

Copyright 2007-2009, Red Hat, Inc and Others
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

PAM python code based on the pam_python code created by Chris AtLee:
http://atlee.ca/software/pam/

#-----------------------------------------------
pam_python (c) 2007 Chris AtLee <chris@atlee.ca>
Licensed under the MIT license:
http://www.opensource.org/licenses/mit-license.php

PAM module for python

Provides an authenticate function that will allow the caller to authenticate
a user against the Pluggable Authentication Modules (PAM) on the system.

Implemented using ctypes, so no compilation is necessary.
"""

from ctypes import CDLL, POINTER, Structure, CFUNCTYPE, cast, pointer, sizeof
from ctypes import c_void_p, c_uint, c_char_p, c_char, c_int
from ctypes.util import find_library

LIBPAM = CDLL(find_library("pam"))
LIBC = CDLL(find_library("c"))

CALLOC = LIBC.calloc
CALLOC.restype = c_void_p
CALLOC.argtypes = [c_uint, c_uint]

STRDUP = LIBC.strdup
STRDUP.argstypes = [c_char_p]
STRDUP.restype = POINTER(c_char)        # NOT c_char_p !!!!

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
        return "<PamMessage %i '%s'>" % (self.msg_style, self.msg)


class PamResponse(Structure):
    """
    wrapper class for pam_response structure
    """
    _fields_ = [("resp", c_char_p), ("resp_retcode", c_int)]

    def __repr__(self):
        return "<PamResponse %i '%s'>" % (self.resp_retcode, self.resp)


CONV_FUNC = CFUNCTYPE(c_int, c_int, POINTER(POINTER(PamMessage)), POINTER(POINTER(PamResponse)), c_void_p)


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


def authenticate(api_handle, username: str, password: str) -> bool:
    """
    Validate PAM authentication, returning whether the authentication was successful or not.

    :param api_handle: Used for resolving the the pam service name and getting the Logger.
    :param username: The username to log in with.
    :param password: The password to log in with.
    :returns: True if the given username and password authenticate for the given service. Otherwise False
    """

    @CONV_FUNC
    def my_conv(n_messages, messages, p_response, app_data):
        """
        Simple conversation function that responds to any prompt where the echo is off with the supplied password
        """
        # Create an array of n_messages response objects
        addr = CALLOC(n_messages, sizeof(PamResponse))
        p_response[0] = cast(addr, POINTER(PamResponse))
        for i in range(n_messages):
            if messages[i].contents.msg_style == PAM_PROMPT_ECHO_OFF:
                pw_copy = STRDUP(password.encode())
                p_response.contents[i].resp = cast(pw_copy, c_char_p)
                p_response.contents[i].resp_retcode = 0
        return 0

    try:
        service = api_handle.settings().authn_pam_service
    except:
        service = 'login'

    api_handle.logger.debug("authn_pam: PAM service is %s" % service)

    handle = PamHandle()
    conv = PamConv(my_conv, 0)
    retval = PAM_START(service.encode(), username.encode(), pointer(conv), pointer(handle))

    if retval != 0:
        # TODO: This is not an authentication error, something has gone wrong starting up PAM
        api_handle.logger.error("authn_pam: error initializing PAM library")
        return False

    retval = PAM_AUTHENTICATE(handle, 0)

    if retval == 0:
        retval = PAM_ACCT_MGMT(handle, 0)

    return retval == 0
