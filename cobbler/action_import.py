"""
Enables the "cobbler distro import" command to seed cobbler
information with available distributions.  A minimal (kickstartless)
profile will also be created with the same name as the distro.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import cexceptions
import os
import os.path
import traceback

class Importer:

   def __init__(self,config,path):
       # FIXME: consider a basename for the import
       self.config = config
       self.path = path
       if path is None:
           raise cexceptions.CobblerException("import_failed","no path specified")
       self.distros = config.distros()
       self.profiles = config.profiles()
       self.systems = config.systems()

   def run(self):
       if not os.path.isdir(self.path):
           raise cexceptions.CobblerException("import_failed","bad path")
       arg = None
       os.path.walk(self.path, self.walker, arg)
       return True

   def walker(self,arg,dirname,fnames):
       # FIXME: requires getting an arch out of the path
       # FIXME: requires making sure the path contains "pxe" somewhere
       print "dirname: %s" % dirname
       if self.is_leaf(dirname,fnames):
           print "is_leaf"
           initrd = None
           kernel = None
           for x in fnames:
               if x.startswith("initrd"):
                   initrd = os.path.join(dirname,x)
               if x.startswith("vmlinuz"):
                   kernel = os.path.join(dirname,x)
               if initrd is not None and kernel is not None:
                   print "kernel: %s" % kernel
                   print "initrd: %s" % initrd
                   self.consider(dirname,kernel,initrd)

   def consider(self,dirname,kernel,initrd):
       if not self.is_pxe_dir(dirname):
           return
       pxe_arch = self.get_pxe_arch(dirname)
       name = self.get_proposed_name(dirname)
       if self.distros.find(name) is not None:
           print "already registered: %s" % name
       else:
           print "adding: %s" % name
           # FIXME
           if self.profiles.find(name) is not None:
               print "already registered: %s" % name
           else:
               print "adding: %s" % name
               # FIXME
 
   def get_proposed_name(self,dirname):
       # FIXME
       str = "_".join(dirname.split("/"))
       if str.startswith("_"):
          return str[1:-1]
       return str

   def get_pxe_arch(self,dirname):
       # FIXME
       return "x86"

   def is_pxe_dir(self,dirname):
       tokens = os.path.split(dirname)
       for x in tokens:
           if x.lower() == "pxe" or x.lower() == "pxeboot":
               return True
       print "not a pxe directory: %s" % dirname
       return False

   def is_leaf(self,dirname,fnames):
       for x in fnames:
          if os.path.isdir(x):
              print "not a leaf directory: %s" % dirname
              return False
       return True
 

