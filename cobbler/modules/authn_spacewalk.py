"""
Authentication module that uses Spacewalk's auth system.
Any org_admin or kickstart_admin can get in.

Copyright 2007-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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

import distutils.sysconfig
import sys
import xmlrpclib

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "authn"

def authenticate(api_handle,username,password):
    """
    Validate a username/password combo, returning True/False
    
    This will pass the username and password back to Spacewalk
    to see if this authentication request is valid.
    """

    spacewalk_url = api_handle.settings().spacewalk_url  

    client = xmlrpclib.Server(spacewalk_url, verbose=0)

    valid = client.auth.checkAuthToken(username,password)
    
    if valid is None:
        return False
    
    return (valid == 1)
        


