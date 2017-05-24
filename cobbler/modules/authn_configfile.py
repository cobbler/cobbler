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
"""

import os

from cobbler.utils import md5


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "authn"


def __parse_storage():

    if not os.path.exists("/etc/cobbler/users.digest"):
        return []
    fd = open("/etc/cobbler/users.digest")
    data = fd.read()
    fd.close()
    results = []
    lines = data.split("\n")
    for line in lines:
        try:
            line = line.strip()
            tokens = line.split(":")
            results.append([tokens[0], tokens[1], tokens[2]])
        except:
            pass
    return results


def authenticate(api_handle, username, password):
    """
    Validate a username/password combo, returning True/False

    Thanks to http://trac.edgewall.org/ticket/845 for supplying
    the algorithm info.
    """
    # debugging only (not safe to enable)
    # api_handle.logger.debug("backend authenticate (%s,%s)" % (username,password))

    userlist = __parse_storage()
    for (user, realm, actual_blob) in userlist:
        if user == username and realm == "Cobbler":
            input = ":".join([user, realm, password])
            input_blob = md5(input).hexdigest()
            if input_blob.lower() == actual_blob.lower():
                return True

    return False
