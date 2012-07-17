"""
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>
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
import glob
import re
import simplejson
import traceback

import utils
from cexceptions import *
import templar

import item_distro
import item_profile
import item_repo
import item_system
import codes

from utils import _

def register():
   """
   The mandatory cobbler module registration hook.
   """
   return "manage/import"


class ImportSignatureManager:

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

        self.sigdata       = None
        self.signature     = None

    # required function for import modules
    def what(self):
        return "import/signatures"

    # required function for import modules
    def run(self,path,name,network_root=None,kickstart_file=None,arch=None,breed=None,os_version=None):
        """
        path: the directory we are scanning for files
        name: the base name of the distro
        network_root: the remote path (nfs/http/ftp) for the distro files
        kickstart_file: user-specified response file, which will override the default
        arch: user-specified architecture
        breed: user-specified breed
        os_version: user-specified OS version
        """
        self.name = name
        self.network_root = network_root
        self.kickstart_file = kickstart_file
        self.arch = arch
        self.breed = breed
        self.os_version = os_version

        self.path = path
        self.rootdir = path
        self.pkgdir = path

        # some fixups for the XMLRPC interface, which does not use "None"
        if self.arch == "":           self.arch           = None
        if self.name == "":           self.name           = None
        if self.kickstart_file == "": self.kickstart_file = None
        if self.os_version == "":     self.os_version     = None
        if self.network_root == "":   self.network_root   = None

        if self.os_version and not self.breed:
            utils.die(self.logger,"OS version can only be specified when a specific breed is selected")

        # load the signature data
        try:
            f = open('/var/lib/cobbler/distro_signatures.json')
            sigjson = f.read()
            f.close()
            self.sigdata = simplejson.loads(sigjson)
        except:
            self.logger.error("Failed to load distro signatures")
            return False

        self.signature = self.scan_signatures()
        if not self.signature:
            self.logger.error("No signature matched in %s" % path)
            return False

        # now walk the filesystem looking for distributions that match certain patterns
        self.logger.info("Adding distros from path %s:"%self.path)
        distros_added = []
        os.path.walk(self.path, self.distro_adder, distros_added)

        if len(distros_added) == 0:
            self.logger.warning("No distros imported, bailing out")
            return False

        return True

    def scan_signatures(self):
        """
        loop through the signatures, looking for a match for both
        the signature directory and the version file
        """
        for breed in self.sigdata["breeds"].keys():
            if self.breed and self.breed != breed:
                continue
            for version in self.sigdata["breeds"][breed].keys():
                if self.os_version and self.os_version != version:
                    continue
                for sig in self.sigdata["breeds"][breed][version]["signatures"]:
                    pkgdir = os.path.join(self.path,sig)
                    if os.path.exists(pkgdir):
                        self.logger.debug("Found a candidate signature: breed=%s, version=%s" % (breed,version))
                        f_re = re.compile(self.sigdata["breeds"][breed][version]["version_file"])
                        for (root,subdir,fnames) in os.walk(self.path):
                            for fname in fnames+subdir:
                                if f_re.match(fname):
                                    # if the version file regex exists, we use it 
                                    # to scan the contents of the target version file
                                    # to ensure it's the right version
                                    if self.sigdata["breeds"][breed][version]["version_file_regex"]:
                                        vf_re = re.compile(self.sigdata["breeds"][breed][version]["version_file_regex"])
                                        vf = open(os.path.join(root,fname),"r")
                                        vf_lines = vf.read().split("\n")
                                        vf.close()
                                        for line in vf_lines:
                                            if vf_re.match(line):
                                                break
                                        else:
                                            continue
                                    self.logger.debug("Found a matching signature: breed=%s, version=%s" % (breed,version))
                                    if not self.breed:
                                        self.breed = breed
                                    if not self.os_version:
                                        self.os_version = version
                                    if not self.kickstart_file:
                                        self.kickstart_file = self.sigdata["breeds"][breed][version]["default_kickstart"]
                                    self.pkgdir = pkgdir
                                    return self.sigdata["breeds"][breed][version]
        return None

    # required function for import modules
    def get_valid_arches(self):
        if self.signature:
            return self.signature["supported_arches"]
        return []

    def get_valid_repo_breeds(self):
        if self.signature:
            return self.signature["supported_repo_breeds"]
        return []

    def distro_adder(self,distros_added,dirname,fnames):
        """
        This is an os.path.walk routine that finds distributions in the directory
        to be scanned and then creates them.
        """

        re_krn = re.compile(self.signature["kernel_file"])
        re_img = re.compile(self.signature["initrd_file"])

        # make sure we don't mismatch PAE and non-PAE types
        initrd = None
        kernel = None
        pae_initrd = None
        pae_kernel = None

        for x in fnames:
            adtls = []

            fullname = os.path.join(dirname,x)
            if os.path.islink(fullname) and os.path.isdir(fullname):
                if fullname.startswith(self.path):
                    # Prevent infinite loop with Sci Linux 5
                    #self.logger.warning("avoiding symlink loop")
                    continue
                self.logger.info("following symlink: %s" % fullname)
                os.path.walk(fullname, self.distro_adder, distros_added)

            if re_img.match(x):
                if x.find("PAE") == -1:
                    initrd = os.path.join(dirname,x)
                else:
                    pae_initrd = os.path.join(dirname, x)

            if re_krn.match(x):
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

    def add_entry(self,dirname,kernel,initrd):
        """
        When we find a directory with a valid kernel/initrd in it, create the distribution objects
        as appropriate and save them.  This includes creating xen and rescue distros/profiles
        if possible.
        """

        # build a proposed name based on the directory structure
        proposed_name = self.get_proposed_name(dirname,kernel)

        # build a list of arches found in the packages directory
        archs = self.learn_arch_from_tree()
        if not archs and self.arch:
            archs.append( self.arch )
        else:
            if self.arch and self.arch not in archs:
                utils.die(self.logger, "Given arch (%s) not found on imported tree %s"%(self.arch,self.path))

        if len(archs) == 0:
            self.logger.error("No arch could be detected in %s, and none was specified via the --arch option" % dirname)
            return []
        elif len(archs) > 1:
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
            distro.set_os_version(self.os_version)
            distro.set_kernel_options(self.signature["kernel_options"])
            distro.set_kernel_options_post(self.signature["kernel_options_post"])

            self.configure_tree_location(distro)

            self.distros.add(distro,save=True)
            distros_added.append(distro)

            # see if the profile name is already used, if so, skip it and
            # do not modify the existing profile

            existing_profile = self.profiles.find(name=name)

            if existing_profile is None:
                self.logger.info("creating new profile: %s" % name)
                profile = self.config.new_profile()
            else:
                self.logger.info("skipping existing profile, name already exists: %s" % name)
                continue

            profile.set_name(name)
            profile.set_distro(name)
            profile.set_kickstart(self.kickstart_file)

            # depending on the name of the profile we can 
            # define a good virt-type for usage with koan
            if name.find("-xen") != -1:
                profile.set_virt_type("xenpv")
            elif name.find("vmware") != -1:
                profile.set_virt_type("vmware")
            else:
                profile.set_virt_type("kvm")

            self.profiles.add(profile,save=True)

        return distros_added

    def learn_arch_from_tree(self):
        """
        If a distribution is imported from DVD, there is a good chance the path doesn't
        contain the arch and we should add it back in so that it's part of the
        meaningful name ... so this code helps figure out the arch name.  This is important
        for producing predictable distro names (and profile names) from differing import sources
        """

        result = {}

        # FIXME : this is called only once, should not be a walk
        os.path.walk(self.path, self.arch_walker, result)

        if result.pop("amd64",False):
            result["x86_64"] = 1
        if result.pop("i686",False):
            result["i386"] = 1
        if result.pop("x86",False):
            result["i386"] = 1

        return result.keys()

    def arch_walker(self,foo,dirname,fnames):
        """
        Function for recursively searching through a directory for
        a kernel file matching a given architecture, called by 
        learn_arch_from_tree()
        """

        re_krn = re.compile(self.signature["kernel_arch"])

        # try to find a kernel header RPM and then look at it's arch.
        for x in fnames:
            if re_krn.match(x):
                if self.signature["kernel_arch_regex"]:
                    re_krn2 = re.compile(self.signature["kernel_arch_regex"])
                    f_krn = open(os.path.join(dirname,x),"r")
                    krn_lines = f_krn.readlines()
                    f_krn.close()
                    for line in krn_lines:
                        m = re_krn2.match(line)
                        if m:
                            for group in m.groups():
                                if group in self.get_valid_arches():
                                    foo[group] = 1
                else:
                    for arch in self.get_valid_arches():
                        if x.find(arch) != -1:
                            foo[arch] = 1
                    for arch in [ "i686" , "amd64" ]:
                        if x.find(arch) != -1:
                            foo[arch] = 1

    def get_proposed_name(self,dirname,kernel=None):
        """
        Given a directory name where we have a kernel/initrd pair, try to autoname
        the distribution (and profile) object based on the contents of that path
        """

        if self.network_root is not None:
            name = self.name
        else:
            # remove the part that says /var/www/cobbler/ks_mirror/name
            name = "-".join(dirname.split("/")[5:])

        if kernel is not None and kernel.find("PAE") != -1:
            name = name + "-PAE"

        # Clear out some cruft from the proposed name
        name = name.replace("--","-")
        for x in ("-netboot","-ubuntu-installer","-amd64","-i386", \
                  "-images","-pxeboot","-install","-isolinux", "-boot", \
                  "-os","-tree","var-www-cobbler-","ks_mirror-"):
            name = name.replace(x,"")

        # remove any architecture name related string, as real arch will be appended later
        name = name.replace("chrp","ppc64")
        for separator in [ '-' , '_'  , '.' ] :
            for arch in ["i386","x86_64","ia64","ppc64","ppc32","ppc","x86","s390x","s390","386","amd"]:
                name = name.replace("%s%s" % (separator,arch),"")

        return name

    def configure_tree_location(self, distro):
        """
        Once a distribution is identified, find the part of the distribution
        that has the URL in it that we want to use for kickstarting the
        distribution, and create a ksmeta variable $tree that contains this.
        """

        base = self.rootdir

        # how we set the tree depends on whether an explicit network_root was specified
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

    def set_install_tree(self, distro, url):
        """
        Simple helper function to set the tree ksmeta
        """
        distro.ks_meta["tree"] = url

# ==========================================================================

def get_import_manager(config,logger):
    return ImportSignatureManager(config,logger)
