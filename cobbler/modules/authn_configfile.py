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
from rhpl.translate import _, N_, textdomain, utf8

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

def authenticate(username,password):
    """
    Validate a username/password combo, returning True/False
    """

    config_parser = ConfigParser.ConfigParser()
    auth_conf = open("/etc/cobbler/auth.conf")
    config_parser.readfp(auth_conf)
    auth_conf.close()
    user_database = config_parser.items("xmlrpc_service_users")
    for x in user_database:
        (db_user,db_password) = x
        db_user     = db_user.strip()
        db_password = db_password.strip()
        if db_user == username and db_password == password and db_password.lower() != "disabled":
            return True
    return False


