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

import glob
import os
import os.path
import re
import shutil

# Import aptsources module if available to obtain repo mirror.
try:
    from aptsources import distro as debdistro
    from aptsources import sourceslist
    apt_available = True
except:
    apt_available = False

from cobbler import item_distro
from cobbler import item_profile

from cexceptions import CX
import item_repo
import templar
import utils


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "manage/import"


class ImportSignatureManager:

    def __init__(self, collection_mgr, logger):
        """
        Constructor
        """
        self.logger = logger
        self.collection_mgr = collection_mgr
        self.api = collection_mgr.api
        self.distros = collection_mgr.distros()
        self.profiles = collection_mgr.profiles()
        self.systems = collection_mgr.systems()
        self.settings = collection_mgr.settings()
        self.repos = collection_mgr.repos()
        self.templar = templar.Templar(collection_mgr)

        self.signature = None
        self.found_repos = {}

    # required function for import modules
    def what(self):
        return "import/signatures"

    def get_file_lines(self, filename):
        """
        Get lines from a file, which may or may not be compressed
        """
        lines = []
        ftype = utils.subprocess_get(self.logger, "/usr/bin/file %s" % filename)
        if ftype.find("gzip") != -1:
            try:
                import gzip
                f = gzip.open(filename, 'r')
                lines = f.readlines()
                f.close()
            except:
                pass
        elif ftype.find("text") != -1:
            f = open(filename, 'r')
            lines = f.readlines()
            f.close()
        return lines

    # required function for import modules
    def run(self, path, name, network_root=None, autoinstall_file=None, arch=None, breed=None, os_version=None):
        """
        path: the directory we are scanning for files
        name: the base name of the distro
        network_root: the remote path (nfs/http/ftp) for the distro files
        autoinstall_file: user-specified response file, which will override the default
        arch: user-specified architecture
        breed: user-specified breed
        os_version: user-specified OS version
        """
        self.name = name
        self.network_root = network_root
        self.autoinstall_file = autoinstall_file
        self.arch = arch
        self.breed = breed
        self.os_version = os_version

        self.path = path
        self.rootdir = path
        self.pkgdir = path

        # some fixups for the XMLRPC interface, which does not use "None"
        if self.arch == "":
            self.arch = None

        if self.name == "":
            self.name = None

        if self.autoinstall_file == "":
            self.autoinstall_file = None

        if self.os_version == "":
            self.os_version = None

        if self.network_root == "":
            self.network_root = None

        if self.os_version and not self.breed:
            utils.die(self.logger, "OS version can only be specified when a specific breed is selected")

        self.signature = self.scan_signatures()
        if not self.signature:
            error_msg = "No signature matched in %s" % path
            self.logger.error(error_msg)
            raise CX(error_msg)

        # now walk the filesystem looking for distributions that match certain patterns
        self.logger.info("Adding distros from path %s:" % self.path)
        distros_added = []
        os.path.walk(self.path, self.distro_adder, distros_added)

        if len(distros_added) == 0:
            self.logger.warning("No distros imported, bailing out")
            return

        # find out if we can auto-create any repository records from the install tree
        if self.network_root is None:
            self.logger.info("associating repos")
            # FIXME: this automagic is not possible (yet) without mirroring
            self.repo_finder(distros_added)

    def scan_signatures(self):
        """
        loop through the signatures, looking for a match for both
        the signature directory and the version file
        """
        sigdata = self.api.get_signatures()
        # self.logger.debug("signature cache: %s" % str(sigdata))
        for breed in sigdata["breeds"].keys():
            if self.breed and self.breed != breed:
                continue
            for version in sigdata["breeds"][breed].keys():
                if self.os_version and self.os_version != version:
                    continue
                for sig in sigdata["breeds"][breed][version]["signatures"]:
                    pkgdir = os.path.join(self.path, sig)
                    if os.path.exists(pkgdir):
                        self.logger.debug("Found a candidate signature: breed=%s, version=%s" % (breed, version))
                        f_re = re.compile(sigdata["breeds"][breed][version]["version_file"])
                        for (root, subdir, fnames) in os.walk(self.path):
                            for fname in fnames + subdir:
                                if f_re.match(fname):
                                    # if the version file regex exists, we use it
                                    # to scan the contents of the target version file
                                    # to ensure it's the right version
                                    if sigdata["breeds"][breed][version]["version_file_regex"]:
                                        vf_re = re.compile(sigdata["breeds"][breed][version]["version_file_regex"])
                                        vf_lines = self.get_file_lines(os.path.join(root, fname))
                                        for line in vf_lines:
                                            if vf_re.match(line):
                                                break
                                        else:
                                            continue
                                    self.logger.debug("Found a matching signature: breed=%s, version=%s" % (breed, version))
                                    if not self.breed:
                                        self.breed = breed
                                    if not self.os_version:
                                        self.os_version = version
                                    if not self.autoinstall_file:
                                        self.autoinstall_file = sigdata["breeds"][breed][version]["default_autoinstall"]
                                    self.pkgdir = pkgdir
                                    return sigdata["breeds"][breed][version]
        return None

    # required function for import modules
    def get_valid_arches(self):
        if self.signature:
            return sorted(self.signature["supported_arches"], key=lambda s: -1 * len(s))
        return []

    def get_valid_repo_breeds(self):
        if self.signature:
            return self.signature["supported_repo_breeds"]
        return []

    def distro_adder(self, distros_added, dirname, fnames):
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

            # most of the time we just want to ignore isolinux
            # directories, unless this is one of the oddball
            # distros where we do want it
            if dirname.find("isolinux") != -1 and not self.signature["isolinux_ok"]:
                continue

            fullname = os.path.join(dirname, x)
            if os.path.islink(fullname) and os.path.isdir(fullname):
                if fullname.startswith(self.path):
                    # Prevent infinite loop with Sci Linux 5
                    # self.logger.warning("avoiding symlink loop")
                    continue
                self.logger.info("following symlink: %s" % fullname)
                os.path.walk(fullname, self.distro_adder, distros_added)

            if re_img.match(x):
                if x.find("PAE") == -1:
                    initrd = os.path.join(dirname, x)
                else:
                    pae_initrd = os.path.join(dirname, x)

            if re_krn.match(x):
                if x.find("PAE") == -1:
                    kernel = os.path.join(dirname, x)
                else:
                    pae_kernel = os.path.join(dirname, x)

            # if we've collected a matching kernel and initrd pair, turn them in and add them to the list
            if initrd is not None and kernel is not None:
                adtls.append(self.add_entry(dirname, kernel, initrd))
                kernel = None
                initrd = None
            elif pae_initrd is not None and pae_kernel is not None:
                adtls.append(self.add_entry(dirname, pae_kernel, pae_initrd))
                pae_kernel = None
                pae_initrd = None

            for adtl in adtls:
                distros_added.extend(adtl)

        if "nexenta" == self.breed:
            # self.logger.warning( "this is nexenta" )
            initrd = os.path.join(self.path, self.signature["initrd_file"])
            kernel = os.path.join(self.path, self.signature["kernel_file"])
            adtls.append(self.add_entry(self.path, kernel, initrd))
            for adtl in adtls:
                distros_added.extend(adtl)

    def add_entry(self, dirname, kernel, initrd):
        """
        When we find a directory with a valid kernel/initrd in it, create the distribution objects
        as appropriate and save them.  This includes creating xen and rescue distros/profiles
        if possible.
        """

        # build a proposed name based on the directory structure
        proposed_name = self.get_proposed_name(dirname, kernel)

        # build a list of arches found in the packages directory
        archs = self.learn_arch_from_tree()
        if not archs and self.arch:
            archs.append(self.arch)
        else:
            if self.arch and self.arch not in archs:
                utils.die(self.logger, "Given arch (%s) not found on imported tree %s" % (self.arch, self.path))

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
                distro = item_distro.Distro(self.collection_mgr)

            if name.find("-autoboot") != -1:
                # this is an artifact of some EL-3 imports
                continue

            distro.set_name(name)
            distro.set_kernel(kernel)
            distro.set_initrd(initrd)
            distro.set_arch(pxe_arch)
            distro.set_breed(self.breed)
            distro.set_os_version(self.os_version)
            distro.set_kernel_options(self.signature.get("kernel_options", ""))
            distro.set_kernel_options_post(self.signature.get("kernel_options_post", ""))
            distro.set_template_files(self.signature.get("template_files", ""))
            supported_distro_boot_loaders = utils.get_supported_distro_boot_loaders(distro, self.api)
            distro.set_supported_boot_loaders(supported_distro_boot_loaders)
            distro.set_boot_loader(supported_distro_boot_loaders[0])

            boot_files = ''
            for boot_file in self.signature["boot_files"]:
                boot_files += '$local_img_path/%s=%s/%s ' % (boot_file, self.path, boot_file)
            distro.set_boot_files(boot_files.strip())

            self.configure_tree_location(distro)

            self.distros.add(distro, save=True)
            distros_added.append(distro)

            # see if the profile name is already used, if so, skip it and
            # do not modify the existing profile

            existing_profile = self.profiles.find(name=name)

            if existing_profile is None:
                self.logger.info("creating new profile: %s" % name)
                profile = item_profile.Profile(self.collection_mgr)
            else:
                self.logger.info("skipping existing profile, name already exists: %s" % name)
                continue

            profile.set_name(name)
            profile.set_distro(name)
            profile.set_autoinstall(self.autoinstall_file)

            # depending on the name of the profile we can
            # define a good virt-type for usage with koan
            if name.find("-xen") != -1:
                profile.set_virt_type("xenpv")
            elif name.find("vmware") != -1:
                profile.set_virt_type("vmware")
            else:
                profile.set_virt_type("kvm")

            self.profiles.add(profile, save=True)

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

        if result.pop("amd64", False):
            result["x86_64"] = 1
        if result.pop("i686", False):
            result["i386"] = 1
        if result.pop("i586", False):
            result["i386"] = 1
        if result.pop("x86", False):
            result["i386"] = 1

        return result.keys()

    def arch_walker(self, foo, dirname, fnames):
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
                    krn_lines = self.get_file_lines(os.path.join(dirname, x))
                    for line in krn_lines:
                        m = re_krn2.match(line)
                        if m:
                            for group in m.groups():
                                group = group.lower()
                                if group in self.get_valid_arches():
                                    foo[group] = 1
                else:
                    for arch in self.get_valid_arches():
                        if x.find(arch) != -1:
                            foo[arch] = 1
                            break
                    for arch in ["i686", "amd64"]:
                        if x.find(arch) != -1:
                            foo[arch] = 1
                            break

    def get_proposed_name(self, dirname, kernel=None):
        """
        Given a directory name where we have a kernel/initrd pair, try to autoname
        the distribution (and profile) object based on the contents of that path
        """

        if self.network_root is not None:
            name = self.name
        else:
            # remove the part that says /var/www/cobbler/distro_mirror/name
            name = "-".join(dirname.split("/")[5:])

        if kernel is not None:
            if kernel.find("PAE") != -1 and name.find("PAE") == -1:
                name += "-PAE"
            if kernel.find("xen") != -1 and name.find("xen") == -1:
                name += "-xen"

        # Clear out some cruft from the proposed name
        name = name.replace("--", "-")
        for x in ("-netboot", "-ubuntu-installer", "-amd64", "-i386",
                  "-images", "-pxeboot", "-install", "-isolinux", "-boot", "-suseboot",
                  "-loader", "-os", "-tree", "var-www-cobbler-", "distro_mirror-"):
            name = name.replace(x, "")

        # remove any architecture name related string, as real arch will be appended later
        name = name.replace("chrp", "ppc64")
        for separator in ['-', '_', '.']:
            for arch in ["i386", "x86_64", "ppc64le", "ppc64el", "ppc64", "ppc32", "ppc", "x86", "386", "amd"]:
                name = name.replace("%s%s" % (separator, arch), "")

        return name

    def configure_tree_location(self, distro):
        """
        Once a distribution is identified, find the part of the distribution
        that has the URL in it that we want to use for automating the Linux
        distribution installation, and create a autoinstall_meta variable $tree
        that contains this.
        """

        base = self.rootdir

        # how we set the tree depends on whether an explicit network_root was specified
        if self.network_root is None:
            dest_link = os.path.join(self.settings.webdir, "links", distro.name)
            # create the links directory only if we are mirroring because with
            # SELinux Apache can't symlink to NFS (without some doing)
            if not os.path.exists(dest_link):
                try:
                    self.logger.info("trying symlink: %s -> %s" % (str(base), str(dest_link)))
                    os.symlink(base, dest_link)
                except:
                    # this shouldn't happen but I've seen it ... debug ...
                    self.logger.warning("symlink creation failed: %(base)s, %(dest)s" % {"base": base, "dest": dest_link})
            tree = "http://@@http_server@@/cblr/links/%s" % (distro.name)
            self.set_install_tree(distro, tree)
        else:
            # where we assign the automated installation file source is relative
            # to our current directory and the input start directory in the crawl.
            # We find the path segments between and tack them on the network source
            # path to find the explicit network path to the distro that Anaconda
            # can digest.
            tail = utils.path_tail(self.path, base)
            tree = self.network_root[:-1] + tail
            self.set_install_tree(distro, tree)

    def set_install_tree(self, distro, url):
        """
        Simple helper function to set the tree automated installation metavariable
        """
        distro.autoinstall_meta["tree"] = url

