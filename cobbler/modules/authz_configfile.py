"""
Authorization module that allow users listed in
the auth_ldap.conf config file

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import distutils.sysconfig
import ConfigParser
import sys
import os
from rhpl.translate import _, N_, textdomain, utf8

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import cexceptions
import utils

CONFIG_FILE='/etc/cobbler/auth_ldap.conf'

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "authz"

def authorize(api_handle,user,resource,arg1=None,arg2=None):
    """
    Validate a user against a resource.
    """

    # FIXME: implement this, only users in /etc/cobbler/users.conf
    # will return 1.  Later we'll do authz_ownership.py

    return 0
