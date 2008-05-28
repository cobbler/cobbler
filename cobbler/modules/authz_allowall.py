"""
Authorization module that allows everything, which is the default
for new cobbler installs.

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import distutils.sysconfig
import ConfigParser
import sys
from utils import _

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import cexceptions
import utils


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "authz"

def authorize(api_handle,user,resource,arg1=None,arg2=None):
    """
    Validate a user against a resource.
    """
    return True


