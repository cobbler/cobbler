"""
Authentication module that defers to Apache and trusts
what Apache trusts.

Copyright 2008-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA.
"""

import distutils.sysconfig
import sys

from cobbler import utils

plib = distutils.sysconfig.get_python_lib()
mod_path = "%s/cobbler" % plib
sys.path.insert(0, mod_path)


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "authn"


def authenticate(api_handle, username, password):
    """
    Validate a username/password combo, returning True/False
    Uses cobbler_auth_helper
    """
    ss = utils.get_shared_secret()
    if password == ss:
        rc = True
    else:
        rc = False
    return rc
