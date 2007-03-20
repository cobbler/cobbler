"""
Enables the "cobbler import" command to seed cobbler
information with available distribution from rsync mirrors
and mounted DVDs.  

Copyright 2006-2007, Red Hat, Inc
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
import glob

import api

WGET_CMD = "wget --mirror --no-parent --no-host-directories --directory-prefix %s/%s %s"
RSYNC_CMD =  "rsync -a %s %s %s/ks_mirror/%s --exclude-from=/etc/cobbler/rsync.exclude --delete --delete-excluded --progress"

TRY_LIST = [
   "Fedora", "RedHat", "Client", "Server", "Centos",
   "Fedora/RPMS", "RedHat/RPMS", "Client/RPMS", "Server/RPMS", "Centos/RPMS",
   "RPMS"
]

class Importer:

   def __init__(self,api,config,mirror,mirror_name):
       self.api = api
       self.config = config
       self.mirror = mirror
       self.mirror_name = mirror_name
       self.distros  = config.distros()
       self.profiles = config.profiles()
       self.systems  = config.systems()
       self.settings = config.settings()

   # ----------------------------------------------------------------------

   def run(self):
       if self.mirror is None:
           raise cexceptions.CobblerException("import_failed","no mirror specified")
       if self.mirror_name is None:
           raise cexceptions.CobblerException("import_failed","no mirror-name specified")

       if self.mirror_name is None:
           raise cexceptions.CobblerException("import_failed","must specify --mirror-name")
       
       # make the output path
       self.path = "%s/ks_mirror/%s" % (self.settings.webdir, self.mirror_name)
       self.mkdir(self.path)

       # prevent rsync from creating the directory name twice
       if not self.mirror.endswith("/"):
           self.mirror = "%s/" % self.mirror 

       if self.mirror.startswith("http://"):
           # http mirrors are kind of primative.  rsync is better.
           self.run_this(WGET_CMD, (self.settings.webdir, self.mirror_name, self.mirror))
       else:
           # use rsync.. no SSH for public mirrors and local files.
           # presence of user@host syntax means use SSH
           spacer = ""
           if not self.mirror.startswith("rsync://") and not self.mirror.startswith("/"):
               spacer = ' -e "ssh" '
           self.run_this(RSYNC_CMD, (spacer, self.mirror, self.settings.webdir, self.mirror_name))


       self.processed_repos = {}

       os.path.walk(self.path, self.walker, None)

       self.guess_kickstarts()
       return True

   # ----------------------------------------------------------------------

   def mkdir(self, dir):
       try:
           os.makedirs(dir)
       except:
           print "- didn't create %s" % dir

   # ----------------------------------------------------------------------

   def run_this(self, cmd, args):
       my_cmd = cmd % args
       print "- %s" % my_cmd
       rc = sub_process.call(my_cmd,shell=True)
       if rc != 0:
          raise cexceptions.CobblerException("Command failed.")

   # ----------------------------------------------------------------------

   def guess_kickstarts(self):

       """
       For all of the profiles in the config w/o a kickstart, look
       at the kernel path, from that, see if we can guess the distro,
       and if we can, assign a kickstart if one is available for it.
       """

       for profile in self.profiles:
           distro = self.distros.find(profile.distro)
           if distro is None:
               raise cexceptions.CobblerException("orphan_distro2",profile.name,profile.distro)
           if not distro.kernel.startswith("%s/ks_mirror/" % self.settings.webdir):
               # this isn't a mirrored profile, so we won't touch it
               print "- skipping %s since profile isn't mirrored" % profile.name
               continue
           if distro.ks_meta.has_key("tree") or profile.ks_meta.has_key("tree"):
               # this distro has already been imported, do not proceed
               print "- skipping %s since existing tree attributes were found" % profile.name
               continue
 
           kdir = os.path.dirname(distro.kernel)   
           base_dir = "/".join(kdir.split("/")[0:-2])
      
           for try_entry in TRY_LIST:
               for dnames in [ "fedora", "centos", "redhat" ]:
                   try_dir = os.path.join(base_dir, try_entry)
                   if os.path.exists(try_dir):
                       rpms = glob.glob(os.path.join(try_dir, "*release-*"))
                       for rpm in rpms:
                           if rpm.find("notes") != -1:
                               continue
                           results = self.scan_rpm_filename(rpm)
                           if results is None:
                               continue
                           (flavor, major, minor) = results
                           print "- determining best kickstart for %s %s.%s" % (flavor, major, minor)          
                           kickstart = self.set_kickstart(profile, flavor, major, minor)
                           print "- kickstart=%s" % kickstart
                           self.configure_tree_location(distro)
                           self.distros.add(distro) # re-save
                           self.api.serialize()

   # --------------------------------------------------------------------

   def configure_tree_location(self, distro):
       # find the tree location
       dirname = os.path.dirname(distro.kernel)
       tokens = dirname.split("/")
       tokens = tokens[:-2]
       base = "/".join(tokens)
       dest_link = os.path.join(self.settings.webdir, "links", distro.name)
       if not os.path.exists(dest_link):
           os.symlink(base, dest_link)
       base = base.replace(self.settings.webdir,"")
       tree = "tree=http://%s/cblr/links/%s" % (self.settings.server, distro.name)
       print "- %s" % tree
       distro.set_ksmeta(tree)

   # ---------------------------------------------------------------------

   def set_kickstart(self, profile, flavor, major, minor):
       if flavor == "fedora":
           if major >= 6:
                return profile.set_kickstart("/etc/cobbler/kickstart_fc6.ks")
       if flavor == "redhat" or flavor == "centos":
           if major >= 5:
                return profile.set_kickstart("/etc/cobbler/kickstart_fc6.ks")
       print "- using default kickstart file choice"
       return profile.set_kickstart("/etc/cobbler/kickstart_fc5.ks")

   # ---------------------------------------------------------------------

   def scan_rpm_filename(self, rpm):
       rpm = os.path.basename(rpm)
       (first, rest) = rpm.split("-release-")
       flavor = first.lower()
       (major, rest) = rest.split("-",1)
       (minor, rest) = rest.split(".",1)
       major = int(major)
       minor = int(minor)
       return (flavor, major, minor)

   # ----------------------------------------------------------------------

   def walker(self,foo,dirname,fnames):
       
       initrd = None
       kernel = None
       if not self.is_relevant_dir(dirname):
           return

       for x in fnames:
           if x.startswith("initrd"):
               initrd = os.path.join(dirname,x)
           if x.startswith("vmlinuz"):
               kernel = os.path.join(dirname,x)
           if initrd is not None and kernel is not None:
               self.last_distro = self.add_entry(dirname,kernel,initrd)
               path_parts = kernel.split("/")[:-3]
               comps_path = "/".join(path_parts)
               print "- running repo update on %s" % comps_path
               self.process_comps_file(comps_path)
   # ----------------------------------------------------------------------
               

   def process_comps_file(self, comps_path):


       comps_file = os.path.join(comps_path, "repodata", "comps.xml")
       if not os.path.exists(comps_file):
           print "- no comps file found: %s" % comps_file
           return
       try:
           # don't run creatrepo twice -- this can happen easily for Xen and PXE, when
           # they'll share same repo files.
           if not self.processed_repos.has_key(comps_path):
               cmd = "createrepo --basedir / --groupfile %s %s" % (comps_file, comps_path)
               print "- %s" % cmd
               sub_process.call(cmd,shell=True)
               self.processed_repos[comps_path] = 1
       except:
           print "- error launching createrepo, ignoring..."
           traceback.print_exc()
        

   def add_entry(self,dirname,kernel,initrd):
       pxe_arch = self.get_pxe_arch(dirname)
       name = self.get_proposed_name(dirname)

       existing_distro = self.distros.find(name)

       if existing_distro is not None:
           print "- modifying existing distro: %s" % name
           distro = existing_distro
       else:
           print "- creating new distro: %s" % name
           distro = self.config.new_distro()
           
       distro.set_name(name)
       distro.set_kernel(kernel)
       distro.set_initrd(initrd)
       distro.set_arch(pxe_arch)
       self.distros.add(distro)
       
       existing_profile = self.profiles.find(name) 

       if existing_profile is None:
           print "- creating new profile: %s" % name 
           profile = self.config.new_profile()
       else:
           print "- modifying existing profile: %s" % name
           profile = existing_profile

       profile.set_name(name)
       profile.set_distro(name)

       self.profiles.add(profile)
       self.api.serialize()

       return distro

   def get_proposed_name(self,dirname):
       name = "-".join(dirname.split("/"))
       if name.startswith("-"):
          name = name[1:]
       name = name.replace("var-www-cobbler-", "")
       name = name.replace("ks_mirror-","")
       name = name.replace("os-images-","")
       name = name.replace("tree-images-","")
       name = name.replace("images-","")
       name = name.replace("tree-","")
       name = name.replace("--","-")
       return name

   def get_pxe_arch(self,dirname):
       t = dirname.lower()
       if t.find("x86_64") != -1:
          return "x86_64"
       if t.find("ia64") != -1:
          return "ia64"
       if t.find("i386") != -1 or t.find("386") != -1 or t.find("x86") != -1:
          return "x86"
       return "x86"

   def is_relevant_dir(self,dirname):
       for x in [ "pxe", "xen", "virt" ]:
           if dirname.find(x) != -1:
               return True
       return False

