"""
This is some of the code behind 'cobbler sync'.

Copyright 2006-2009, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>
John Eckersberg <jeckersb@redhat.com>

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

import os
import os.path
import shutil
import time
import sys
import glob
import traceback
import errno
import re
from utils import popen2
from shlex import shlex


import utils
from cexceptions import *
import templar

import item_distro
import item_profile
import item_repo
import item_system

from utils import _

# FIXME: add --quiet depending on if not --verbose?
RSYNC_CMD =  "rsync -a %s '%s' %s --exclude-from=/etc/cobbler/rsync.exclude --progress"

def register():
   """
   The mandatory cobbler module registration hook.
   """
   return "manage/import"


class ImportDebianUbuntuManager:

    def __init__(self,config,logger):
        """
        Constructor
        """
        self.logger        = logger
        self.config        = config
        self.api           = config.api
        self.distros       = config.distros()
        self.profiles      = config.profiles()
        self.systems       = config.systems()
        self.settings      = config.settings()
        self.repos         = config.repos()
        self.templar       = templar.Templar(config)

    # required function for import modules
    def what(self):
        return "import/debian_ubuntu"

    # required function for import modules
    def check_for_signature(self,path,cli_breed):
       signatures = [
           'pool',
       ]

       self.logger.info("scanning %s for distro signature" % path)
       for signature in signatures:
           d = os.path.join(path,signature)
           if os.path.exists(d):
               self.logger.info("Found a debian-based compatible signature: %s" % signature)
               return (True,signature)

       if cli_breed and cli_breed in self.get_valid_breeds():
           self.logger.info("Warning: No distro signature for kernel at %s, using value from command line" % path)
           return (True,None)

       return (False,None)

    # required function for import modules
    def run(self,pkgdir,mirror,mirror_name,network_root=None,kickstart_file=None,rsync_flags=None,arch=None,breed=None,os_version=None):
        self.pkgdir = pkgdir
        self.mirror = mirror
        self.mirror_name = mirror_name
        self.network_root = network_root
        self.kickstart_file = kickstart_file
        self.rsync_flags = rsync_flags
        self.arch = arch
        self.breed = breed
        self.os_version = os_version

        # some fixups for the XMLRPC interface, which does not use "None"
        if self.arch == "":           self.arch           = None
        if self.mirror == "":         self.mirror         = None
        if self.mirror_name == "":    self.mirror_name    = None
        if self.kickstart_file == "": self.kickstart_file = None
        if self.os_version == "":     self.os_version     = None
        if self.rsync_flags == "":    self.rsync_flags    = None
        if self.network_root == "":   self.network_root   = None

        # If no breed was specified on the command line, figure it out
        if self.breed == None:
            self.breed = self.get_breed_from_directory()
            if not self.breed:
                utils.die(self.logger,"import failed - could not determine breed of debian-based distro")
               
        # debug log stuff for testing
        #self.logger.info("DEBUG: self.pkgdir = %s" % str(self.pkgdir))
        #self.logger.info("DEBUG: self.mirror = %s" % str(self.mirror))
        #self.logger.info("DEBUG: self.mirror_name = %s" % str(self.mirror_name))
        #self.logger.info("DEBUG: self.network_root = %s" % str(self.network_root))
        #self.logger.info("DEBUG: self.kickstart_file = %s" % str(self.kickstart_file))
        #self.logger.info("DEBUG: self.rsync_flags = %s" % str(self.rsync_flags))
        #self.logger.info("DEBUG: self.arch = %s" % str(self.arch))
        #self.logger.info("DEBUG: self.breed = %s" % str(self.breed))
        #self.logger.info("DEBUG: self.os_version = %s" % str(self.os_version))

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
            if self.arch not in self.get_valid_arches():
                utils.die(self.logger,"arch must be one of: %s" % string.join(self.get_valid_arches(),", "))

        # if we're going to do any copying, set where to put things
        # and then make sure nothing is already there.

        self.path = os.path.normpath( "%s/ks_mirror/%s" % (self.settings.webdir, self.mirror_name) )
        if os.path.exists(self.path) and self.arch is None:
            # FIXME : Raise exception even when network_root is given ?
            utils.die(self.logger,"Something already exists at this import location (%s).  You must specify --arch to avoid potentially overwriting existing files." % self.path)

        # import takes a --kickstart for forcing selection that can't be used in all circumstances

        if self.kickstart_file and not self.breed:
            utils.die(self.logger,"Kickstart file can only be specified when a specific breed is selected")

        if self.os_version and not self.breed:
            utils.die(self.logger,"OS version can only be specified when a specific breed is selected")

        if self.breed and self.breed.lower() not in self.get_valid_breeds():
            utils.die(self.logger,"Supplied import breed is not supported by this module")

        # if --arch is supplied, make sure the user is not importing a path with a different
        # arch, which would just be silly.

        if self.arch:
            # append the arch path to the name if the arch is not already
            # found in the name.
            for x in self.get_valid_arches():
                if self.path.lower().find(x) != -1:
                    if self.arch != x :
                        utils.die(self.logger,"Architecture found on pathname (%s) does not fit the one given in command line (%s)"%(x,self.arch))
                    break
            else:
                # FIXME : This is very likely removed later at get_proposed_name, and the guessed arch appended again
                self.path += ("-%s" % self.arch)

        # make the output path and mirror content but only if not specifying that a network
        # accessible support location already exists (this is --available-as on the command line)

        if self.network_root is None:
            # we need to mirror (copy) the files

            utils.mkdir(self.path)

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

                utils.run_this(rsync_cmd, (spacer, self.mirror, self.path), self.logger)

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

        # find the most appropriate answer files for each profile object

        self.logger.info("associating kickstarts")
        self.kickstart_finder(distros_added)

        # ensure bootloaders are present
        self.api.pxegen.copy_bootloaders()

        return True

    # required function for import modules
    def get_valid_arches(self):
        return ["i386", "x86_64", "x86",]

    # required function for import modules
    def get_valid_breeds(self):
        return ["debian","ubuntu"]

    # required function for import modules
    def get_valid_os_versions(self):
        return ["dapper", "hardy", "intrepid", "jaunty", "karmic", "lucid", "maverick", "natty"]

    def get_release_files(self):
        """
        Find distro release packages.
        """
        if self.breed == "debian":
            return glob.glob(os.path.join(self.get_pkgdir(), "main/b/base-files" , "base-files_*"))
        elif self.breed == "ubuntu":
            return glob.glob(os.path.join(self.get_rootdir(), "dists/*"))
        else:
            return []

    def get_breed_from_directory(self):
        for breed in self.get_valid_breeds():
            # NOTE : Although we break the loop after the first match,
            # multiple debian derived distros can actually live at the same pool -- JP
            d = os.path.join(self.mirror, breed)
            if (os.path.islink(d) and os.path.isdir(d) and os.path.realpath(d) == os.path.realpath(self.mirror)) or os.path.basename(self.mirror) == breed:
                return breed
        else:
            return None

    def get_tree_location(self, distro):
        """
        Once a distribution is identified, find the part of the distribution
        that has the URL in it that we want to use for kickstarting the
        distribution, and create a ksmeta variable $tree that contains this.
        """

        base = self.get_rootdir()

        if self.network_root is None:
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
            self.set_install_tree(distro, tree)
        else:
            # where we assign the kickstart source is relative to our current directory
            # and the input start directory in the crawl.  We find the path segments
            # between and tack them on the network source path to find the explicit
            # network path to the distro that Anaconda can digest.
            tail = self.path_tail(self.path, base)
            tree = self.network_root[:-1] + tail
            self.set_install_tree(distro, tree)

        return

    def distro_adder(self,distros_added,dirname,fnames):
        """
        This is an os.path.walk routine that finds distributions in the directory
        to be scanned and then creates them.
        """

        # FIXME: If there are more than one kernel or initrd image on the same directory,
        # results are unpredictable

        initrd = None
        kernel = None

        for x in fnames:
            adtls = []

            fullname = os.path.join(dirname,x)
            if os.path.islink(fullname) and os.path.isdir(fullname):
                if fullname.startswith(self.path):
                    self.logger.warning("avoiding symlink loop")
                    continue
                self.logger.info("following symlink: %s" % fullname)
                os.path.walk(fullname, self.distro_adder, distros_added)

            if ( x.startswith("initrd") or x.startswith("ramdisk.image.gz") or x.startswith("vmkboot.gz") ) and x != "initrd.size":
                initrd = os.path.join(dirname,x)
            if ( x.startswith("vmlinu") or x.startswith("kernel.img") or x.startswith("linux") or x.startswith("mboot.c32") ) and x.find("initrd") == -1:
                kernel = os.path.join(dirname,x)

            # if we've collected a matching kernel and initrd pair, turn the in and add them to the list
            if initrd is not None and kernel is not None:
                adtls.append(self.add_entry(dirname,kernel,initrd))
                kernel = None
                initrd = None

            for adtl in adtls:
                distros_added.extend(adtl)

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

        archs = self.learn_arch_from_tree()
        if not archs:
            if self.arch:
                archs.append( self.arch )
        else:
            if self.arch and self.arch not in archs:
                utils.die(self.logger, "Given arch (%s) not found on imported tree %s"%(self.arch,self.get_pkgdir()))
        if proposed_arch:
            if archs and proposed_arch not in archs:
                self.logger.warning("arch from pathname (%s) not found on imported tree %s" % (proposed_arch,self.get_pkgdir()))
                return

            archs = [ proposed_arch ]

        if len(archs)>1:
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
            distro.set_breed(self.breed)
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
            profile.set_kickstart(self.kickstart_file)

            # depending on the name of the profile we can define a good virt-type
            # for usage with koan

            if name.find("-xen") != -1:
                profile.set_virt_type("xenpv")
            else:
                profile.set_virt_type("qemu")

            # save our new profile to the collection

            self.profiles.add(profile,save=True)

        return distros_added

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
        name = name.replace("-isolinux","")

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
                for arch in self.get_valid_arches():
                    if x.find(arch) != -1:
                        foo[arch] = 1
                for arch in [ "i686" , "amd64" ]:
                    if x.find(arch) != -1:
                        foo[arch] = 1

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
            if self.kickstart_file == None:
                for file in self.get_release_files():
                    results = self.scan_pkg_filename(file)
                    # FIXME : If os is not found on tree but set with CLI, no kickstart is searched
                    if results is None:
                        self.logger.warning("skipping %s" % file)
                        continue
                    (flavor, major, minor) = results
                    version , ks = self.set_variance(flavor, major, minor, distro.arch)
                    if self.os_version:
                        if self.os_version != version:
                            utils.die(self.logger,"CLI version differs from tree : %s vs. %s" % (self.os_version,version))
                    ds = self.get_datestamp()
                    distro.set_comment("%s %s (%s.%s) %s" % (self.breed,version,major,minor,self.arch))
                    distro.set_os_version(version)
                    if ds is not None:
                        distro.set_tree_build_time(ds)
                    profile.set_kickstart(ks)
                    self.profiles.add(profile,save=True)

            self.configure_tree_location(distro)
            self.distros.add(distro,save=True) # re-save
            self.api.serialize()

    def configure_tree_location(self, distro):
        """
        Once a distribution is identified, find the part of the distribution
        that has the URL in it that we want to use for kickstarting the
        distribution, and create a ksmeta variable $tree that contains this.
        """

        base = self.get_rootdir()

        if self.network_root is None:
            dists_path = os.path.join( self.path , "dists" )
            if os.path.isdir( dists_path ):
                tree = "http://@@http_server@@/cblr/ks_mirror/%s" % (self.mirror_name)
            else:
                tree = "http://@@http_server@@/cblr/repo_mirror/%s" % (distro.name)
            self.set_install_tree(distro, tree)
        else:
            # where we assign the kickstart source is relative to our current directory
            # and the input start directory in the crawl.  We find the path segments
            # between and tack them on the network source path to find the explicit
            # network path to the distro that Anaconda can digest.
            tail = utils.path_tail(self.path, base)
            tree = self.network_root[:-1] + tail
            self.set_install_tree(distro, tree)

    def get_rootdir(self):
        return self.mirror

    def get_pkgdir(self):
        if not self.pkgdir:
            return None
        return os.path.join(self.get_rootdir(),self.pkgdir)

    def set_install_tree(self, distro, url):
        idx = url.find("://")
        url = url[idx+3:]

        idx = url.find("/")
        distro.ks_meta["hostname"] = url[:idx]
        distro.ks_meta["directory"] = url[idx:]
        if not distro.os_version :
            utils.die(self.logger, "OS version is required for debian distros")
        distro.ks_meta["suite"] = distro.os_version

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

    def match_kernelarch_file(self, filename):
        """
        Is the given filename a kernel filename?
        """
        if not filename.endswith("deb"):
            return False
        if filename.startswith("linux-headers-"):
            return True
        return False

    def scan_pkg_filename(self, file):
        """
        Determine what the distro is based on the release package filename.
        """
        file = os.path.basename(file)

        if self.breed == "debian":
            self.logger.info("processing deb : %s" % file)
            # get all the tokens and try to guess a version
            accum = []
            tokens = file.split("_")
            tokens2 = tokens[1].split(".")
            self.logger.info("DEBUG: tokens = %s, tokens2 = %s" % (str(tokens), str(tokens2)))
            for t2 in tokens2:
               try:
                   self.logger.info("DEBUG: t2 = %s" % t2)
                   val = int(t2)
                   accum.append(val)
               except:
                   self.logger.info("DEBUG: not an int")
                   pass
            # Safeguard for non-guessable versions
            self.logger.info("DEBUG: accum = %s" % str(accum))
            if not accum:
               return None
            accum.append(0)

            return (file, accum[0], accum[1])
        elif self.breed == "ubuntu":
            #self.logger.info("scanning file : %s" % file)
            dist_names = { "dapper"  : (6,4),
                           "hardy"   : (8,4),
                           "intrepid": (8,10),
                           "jaunty"  : (9,4),
                           "karmic"  : (9,10),
                           "lynx"    : (10,4),
                           "maverick": (10,10),
                           "natty"   : (11,4),
                         }
            if file in dist_names.keys():
                return (file, dist_names[file][0], dist_names[file][1])
            else:
                return None

    def get_datestamp(self):
        """
        Based on a VMWare tree find the creation timestamp
        """
        pass

    def set_variance(self, flavor, major, minor, arch):
        """
        Set distro specific versioning.
        """

        if self.breed == "debian":
            dist_names = { '4.0' : "etch" , '5.0' : "lenny" }
            dist_vers = "%s.%s" % ( major , minor )
            os_version = dist_names[dist_vers]

            return os_version , "/var/lib/cobbler/kickstarts/sample.seed"
        elif self.breed == "ubuntu":
            # Release names taken from wikipedia
            dist_names = { '6.4'  :"dapper", 
                           '8.4'  :"hardy", 
                           '8.10' :"intrepid", 
                           '9.4'  :"jaunty",
                           '9.10' :"karmic",
                           '10.4' :"lynx",
                           '10.10':"maverick",
                           '11.4' :"natty",
                         }
            dist_vers = "%s.%s" % ( major , minor )
            if not dist_names.has_key( dist_vers ):
                dist_names['4ubuntu2.0'] = "IntrepidIbex"
            os_version = dist_names[dist_vers]
 
            return os_version , "/var/lib/cobbler/kickstarts/sample.seed"
        else:
            return None

    def process_repos(self, main_importer, distro):

        # Create a disabled repository for the new distro, and the security updates
        #
        # NOTE : We cannot use ks_meta nor os_version because they get fixed at a later stage

        repo = item_repo.Repo(main_importer.config)
        repo.set_breed( "apt" )
        repo.set_arch( distro.arch )
        repo.set_keep_updated( False )
        repo.yumopts["--ignore-release-gpg"] = None
        repo.yumopts["--verbose"] = None
        repo.set_name( distro.name )
        repo.set_os_version( distro.os_version )
        # NOTE : The location of the mirror should come from timezone
        repo.set_mirror( "http://ftp.%s.debian.org/debian/dists/%s" % ( 'us' , '@@suite@@' ) )

        security_repo = item_repo.Repo(main_importer.config)
        security_repo.set_breed( "apt" )
        security_repo.set_arch( distro.arch )
        security_repo.set_keep_updated( False )
        security_repo.yumopts["--ignore-release-gpg"] = None
        security_repo.yumopts["--verbose"] = None
        security_repo.set_name( distro.name + "-security" )
        security_repo.set_os_version( distro.os_version )
        # There are no official mirrors for security updates
        security_repo.set_mirror( "http://security.debian.org/debian-security/dists/%s/updates" % '@@suite@@' )

        self.logger.info("Added repos for %s" % distro.name)
        repos  = main_importer.config.repos()
        repos.add(repo,save=True)
        repos.add(security_repo,save=True)

# ==========================================================================

def get_import_manager(config,logger):
    return ImportDebianUbuntuManager(config,logger)
