"""
Authentication module that uses Spacewalk's auth system.
Any org_admin or kickstart_admin can get in.

Copyright 2007-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
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

    Thanks to http://trac.edgewall.org/ticket/845 for supplying
    the algorithm info.
    """

    spacewalk_url = api_handle.settings().spacewalk_url  

    client = xmlrpclib.Server(spacewalk_url, verbose=0)

    key = client.auth.login(username,password)
    if key is None:
        return False

    # NOTE: this is technically a little bit of authz, but
    # not enough to warrant a seperate module yet.
    list = client.user.list_roles(key, username)
    success = False
    for role in list:
       if role == "org_admin" or "kickstart_admin":
           success = True

    try:
        client.auth.logout(key)
    except:
        # workaround for https://bugzilla.redhat.com/show_bug.cgi?id=454474
        # which is a Java exception from Spacewalk
        pass
    return success


