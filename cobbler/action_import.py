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

from cexceptions import *
import os
import os.path
import traceback
import sub_process
import glob
import api
import utils
import shutil
from rhpl.translate import _, N_, textdomain, utf8

WGET_CMD = "wget --mirror --no-parent --no-host-directories --directory-prefix %s/%s %s"
RSYNC_CMD =  "rsync -a %s %s %s/ks_mirror/%s --exclude-from=/etc/cobbler/rsync.exclude --progress"

TRY_LIST = [
   "Fedora", "RedHat", "Client", "Server", "Centos", "CentOS",
   "Fedora/RPMS", "RedHat/RPMS", "Client/RPMS", "Server/RPMS", "Centos/RPMS",
   "CentOS/RPMS", "RPMS"
]

class Importer:

   def __init__(self,api,config,mirror,mirror_name,network_root=None):
       """
       Performs an import of a install tree (or trees) from the given
       mirror address.  The prefix of the distro is to be specified
       by mirror name.  For instance, if FC-6 is given, FC-6-xen-i386
       would be a potential distro that could be created.  For content
       available on external servers via a known nfs:// or ftp:// or
       http:// path, we can import without doing rsync mirorring to 
       cobbler's http directory.  This is explained in more detail 
       in the manpage.  Leave network_root to None if want mirroring.
       """
       self.api = api
       self.config = config
       self.mirror = mirror
       self.mirror_name = mirror_name
       self.network_root = network_root 
       self.distros  = config.distros()
       self.profiles = config.profiles()
       self.systems  = config.systems()
       self.settings = config.settings()
       self.distros_added = []

   # ----------------------------------------------------------------------

   def run(self):
       if self.mirror is None:
           raise CX(_("import failed.  no --mirror specified"))
       if self.mirror_name is None:
           raise CX(_("import failed.  no --name specified"))

       if self.mirror_name is None:
           raise CX(_("import failed.  no --name specified"))
       
       # make the output path and mirror content but only if not specifying that a network
       # accessible support location already exists

       if self.network_root is None:
           self.path = "%s/ks_mirror/%s" % (self.settings.webdir, self.mirror_name)
           self.mkdir(self.path)

           # prevent rsync from creating the directory name twice
           if not self.mirror.endswith("/"):
               self.mirror = "%s/" % self.mirror 

           if self.mirror.startswith("http://") or self.mirror.startswith("ftp://") or self.mirror.startswith("nfs://"):
               # http mirrors are kind of primative.  rsync is better.
               # that's why this isn't documented in the manpage.
               # TODO: how about adding recursive FTP as an option?
               raise CX(_("unsupported protocol"))
           else:
               # use rsync.. no SSH for public mirrors and local files.
               # presence of user@host syntax means use SSH
               spacer = ""
               if not self.mirror.startswith("rsync://") and not self.mirror.startswith("/"):
                   spacer = ' -e "ssh" '
               self.run_this(RSYNC_CMD, (spacer, self.mirror, self.settings.webdir, self.mirror_name))

       # see that the root given is valid

       if self.network_root is not None:
           if not os.path.exists(self.mirror):
               raise CX(_("path does not exist: %s") % self.mirror)

           if not self.network_root.endswith("/"):
               self.network_root = self.network_root + "/"
           self.path = self.mirror
           found_root = False
           valid_roots = [ "nfs://", "ftp://", "http://" ]
           for valid_root in valid_roots:
               if self.network_root.startswith(valid_root):
                   found_root = True
           if not found_root:
               raise CX(_("Network root given to --available-as must be nfs://, ftp://, or http://"))

       self.processed_repos = {}

       print _("---------------- (adding distros)")
       os.path.walk(self.path, self.distro_adder, {})

       if self.network_root is None:
           print _("---------------- (associating repos)")
           # FIXME: this automagic is not possible (yet) without mirroring 
           self.repo_finder()

       print _("---------------- (associating kickstarts)")
       self.kickstart_finder() 

       print _("---------------- (syncing)")
       self.api.sync()

       return True

   # ----------------------------------------------------------------------

   def mkdir(self, dir):
       try:
           os.makedirs(dir)
       except:
           pass

   # ----------------------------------------------------------------------

   def run_this(self, cmd, args):
       my_cmd = cmd % args
       print _("- %s") % my_cmd
       rc = sub_process.call(my_cmd,shell=True)
       if rc != 0:
          raise CX(_("Command failed"))

   # ----------------------------------------------------------------------

   def kickstart_finder(self):
       """
       For all of the profiles in the config w/o a kickstart, look
       at the kernel path, from that, see if we can guess the distro,
       and if we can, assign a kickstart if one is available for it.
       """

       for profile in self.profiles:
           distro = self.distros.find(profile.distro)
           if distro is None or not (distro in self.distros_added):
               print _("- skipping distro %s since it wasn't imported this time") % profile.distro
               continue

           # THIS IS OBSOLETE:
           #
           #if not distro.kernel.startswith("%s/ks_mirror/" % self.settings.webdir):
           #    # this isn't a mirrored profile, so we won't touch it
           #    print _("- skipping %s since profile isn't mirrored") % profile.name
           #    continue
 
           kdir = os.path.dirname(distro.kernel)   
           base_dir = "/".join(kdir.split("/")[0:-2])
      
           for try_entry in TRY_LIST:
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
                       print _("- finding default kickstart template for %(flavor)s %(major)s") % { "flavor" : flavor, "major" : major }
                       kickstart = self.set_kickstart(profile, flavor, major, minor)
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

       # create the links directory only if we are mirroring because with
       # SELinux Apache can't symlink to NFS (without some doing)

       if self.network_root is None:
           if not os.path.exists(dest_link):
               try:
                   os.symlink(base, dest_link)
               except:
                   # this shouldn't happen but I've seen it ... debug ...
                   print _("- symlink creation failed: %(base)s, %(dest)s") % { "base" : base, "dest" : dest_link }

           # FIXME: looks like "base" isn't used later.  remove?
           base = base.replace(self.settings.webdir,"")
       
       meta = distro.ks_meta

       # how we set the tree depends on whether an explicit network_root was specified
       if self.network_root is None:
           meta["tree"] = "http://%s/cblr/links/%s" % (self.settings.server, distro.name)
       else:
           # where we assign the kickstart source is relative to our current directory
           # and the input start directory in the crawl.  We find the path segments
           # between and tack them on the network source path to find the explicit
           # network path to the distro that Anaconda can digest.  
           tail = self.path_tail(self.mirror, base)
           meta["tree"] = self.network_root
           if meta["tree"].endswith("/"):
              meta["tree"] = self.network_root[:-1]
           meta["tree"] = meta["tree"] + tail.rstrip()

       print _("- tree: %s") % meta["tree"]
       distro.set_ksmeta(meta)

   # ---------------------------------------------------------------------

   def path_tail(self, apath, bpath):
       """ 
       Given two paths (B is longer than A), find the part in B not in A
       """
       position = bpath.find(apath)
       if position != 0:
           print "%s, %s, %s" % (apath, bpath, position)
           raise CX(_("Error: possible symlink traversal?: %s") % bpath)
       rposition = position + len(self.mirror)
       result = bpath[rposition:]
       if not result.startswith("/"):
           result = "/" + result
       return result

   # ---------------------------------------------------------------------

   def set_kickstart(self, profile, flavor, major, minor):
       if flavor == "fedora":
           if major >= 6:
                return profile.set_kickstart("/etc/cobbler/kickstart_fc6.ks")
       if flavor == "redhat" or flavor == "centos":
           if major >= 5:
                return profile.set_kickstart("/etc/cobbler/kickstart_fc6.ks")
       print _("- using default kickstart file choice")
       return profile.set_kickstart("/etc/cobbler/kickstart_fc5.ks")

   # ---------------------------------------------------------------------

   def scan_rpm_filename(self, rpm):
       """
       Determine what the distro is based on the release RPM filename.
       """

       rpm = os.path.basename(rpm)

       # if it looks like a RHEL RPM we'll cheat.
       # it may be slightly wrong, but it will be close enough
       # for RHEL5 we can get it exactly.
       
       for x in [ "4AS", "4ES", "4WS" ]:
          if rpm.find(x) != -1:
             return ("redhat", 4, 0)
       for x in [ "3AS", "3ES", "3WS" ]:
          if rpm.find(x) != -1:
             return ("redhat", 3, 0)
       for x in [ "2AS", "2ES", "2WS" ]:
          if rpm.find(x) != -1:
             return ("redhat", 2, 0)

       # now get the flavor:
       flavor = "redhat"
       if rpm.lower().find("fedora") != -1:
          flavor = "fedora"
       if rpm.lower().find("centos") != -1:
          flavor = "centos"

       # get all the tokens and try to guess a version
       accum = []
       tokens = rpm.split(".")
       for t in tokens:
          tokens2 = t.split("-")
          for t2 in tokens2:
             try:
                 float(t2)
                 accum.append(t2)
             except:
                 pass

       major = float(accum[0])
       minor = float(accum[1])
       return (flavor, major, minor)

   # ----------------------------------------------------------------------

   def distro_adder(self,foo,dirname,fnames):
       
       initrd = None
       kernel = None
       
       # NOTE: can't make this optomization anymore since we may have to re-invoke
       # walk for symlinks.
       #
       #
       #if not self.is_relevant_dir(dirname):
       #    print "DEBUG: %s is not relevant" % dirname
       #    return

       for x in fnames:

           fullname = os.path.join(dirname,x)
           if os.path.islink(fullname) and os.path.isdir(fullname):
              print "- following symlink: %s" % fullname
              os.path.walk(fullname, self.distro_adder, {})

           if x.startswith("initrd"):
               initrd = os.path.join(dirname,x)
           if x.startswith("vmlinuz"):
               kernel = os.path.join(dirname,x)
           if initrd is not None and kernel is not None and dirname.find("isolinux") == -1:
               self.add_entry(dirname,kernel,initrd)
               path_parts = kernel.split("/")[:-2]
               comps_path = "/".join(path_parts)



   # ----------------------------------------------------------------------
   
   def repo_finder(self):
       
       for distro in self.distros_added:
           print _("- traversing distro %s") % distro.name
           if distro.kernel.find("ks_mirror") != -1:
               basepath = os.path.dirname(distro.kernel)
               top = "/".join(basepath.split("/")[0:-2]) # up one level
               print _("- descent into %s") % top
               os.path.walk(top, self.repo_scanner, distro)
           else:
               print _("- this distro isn't mirrored")

   # ----------------------------------------------------------------------

   def repo_scanner(self,distro,dirname,fnames):
       
       print "DEBUG: repo scanner for %s" % dirname
       for x in fnames:
           if x == "base": # don't do "repodata"
               self.process_comps_file(dirname, distro)
               continue

   # ----------------------------------------------------------------------
               

   def process_comps_file(self, comps_path, distro):

       # all of this is mainly to set up the core repos in a sane
       # way and shouldn't fail if the tree structure is too foreign
       masterdir = "repodata"
       if not os.path.exists(os.path.join(comps_path, "repodata")):
           # older distros...
           masterdir = "base"

       print _("- scanning: %(path)s (distro: %(name)s)") % { "path" : comps_path, "name" : distro.name }

       # figure out what our comps file is ...
       print _("- looking for %(p1)s/%(p2)s/comps*.xml") % { "p1" : comps_path, "p2" : masterdir }
       files = glob.glob("%s/%s/comps*.xml" % (comps_path, masterdir))
       if len(files) == 0:
           print _("- no comps found here: %s") % os.path.join(comps_path, masterdir)
           return # no comps xml file found

       # pull the filename from the longer part
       comps_file = files[0].split("/")[-1]

       try:

           # store the yum configs on the filesystem so we can use them later.
           # and configure them in the kickstart post, etc

           counter = len(distro.source_repos)

           # find path segment for yum_url (changing filesystem path to http:// trailing fragment)
           seg = comps_path.rfind("ks_mirror")
           urlseg = comps_path[seg+10:]

           # write a yum config file that shows how to use the repo.
           if counter == 0:
               dotrepo = "%s.repo" % distro.name
           else:
               dotrepo = "%s-%s.repo" % (distro.name, counter)

           fname = os.path.join(self.settings.webdir, "ks_mirror", "config", "%s-%s.repo" % (distro.name, counter))
           repo_url = "http://%s/cobbler/ks_mirror/config/%s-%s.repo" % (self.settings.server, distro.name, counter)
         
           repo_url2 = "http://%s/cobbler/ks_mirror/%s" % (self.settings.server, urlseg) 

           distro.source_repos.append([repo_url,repo_url2])

           print _("- url: %s") % repo_url
           config_file = open(fname, "w+")
           config_file.write("[%s]\n" % "core-%s" % counter)
           config_file.write("name=%s\n" % "core-%s " % counter)
           config_file.write("baseurl=http://%s/cobbler/ks_mirror/%s\n" % (self.settings.server, urlseg))
           config_file.write("enabled=1\n")
           config_file.write("gpgcheck=0\n")
           config_file.close()

           # don't run creatrepo twice -- this can happen easily for Xen and PXE, when
           # they'll share same repo files.
           if not self.processed_repos.has_key(comps_path):
               utils.remove_yum_olddata(comps_path)
               #cmd = "createrepo --basedir / --groupfile %s %s" % (os.path.join(comps_path, masterdir, comps_file), comps_path)
               cmd = "createrepo -c cache --groupfile %s %s" % (os.path.join(comps_path, masterdir, comps_file), comps_path)
               print _("- %s") % cmd
               sub_process.call(cmd,shell=True)
               self.processed_repos[comps_path] = 1
               # for older distros, if we have a "base" dir parallel with "repodata", we need to copy comps.xml up one...
               p1 = os.path.join(comps_path, "repodata", "comps.xml")
               p2 = os.path.join(comps_path, "base", "comps.xml")
               if os.path.exists(p1) and os.path.exists(p2):
                   print _("- cp %(p1)s %(p2)s") % { "p1" : p1, "p2" : p2 }
                   shutil.copyfile(p1,p2)

       except:
           print _("- error launching createrepo, ignoring...")
           traceback.print_exc()
        

   def add_entry(self,dirname,kernel,initrd):
       pxe_arch = self.get_pxe_arch(dirname)
       name = self.get_proposed_name(dirname, pxe_arch)

       existing_distro = self.distros.find(name)

       if existing_distro is not None:
           print _("- modifying existing distro: %s") % name
           distro = existing_distro
       else:
           print _("- creating new distro: %s") % name
           distro = self.config.new_distro()
           
       distro.set_name(name)
       distro.set_kernel(kernel)
       distro.set_initrd(initrd)
       distro.set_arch(pxe_arch)
       distro.source_repos = []
       self.distros.add(distro)
       self.distros_added.append(distro)       

       existing_profile = self.profiles.find(name) 

       if existing_profile is None:
           print _("- creating new profile: %s") % name 
           profile = self.config.new_profile()
       else:
           print _("- modifying existing profile: %s") % name
           profile = existing_profile

       profile.set_name(name)
       profile.set_distro(name)

       self.profiles.add(profile)
       self.api.serialize()

       return distro

   def get_proposed_name(self,dirname,pxe_arch):
       archname = pxe_arch
       if archname == "x86":
          archname = "i386"
       # FIXME: this is new, needs testing ...
       if self.network_root is not None:
          name = "-".join(self.path_tail(self.path,dirname).split("/"))
       else:
          # remove the part that says /var/www/cobbler/ks_mirror/name
          name = "-".join(dirname.split("/")[6:])
       if name.startswith("-"):
          name = name[1:]
       name = self.mirror_name + "-" + name
       name = name.replace("-os","")
       name = name.replace("-images","")
       name = name.replace("-tree","")
       name = name.replace("var-www-cobbler-", "")
       name = name.replace("ks_mirror-","")
       name = name.replace("-pxeboot","")  
       name = name.replace("--","-")
       name = name.replace("-i386","")
       name = name.replace("_i386","")
       name = name.replace("-x86_64","")
       name = name.replace("_x86_64","")
       name = name.replace("-ia64","")
       name = name.replace("_ia64","")
       # ensure arch is on the end, regardless of path used.
       name = name + "-" + archname

       return name

   def arch_walker(self,foo,dirname,fnames):
       """
       See docs on learn_arch_from_tree
       """
 
       # don't care about certain directories
       match = False
       for x in TRY_LIST:
           if dirname.find(x) != -1:
               match = True
               continue
       if not match:
          return

       # try to find a kernel header RPM and then look at it's arch.
       for x in fnames:
           if not x.endswith("rpm"):
               continue
           if x.find("kernel-header") != -1:
               print _("- kernel header found: %s") % x
               if x.find("i386") != -1:
                   foo["result"] = "x86"
                   return
               elif x.find("x86_64") != -1: 
                   foo["result"] = "x86_64"
                   return
               elif x.find("ia64") != -1:
                   foo["result"] = "ia64"
                   return
                

   def learn_arch_from_tree(self,dirname):
       """ 
       If a distribution is imported from DVD, there is a good chance the path doesn't contain the arch
       and we should add it back in so that it's part of the meaningful name ... so this code helps
       figure out the arch name.  This is important for producing predictable distro names (and profile names)
       from differing import sources
       """
       dirname2 = "/".join(dirname.split("/")[:-2])  # up two from images, then down as many as needed
       print _("- scanning %s for architecture info") % dirname2
       result = { "result" : "x86" } # default, but possibly not correct ... 
       os.path.walk(dirname2, self.arch_walker, result)      
       return result["result"]

   def get_pxe_arch(self,dirname):
       t = dirname.lower()
       if t.find("x86_64") != -1:
          return "x86_64"
       if t.find("ia64") != -1:
          return "ia64"
       if t.find("i386") != -1 or t.find("386") != -1 or t.find("x86") != -1:
          return "x86"
       return self.learn_arch_from_tree(dirname)

   def is_relevant_dir(self,dirname):
       for x in [ "pxe", "xen", "virt" ]:
           if dirname.find(x) != -1:
               return True
       return False

