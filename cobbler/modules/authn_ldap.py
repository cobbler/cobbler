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
import sys
import os
from utils import _
import md5
import traceback
import ldap

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import cexceptions
import utils
import api as cobbler_api

def register():
    """
    The mandatory cobbler module registration hook.
    """

    return "authn"

def authenticate(api_handle,username,password):
    """
    Validate an ldap bind, returning True/False
    """

    server    = api_handle.settings().ldap_server
    basedn    = api_handle.settings().ldap_base_dn
    port      = api_handle.settings().ldap_port
    tls       = api_handle.settings().ldap_tls
    anon_bind = api_handle.settings().ldap_anonymous_bind
    prefix    = api_handle.settings().ldap_search_prefix

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

    # if we're not allowed to search anonymously,
    # grok the search bind settings and attempt to bind
    anon_bind = str(anon_bind).lower()
    if anon_bind not in [ "on", "true", "yes", "1" ]:
        searchdn = api_handle.settings().ldap_search_bind_dn
        searchpw = api_handle.settings().ldap_search_passwd

        if searchdn == '' or searchpw == '':
            raise "Missing search bind settings"

        try:
            dir.simple_bind_s(searchdn, searchpw)
        except:
            traceback.print_exc()
            return False

    # perform a subtree search in basedn to find the full dn of the user
    # TODO: what if username is a CN?  maybe it goes into the config file as well?
    filter = prefix + username
    result = dir.search_s(basedn, ldap.SCOPE_SUBTREE, filter, [])
    if result:
        for dn,entry in result:
            # username _should_ be unique so we should only have one result
            # ignore entry; we don't need it
            pass
    else:
        return False

    try:
        # attempt to bind as the user
        dir.simple_bind_s(dn,password)
        dir.unbind()
        return True
    except:
        # traceback.print_exc()
        return False
    # catch-all
    return False

if __name__ == "__main__":
    api_handle = cobbler_api.BootAPI()
    print authenticate(api_handle, "guest", "guest")

