"""
Authentication module that uses ldap
Settings in /etc/cobbler/authn_ldap.conf
Choice of authentication module is in /etc/cobbler/modules.conf

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import distutils.sysconfig
#import ConfigParser
import sys
import os
from rhpl.translate import _, N_, textdomain, utf8
import md5
import traceback
import ldap
import traceback

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import cexceptions
import utils
import api as cobbler_api

#CONFIG_FILE='/etc/cobbler/auth_ldap.conf'

def register():
    """
    The mandatory cobbler module registration hook.
    """

    return "authn"

def authenticate(api_handle,username,password):
    """
    Validate an ldap bind, returning True/False
    """
    
    server = api_handle.settings().ldap_server
    basedn = api_handle.settings().ldap_base_dn
    port   = api_handle.settings().ldap_port
    tls    = api_handle.settings().ldap_tls

    # parse CONFIG_FILE
    # server,basedn,port,tls = __parse_config()

    # form our ldap uri based on connection port
    if port == '389':
        uri = 'ldap://' + server
    elif port == '636':
        uri = 'ldaps://' + server
    else:
        uri = 'ldap://' + "%s:%s" % (server,port)

    # connect to LDAP host
    dir = ldap.initialize(uri)

    # start_tls if tls is 'on', 'true' or 'yes'
    # and we're not already using old-SSL
    tls = str(tls).lower()
    if port != '636':
        if tls in [ "on", "true", "yes", "1" ]:
            try:
                dir.start_tls_s()
            except:
                traceback.print_exc()
                return False

    # perform a subtree search in basedn to find the full dn of the user
    # TODO: what if username is a CN?  maybe it goes into the config file as well?
    filter = "uid=" + username
    result = dir.search_s(basedn, ldap.SCOPE_SUBTREE, filter, [])
    if result:
        for dn,entry in result:
            # uid should be unique so we should only have one result
            # ignore entry; we don't need it
            pass
    else:
        print "FAIL 2"
        return False

    try:
        # attempt to bind as the user
        dir.simple_bind_s(dn,password)
        dir.unbind()
        print "FAIL 1"
        return True
    except:
        traceback.print_exc()
        return False
    # catch-all
    return False

if __name__ == "__main__":
    api_handle = cobbler_api.BootAPI()
    # print authenticate(api_handle, "mdehaan", "test1")
    print authenticate(api_handle, "mdehaan", "dog8code")