# ==========================================================================
# Repo Functions

    def repo_finder(self, distros_added):
        """
        This routine looks through all distributions and tries to find
        any applicable repositories in those distributions for post-install
        usage.
        """
        for repo_breed in self.get_valid_repo_breeds():
            self.logger.info("checking for %s repo(s)" % repo_breed)
            repo_adder = None
            if repo_breed == "yum":
                repo_adder = self.yum_repo_adder
            elif repo_breed == "rhn":
                repo_adder = self.rhn_repo_adder
            elif repo_breed == "rsync":
                repo_adder = self.rsync_repo_adder
            elif repo_breed == "apt":
                repo_adder = self.apt_repo_adder
            else:
                self.logger.warning("skipping unknown/unsupported repo breed: %s" % repo_breed)
                continue

            for distro in distros_added:
                if distro.kernel.find("distro_mirror") != -1:
                    repo_adder(distro)
                    self.distros.add(distro, save=True, with_triggers=False)
                else:
                    self.logger.info("skipping distro %s since it isn't mirrored locally" % distro.name)

    # ==========================================================================
    # yum-specific

    def yum_repo_adder(self, distro):
        """
        For yum, we recursively scan the rootdir for repos to add
        """
        self.logger.info("starting descent into %s for %s" % (self.rootdir, distro.name))
        os.path.walk(self.rootdir, self.yum_repo_scanner, distro)

    def yum_repo_scanner(self, distro, dirname, fnames):
        """
        This is an os.path.walk routine that looks for potential yum repositories
        to be added to the configuration for post-install usage.
        """

        matches = {}
        for x in fnames:
            if x == "base" or x == "repodata":
                self.logger.info("processing repo at : %s" % dirname)
                # only run the repo scanner on directories that contain a comps.xml
                gloob1 = glob.glob("%s/%s/*comps*.xml" % (dirname, x))
                if len(gloob1) >= 1:
                    if dirname in matches:
                        self.logger.info("looks like we've already scanned here: %s" % dirname)
                        continue
                    self.logger.info("need to process repo/comps: %s" % dirname)
                    self.yum_process_comps_file(dirname, distro)
                    matches[dirname] = 1
                else:
                    self.logger.info("directory %s is missing xml comps file, skipping" % dirname)
                    continue

    def yum_process_comps_file(self, comps_path, distro):
        """
        When importing Fedora/EL certain parts of the install tree can also be used
        as yum repos containing packages that might not yet be available via updates
        in yum.  This code identifies those areas. Existing repodata will be used as-is,
        but repodate is created for earlier, non-yum based, installers.
        """

        if os.path.exists(os.path.join(comps_path, "repodata")):
            keeprepodata = True
            masterdir = "repodata"
        else:
            # older distros...
            masterdir = "base"
            keeprepodata = False

        # figure out what our comps file is ...
        self.logger.info("looking for %(p1)s/%(p2)s/*comps*.xml" % {"p1": comps_path, "p2": masterdir})
        files = glob.glob("%s/%s/*comps*.xml" % (comps_path, masterdir))
        if len(files) == 0:
            self.logger.info("no comps found here: %s" % os.path.join(comps_path, masterdir))
            return      # no comps xml file found

        # pull the filename from the longer part
        comps_file = files[0].split("/")[-1]

        try:
            # store the yum configs on the filesystem so we can use them later.
            # and configure them in the automated installation file post section,
            # etc

            counter = len(distro.source_repos)

            # find path segment for yum_url (changing filesystem path to http:// trailing fragment)
            seg = comps_path.rfind("distro_mirror")
            urlseg = comps_path[(seg + len("distro_mirror") + 1):]

            fname = os.path.join(self.settings.webdir, "distro_mirror", "config", "%s-%s.repo" % (distro.name, counter))

            repo_url = "http://@@http_server@@/cobbler/distro_mirror/config/%s-%s.repo" % (distro.name, counter)
            repo_url2 = "http://@@http_server@@/cobbler/distro_mirror/%s" % (urlseg)

            distro.source_repos.append([repo_url, repo_url2])

            config_dir = os.path.dirname(fname)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            # NOTE: the following file is now a Cheetah template, so it can be remapped
            # during sync, that's why we have the @@http_server@@ left as templating magic.
            # repo_url2 is actually no longer used. (?)

            config_file = open(fname, "w+")
            config_file.write("[core-%s]\n" % counter)
            config_file.write("name=core-%s\n" % counter)
            config_file.write("baseurl=http://@@http_server@@/cobbler/distro_mirror/%s\n" % (urlseg))
            config_file.write("enabled=1\n")
            config_file.write("gpgcheck=0\n")
            config_file.write("priority=$yum_distro_priority\n")
            config_file.close()

            # don't run creatrepo twice -- this can happen easily for Xen and PXE, when
            # they'll share same repo files.
            if keeprepodata:
                self.logger.info("Keeping repodata as-is :%s/repodata" % comps_path)
                self.found_repos[comps_path] = 1

            elif comps_path not in self.found_repos:
                utils.remove_yum_olddata(comps_path)
                cmd = "createrepo %s --groupfile %s %s" % (self.settings.createrepo_flags, os.path.join(comps_path, masterdir, comps_file), comps_path)
                utils.subprocess_call(self.logger, cmd, shell=True)
                self.found_repos[comps_path] = 1
                # for older distros, if we have a "base" dir parallel with "repodata", we need to copy comps.xml up one...
                p1 = os.path.join(comps_path, "repodata", "comps.xml")
                p2 = os.path.join(comps_path, "base", "comps.xml")
                if os.path.exists(p1) and os.path.exists(p2):
                    shutil.copyfile(p1, p2)

        except:
            self.logger.error("error launching createrepo (not installed?), ignoring")
            utils.log_exc(self.logger)

    # ==========================================================================
    # apt-specific

    def apt_repo_adder(self, distro):
        self.logger.info("adding apt repo for %s" % distro.name)
        # Obtain repo mirror from APT if available
        mirror = False
        if apt_available:
            # Example returned URL: http://us.archive.ubuntu.com/ubuntu
            mirror = self.get_repo_mirror_from_apt()
        if not mirror:
            mirror = "http://archive.ubuntu.com/ubuntu"

        repo = item_repo.Repo(self.collection_mgr)
        repo.set_breed("apt")
        repo.set_arch(distro.arch)
        repo.set_keep_updated(True)
        repo.set_apt_components("main universe")        # TODO: make a setting?
        repo.set_apt_dists("%s %s-updates %s-security" % ((distro.os_version,) * 3))
        repo.set_name(distro.name)
        repo.set_os_version(distro.os_version)

        if distro.breed == "ubuntu":
            repo.set_mirror(mirror)
        else:
            # NOTE : The location of the mirror should come from timezone
            repo.set_mirror("http://ftp.%s.debian.org/debian/dists/%s" % ('us', distro.os_version))

        self.logger.info("Added repos for %s" % distro.name)
        repos = self.collection_mgr.repos()
        repos.add(repo, save=True)
        # FIXME:
        # Add the found/generated repos to the profiles
        # that were created during the import process

    def get_repo_mirror_from_apt(self):
        """
        This tries to determine the apt mirror/archive to use (when processing repos)
        if the host machine is Debian or Ubuntu.
        """
        try:
            sources = sourceslist.SourcesList()
            release = debdistro.get_distro()
            release.get_sources(sources)
            mirrors = release.get_server_list()
            for mirror in mirrors:
                if mirror[2]:
                    mirror = mirror[1]
                    break
        except:
            return False

        return mirror

    # ==========================================================================
    # rhn-specific

    def rhn_repo_adder(self, distro):
        """ not currently used """
        return

    # ==========================================================================
    # rsync-specific

    def rsync_repo_adder(self, distro):
        """ not currently used """
        return

# ==========================================================================


def get_import_manager(config, logger):
    return ImportSignatureManager(config, logger)
