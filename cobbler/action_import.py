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

import api

WGET_CMD = "wget --mirror --no-parent --no-host-directories --directory-prefix %s/%s %s"
RSYNC_CMD =  "rsync -a %s %s %s/ks_mirror/%s --exclude-from=/etc/cobbler/rsync.exclude --delete --delete-excluded --progress"

# MATCH_LIST uses path segments of mirror URLs to assign kickstart
# files.  It's not all that intelligent.
# patches welcome!

MATCH_LIST = (
   ( "FC-5/"    , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "FC-6/"    , "/etc/cobbler/kickstart_fc6.ks" ),
   ( "RHEL-4/"  , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "RHEL-5/"  , "/etc/cobbler/kickstart_fc6.ks" ),
   ( "Centos/4" , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "Centos/5" , "/etc/cobbler/kickstart_fc6.ks" ),
   ( "1/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "2/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "3/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "4/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "5/"       , "/etc/cobbler/kickstart_fc5.ks" ),
   ( "6/"       , "/etc/cobbler/kickstart_fc6.ks" ),
)

# the following is a filter to reduce import scan times,
# particularly over NFS.  these indicate directory segments
# that we do not need to recurse into.  In the case where
# these path segments are important to a certain distro import,
# it's a bug, and this list needs to be edited.  please submit
# patches or reports in this case.

DIRECTORY_SIEVE = [
   "debuginfo", "ppc", "s390x", "s390", "variant-src",
   "ftp-isos", "compat-layer", "compat-layer-tree",
   "SRPMS", "headers", "dosutils", "Publishers",
   "LIVE", "RedHat", "image-template", "logs",
   "EMEA", "APAC", "isolinux",
   "debug", "repodata", "repoview", "Fedora",
   "stylesheet-images", "buildinstall", "partner", "noarch",
   "src-isos", "dvd-isos", "docs", "misc"
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
       self.serialize_counter = 0

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


       processed_repos = {}
       os.path.walk(self.path, self.walker, processed_repos)
       self.guess_kickstarts()
       return True


   def mkdir(self, dir):
       try:
           os.makedirs(dir)
       except:
           print "- didn't create %s" % dir

   def run_this(self, cmd, args):
       my_cmd = cmd % args
       print "- %s" % my_cmd
       sub_process.call(my_cmd,shell=True)

   def guess_kickstarts(self):

       """
       For all of the profiles in the config w/o a kickstart, look
       at the kernel path, from that, see if we can guess the distro,
       and if we can, assign a kickstart if one is available for it.
       """
       # FIXME: refactor this and make it more intelligent
       # FIXME: if no distro can be found from the path, find through alternative means.

       for profile in self.profiles:
           distro = self.distros.find(profile.distro)
           if distro is None:
               raise cexceptions.CobblerException("orphan_distro2",profile.name,profile.distro)
           kpath = distro.kernel
           if not kpath.startswith("%s/ks_mirror/" % self.settings.webdir):
               continue
           for entry in MATCH_LIST:
               (part, kickstart) = entry
               if kpath.find(part) != -1:
                   if os.path.exists(kickstart):
                       print "*** ASSIGNING kickstart: %s" % kickstart
                       profile.set_kickstart(kickstart)
                       # from the kernel path, the tree path is always two up.
                       dirname = os.path.dirname(kpath)
                       print "dirname = %s" % dirname
                       tokens = dirname.split("/")
                       tokens = tokens[:-2]
                       base = "/".join(tokens) 
                       dest_link = os.path.join(self.settings.webdir, "links", distro.name)
                       print "base=%s -> %s to %s" % (base, dest_link)
                       if not os.path.exists(dest_link):
                           os.symlink(base, dest_link)                       
                       base = base.replace(self.settings.webdir,"")
                       tree = "tree=http://%s/cblr/links/%s" % distro.name
                       print "*** KICKSTART TREE = %s" % tree
                       distro.set_ksmeta(tree)
                       self.serialize_counter = self.serialize_counter + 1
                       if (self.serialize_counter % 5) == 0:
                           self.api.serialize()

   def walker(self,processed_repos,dirname,fnames):
       initrd = None
       kernel = None
       for tentative in fnames:
           for filter_out in DIRECTORY_SIEVE:
               if tentative == filter_out:
                   fnames.remove(tentative)
       print "%s" % dirname
       if not self.is_pxe_or_virt_dir(dirname):
           return
       # keep track of where we've run create repo
       for x in fnames:
           if x.startswith("initrd"):
               initrd = os.path.join(dirname,x)
           if x.startswith("vmlinuz"):
               kernel = os.path.join(dirname,x)
           if initrd is not None and kernel is not None:
               self.add_entry(dirname,kernel,initrd)
               # repo is up two locations and down in repodata
               path_parts = kernel.split("/")[:-3]
               comps_path = "/".join(path_parts)
               print "- looking for comps in %s" % comps_path
               comps_file = os.path.join(comps_path, "repodata", "comps.xml")
               if not os.path.exists(comps_file):
                   print "- no comps file found: %s" % comps_file
               try:
                   # don't run creatrepo twice -- this can happen easily for Xen and PXE, when
                   # they'll share same repo files.
                   if not processed_repos.has_key(comps_path):
                      cmd = "createrepo --basedir / --groupfile %s %s" % (comps_file, comps_path)
                      print "- %s" % cmd
                      sub_process.call(cmd,shell=True)
                      print "- repository updated"
                      processed_repos[comps_path] = 1
               except:
                   print "- error launching createrepo, ignoring for now..."
                   traceback.print_exc()

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
           print "(distro added)"
           if self.profiles.find(name) is None:
               profile = self.config.new_profile()
               profile.set_name(name)
               profile.set_distro(name)
               self.profiles.add(profile)
               print "(profile added)"
           self.serialize_counter = self.serialize_counter + 1
           if (self.serialize_counter % 5) == 0:
               self.api.serialize()

   def get_proposed_name(self,dirname):
       name = "-".join(dirname.split("/"))
       if name.startswith("-"):
          name = name[1:]
       # some of this filtering is a bit excessive though we want to compensate for
       # finding "tree" vs "image" in the path and so on, and being a little more
       # aggressive in filtering will reduce path name lengths in all circumstances.
       # long paths are bad because they are hard to type, look weird, and run up
       # against the 255 char kernel options limit too quickly.
       name = name.replace("var-www-cobbler-", "")
       name = name.replace("ks-mirror-","")
       name = name.replace("os-images-","")
       name = name.replace("tree-images-","")
       name = name.replace("images-","")
       name = name.replace("tree-","")
       name = name.replace("--","-")
       return name

   def get_pxe_arch(self,dirname):
       t = dirname
       if t.find("x86_64") != -1:
          return "x86_64"
       if t.find("ia64") != -1:
          return "ia64"
       if t.find("i386") != -1 or t.find("386") != -1 or t.find("x86") != -1:
          return "x86"
       return "x86"

   def is_pxe_or_virt_dir(self,dirname):
       if dirname.find("pxe") != -1 or dirname.find("xen") != -1 or dirname.find("virt") != -1:
           return True
       return False

