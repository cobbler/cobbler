"""
Authentication module that defers to Apache and trusts
what Apache trusts.

Copyright 2008-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import distutils.sysconfig
import sys
import os
from utils import _
import traceback

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import cexceptions
import utils

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "authn"

def authenticate(api_handle,username,password):
    """
    Validate a username/password combo, returning True/False
    Uses cobbler_auth_helper
    """

    fd = open("/var/lib/cobbler/web.ss")
    data = fd.read()
    if password == data:
       rc = 1
    else:
       rc = 0
    fd.close()
    return data

