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
import sub_process

import api

# MATCH_LIST uses path segments of mirror URLs to assign kickstart
# files.  It's not all that intelligent.

# FIXME: add common FC, RHEL, and Centos path segments
# it's exceedingly wrong right now and the kickstart file
# for FC5 is sent everywhere.  That probably WON'T work in most
# places even though it's a minimalistic kickstart.  This will
# get patched over time.
MATCH_LIST = (
   ( "1/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "2/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "3/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "4/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "5/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "FC-5/"    , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "FC-6/"    , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "RHEL-4/"  , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "6/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "5/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "Centos/4" , "/etc/cobbler/kickstart_fc5.ks" )
)

class Importer:

   def __init__(self,api,config,path,mirror,mirror_name):
       self.api = api
       self.config = config
       self.path = path
       self.mirror = mirror
       self.mirror_name = mirror_name
       self.distros  = config.distros()
       self.profiles = config.profiles()
       self.systems  = config.systems()
       self.settings = config.settings()

   def run(self):
       if self.path is None and self.mirror is None:
           raise cexceptions.CobblerException("import_failed","no path specified")
       if self.path and not os.path.isdir(self.path):
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
           try:
               os.mkdir(self.path)
           except:
               if not os.path.exists(self.path):
                   raise cexceptions.CobblerException("couldn't create: %s" % (self.path))
           cmd = "rsync -az %s /var/www/cobbler/localmirror/%s --progress" % (self.mirror, self.mirror_name)
           sub_process.call(cmd,shell=True)
           update_file = open(os.path.join(self.path,"update.sh"),"w+")
           update_file.write("#!/bin/sh")
           update_file.write("%s\n" % cmd)
           # leave this commented out in the file because it will
           # erase user customizations.
           update_file.write("#cobbler import --path=%s" % self.path)
           update_file.close()
       if self.path is not None:
           arg = None
           os.path.walk(self.path, self.walker, arg)
           self.scrub_orphans()
           self.guess_kickstarts()
           return True
       raise cexceptions.CobblerException("path not specified")

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
           remove = False
           if not os.path.exists(distro.kernel):
               print "*** ORPHANED DISTRO: %s" % distro.name
               remove = True
           if not os.path.exists(distro.initrd):
               print "*** ORPHANED DISTRO: %s" % distro.name
               remove = True
           if not remove:
               continue
           # cascade removal
           for profile in self.profiles:
               if profile.distro == distro.name:
                   # cascade removal of systems
                   for system in self.systems:
                       if system.profile == profile.name:
                           print "SYSTEM REMOVED: %s" % system.name
                           self.systems.remove(system.name)
                   print "PROFILE REMOVED: %s" % profile.name
                   self.profiles.remove(profile.name)
           print "DISTRO REMOVED: %s" % distro.name
           self.distros.remove(distro.name)

   def guess_kickstarts(self):
       """
       For all of the profiles in the config w/o a kickstart, look
       at the kernel path, from that, see if we can guess the distro,
       and if we can, assign a kickstart if one is available for it.
       """
       for profile in self.profiles:
           distro = self.distros.find(profile.name)
           kpath = distro.kernel
           if not kpath.startswith("/var/www/cobbler/localmirror/"):
               continue
           for entry in MATCH_LIST:
               (part, kickstart) = entry
               if kpath.find(part) != -1:
                   if os.path.exists(kickstart):
                       print "*** ASSIGNING kickstart: %s" % kickstart
                       profile.set_kickstart(kickstart)
                       # from the kernel path, the tree path is always two up.
                       # FIXME: that's probably not always true
                       dirname = os.path.dirname(kpath)
                       print "dirname = %s" % dirname
                       tokens = dirname.split("/")
                       print "tokens = %s" % tokens
                       tokens = tokens[:-2]
                       base = "/".join(tokens)
                       print "base=%s" % base
                       base = base.replace("/var/www/cobbler/","")
                       #firstpart = base.split("/")[0] # mirror_name
                       print "base2=%s" % base
                       print "%s" % base
                       tree = "tree=http://%s/%s" % (self.settings.server, base)
                       print "%s" % tree
                       print "*** ASSIGNING KICKSTART TREE = %s" % tree
                       profile.set_ksmeta(tree)
                       self.api.serialize()

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
           self.api.serialize()

   def get_proposed_name(self,dirname):
       # for now, just use the path to the images directory as the
       # name or the profile.  This provides the added bonus of letting
       # the shell interpolate it.
       return dirname

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

