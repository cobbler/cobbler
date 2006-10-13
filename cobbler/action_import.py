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

# MATCH_LIST uses path segments of mirror URLs to assign kickstart
# files.  It's not all that intelligent.

# FIXME: add common FC, RHEL, and Centos path segments
MATCH_LIST = ( 
   ( "FC-5/"    , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "FC-6/"    , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "RHEL-4/"  , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "6/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "5/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "Centos/4" , "/etc/cobbler/kickstart_fc5.ks" )
)

class Importer:

   def __init__(self,config,path,mirror,mirror_name):
       # FIXME: consider a basename for the import
       self.config = config
       self.path = path
       self.mirror = mirror
       self.mirror_name = mirror_name
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
       if self.mirror is not None:
           if not self.mirror.startswith("rsync://"):
               raise cexceptions.CobblerException("import_failed","expecting rsync:// url")
           if self.mirror_name is None:
               raise cexceptions.CobblerException("import_failed","must specify --mirror-name")
           # FIXME:  --delete is a little harsh and should be a command
           # line option and not the default (?)
           print "This will take a while..."
           self.path = "/var/www/cobbler/localmirror/%s" % self.mirror_name
           cmd = "rsync -az %s /var/www/cobbler/localmirror/%s --progress" % self.mirror_name
           sub_process.call(cmd,shell=True)
           update_file = os.path.open(os.path.join(self.path,"update.sh"))
           update.file.write("#!/bin/sh")
           update_file.write(cmd)
           update_file.close()
       if self.path is not None:
           arg = None
           os.path.walk(self.path, self.walker, arg)
           self.scrub_orphans()
           self.guess_kickstarts()
           return True
       return False

   def scrub_orphans(self):
       """
       This has nothing to do with parentless children that need baths.
       first: remove any distros with missing kernel or initrd files
       second: remove any profiles that depend on distros that don't exist
       systems will be left as orphans as the MAC info may be useful
       to the sysadmin and may not be recorded elsewhere.  We will report
       the orphaned systems.  
       FIXME: this should also be a seperate API command!
       """
       print "*** SCRUBBING ORPHANS"
       # FIXME
       for distro in self.distros:
           if not os.path.exists(distro.kernel):
               print "*** ORPHANED DISTRO: %s" % distro.name
               self.distros.remove(distro.name)
               continue
           if not os.path.exists(distro.initrd):
               print "*** ORPHANED DISTRO: %s" % distro.name
               self.distros.remove(distro.initrd)
               continue
           print "*** KEEPING: %s" % distro.name
       for profile in self.profiles:
           if not self.distros.find(profile.distro):
               print "*** ORPHANED PROFILE: %s" % profile.name
               self.profiles.remove(profile.name)
               continue
           print "*** KEEPING: %s" % profile.name
       for system in self.systems:
           if not self.profiles.find(system.profile):
               print "*** ORPHANED SYSTEM (NOT DELETED): %s" % system.name
               continue

   def guess_kickstarts(self):
       """
       For all of the profiles in the config w/o a kickstart, look
       at the kernel path, from that, see if we can guess the distro,
       and if we can, assign a kickstart if one is available for it.
       """
       print "*** GUESSING KICKSTARTS"
       for profile in self.profiles:
           distro = self.distros.find(profile.name)
           kpath = distro.kernel
           if not kpath.startswith("/var/www/cobbler"):
               print "*** CAN'T GUESS (kpath): %s" % kpath
               continue 
           for entry in MATCH_LIST:
               (part, kickstart) = entry
               if kpath.find(part) != -1:
                   print "*** CONSIDERING: %s" % kickstart
                   if os.path.exists(kickstart):
                       print "*** ASSIGNING kickstart: %s" % kickstart
                       profile.set_kickstart(kickstart)      
                       # from the kernel path, the tree path is always two up.
                       # FIXME: that's probably not always true
                       base = os.path.basename(kpath)
                       base = os.path.basename(base)
                       base = base.replace("/var/www/cobbler/","")
                       print "%s" % base
                       tree = "tree=http://%s/localmirror/%s/" % (self.settings,server, self.mirror_name, base)
                       print "%s" % tree
                       print "*** ASSIGNING KS META = %s" % tree
                       profile.set_ksmeta(tree)

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
       temp  = "_".join(dirname.split("/"))
       if temp.startswith("_"):
          temp = temp[1:]
       return temp

   def get_pxe_arch(self,dirname):
       t = dirname
       if t.find("x86_64") != -1:
          return "x86_64"
       if t.find("ia64") != -1:
          return "ia64"
       if t.find("i386") != -1 or t.find("386") != -1 or t.find("x86") != -1:
          return "x86"
       return "x86"

   def is_pxe_or_xen_dir(self,dirname):
       if dirname.find("pxe") != -1 or dirname.find("xen") != -1:
           return True
       return False

