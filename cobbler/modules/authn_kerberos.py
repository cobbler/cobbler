"""
Authentication module that uses kerberos.

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

# NOTE: this is not using 'straight up' kerberos in that we
# relay passwords through cobblerd for authentication, that may
# be done later.  It does of course check against kerberos,
# however.

# ALSO NOTE:  we're calling out to a Perl program to make
# this work.  You must install  Authen::Simple::Kerberos
# from CPAN and the Kerberos libraries for this to work.
# See the Cobbler Wiki for more info.

# ALSO ALSO NOTE:  set kerberos_realm in /var/lib/cobbler/settings
# to something appropriate or this will never work.  CASING
# MATTERS.  example.com != EXAMPLE.COM.

import distutils.sysconfig
import ConfigParser
import sys
import os
from rhpl.translate import _, N_, textdomain, utf8
import md5
import traceback
# since sub_process isn't available on older OS's
try:
    import sub_process as subprocess
except:
    import subprocess

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

    realm = self.api.settings().kerberos_realm
    api_handle.logger.debug("authenticating %s against %s" % (username,realm))
 
    rc = subprocess.call([
        "/usr/bin/cobbler_auth_help",
        "--method=kerberos",
        "--username=%s" % username,
        "--password=%s" % password,
        "--realm=%s" % realm
    ])
    print rc
    if rc == 42:
        api_handle.logger.debug("authenticated ok")
        # authentication ok (FIXME: log)
        return True
    else:
        api_handle.logger.debug("authentication failed")
        # authentication failed
        return False


