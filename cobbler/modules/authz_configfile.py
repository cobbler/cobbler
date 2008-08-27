"""
Authorization module that allow users listed in
/etc/cobbler/users.conf to be permitted to access resources.
For instance, when using authz_ldap, you want to use authn_configfile,
not authz_allowall, which will most likely NOT do what you want.

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
from utils import _

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import cexceptions
import utils

CONFIG_FILE='/etc/cobbler/users.conf'

def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "authz"

def __parse_config():
    if not os.path.exists(CONFIG_FILE):
        return []
    config = ConfigParser.SafeConfigParser()
    config.read(CONFIG_FILE)
    alldata = {}
    groups = config.sections()
    for g in groups:
       alldata[str(g)] = {}
       opts = config.options(g)
       for o in opts:
           alldata[g][o] = 1
    return alldata 


def authorize(api_handle,user,resource,arg1=None,arg2=None):
    """
    Validate a user against a resource.
    All users in the file are permitted by this module.
    """

    # FIXME: this must be modified to use the new ACL engine

    data = __parse_config()
    for g in data:
        if user in data[g]:
           return 1
    return 0

if __name__ == "__main__":
    print __parse_config()
