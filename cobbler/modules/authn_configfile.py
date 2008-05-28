"""
Authentication module that uses /etc/cobbler/auth.conf
Choice of authentication module is in /etc/cobbler/modules.conf

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
import os
from utils import _
import md5
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
            results.append([tokens[0],tokens[1],tokens[2]])
        except:
            pass
    return results

def authenticate(api_handle,username,password):
    """
    Validate a username/password combo, returning True/False

    Thanks to http://trac.edgewall.org/ticket/845 for supplying
    the algorithm info.
    """
  
    # debugging only (not safe to enable)
    # api_handle.logger.debug("backend authenticate (%s,%s)" % (username,password))

    userlist = __parse_storage()
    for (user,realm,actual_blob) in userlist:
        if user == username and realm == "Cobbler":
            input = ":".join([user,realm,password])
            input_blob = md5.md5(input).hexdigest()
            if input_blob.lower() == actual_blob.lower():
                return True

    return False


