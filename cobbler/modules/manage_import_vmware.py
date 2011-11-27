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
import codes
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

def register():
   """
   The mandatory cobbler module registration hook.
   """
   return "manage/import"


class ImportVMWareManager:

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
        return "import/vmware"

    # required function for import modules
    def check_for_signature(self,path,cli_breed):
       signatures = [
           'VMware/RPMS',
           'imagedd.bz2',
           'tboot.b00',
       ]

       for signature in signatures:
           d = os.path.join(path,signature)
           if os.path.exists(d):
               self.logger.info("Found a vmware compatible signature: %s" % signature)
               return (True,signature)

       if cli_breed and cli_breed in self.get_valid_breeds():
           self.logger.info("Warning: No distro signature for kernel at %s, using value from command line" % path)
           return (True,None)

       return (False,None)

    # required function for import modules
    def run(self,pkgdir,name,path,network_root=None,kickstart_file=None,rsync_flags=None,arch=None,breed=None,os_version=None):
        self.pkgdir = pkgdir
        self.network_root = network_root
        self.kickstart_file = kickstart_file
        self.rsync_flags = rsync_flags
        self.arch = arch
        self.breed = breed
        self.os_version = os_version
        self.name = name
        self.path = path
        self.rootdir = path

        # some fixups for the XMLRPC interface, which does not use "None"
        if self.arch == "":           self.arch           = None
        if self.kickstart_file == "": self.kickstart_file = None
        if self.os_version == "":     self.os_version     = None
        if self.rsync_flags == "":    self.rsync_flags    = None
        if self.network_root == "":   self.network_root   = None

        # If no breed was specified on the command line, set it to "redhat" for this module
        if self.breed == None:
            self.breed = "vmware"

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
        return ["vmware",]

    # required function for import modules
    def get_valid_os_versions(self):
        return codes.VALID_OS_VERSIONS["vmware"]

    def get_valid_repo_breeds(self):
        return ["rsync", "rhn", "yum",]

    def get_release_files(self):
        """
        Find distro release packages.
        """
        data = glob.glob(os.path.join(self.get_pkgdir(), "vmware-esx-vmware-release-*"))
        data2 = []
        for x in data:
            b = os.path.basename(x)
            if b.find("vmware") != -1:
                data2.append(x)
        if len(data2) == 0:
            # ESXi maybe?
            data2 = glob.glob(os.path.join(self.get_rootdir(), "*.*"))
        return data2

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
            tail = utils.path_tail(self.path, base)
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

            if ( x.startswith("initrd") or x.startswith("ramdisk.image.gz") or x.startswith("vmkboot.gz") or x.startswith("s.v00") ) and x != "initrd.size":
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

        arch = "x86_64" # esxi only supports 64-bit
        proposed_name = self.get_proposed_name(dirname,kernel)

        distros_added = []

        name = proposed_name + "-" + arch
        existing_distro = self.distros.find(name=name)

        if existing_distro is not None:
            self.logger.warning("skipping import, as distro name already exists: %s" % name)
        else:
            self.logger.info("creating new distro: %s" % name)
            distro = self.config.new_distro()
            distro.set_name(name)
            distro.set_kernel(kernel)
            distro.set_initrd(initrd)
            distro.set_arch(arch)
            distro.set_breed(self.breed)
            # If a version was supplied on command line, we set it now
            if self.os_version:
                distro.set_os_version(self.os_version)
            self.distros.add(distro,save=True)
            distros_added.append(distro)

        # see if the profile name is already used, if so, skip it and
        # do not modify the existing profile

        existing_profile = self.profiles.find(name=name)

        if existing_profile is not None:
            self.logger.info("skipping existing profile, name already exists: %s" % name)
        else:
            self.logger.info("creating new profile: %s" % name)
            #FIXME: The created profile holds a default kickstart, and should be breed specific
            profile = self.config.new_profile()
            profile.set_name(name)
            profile.set_distro(name)
            profile.set_kickstart(self.kickstart_file)

            # We just set the virt type to vmware for these
            # since newer VMwares support running ESX as a guest for testing
            profile.set_virt_type("vmware")

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

    def kickstart_finder(self,distros_added):
        """
        For all of the profiles in the config w/o a kickstart, use the
        given kickstart file, or look at the kernel path, from that,
        see if we can guess the distro, and if we can, assign a kickstart
        if one is available for it.
        """

        # FIXME: this is bass-ackwards... why do we loop through all
        # profiles to find distros we added when we already have the list
        # of distros we added??? It would be easier to loop through the
        # distros_added list and modify all child profiles

        for profile in self.profiles:
            distro = self.distros.find(name=profile.get_conceptual_parent().name)
            if distro is None or not (distro in distros_added):
                continue

            kdir = os.path.dirname(distro.kernel)
            release_files = self.get_release_files()
            for release_file in release_files:
                results = self.scan_pkg_filename(release_file)
                if results is None:
                    continue
                (flavor, major, minor, release, update) = results
                version , ks = self.set_variance(flavor, major, minor, release, update, distro.arch)
                if self.os_version:
                    if self.os_version != version:
                        utils.die(self.logger,"CLI version differs from tree : %s vs. %s" % (self.os_version,version))
                ds = self.get_datestamp()
                distro.set_comment("%s.%s.%s update %s" % (version,minor,release,update))
                distro.set_os_version(version)
                if ds is not None:
                    distro.set_tree_build_time(ds)
                if self.kickstart_file == None:
                    profile.set_kickstart(ks)
                boot_files = ''
                if version == "esxi4":
                    self.logger.info("This is an ESXi4 distro - adding extra PXE files to boot-files list")
                    # add extra files to boot_files in the distro
                    for file in ('vmkernel.gz','sys.vgz','cim.vgz','ienviron.vgz','install.vgz'):
                       boot_files += '$img_path/%s=%s/%s ' % (file,self.path,file)
                elif version == "esxi5":
                    self.logger.info("This is an ESXi5 distro - copying all files to boot-files list")
                    #for file in glob.glob(os.path.join(self.path,"*.*")):
                    #   file_name = os.path.basename(file)
                    #   boot_files += '$img_path/%s=%s ' % (file_name,file)
                    boot_files = '$img_path/=%s' % os.path.join(self.path,"*.*")
                distro.set_boot_files(boot_files.strip())
                self.profiles.add(profile,save=True)
                # we found the correct details above, we can stop looping
                break

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
            self.set_install_tree( distro, tree)
        else:
            # where we assign the kickstart source is relative to our current directory
            # and the input start directory in the crawl.  We find the path segments
            # between and tack them on the network source path to find the explicit
            # network path to the distro that Anaconda can digest.
            tail = utils.path_tail(self.path, base)
            tree = self.network_root[:-1] + tail
            self.set_install_tree( distro, tree)

    def get_rootdir(self):
        return self.rootdir

    def get_pkgdir(self):
        if not self.pkgdir:
            return None
        return os.path.join(self.get_rootdir(),self.pkgdir)

    def set_install_tree(self, distro, url):
        distro.ks_meta["tree"] = url

    def scan_pkg_filename(self, filename):
        """
        Determine what the distro is based on the release package filename.
        """
        file_base_name = os.path.basename(filename)

        success = False

        if file_base_name.lower().find("-esx-") != -1:
            flavor = "esx"
            match = re.search(r'release-(\d)+-(\d)+\.(\d)+\.(\d)+-(\d)\.', filename)
            if match:
                major   = match.group(2)
                minor   = match.group(3)
                release = match.group(4)
                update  = match.group(5)
                success = True
        elif file_base_name.lower() == "vmkernel.gz":
            flavor  = "esxi"
            major   = 0
            minor   = 0
            release = 0
            update  = 0

            # this should return something like:
            # VMware ESXi 4.1.0 [Releasebuild-260247], built on May 18 2010
            # though there will most likely be multiple results
            scan_cmd = 'gunzip -c %s | strings | grep -i "^vmware esxi"' % filename
            (data,rc) = utils.subprocess_sp(None, scan_cmd)
            lines = data.split('\n')
            m = re.compile(r'ESXi (\d)+\.(\d)+\.(\d)+ \[Releasebuild-([\d]+)\]')
            for line in lines:
                match = m.search(line)
                if match:
                    major   = match.group(1)
                    minor   = match.group(2)
                    release = match.group(3)
                    update  = match.group(4)
                    success = True
                    break
        elif file_base_name.lower() == "s.v00":
            flavor  = "esxi"
            major   = 0
            minor   = 0
            release = 0
            update  = 0

            # this should return something like:
            # VMware ESXi 5.0.0 build-469512
            # though there will most likely be multiple results
            scan_cmd = 'gunzip -c %s | strings | grep -i "^# vmware esxi"' % filename
            (data,rc) = utils.subprocess_sp(None, scan_cmd)
            lines = data.split('\n')
            m = re.compile(r'ESXi (\d)+\.(\d)+\.(\d)+[ ]+build-([\d]+)')
            for line in lines:
                match = m.search(line)
                if match:
                    major   = match.group(1)
                    minor   = match.group(2)
                    release = match.group(3)
                    update  = match.group(4)
                    success = True
                    break

        if success:
            return (flavor, major, minor, release, update)
        else:
            return None

    def get_datestamp(self):
        """
        Based on a VMWare tree find the creation timestamp
        """
        pass

    def set_variance(self, flavor, major, minor, release, update, arch):
        """
        Set distro specific versioning.
        """
        os_version = "%s%s" % (flavor, major)
        if os_version == "esx4":
            ks = "/var/lib/cobbler/kickstarts/esx.ks"
        elif os_version == "esxi4":
            ks = "/var/lib/cobbler/kickstarts/esxi4-ks.cfg"
        elif os_version == "esxi5":
            ks = "/var/lib/cobbler/kickstarts/esxi5-ks.cfg"
        else:
            ks = "/var/lib/cobbler/kickstarts/default.ks"
        return os_version , ks

# ==========================================================================

def get_import_manager(config,logger):
    return ImportVMWareManager(config,logger)
