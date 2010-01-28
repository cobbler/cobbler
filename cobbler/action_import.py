"""
Enables the "cobbler import" command to seed cobbler
information with available distribution from rsync mirrors
and mounted DVDs.  

Copyright 2006-2009, Red Hat, Inc
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

from cexceptions import *
import os
import os.path
import traceback
import glob
import api
import utils
import shutil
from utils import _
import item_repo
import clogger

# FIXME: add --quiet depending on if not --verbose?
RSYNC_CMD =  "rsync -a %s '%s' %s/ks_mirror/%s --exclude-from=/etc/cobbler/rsync.exclude --progress"

class Importer:

   def __init__(self,api,config,mirror,mirror_name,network_root=None,kickstart_file=None,rsync_flags=None,arch=None,breed=None,os_version=None,logger=None):
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
       self.kickstart_file = kickstart_file
       self.rsync_flags = rsync_flags
       self.arch = arch
       self.breed = breed
       self.os_version = os_version
       if logger is None:
           logger       = clogger.Logger()
       self.logger      = logger


   # ========================================================================

   def run(self):

       """
       This contains the guts of the import command.
       """

       # some fixups for the XMLRPC interface, which does not use "None"
       if self.arch == "":           self.arch           = None
       if self.mirror == "":         self.mirror         = None
       if self.mirror_name == "":    self.mirror_name    = None
       if self.breed == "":          self.breed          = None
       if self.kickstart_file == "": self.kickstart_file = None
       if self.os_version == "":     self.os_version     = None
       if self.rsync_flags == "":    self.rsync_flags    = None
       if self.network_root == "":   self.network_root   = None

       # both --import and --name are required arguments

       if self.mirror is None:
           utils.die(self.logger,"import failed.  no --path specified")
       if self.mirror_name is None:
           utils.die(self.logger,"import failed.  no --name specified")

       # if --arch is supplied, validate it to ensure it's valid

       if self.arch is not None and self.arch != "":
           self.arch = self.arch.lower()
           if self.arch == "x86":
               # be consistent
               self.arch = "i386"
           if self.arch not in [ "i386", "ia64", "ppc", "ppc64", "s390", "s390x", "x86_64", ]:
               utils.die(self.logger,"arch must be i386, ia64, ppc, ppc64, s390, s390x or x86_64")

       # if we're going to do any copying, set where to put things
       # and then make sure nothing is already there.

       mpath = os.path.join(self.settings.webdir, "ks_mirror", self.mirror_name)
       if os.path.exists(mpath) and self.arch is None:
           # FIXME : Raise exception even when network_root is given ?
           utils.die(self.logger,"Something already exists at this import location (%s).  You must specify --arch to avoid potentially overwriting existing files." % mpath)

       # import takes a --kickstart for forcing selection that can't be used in all circumstances
 
       if self.kickstart_file and not self.breed:
           utils.die(self.logger,"Kickstart file can only be specified when a specific breed is selected")

       if self.os_version and not self.breed:
           utils.die(self.logger,"OS version can only be specified when a specific breed is selected")

       #if self.breed and self.breed.lower() not in [ "redhat", "debian", "ubuntu", "windows" ]:
       if self.breed and self.breed.lower() not in [ "redhat" ]:
           utils.die(self.logger,"Supplied import breed is not supported")
 
       # if --arch is supplied, make sure the user is not importing a path with a different
       # arch, which would just be silly.  

       if self.arch:
           # append the arch path to the name if the arch is not already
           # found in the name.
           for x in [ "i386", "ia64", "ppc", "ppc64", "s390", "s390x", "x86_64", "x86", ]:
               if self.mirror_name.lower().find(x) != -1:
                   if self.arch != x :
                       utils.die(self.logger,"Architecture found on pathname (%s) does not fit the one given in command line (%s)"%(x,self.arch))
                   break
           else:
               # FIXME : This is very likely removed later at get_proposed_name, and the guessed arch appended again
               self.mirror_name = self.mirror_name + "-" + self.arch

       # make the output path and mirror content but only if not specifying that a network
       # accessible support location already exists (this is --available-as on the command line)

       if self.network_root is None:
 
           # we need to mirror (copy) the files 

           self.path = os.path.normpath( "%s/ks_mirror/%s" % (self.settings.webdir, self.mirror_name) )
           self.mkdir(self.path)

           # prevent rsync from creating the directory name twice
           # if we are copying via rsync

           if not self.mirror.endswith("/"):
               self.mirror = "%s/" % self.mirror 

           if self.mirror.startswith("http://") or self.mirror.startswith("ftp://") or self.mirror.startswith("nfs://"):

               # http mirrors are kind of primative.  rsync is better.
               # that's why this isn't documented in the manpage and we don't support them.
               # TODO: how about adding recursive FTP as an option?

               utils.die(self.logger,"unsupported protocol")

           else:

               # good, we're going to use rsync.. 
               # we don't use SSH for public mirrors and local files.
               # presence of user@host syntax means use SSH

               spacer = ""
               if not self.mirror.startswith("rsync://") and not self.mirror.startswith("/"):
                   spacer = ' -e "ssh" '
               rsync_cmd = RSYNC_CMD
               if self.rsync_flags:
                   rsync_cmd = rsync_cmd + " " + self.rsync_flags

               # kick off the rsync now

               self.run_this(rsync_cmd, (spacer, self.mirror, self.settings.webdir, self.mirror_name))

       else:

           # rather than mirroring, we're going to assume the path is available
           # over http, ftp, and nfs, perhaps on an external filer.  scanning still requires
           # --mirror is a filesystem path, but --available-as marks the network path
          
           if not os.path.exists(self.mirror):
               utils.die(self.logger, "path does not exist: %s" % self.mirror)

           # find the filesystem part of the path, after the server bits, as each distro
           # URL needs to be calculated relative to this. 

           if not self.network_root.endswith("/"):
               self.network_root = self.network_root + "/"
           self.path = os.path.normpath( self.mirror )
           valid_roots = [ "nfs://", "ftp://", "http://" ]
           for valid_root in valid_roots:
               if self.network_root.startswith(valid_root):
                   break
           else:
               utils.die(self.logger, "Network root given to --available-as must be nfs://, ftp://, or http://")
           if self.network_root.startswith("nfs://"):
               try:
                   (a,b,rest) = self.network_root.split(":",3)
               except:
                   utils.die(self.logger, "Network root given to --available-as is missing a colon, please see the manpage example.")

       # now walk the filesystem looking for distributions that match certain patterns

       self.logger.info("adding distros")
       distros_added = []
       # FIXME : search below self.path for isolinux configurations or known directories from TRY_LIST
       os.path.walk(self.path, self.distro_adder, distros_added)

       # find out if we can auto-create any repository records from the install tree

       if self.network_root is None:
           self.logger.info("associating repos")
           # FIXME: this automagic is not possible (yet) without mirroring 
           self.repo_finder(distros_added)

       # find the most appropriate answer files for each profile object

       self.logger.info("associating kickstarts")
       self.kickstart_finder(distros_added) 

       # ensure bootloaders are present
       self.api.pxegen.copy_bootloaders()

       return True

   # ----------------------------------------------------------------------

   def mkdir(self, dir):

       """
       A more tolerant mkdir.
       FIXME: use the one in utils.py (?)
       """

       try:
           os.makedirs(dir)
       except OSError , ex:
           if ex.strerror == "Permission denied":
               utils.die(self.logger, "Permission denied at %s" % dir)
       except:
           pass

   # ----------------------------------------------------------------------

   def run_this(self, cmd, args):

       """
       A simple wrapper around subprocess calls.
       """

       my_cmd = cmd % args
       rc = utils.subprocess_call(self.logger,my_cmd,shell=True)
       if rc != 0:
          utils.die(self.logger,"Command failed")

   # =======================================================================

   def kickstart_finder(self,distros_added):

       """
       For all of the profiles in the config w/o a kickstart, use the
       given kickstart file, or look at the kernel path, from that, 
       see if we can guess the distro, and if we can, assign a kickstart 
       if one is available for it.
       """

       for profile in self.profiles:
           distro = self.distros.find(name=profile.get_conceptual_parent().name)
           if distro is None or not (distro in distros_added):
               continue

           kdir = os.path.dirname(distro.kernel)   
           importer = import_factory(kdir,self.path,self.breed,self.logger)
           if self.kickstart_file == None:
               for rpm in importer.get_release_files():
                     # FIXME : This redhat specific check should go into the importer.find_release_files method
                     if rpm.find("notes") != -1:
                         continue
                     results = importer.scan_pkg_filename(rpm)
                     # FIXME : If os is not found on tree but set with CLI, no kickstart is searched
                     if results is None:
                         self.logger.warning("No version found on imported tree")

                         continue
                     (flavor, major, minor) = results
                     version , ks = importer.set_variance(flavor, major, minor, distro.arch)
                     if self.os_version:
                         if self.os_version != version:
                             utils.die(self.logger,"CLI version differs from tree : %s vs. %s" % (self.os_version,version))
                     ds = importer.get_datestamp()
                     distro.set_comment("%s.%s" % (version, int(minor)))
                     distro.set_os_version(version)
                     if ds is not None:
                         distro.set_tree_build_time(ds)
                     profile.set_kickstart(ks)
                     self.profiles.add(profile,save=True)

           self.configure_tree_location(distro,importer)
           self.distros.add(distro,save=True) # re-save
           self.api.serialize()

   # ==========================================================================


   def configure_tree_location(self, distro, importer):

       """
       Once a distribution is identified, find the part of the distribution
       that has the URL in it that we want to use for kickstarting the
       distribution, and create a ksmeta variable $tree that contains this.
       """

       base = importer.get_rootdir()

       if self.network_root is None:
           if distro.breed == "debian" or distro.breed == "ubuntu":
               dists_path = os.path.join( self.path , "dists" )
               if os.path.isdir( dists_path ):
                   tree = "http://@@http_server@@/cblr/ks_mirror/%s" % (self.mirror_name)
               else:
                   tree = "http://@@http_server@@/cblr/repo_mirror/%s" % (distro.name)
           else:
               dest_link = os.path.join(self.settings.webdir, "links", distro.name)
               # create the links directory only if we are mirroring because with
               # SELinux Apache can't symlink to NFS (without some doing)
               if not os.path.exists(dest_link):
                   try:
                       os.symlink(base, dest_link)
                   except:
                       # this shouldn't happen but I've seen it ... debug ...
                       self.logger.warning("symlink creation failed: %(base)s, %(dest)s") % { "base" : base, "dest" : dest_link }
               # how we set the tree depends on whether an explicit network_root was specified
               tree = "http://@@http_server@@/cblr/links/%s" % (distro.name)
           importer.set_install_tree( distro, tree)
       else:
           # where we assign the kickstart source is relative to our current directory
           # and the input start directory in the crawl.  We find the path segments
           # between and tack them on the network source path to find the explicit
           # network path to the distro that Anaconda can digest.  
           tail = self.path_tail(self.path, base)
           tree = self.network_root[:-1] + tail
           importer.set_install_tree( distro, tree)

   # ============================================================================

   def path_tail(self, apath, bpath):
       """ 
       Given two paths (B is longer than A), find the part in B not in A
       """
       position = bpath.find(apath)
       if position != 0:
           utils.die(self.logger, "- warning: possible symlink traversal?: %s")
       rposition = position + len(self.mirror)
       result = bpath[rposition:]
       if not result.startswith("/"):
           result = "/" + result
       return result

   # ======================================================================
   
   def repo_finder(self,distros_added):

       """
       This routine looks through all distributions and tries to find 
       any applicable repositories in those distributions for post-install
       usage.
       """
       
       for distro in distros_added:
           self.logger.info("traversing distro %s" % distro.name)
           # FIXME : Shouldn't decide this the value of self.network_root ?
           if distro.kernel.find("ks_mirror") != -1:
               basepath = os.path.dirname(distro.kernel)
               importer = import_factory(basepath,self.path,self.breed,self.logger)
               top = importer.get_rootdir()
               self.logger.info("descent into %s" % top)
               if distro.breed in [ "debian" , "ubuntu" ]:
                   dists_path = os.path.join( self.path , "dists" )
                   if not os.path.isdir( dists_path ):
                       importer.process_repos( self , distro )
               else:
                   # FIXME : The location of repo definition is known from breed
                   os.path.walk(top, self.repo_scanner, distro)
           else:
               self.logger.info("this distro isn't mirrored")

   # ========================================================================


   def repo_scanner(self,distro,dirname,fnames):

       """
       This is an os.path.walk routine that looks for potential yum repositories
       to be added to the configuration for post-install usage.
       """
       
       matches = {}
       for x in fnames:
          if x == "base" or x == "repodata":
               self.logger.info("processing repo at : %s" % dirname)
               # only run the repo scanner on directories that contain a comps.xml
               gloob1 = glob.glob("%s/%s/*comps*.xml" % (dirname,x))
               if len(gloob1) >= 1:
                   if matches.has_key(dirname):
                       self.logger.info("looks like we've already scanned here: %s" % dirname)
                       continue
                   self.logger.info("need to process repo/comps: %s" % dirname)
                   self.process_comps_file(dirname, distro)
                   matches[dirname] = 1
               else:
                   self.logger.info("directory %s is missing xml comps file, skipping" % dirname)
                   continue

   # =======================================================================================



   def process_comps_file(self, comps_path, distro):
       """
       When importing Fedora/EL certain parts of the install tree can also be used
       as yum repos containing packages that might not yet be available via updates
       in yum.  This code identifies those areas.
       """

       processed_repos = {}

       masterdir = "repodata"
       if not os.path.exists(os.path.join(comps_path, "repodata")):
           # older distros...
           masterdir = "base"

       # figure out what our comps file is ...
       self.logger.info("looking for %(p1)s/%(p2)s/*comps*.xml" % { "p1" : comps_path, "p2" : masterdir })
       files = glob.glob("%s/%s/*comps*.xml" % (comps_path, masterdir))
       if len(files) == 0:
           self.logger.info("no comps found here: %s" % os.path.join(comps_path, masterdir))
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

           repo_url = "http://@@http_server@@/cobbler/ks_mirror/config/%s-%s.repo" % (distro.name, counter)
           
           repo_url2 = "http://@@http_server@@/cobbler/ks_mirror/%s" % (urlseg)
           
           distro.source_repos.append([repo_url,repo_url2])

           # NOTE: the following file is now a Cheetah template, so it can be remapped
           # during sync, that's why we have the @@http_server@@ left as templating magic.
           # repo_url2 is actually no longer used. (?)

           config_file = open(fname, "w+")
           config_file.write("[core-%s]\n" % counter)
           config_file.write("name=core-%s\n" % counter)
           config_file.write("baseurl=http://@@http_server@@/cobbler/ks_mirror/%s\n" % (urlseg))
           config_file.write("enabled=1\n")
           config_file.write("gpgcheck=0\n")
           config_file.write("priority=$yum_distro_priority\n")
           config_file.close()

           # don't run creatrepo twice -- this can happen easily for Xen and PXE, when
           # they'll share same repo files.

           if not processed_repos.has_key(comps_path):
               utils.remove_yum_olddata(comps_path)
               #cmd = "createrepo --basedir / --groupfile %s %s" % (os.path.join(comps_path, masterdir, comps_file), comps_path)
               cmd = "createrepo %s --groupfile %s %s" % (self.settings.createrepo_flags,os.path.join(comps_path, masterdir, comps_file), comps_path)
               utils.subprocess_call(self.logger, cmd, shell=True)
               processed_repos[comps_path] = 1
               # for older distros, if we have a "base" dir parallel with "repodata", we need to copy comps.xml up one...
               p1 = os.path.join(comps_path, "repodata", "comps.xml")
               p2 = os.path.join(comps_path, "base", "comps.xml")
               if os.path.exists(p1) and os.path.exists(p2):
                   shutil.copyfile(p1,p2)

       except:
           self.logger.error("error launching createrepo (not installed?), ignoring")
           utils.log_exc(self.logger)


   # ========================================================================

   def distro_adder(self,distros_added,dirname,fnames):

       """
       This is an os.path.walk routine that finds distributions in the directory
       to be scanned and then creates them.
       """

       # FIXME: If there are more than one kernel or initrd image on the same directory,
       # results are unpredictable

       initrd = None
       kernel = None

       # make sure we don't mismatch PAE and non-PAE types
       pae_initrd = None
       pae_kernel = None

       for x in fnames:

           adtls = []

           fullname = os.path.join(dirname,x)
           if os.path.islink(fullname) and os.path.isdir(fullname):
              if fullname.startswith(self.path):
                  # Prevent infinite loop with Sci Linux 5
                  self.logger.warning("avoiding symlink loop")
                  continue
              self.logger.info("following symlink: %s" % fullname)
              os.path.walk(fullname, self.distro_adder, distros_added)

           if ( x.startswith("initrd") or x.startswith("ramdisk.image.gz") ) and x != "initrd.size":
               if x.find("PAE") == -1:
                  initrd = os.path.join(dirname,x)
               else:
                  pae_initrd = os.path.join(dirname, x)

           if ( x.startswith("vmlinu") or x.startswith("kernel.img") or x.startswith("linux") ) and x.find("initrd") == -1:
               if x.find("PAE") == -1:
                  kernel = os.path.join(dirname,x)
               else:
                  pae_kernel = os.path.join(dirname, x)

           # if we've collected a matching kernel and initrd pair, turn the in and add them to the list
           if initrd is not None and kernel is not None and dirname.find("isolinux") == -1:
               adtls.append(self.add_entry(dirname,kernel,initrd))
               kernel = None
               initrd = None
           elif pae_initrd is not None and pae_kernel is not None and dirname.find("isolinux") == -1:
               adtls.append(self.add_entry(dirname,pae_kernel,pae_initrd))
               pae_kernel = None
               pae_initrd = None
           for adtl in adtls:
               distros_added.extend(adtl)


   # ========================================================================

   def add_entry(self,dirname,kernel,initrd):

       """
       When we find a directory with a valid kernel/initrd in it, create the distribution objects
       as appropriate and save them.  This includes creating xen and rescue distros/profiles
       if possible.
       """

       proposed_name = self.get_proposed_name(dirname,kernel)
       proposed_arch = self.get_proposed_arch(dirname)
       if self.arch and proposed_arch and self.arch != proposed_arch:
           utils.die(self.logger,"Arch from pathname (%s) does not match with supplied one %s"%(proposed_arch,self.arch))

       importer = import_factory(dirname,self.path,self.breed,self.logger)

       archs = importer.learn_arch_from_tree()
       if not archs:
           if self.arch:
               archs.append( self.arch )
       else:
            if self.arch and self.arch not in archs:
               utils.die(self.logger, "Given arch (%s) not found on imported tree %s"%(self.arch,importer.get_pkgdir()))
       if proposed_arch:
           if archs and proposed_arch not in archs:
               self.logger.warning("arch from pathname (%s) not found on imported tree %s" % (proposed_arch,importer.get_pkgdir()))
               return

           archs = [ proposed_arch ]

       if importer.breed == "ubuntu" and dirname.find("ubuntu-installer") == -1:
           self.logger.info("skipping entry, there are no netboot images")
           return


       if len(archs)>1:
           if importer.breed in [ "redhat" ]:
               self.logger.warning("directory %s holds multiple arches : %s" % (dirname, archs))
               return
           self.logger.warning("- Warning : Multiple archs found : %s" % (archs))

       distros_added = []

       for pxe_arch in archs:

           name = proposed_name + "-" + pxe_arch
           existing_distro = self.distros.find(name=name)

           if existing_distro is not None:
               self.logger.warning("skipping import, as distro name already exists: %s" % name)
               continue

           else:
               self.logger.info("creating new distro: %s" % name)
               distro = self.config.new_distro()
           
           if name.find("-autoboot") != -1:
               # this is an artifact of some EL-3 imports
               continue

           distro.set_name(name)
           distro.set_kernel(kernel)
           distro.set_initrd(initrd)
           distro.set_arch(pxe_arch)
           distro.set_breed(importer.breed)
           # If a version was supplied on command line, we set it now
           if self.os_version:
               distro.set_os_version(self.os_version)

           self.distros.add(distro,save=True)
           distros_added.append(distro)       

           existing_profile = self.profiles.find(name=name) 

           # see if the profile name is already used, if so, skip it and 
           # do not modify the existing profile

           if existing_profile is None:
               self.logger.info("creating new profile: %s" % name)
               #FIXME: The created profile holds a default kickstart, and should be breed specific
               profile = self.config.new_profile()
           else:
               self.logger.info("skipping existing profile, name already exists: %s" % name)
               continue

           # save our minimal profile which just points to the distribution and a good
           # default answer file

           profile.set_name(name)
           profile.set_distro(name)
           if self.kickstart_file:
               profile.set_kickstart(self.kickstart_file)
           else:
               profile.set_kickstart(importer.ks)

           # depending on the name of the profile we can define a good virt-type
           # for usage with koan

           if name.find("-xen") != -1:
               profile.set_virt_type("xenpv")
           else:
               profile.set_virt_type("qemu")

           # save our new profile to the collection

           self.profiles.add(profile,save=True)

           # Create a rescue image as well, if this is not a xen distro
           # but only for red hat profiles

           # this code disabled as it seems to be adding "-rescue" to 
           # distros that are /not/ rescue related, which is wrong.
           # left as a FIXME for those who find this feature interesting.

           #if name.find("-xen") == -1 and importer.breed == "redhat":
           #    rescue_name = 'rescue-' + name
           #    existing_profile = self.profiles.find(name=rescue_name)
           #
           #    if existing_profile is None:
           #        self.logger.info("creating new profile: %s" % rescue_name)
           #        profile = self.config.new_profile()
           #    else:
           #        continue
           #
           #    profile.set_name(rescue_name)
           #    profile.set_distro(name)
           #    profile.set_virt_type("qemu")
           #    profile.kernel_options['rescue'] = None
           #    profile.kickstart = '/var/lib/cobbler/kickstarts/pxerescue.ks'
           #
           #    self.profiles.add(profile,save=True)

       # self.api.serialize() # not required, is implicit

       return distros_added

   # ========================================================================

   def get_proposed_name(self,dirname,kernel=None):

       """
       Given a directory name where we have a kernel/initrd pair, try to autoname
       the distribution (and profile) object based on the contents of that path
       """

       if self.network_root is not None:
          name = self.mirror_name + "-".join(self.path_tail(os.path.dirname(self.path),dirname).split("/"))
       else:
          # remove the part that says /var/www/cobbler/ks_mirror/name
          name = "-".join(dirname.split("/")[5:])

       if kernel is not None and kernel.find("PAE") != -1:
          name = name + "-PAE"

       # These are all Ubuntu's doing, the netboot images are buried pretty
       # deep. ;-) -JC
       name = name.replace("-netboot","")
       name = name.replace("-ubuntu-installer","")
       name = name.replace("-amd64","")
       name = name.replace("-i386","")

       # we know that some kernel paths should not be in the name

       name = name.replace("-images","")
       name = name.replace("-pxeboot","")  
       name = name.replace("-install","")  

       # some paths above the media root may have extra path segments we want
       # to clean up

       name = name.replace("-os","")
       name = name.replace("-tree","")
       name = name.replace("var-www-cobbler-", "")
       name = name.replace("ks_mirror-","")
       name = name.replace("--","-")

       # remove any architecture name related string, as real arch will be appended later

       name = name.replace("chrp","ppc64")

       for separator in [ '-' , '_'  , '.' ] :
         for arch in [ "i386" , "x86_64" , "ia64" , "ppc64", "ppc32", "ppc", "x86" , "s390x", "s390" , "386" , "amd" ]:
           name = name.replace("%s%s" % ( separator , arch ),"")

       return name

   # ========================================================================

   def get_proposed_arch(self,dirname):
       """
       Given an directory name, can we infer an architecture from a path segment?
       """

       if dirname.find("x86_64") != -1 or dirname.find("amd") != -1:
          return "x86_64"
       if dirname.find("ia64") != -1:
          return "ia64"
       if dirname.find("i386") != -1 or dirname.find("386") != -1 or dirname.find("x86") != -1:
          return "i386"
       if dirname.find("s390x") != -1:
          return "s390x"
       if dirname.find("s390") != -1:
          return "s390"
       if dirname.find("ppc64") != -1 or dirname.find("chrp") != -1:
          return "ppc64"
       if dirname.find("ppc32") != -1:
          return "ppc"
       if dirname.find("ppc") != -1:
          return "ppc"
       return None

# ==============================================


def guess_breed(kerneldir,path,cli_breed,logger):

    """
    This tries to guess the distro. Traverses from kernel dir to imported root checking 
    for distro signatures, which are the locations in media where the search for release 
    packages should start.  When a debian/ubuntu pool is found, the upper directory should 
    be checked to get the real breed. If we are on a real media, the upper directory will 
    be at the same level, as a local '.' symlink
    The lowercase names are required for fat32/vfat filesystems
    """
    signatures = [
       [ 'pool'        , "debian" ],
       [ 'RedHat/RPMS' , "redhat" ],
       [ 'RedHat/rpms' , "redhat" ],
       [ 'RedHat/Base' , "redhat" ],
       [ 'Fedora/RPMS' , "redhat" ],
       [ 'Fedora/rpms' , "redhat" ],
       [ 'CentOS/RPMS' , "redhat" ],
       [ 'CentOS/rpms' , "redhat" ],
       [ 'CentOS'      , "redhat" ],
       [ 'Packages'    , "redhat" ],
       [ 'Fedora'      , "redhat" ],
       [ 'Server'      , "redhat" ],
       [ 'Client'      , "redhat" ],
       [ 'isolinux.bin', None ],
    ]
    guess = None

    while kerneldir != os.path.dirname(path) :
        logger.info("scanning %s for distro signature" % kerneldir)
        for (x, breedguess) in signatures:
            d = os.path.join( kerneldir , x )
            if os.path.exists( d ):
                guess = breedguess
                break
        if guess: 
            break

        kerneldir = os.path.dirname(kerneldir)
    else:
        if cli_breed:
            logger.info("Warning: No distro signature for kernel at %s, using value from command line" % kerneldir)
            return (cli_breed , kerneldir , None)
        utils.die(logger, "No distro signature for kernel at %s" % kerneldir )

    if guess == "debian" :
        for suite in [ "debian" , "ubuntu" ] :
            # NOTE : Although we break the loop after the first match, 
            # multiple debian derived distros can actually live at the same pool -- JP
            d = os.path.join( kerneldir , suite )
            if os.path.islink(d) and os.path.isdir(d):
                if os.path.realpath(d) == os.path.realpath(kerneldir):
                    return (suite, kerneldir ,x)
            if os.path.basename( kerneldir ) == suite :
                return (suite , kerneldir , x)

    return (guess, kerneldir , x)

# ============================================================


def import_factory(kerneldir,path,cli_breed,logger):
    """
    Given a directory containing a kernel, return an instance of an Importer
    that can be used to complete the import.
    """

    breed , rootdir, pkgdir = guess_breed(kerneldir,path,cli_breed,logger)
    # NOTE : The guess_breed code should be included in the factory, in order to make 
    # the real root directory available, so allowing kernels at different levels within 
    # the same tree (removing the isolinux rejection from distro_adder) -- JP

    if rootdir[1]:
        logger.info("found content (breed=%s) at %s" % (breed,os.path.join( rootdir[0] , rootdir[1])))
    else:
        logger.info("found content (breed=%s) at %s" % (breed,rootdir[0]))
    if cli_breed:
        if cli_breed != breed:
            utils.die(logger, "Requested breed (%s); breed found is %s" % ( cli_breed , breed ) )
        breed = cli_breed

    if breed == "redhat":
        return RedHatImporter(logger,rootdir,pkgdir)
    # disabled for 2.0
    #elif breed == "debian":
    #    return DebianImporter(logger,rootdir,pkgdir)
    #elif breed == "ubuntu":
    #    return UbuntuImporter(logger,rootdir,pkgdir)
    elif breed:
        utils.die(logger, "Unsupported OS breed %s" % breed)


class BaseImporter:
   """
   Base class for distribution specific importer code.
   """

   # FIXME : Rename learn_arch_from_tree into guess_arch and simplify. 
   # FIXME : Drop package extension check and make a single search for all names.
   # FIXME:  Next methods to be moved here: kickstart_finder TRY_LIST loop

   # ===================================================================

   def arch_walker(self,foo,dirname,fnames):
       """
       See docs on learn_arch_from_tree.

       The TRY_LIST is used to speed up search, and should be dropped for default importer
       Searched kernel names are kernel-header, linux-headers-, kernel-largesmp, kernel-hugemem
       
       This method is useful to get the archs, but also to package type and a raw guess of the breed
       """
 
       # try to find a kernel header RPM and then look at it's arch.
       for x in fnames:
           if self.match_kernelarch_file(x):
               for arch in [ "i386" , "x86_64" , "ia64" , "ppc64", "ppc", "s390", "s390x" ]:
                   if x.find(arch) != -1:
                       foo[arch] = 1
               for arch in [ "i686" , "amd64" ]:
                   if x.find(arch) != -1:
                       foo[arch] = 1
   
   # ===================================================================

   def get_rootdir(self):
       return self.rootdir
   
   # ===================================================================

   def get_pkgdir(self):
       if not self.pkgdir:
           return None
       return os.path.join(self.get_rootdir(),self.pkgdir)
   
   # ===================================================================

   def set_install_tree(self, distro, url):
       distro.ks_meta["tree"] = url
   
   # ===================================================================

   def learn_arch_from_tree(self):
       """ 
       If a distribution is imported from DVD, there is a good chance the path doesn't 
       contain the arch and we should add it back in so that it's part of the 
       meaningful name ... so this code helps figure out the arch name.  This is important 
       for producing predictable distro names (and profile names) from differing import sources
       """
       result = {}
       # FIXME : this is called only once, should not be a walk      
       if self.get_pkgdir():
           os.path.walk(self.get_pkgdir(), self.arch_walker, result)      
       if result.pop("amd64",False):
           result["x86_64"] = 1
       if result.pop("i686",False):
           result["i386"] = 1
       return result.keys()

   def get_datestamp(self):
       """
       Allows each breed to return its datetime stamp
       """
       return None
   # ===================================================================

   def __init__(self,logger,rootdir,pkgdir):
       raise exceptions.NotImplementedError
   
   # ===================================================================

   def process_repos(self, main_importer, distro):
       raise exceptions.NotImplementedError

# ===================================================================
# ===================================================================

class RedHatImporter ( BaseImporter ) :

   def __init__(self,logger,rootdir,pkgdir):
       self.breed = "redhat"
       self.ks = "/var/lib/cobbler/kickstarts/default.ks"
       self.rootdir = rootdir
       self.pkgdir = pkgdir
       self.logger = logger

   # ================================================================

   def get_release_files(self):
       data = glob.glob(os.path.join(self.get_pkgdir(), "*release-*"))
       data2 = []
       for x in data:
          b = os.path.basename(x)
          if b.find("fedora") != -1 or \
             b.find("redhat") != -1 or \
             b.find("centos") != -1:
                 data2.append(x)
       return data2

   # ================================================================

   def match_kernelarch_file(self, filename):
       """
       Is the given filename a kernel filename?
       """

       if not filename.endswith("rpm") and not filename.endswith("deb"):
           return False
       for match in ["kernel-header", "kernel-source", "kernel-smp", "kernel-largesmp", "kernel-hugemem", "linux-headers-", "kernel-devel", "kernel-"]:
           if filename.find(match) != -1:
               return True
       return False

   # ================================================================

   def scan_pkg_filename(self, rpm):
       """
       Determine what the distro is based on the release package filename.
       """

       rpm = os.path.basename(rpm)

       # if it looks like a RHEL RPM we'll cheat.
       # it may be slightly wrong, but it will be close enough
       # for RHEL5 we can get it exactly.
       
       for x in [ "4AS", "4ES", "4WS", "4common", "4Desktop" ]:
          if rpm.find(x) != -1:
             return ("redhat", 4, 0)
       for x in [ "3AS", "3ES", "3WS", "3Desktop" ]:
          if rpm.find(x) != -1:
             return ("redhat", 3, 0)
       for x in [ "2AS", "2ES", "2WS", "2Desktop" ]:
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

   def get_datestamp(self):
       """
       Based on a RedHat tree find the creation timestamp
       """
       base = self.get_rootdir()
       if os.path.exists("%s/.discinfo" % base):
           discinfo = open("%s/.discinfo" % base, "r")
           datestamp = discinfo.read().split("\n")[0]
           discinfo.close()
       else:
           return 0
       return float(datestamp)

   def set_variance(self, flavor, major, minor, arch):
  
       """
       find the profile kickstart and set the distro breed/os-version based on what
       we can find out from the rpm filenames and then return the kickstart
       path to use.
       """

       if flavor == "fedora":

           # this may actually fail because the libvirt/virtinst database
           # is not always up to date.  We keep a simplified copy of this
           # in codes.py.  If it fails we set it to something generic
           # and don't worry about it.

           try:
               os_version = "fedora%s" % int(major)
           except:
               os_version = "other"

       if flavor == "redhat" or flavor == "centos":

           if major <= 2:
                # rhel2.1 is the only rhel2
                os_version = "rhel2.1"
           else:
                try:
                    # must use libvirt version
                    os_version = "rhel%s" % (int(major))
                except:
                    os_version = "other"

       kickbase = "/var/lib/cobbler/kickstarts"
       # Look for ARCH/OS_VERSION.MINOR kickstart first
       #          ARCH/OS_VERSION next
       #          OS_VERSION next
       #          OS_VERSION.MINOR next
       #          ARCH/default.ks next
       #          FLAVOR.ks next
       kickstarts = [
           "%s/%s/%s.%i.ks" % (kickbase,arch,os_version,int(minor)), 
           "%s/%s/%s.ks" % (kickbase,arch,os_version), 
           "%s/%s.%i.ks" % (kickbase,os_version,int(minor)),
           "%s/%s.ks" % (kickbase,os_version),
           "%s/%s/default.ks" % (kickbase,arch),
           "%s/%s.ks" % (kickbase,flavor),
       ]
       for kickstart in kickstarts:
           if os.path.exists(kickstart):
               return os_version, kickstart

       major = int(major) 

       if flavor == "fedora":
           if major >= 8:
                return os_version , "/var/lib/cobbler/kickstarts/sample_end.ks"
           if major >= 6:
                return os_version , "/var/lib/cobbler/kickstarts/sample.ks"

       if flavor == "redhat" or flavor == "centos":
           if major >= 5:
                return os_version , "/var/lib/cobbler/kickstarts/sample.ks"

           return os_version , "/var/lib/cobbler/kickstarts/legacy.ks"

       self.logger.warning("could not use distro specifics, using rhel 4 compatible kickstart")
       return None , "/var/lib/cobbler/kickstarts/legacy.ks"

#class DebianImporter ( BaseImporter ) :
#
#   def __init__(self,logger,rootdir,pkgdir):
#       self.breed = "debian"
#       self.ks = "/var/lib/cobbler/kickstarts/sample.seed"
#       self.rootdir = rootdir
#       self.pkgdir = pkgdir
#       self.logger = logger
#
#   def get_release_files(self):
#       if not self.get_pkgdir():
#           return []
#       # search for base-files or base-installer ?
#       return glob.glob(os.path.join(self.get_pkgdir(), "main/b/base-files" , "base-files_*"))
#
#   def match_kernelarch_file(self, filename):
#       if not filename.endswith("deb"):
#           return False
#       if filename.startswith("linux-headers-"):
#           return True
#       return False
#
#   def scan_pkg_filename(self, deb):
#
#       deb = os.path.basename(deb)
#       self.logger.info("processing deb : %s" % deb)
#
#       # get all the tokens and try to guess a version
#       accum = []
#       tokens = deb.split("_")
#       tokens2 = tokens[1].split(".")
#       for t2 in tokens2:
#          try:
#              val = int(t2)
#              accum.append(val)
#          except:
#              pass
#       # Safeguard for non-guessable versions
#       if not accum:
#          return None
#       accum.append(0)
#
#       return (None, accum[0], accum[1])
#
#   def set_variance(self, flavor, major, minor, arch):
#
#       dist_names = { '4.0' : "etch" , '5.0' : "lenny" }
#       dist_vers = "%s.%s" % ( major , minor )
#       os_version = dist_names[dist_vers]
#
#       return os_version , "/var/lib/cobbler/kickstarts/sample.seed"
#
#   def set_install_tree(self, distro, url):
#       idx = url.find("://")
#       url = url[idx+3:]
#
#       idx = url.find("/")
#       distro.ks_meta["hostname"] = url[:idx]
#       distro.ks_meta["directory"] = url[idx:]
#       if not distro.os_version :
#           utils.die(self.logger, "OS version is required for debian distros")
#       distro.ks_meta["suite"] = distro.os_version
#   
#   def process_repos(self, main_importer, distro):
#
#       # Create a disabled repository for the new distro, and the security updates
#       #
#       # NOTE : We cannot use ks_meta nor os_version because they get fixed at a later stage
#
#       repo = item_repo.Repo(main_importer.config)
#       repo.set_breed( "apt" )
#       repo.set_arch( distro.arch )
#       repo.set_keep_updated( False )
#       repo.yumopts["--ignore-release-gpg"] = None
#       repo.yumopts["--verbose"] = None
#       repo.set_name( distro.name )
#       repo.set_os_version( distro.os_version )
#       # NOTE : The location of the mirror should come from timezone
#       repo.set_mirror( "http://ftp.%s.debian.org/debian/dists/%s" % ( 'us' , '@@suite@@' ) )
#
#       security_repo = item_repo.Repo(main_importer.config)
#       security_repo.set_breed( "apt" )
#       security_repo.set_arch( distro.arch )
#       security_repo.set_keep_updated( False )
#       security_repo.yumopts["--ignore-release-gpg"] = None
#       security_repo.yumopts["--verbose"] = None
#       security_repo.set_name( distro.name + "-security" )
#       security_repo.set_os_version( distro.os_version )
#       # There are no official mirrors for security updates
#       security_repo.set_mirror( "http://security.debian.org/debian-security/dists/%s/updates" % '@@suite@@' )
#
#       self.logger.info("Added repos for %s" % distro.name)
#       repos  = main_importer.config.repos()
#       repos.add(repo,save=True)
#       repos.add(security_repo,save=True)


#class UbuntuImporter ( DebianImporter ) :
#
#   def __init__(self,rootdir,pkgdir):
#       DebianImporter.__init__(self,rootdir,pkgdir)
#       self.breed = "ubuntu"
#
#   def get_release_files(self):
#       if not self.get_pkgdir():
#           return []
#       return glob.glob(os.path.join(self.get_pkgdir(), "main/u/ubuntu-docs" , "ubuntu-docs_*"))
#
#   def set_variance(self, flavor, major, minor, arch):
#  
#       # Release names taken from wikipedia
#       dist_names = { '6.4':"dapper", '8.4':"hardy", '8.10':"intrepid", '9.4':"jaunty" }
#       dist_vers = "%s.%s" % ( major , minor )
#       if not dist_names.has_key( dist_vers ):
#           dist_names['4ubuntu2.0'] = "IntrepidIbex"
#       os_version = dist_names[dist_vers]
#
#       return os_version , "/var/lib/cobbler/kickstarts/sample.seed"
#
#   def process_repos(self, main_importer, distro):
#
#       pass


