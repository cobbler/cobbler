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

import api

class Importer:

   def __init__(self,config,path,mirror):
       # FIXME: consider a basename for the import
       self.config = config
       self.path = path
       self.mirror = mirror
       if path is None:
           raise cexceptions.CobblerException("import_failed","no path specified")
       self.distros = config.distros()
       self.profiles = config.profiles()
       self.systems = config.systems()

   def run(self):
       if self.path is None and self.mirror is None:
           raise cexceptions.CobblerException("import_failed","no path specified")
       if not os.path.isdir(self.path):
           raise cexceptions.CobblerException("import_failed","bad path")
       if self.path is not None:
           arg = None
           os.path.walk(self.path, self.walker, arg)
           return True
       return False

   def walker(self,arg,dirname,fnames):
       # FIXME: requires getting an arch out of the path
       # FIXME: requires making sure the path contains "pxe" somewhere
       print "dirname: %s" % dirname
       initrd = None
       kernel = None
       if not self.is_pxe_or_xen_dir(dirname):
           return
       for x in fnames:
           if x.startswith("initrd"):
               initrd = os.path.join(dirname,x)
           if x.startswith("vmlinuz"):
               kernel = os.path.join(dirname,x)
           if initrd is not None and kernel is not None:
               self.add_entry(dirname,kernel,initrd)

   def add_entry(self,dirname,kernel,initrd):
       pxe_arch = self.get_pxe_arch(dirname)
       name = self.get_proposed_name(dirname)
       if self.distros.find(name) is not None:
           print "already registered: %s" % name
       else:
           distro = self.config.new_distro()
           distro.set_name(name)
           distro.set_kernel(kernel)
           distro.set_initrd(initrd)
           distro.set_arch(pxe_arch)
           self.distros.add(distro)
           print "*** DISTRO ADDED ***"
           if self.profiles.find(name) is not None:
               print "already registered: %s" % name
           else:
               profile = self.config.new_profile()
               profile.set_name(name)
               profile.set_distro(name)
               self.profiles.add(profile)
               print "*** PROFILE ADDED ***"

   def get_proposed_name(self,dirname):
       # FIXME: how can this name be nicer?
       str = "_".join(dirname.split("/"))
       if str.startswith("_"):
          return str[1:]
       return str

   def get_pxe_arch(self,dirname):
       tokens = os.path.split(dirname)
       tokens = [x.lower() for x in tokens]
       for t in tokens:
          if t == "i386" or t == "386" or t == "x86":
              return "x86"
          if t == "x86_64":
              return "x86_64"
          if t == "ia64":
              return "ia64"
       return "x86"

   def is_pxe_or_xen_dir(self,dirname):
       tokens = os.path.split(dirname)
       for x in tokens:
           if x.lower() == "pxe" or x.lower() == "pxeboot" or x.lower() == "xen":
               return True
       return False
