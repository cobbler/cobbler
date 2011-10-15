"""
(C) 2009, Red Hat Inc.
Michael DeHaan <mdehaan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""


import distutils.sysconfig
import sys
import os
import traceback
from cobbler.cexceptions import *
import os
import sys
#import xmlrpclib
import cobbler.module_loader as module_loader
import cobbler.utils as utils

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)


def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/change/*"


def run(api,args,logger):

    settings = api.settings()
    scm_track_enabled  = str(settings.scm_track_enabled).lower()
    mode = str(settings.scm_track_mode).lower()

    if scm_track_enabled not in [ "y", "yes", "1", "true" ]:
       # feature disabled
       return 0
   
    if mode == "git":

       old_dir = os.getcwd()
       os.chdir("/var/lib/cobbler")
       if os.getcwd() != "/var/lib/cobbler":
           raise "danger will robinson"

       if not os.path.exists("/var/lib/cobbler/.git"):
           rc = utils.subprocess_call(logger,"git init",shell=True)

       # FIXME: if we know the remote user of an XMLRPC call
       # use them as the author
       rc = utils.subprocess_call(logger,"git add --all config",shell=True)
       rc = utils.subprocess_call(logger,"git add --all kickstarts",shell=True)
       rc = utils.subprocess_call(logger,"git add --all snippets",shell=True)
       rc = utils.subprocess_call(logger,"git commit -m 'API update' --author 'cobbler <root@localhost.localdomain>'",shell=True)

       os.chdir(old_dir)
       return 0

    elif mode == "hg":
        # use mercurial        
        old_dir = os.getcwd()
        os.chdir("/var/lib/cobbler")
        if os.getcwd() != "/var/lib/cobbler":
            raise "danger will robinson"
        
        if not os.path.exists("/var/lib/cobbler/.hg"):
            rc = utils.subprocess_call(logger,"hg init",shell=True)
            
        # FIXME: if we know the remote user of an XMLRPC call
        # use them as the user
        rc = utils.subprocess_call(logger,"hg add config",shell=True)
        rc = utils.subprocess_call(logger,"hg add kickstarts",shell=True)
        rc = utils.subprocess_call(logger,"hg add snippets",shell=True)
        rc = utils.subprocess_call(logger,"hg commit -m 'API update' --user 'cobbler <root@localhost.localdomain>'",shell=True)

        os.chdir(old_dir)
        return 0

    else:
       raise CX("currently unsupported SCM type: %s" % mode)
