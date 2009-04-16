import distutils.sysconfig
import sys
import os
import traceback
from cobbler.cexceptions import *
import os
import sub_process
import sys
#import xmlrpclib
import cobbler.module_loader as module_loader

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/change/*"

def scall(args):
    op = sub_process.Popen(args, shell=False, close_fds=True, stdout=sub_process.PIPE, stderr=sub_process.PIPE)
    op.communicate()
    

def run(api,args):

    
    settings = api.settings()

    scm_track_enabled   = str(settings.scm_track_enabled).lower()
    mode                = str(settings.scm_track_mode).lower()

    if scm_track_enabled not in [ "y", "yes", "1", "true" ]:
       # feature disabled
       return 0
   
    if mode == "git":

       old_dir = os.getcwd()
       os.chdir("/var/lib/cobbler")
       if os.getcwd() != "/var/lib/cobbler":
           raise "danger will robinson"

       if not os.path.exists("/var/lib/cobbler/.git"):
           scall(["git","init"])

       # FIXME: if we know the remote user of an XMLRPC call
       # use them as the author

       scall(["git","add","config"])
       scall(["git","add","kickstarts"])
       scall(["git","add","snippets"])

       scall(["git","commit","-m",'API update',"--author","'cobbler <root@localhost.localdomain>'"])

       os.chdir(old_dir)

       return 0

    else:
       raise CX("currently unsupported SCM type: %s" % mode)
