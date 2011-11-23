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

import codes
import utils
from cexceptions import *
import templar

import item_distro
import item_profile
import item_repo
import item_system

from utils import _

# Import aptsources module if available to obtain repo mirror.
try:
    from aptsources import distro
    from aptsources import sourceslist
    apt_available = True
except:
    apt_available = False

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

       #self.logger.info("scanning %s for a debian/ubuntu distro signature" % path)
       for signature in signatures:
           d = os.path.join(path,signature)
           if os.path.exists(d):
               self.logger.info("Found a debian/ubuntu compatible signature: %s" % signature)
               return (True,signature)

       if cli_breed and cli_breed in self.get_valid_breeds():
           self.logger.info("Warning: No distro signature for kernel at %s, using value from command line" % path)
           return (True,None)

       return (False,None)

    # required function for import modules
    def run(self,pkgdir,name,path,network_root=None,kickstart_file=None,rsync_flags=None,arch=None,breed=None,os_version=None):
        self.pkgdir = pkgdir
        self.name = name
        self.network_root = network_root
        self.kickstart_file = kickstart_file
        self.rsync_flags = rsync_flags
        self.arch = arch
        self.breed = breed
        self.os_version = os_version
        self.path = path

        # some fixups for the XMLRPC interface, which does not use "None"
        if self.arch == "":           self.arch           = None
        if self.kickstart_file == "": self.kickstart_file = None
        if self.os_version == "":     self.os_version     = None
        if self.rsync_flags == "":    self.rsync_flags    = None
        if self.network_root == "":   self.network_root   = None

        # If no breed was specified on the command line, figure it out
        if self.breed == None:
            self.breed = self.get_breed_from_directory()
            if not self.breed:
                utils.die(self.logger,"import failed - could not determine breed of debian-based distro")
               
        # if we're going to do any copying, set where to put things
        # and then make sure nothing is already there.

        # import takes a --kickstart for forcing selection that can't be used in all circumstances

        if self.kickstart_file and not self.breed:
            utils.die(self.logger,"Kickstart file can only be specified when a specific breed is selected")

        if self.os_version and not self.breed:
            utils.die(self.logger,"OS version can only be specified when a specific breed is selected")

        if self.breed and self.breed.lower() not in self.get_valid_breeds():
            utils.die(self.logger,"Supplied import breed is not supported by this module")

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

    # required function for import modules
    def get_valid_arches(self):
        return ["i386", "ppc", "x86_64", "x86",]

    # required function for import modules
    def get_valid_breeds(self):
        return ["debian","ubuntu"]

    # required function for import modules
    def get_valid_os_versions(self):
        if self.breed == "debian":
            return codes.VALID_OS_VERSIONS["debian"]
        elif self.breed == "ubuntu":
            return codes.VALID_OS_VERSIONS["ubuntu"]
        else:
            return []

    def get_valid_repo_breeds(self):
        return ["apt",]

    def get_release_files(self):
        """
        Find distro release packages.
        """
        return glob.glob(os.path.join(self.get_rootdir(), "dists/*"))

    def get_breed_from_directory(self):
        for breed in self.get_valid_breeds():
            # NOTE : Although we break the loop after the first match,
            # multiple debian derived distros can actually live at the same pool -- JP
            d = os.path.join(self.path, breed)
            if (os.path.islink(d) and os.path.isdir(d) and os.path.realpath(d) == os.path.realpath(self.path)) or os.path.basename(self.path) == breed:
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
            dists_path = os.path.join(self.path, "dists")
            if os.path.isdir(dists_path):
                tree = "http://@@http_server@@/cblr/ks_mirror/%s" % (self.name)
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

        return

    def repo_finder(self, distros_added):
        for distro in distros_added:
            self.logger.info("traversing distro %s" % distro.name)
            # FIXME : Shouldn't decide this the value of self.network_root ?
            if distro.kernel.find("ks_mirror") != -1:
                basepath = os.path.dirname(distro.kernel)
                top = self.get_rootdir()
                self.logger.info("descent into %s" % top)
                dists_path = os.path.join(self.path, "dists")
                if not os.path.isdir(dists_path):
                    self.process_repos(self, distro)
            else:
                self.logger.info("this distro isn't mirrored")

    def get_repo_mirror_from_apt(self):
        """
        This tries to determine the apt mirror/archive to use (when processing repos)
        if the host machine is Debian or Ubuntu.
        """
        try:
            sources = sourceslist.SourcesList()
            release = distro.get_distro()
            release.get_sources(sources)
            mirrors = release.get_server_list()
            for mirror in mirrors:
                if mirror[2] == True:
                    mirror = mirror[1]
                    break
        except:
            return False

        return mirror

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
            self.logger.error("Arch from pathname (%s) does not match with supplied one (%s)"%(proposed_arch,self.arch))
            return

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
            elif name.find("vmware") != -1:
                profile.set_virt_type("vmware")
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
            name = self.name #+ "-".join(utils.path_tail(os.path.dirname(self.path),dirname).split("/"))
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
                    (flavor, major, minor, release) = results
                    # Why use set_variance()? scan_pkg_filename() does everything we need now - jcammarata
                    #version , ks = self.set_variance(flavor, major, minor, distro.arch)
                    if self.os_version:
                        if self.os_version != flavor:
                            utils.die(self.logger,"CLI version differs from tree : %s vs. %s" % (self.os_version,flavor))
                    distro.set_comment("%s %s (%s.%s.%s) %s" % (self.breed,flavor,major,minor,release,self.arch))
                    distro.set_os_version(flavor)
                    # is this even valid for debian/ubuntu? - jcammarata
                    #ds = self.get_datestamp()
                    #if ds is not None:
                    #    distro.set_tree_build_time(ds)
                    profile.set_kickstart("/var/lib/cobbler/kickstarts/sample.seed")
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
                tree = "http://@@http_server@@/cblr/ks_mirror/%s" % (self.name)
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
        return self.path

    def get_pkgdir(self):
        if not self.pkgdir:
            return None
        return os.path.join(self.get_rootdir(),self.pkgdir)

    def set_install_tree(self, distro, url):
        distro.ks_meta["tree"] = url

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
        if result.pop("x86",False):
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
        # FIXME: all of these dist_names should probably be put in a function
        # which would be called in place of looking in codes.py.  Right now
        # you have to update both codes.py and this to add a new release
        if self.breed == "debian":
            dist_names = ['etch','lenny',]
        elif self.breed == "ubuntu":
            dist_names = ['dapper','hardy','intrepid','jaunty','karmic','lynx','maverick','natty',]
        else:
            return None

        if os.path.basename(file) in dist_names:
            release_file = os.path.join(file,'Release')
            self.logger.info("Found %s release file: %s" % (self.breed,release_file))

            f = open(release_file,'r')
            lines = f.readlines()
            f.close()

            for line in lines:
                if line.lower().startswith('version: '):
                    version = line.split(':')[1].strip()
                    values = version.split('.')
                    if len(values) == 1:
                        # I don't think you'd ever hit this currently with debian or ubuntu,
                        # just including it for safety reasons
                        return (os.path.basename(file), values[0], "0", "0")
                    elif len(values) == 2:
                        return (os.path.basename(file), values[0], values[1], "0")
                    elif len(values) > 2:
                        return (os.path.basename(file), values[0], values[1], values[2])
        return None

    def get_datestamp(self):
        """
        Not used for debian/ubuntu... should probably be removed? - jcammarata
        """
        pass

    def set_variance(self, flavor, major, minor, arch):
        """
        Set distro specific versioning.
        """
        # I don't think this is required anymore, as the scan_pkg_filename() function
        # above does everything we need it to - jcammarata
        #
        #if self.breed == "debian":
        #    dist_names = { '4.0' : "etch" , '5.0' : "lenny" }
        #    dist_vers = "%s.%s" % ( major , minor )
        #    os_version = dist_names[dist_vers]
        #
        #    return os_version , "/var/lib/cobbler/kickstarts/sample.seed"
        #elif self.breed == "ubuntu":
        #    # Release names taken from wikipedia
        #    dist_names = { '6.4'  :"dapper", 
        #                   '8.4'  :"hardy", 
        #                   '8.10' :"intrepid", 
        #                   '9.4'  :"jaunty",
        #                   '9.10' :"karmic",
        #                   '10.4' :"lynx",
        #                   '10.10':"maverick",
        #                   '11.4' :"natty",
        #                 }
        #    dist_vers = "%s.%s" % ( major , minor )
        #    if not dist_names.has_key( dist_vers ):
        #        dist_names['4ubuntu2.0'] = "IntrepidIbex"
        #    os_version = dist_names[dist_vers]
        # 
        #    return os_version , "/var/lib/cobbler/kickstarts/sample.seed"
        #else:
        #    return None
        pass

    def process_repos(self, main_importer, distro):
        # Create a disabled repository for the new distro, and the security updates
        #
        # NOTE : We cannot use ks_meta nor os_version because they get fixed at a later stage

        # Obtain repo mirror from APT if available
        mirror = False
        if apt_available:
            # Example returned URL: http://us.archive.ubuntu.com/ubuntu
            mirror = self.get_repo_mirror_from_apt()
            if mirror:
                mirror = mirror + "/dists"
        if not mirror:
            mirror = "http://archive.ubuntu.com/ubuntu/dists/"

        repo = item_repo.Repo(main_importer.config)
        repo.set_breed( "apt" )
        repo.set_arch( distro.arch )
        repo.set_keep_updated( False )
        repo.yumopts["--ignore-release-gpg"] = None
        repo.yumopts["--verbose"] = None
        repo.set_name( distro.name )
        repo.set_os_version( distro.os_version )

        if distro.breed == "ubuntu":
            repo.set_mirror( "%s/%s" % (mirror, distro.os_version) )
        else:
            # NOTE : The location of the mirror should come from timezone
            repo.set_mirror( "http://ftp.%s.debian.org/debian/dists/%s" % ( 'us' , distro.os_version ) )

        security_repo = item_repo.Repo(main_importer.config)
        security_repo.set_breed( "apt" )
        security_repo.set_arch( distro.arch )
        security_repo.set_keep_updated( False )
        security_repo.yumopts["--ignore-release-gpg"] = None
        security_repo.yumopts["--verbose"] = None
        security_repo.set_name( distro.name + "-security" )
        security_repo.set_os_version( distro.os_version )
        # There are no official mirrors for security updates
        if distro.breed == "ubuntu":
            security_repo.set_mirror( "%s/%s-security" % (mirror, distro.os_version) )
        else:
            security_repo.set_mirror( "http://security.debian.org/debian-security/dists/%s/updates" % distro.os_version )

        self.logger.info("Added repos for %s" % distro.name)
        repos  = main_importer.config.repos()
        repos.add(repo,save=True)
        repos.add(security_repo,save=True)

# ==========================================================================

def get_import_manager(config,logger):
    return ImportDebianUbuntuManager(config,logger)
