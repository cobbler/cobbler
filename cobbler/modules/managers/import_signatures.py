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

from typing import List, Callable, Any, Optional

import glob
import gzip
import os
import os.path
import re
import shutil
import stat

import magic

try:
    import hivex  # type: ignore
    from hivex.hive_types import REG_EXPAND_SZ, REG_SZ  # type: ignore

    HAS_HIVEX = True
except ImportError:
    HAS_HIVEX = False  # type: ignore

from cobbler import clogger
from cobbler import templar
from cobbler.items import profile, distro
from cobbler.cexceptions import CX
from cobbler import utils

import cobbler.items.repo as item_repo

# Import aptsources module if available to obtain repo mirror.
try:
    from aptsources import distro as debdistro
    from aptsources import sourceslist

    apt_available = True
except:
    apt_available = False


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage/import"


def import_walker(top: str, func: Callable, arg: Any):
    """
    Directory tree walk with callback function.

    For each directory in the directory tree rooted at top (including top itself, but excluding '.' and '..'), call
    ``func(arg, dirname, fnames)``. dirname is the name of the directory, and fnames a list of the names of the files
    and subdirectories in dirname (excluding '.' and '..').  ``func`` may modify the ``fnames`` list in-place (e.g. via
    ``del`` or ``slice`` assignment), and walk will only recurse into the subdirectories whose names remain in
    ``fnames``; this can be used to implement a filter, or to impose a specific order of visiting. No semantics are
    defined for, or required of, ``arg``, beyond that arg is always passed to ``func``. It can be used, e.g., to pass
    a filename pattern, or a mutable object designed to accumulate statistics.

    :param top: The most top directory for which func should be run.
    :param func: A function which is called as described in the above description.
    :param arg: Passing ``None`` for this is common.
    """
    try:
        names = os.listdir(top)
    except os.error:
        return
    func(arg, top, names)
    for name in names:
        name = os.path.join(top, name)
        try:
            st = os.lstat(name)
        except os.error:
            continue
        if stat.S_ISDIR(st.st_mode):
            import_walker(name, func, arg)


class ImportSignatureManager:
    """
    This class contains most of the magic behind the ``cobbler import`` command. It uses the signatures as a data source
    and then automatically adds the detected distro to Cobbler.
    """

    def __init__(self, collection_mgr, logger: clogger.Logger):
        """
        Main constructor for our class.

        :param collection_mgr: This is the collection manager which has every information in Cobbler available.
        :param logger: This is the logger to audit all actions with.
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
    def what(self) -> str:
        """
        Identifies what service this manages.

        :return: Always will return ``import/signatures``.
        """
        return "import/signatures"

    def get_file_lines(self, filename: str):
        """
        Get lines from a file, which may or may not be compressed. If compressed then it will be uncompressed using
        ``gzip`` as the algorithm.

        :param filename: The name of the file to be read.
        :return: An array with all the lines.
        """
        ftype = magic.detect_from_filename(filename)
        if ftype.mime_type == "application/gzip":
            try:
                with gzip.open(filename, 'r') as f:
                    return f.readlines()
            except:
                pass
        elif (
            ftype.mime_type == "application/x-ms-wim"
            or filename.lower().endswith('.wim')
            and (self.file_version[0] < 5 or self.file_version[0] == 5 and self.file_version[1] < 37)
        ):
            cmd = "/usr/bin/wiminfo"
            if os.path.exists(cmd):
                    cmd = "%s %s" % (cmd, filename)
                    return utils.subprocess_get(None, cmd).splitlines()

            self.logger.info("no %s found, please install wimlib-utils", cmd)
        elif ftype.mime_type == "text/plain":
            with open(filename, 'r') as f:
                return f.readlines()
        else:
            self.logger.info('Could not detect the filetype and read the content of file "%s". Returning nothing.' %
                             filename)
        return []

    def get_file_version(self):
        """
        This calls file and asks for the version number.

        :return: The major file version number.
        """
        cmd = "/usr/bin/file"
        if os.path.exists(cmd):
            cmd = f"{cmd} -v"
            version_str = utils.subprocess_get(None, cmd).splitlines()[0]
            if len(version_str) < 1:
                return [0, 0]
            version_str = (version_str.split("-"))[1]
            if len(version_str) != 2 or version_str[0] != "file":
                return [0, 0]
            version_str = version_str.split(".")
            if len(version_str) < 2:
                return [0, 0]
            version = []
            for v in version_str:
                version.append(int(v))
            return version
        return [0, 0]

    def run(self, path: str, name: str, network_root=None, autoinstall_file=None, arch: Optional[str] = None,
            breed=None, os_version=None):
        """
        This is the main entry point in a manager. It is a required function for import modules.

        :param path: the directory we are scanning for files
        :param name: the base name of the distro
        :param network_root: the remote path (nfs/http/ftp) for the distro files
        :param autoinstall_file: user-specified response file, which will override the default
        :param arch: user-specified architecture
        :param breed: user-specified breed
        :param os_version: user-specified OS version
        """
        self.name = name
        self.network_root = network_root
        self.autoinstall_file = autoinstall_file
        self.arch = arch
        self.breed = breed
        self.os_version = os_version
        self.file_version = self.get_file_version()

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
        if self.breed == "windows":
            self.import_winpe()

        distros_added = []
        import_walker(self.path, self.distro_adder, distros_added)

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
        Loop through the signatures, looking for a match for both the signature directory and the version file.
        """
        sigdata = self.api.get_signatures()
        # self.logger.debug("signature cache: %s" % str(sigdata))
        for breed in list(sigdata["breeds"].keys()):
            if self.breed and self.breed != breed:
                continue
            for version in list(sigdata["breeds"][breed].keys()):
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
                                    # if the version file regex exists, we use it to scan the contents of the target
                                    # version file to ensure it's the right version
                                    if sigdata["breeds"][breed][version]["version_file_regex"]:
                                        vf_re = re.compile(sigdata["breeds"][breed][version]["version_file_regex"])
                                        vf_lines = self.get_file_lines(os.path.join(root, fname))
                                        for line in vf_lines:
                                            if vf_re.match(line):
                                                break
                                        else:
                                            continue
                                    self.logger.debug("Found a matching signature: breed=%s, version=%s" %
                                    (breed, version))
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
    def get_valid_arches(self) -> list:
        """
        Get all valid architectures from the signature file.

        :return: An empty list or all valid architectures.
        """
        if self.signature:
            return sorted(self.signature["supported_arches"], key=lambda s: -1 * len(s))
        return []

    def get_valid_repo_breeds(self) -> list:
        """
        Get all valid repository architectures from the signatures file.

        :return: An empty list or all valid architectures.
        """
        if self.signature:
            return self.signature["supported_repo_breeds"]
        return []

    def distro_adder(self, distros_added, dirname: str, fnames):
        """
        This is an import_walker routine that finds distributions in the directory to be scanned and then creates them.

        :param distros_added: Unknown what this currently does.
        :param dirname: Unknown what this currently does.
        :param fnames: Unknown what this currently does.
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

            # Most of the time we just want to ignore isolinux directories, unless this is one of the oddball distros
            # where we do want it.
            if dirname.find("isolinux") != -1 and not self.signature["isolinux_ok"]:
                continue

            fullname = os.path.join(dirname, x)
            if os.path.islink(fullname) and os.path.isdir(fullname):
                if fullname.startswith(self.path):
                    # Prevent infinite loop with Sci Linux 5
                    # self.logger.warning("avoiding symlink loop")
                    continue
                self.logger.info("following symlink: %s" % fullname)
                import_walker(fullname, self.distro_adder, distros_added)

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
            elif self.breed == "windows" and "wimboot" in self.signature["kernel_file"]:
                kernel = os.path.join(self.settings.tftpboot_location, "wimboot")

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

    def add_entry(self, dirname: str, kernel, initrd):
        """
        When we find a directory with a valid kernel/initrd in it, create the distribution objects as appropriate and
        save them. This includes creating xen and rescue distros/profiles if possible.

        :param dirname: Unkown what this currently does.
        :param kernel: Unkown what this currently does.
        :param initrd: Unkown what this currently does.
        :return: Unkown what this currently does.
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
            self.logger.warning("- Warning : Multiple archs found : %s" % archs)

        distros_added = []
        for pxe_arch in archs:
            name = proposed_name + "-" + pxe_arch
            existing_distro = self.distros.find(name=name)

            if existing_distro is not None:
                self.logger.warning("skipping import, as distro name already exists: %s" % name)
                continue
            else:
                self.logger.info("creating new distro: %s" % name)
                new_distro = distro.Distro(self.collection_mgr)

            if name.find("-autoboot") != -1:
                # this is an artifact of some EL-3 imports
                continue

            new_distro.set_name(name)
            new_distro.set_kernel(kernel)
            new_distro.set_initrd(initrd)
            new_distro.set_arch(pxe_arch)
            new_distro.set_breed(self.breed)
            new_distro.set_os_version(self.os_version)
            new_distro.set_kernel_options(self.signature.get("kernel_options", ""))
            new_distro.set_kernel_options_post(self.signature.get("kernel_options_post", ""))
            new_distro.set_template_files(self.signature.get("template_files", ""))
            supported_distro_boot_loaders = utils.get_supported_distro_boot_loaders(new_distro, self.api)
            new_distro.set_supported_boot_loaders(supported_distro_boot_loaders)
            new_distro.set_boot_loader(supported_distro_boot_loaders[0])

            boot_files = ''
            for boot_file in self.signature["boot_files"]:
                boot_files += '$local_img_path/%s=%s/%s ' % (boot_file, self.path, boot_file)
            new_distro.set_boot_files(boot_files.strip())

            self.configure_tree_location(new_distro)

            self.distros.add(new_distro, save=True)
            distros_added.append(new_distro)

            # see if the profile name is already used, if so, skip it and
            # do not modify the existing profile

            existing_profile = self.profiles.find(name=name)

            if existing_profile is None:
                self.logger.info("creating new profile: %s" % name)
                new_profile = profile.Profile(self.collection_mgr)
            else:
                self.logger.info("skipping existing profile, name already exists: %s" % name)
                continue

            new_profile.set_name(name)
            new_profile.set_distro(name)
            new_profile.set_autoinstall(self.autoinstall_file)

            # depending on the name of the profile we can
            # define a good virt-type for usage with koan
            if name.find("-xen") != -1:
                new_profile.set_virt_type("xenpv")
            elif name.find("vmware") != -1:
                new_profile.set_virt_type("vmware")
            else:
                new_profile.set_virt_type("kvm")

            if self.breed == "windows":
                dest_path = os.path.join(self.path, "boot")
                kernel_path = f"http://@@http_server@@/images/{name}/wimboot"
                if new_distro.os_version in ("xp", "2003"):
                    kernel_path = "pxeboot.0"
                bootmgr = "bootmgr.exe"
                if "wimboot" in kernel:
                    bootmgr = "bootmgr.efi"
                bootmgr_path = os.path.join(dest_path, bootmgr)
                bcd_path = os.path.join(dest_path, "bcd")
                winpe_path = os.path.join(dest_path, "winpe.wim")
                if (
                    os.path.exists(bootmgr_path)
                    and os.path.exists(bcd_path)
                    and os.path.exists(winpe_path)
                ):
                    new_profile.autoinstall_meta = {
                        "kernel": kernel_path,
                        "bootmgr": bootmgr,
                        "bcd": "bcd",
                        "winpe": "winpe.wim",
                        "answerfile": "autounattended.xml",
                        "post_install_script": "post_install.cmd",
                    }

            self.profiles.add(new_profile, save=True)

        return distros_added

    def learn_arch_from_tree(self) -> list:
        """
        If a distribution is imported from DVD, there is a good chance the path doesn't contain the arch and we should
        add it back in so that it's part of the meaningful name ... so this code helps figure out the arch name.  This
        is important for producing predictable distro names (and profile names) from differing import sources.

        :return: The guessed architecture from a distribution dvd.
        :rtype: list
        """

        result = {}

        # FIXME : this is called only once, should not be a walk
        import_walker(self.path, self.arch_walker, result)

        if result.pop("amd64", False):
            result["x86_64"] = 1
        if result.pop("i686", False):
            result["i386"] = 1
        if result.pop("i586", False):
            result["i386"] = 1
        if result.pop("x86", False):
            result["i386"] = 1
        if result.pop("arm64", False):
            result["aarch64"] = 1

        return list(result.keys())

    def arch_walker(self, foo: dict, dirname: str, fnames: list):
        """
        Function for recursively searching through a directory for a kernel file matching a given architecture, called
        by ``learn_arch_from_tree()``

        :param foo: Into this dict there will be put additional meta information.
        :param dirname: The directory name where the kernel can be found.
        :param fnames: This should be a list like object which will be looped over.
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

    def get_proposed_name(self, dirname: str, kernel=None) -> str:
        """
        Given a directory name where we have a kernel/initrd pair, try to autoname the distribution (and profile) object
        based on the contents of that path.

        :param dirname: The directory where the distribution is living in.
        :param kernel: The kernel of that distro.
        :return: The name which is recommended.
        :rtype: str
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
            for arch in ["i386", "x86_64", "ia64", "ppc64le", "ppc64el", "ppc64", "ppc32", "ppc", "x86", "s390x",
                         "s390", "386", "amd"]:
                name = name.replace("%s%s" % (separator, arch), "")

        return name

    def configure_tree_location(self, distribution: distro.Distro):
        """
        Once a distribution is identified, find the part of the distribution that has the URL in it that we want to use
        for automating the Linux distribution installation, and create a autoinstall_meta variable $tree that contains
        this.

        :param distribution: The distribution object for that the tree should be configured.
        """

        base = self.rootdir

        # how we set the tree depends on whether an explicit network_root was specified
        if self.network_root is None:
            dest_link = os.path.join(self.settings.webdir, "links", distribution.name)
            # create the links directory only if we are mirroring because with SELinux Apache can't symlink to NFS
            # (without some doing)
            if not os.path.exists(dest_link):
                try:
                    self.logger.info("trying symlink: %s -> %s" % (str(base), str(dest_link)))
                    os.symlink(base, dest_link)
                except:
                    # FIXME: This shouldn't happen but I've seen it ... debug ...
                    self.logger.warning(
                        "symlink creation failed: %(base)s, %(dest)s" % {"base": base, "dest": dest_link})
            tree = "http://@@http_server@@/cblr/links/%s" % distribution.name
            self.set_install_tree(distribution, tree)
        else:
            # Where we assign the automated installation file source is relative to our current directory and the input
            # start directory in the crawl. We find the path segments between and tack them on the network source
            # path to find the explicit network path to the distro that Anaconda can digest.
            tail = utils.path_tail(self.path, base)
            tree = self.network_root[:-1] + tail
            self.set_install_tree(distribution, tree)

    def set_install_tree(self, distribution: distro.Distro, url: str):
        """
        Simple helper function to set the tree automated installation metavariable.

        :param distribution: The distribution object for which the install tree should be set.
        :param url: The url for the tree.
        """
        distribution.autoinstall_meta["tree"] = url

    # ==========================================================================
    # Repo Functions

    def repo_finder(self, distros_added: List[distro.Distro]):
        """
        This routine looks through all distributions and tries to find any applicable repositories in those
        distributions for post-install usage.

        :param distros_added: This is an iteratable set of distributions.
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

            for current_distro_added in distros_added:
                if current_distro_added.kernel.find("distro_mirror") != -1:
                    repo_adder(current_distro_added)
                    self.distros.add(current_distro_added, save=True, with_triggers=False)
                else:
                    self.logger.info("skipping distro %s since it isn't mirrored locally" % current_distro_added.name)

    # ==========================================================================
    # yum-specific

    def yum_repo_adder(self, distro: distro.Distro):
        """
        For yum, we recursively scan the rootdir for repos to add

        :param distro: The distribution object to scan and possibly add.
        """
        self.logger.info("starting descent into %s for %s" % (self.rootdir, distro.name))
        import_walker(self.rootdir, self.yum_repo_scanner, distro)

    def yum_repo_scanner(self, distro: distro.Distro, dirname: str, fnames):
        """
        This is an import_walker routine that looks for potential yum repositories to be added to the configuration for
        post-install usage.

        :param distro: The distribution object to check for.
        :param dirname: The folder with repositories to check.
        :param fnames: Unkown what this does exactly.
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

    def yum_process_comps_file(self, comps_path: str, distribution: distro.Distro):
        """
        When importing Fedora/EL certain parts of the install tree can also be used as yum repos containing packages
        that might not yet be available via updates in yum. This code identifies those areas. Existing repodata will be
        used as-is, but repodate is created for earlier, non-yum based, installers.

        :param comps_path: Not know what this is exactly for.
        :param distribution: The distributions to check.
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
            return  # no comps xml file found

        # pull the filename from the longer part
        comps_file = files[0].split("/")[-1]

        try:
            # Store the yum configs on the filesystem so we can use them later. And configure them in the automated
            # installation file post section, etc.

            counter = len(distribution.source_repos)

            # find path segment for yum_url (changing filesystem path to http:// trailing fragment)
            seg = comps_path.rfind("distro_mirror")
            urlseg = comps_path[(seg + len("distro_mirror") + 1):]

            fname = os.path.join(self.settings.webdir,
                                 "distro_mirror", "config", "%s-%s.repo" % (distribution.name, counter))

            repo_url = "http://@@http_server@@/cobbler/distro_mirror/config/%s-%s.repo" % (distribution.name, counter)
            repo_url2 = "http://@@http_server@@/cobbler/distro_mirror/%s" % urlseg

            distribution.source_repos.append([repo_url, repo_url2])

            config_dir = os.path.dirname(fname)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            # NOTE: the following file is now a Cheetah template, so it can be remapped during sync, that's why we have
            # the @@http_server@@ left as templating magic.
            # repo_url2 is actually no longer used. (?)

            with open(fname, "w+") as config_file:
                config_file.write("[core-%s]\n" % counter)
                config_file.write("name=core-%s\n" % counter)
                config_file.write("baseurl=http://@@http_server@@/cobbler/distro_mirror/%s\n" % urlseg)
                config_file.write("enabled=1\n")
                config_file.write("gpgcheck=0\n")
                config_file.write("priority=$yum_distro_priority\n")

            # Don't run creatrepo twice -- this can happen easily for Xen and PXE, when they'll share same repo files.
            if keeprepodata:
                self.logger.info("Keeping repodata as-is :%s/repodata" % comps_path)
                self.found_repos[comps_path] = 1

            elif comps_path not in self.found_repos:
                utils.remove_yum_olddata(comps_path)
                cmd = "createrepo %s --groupfile %s %s" % (
                    self.settings.createrepo_flags, os.path.join(comps_path, masterdir, comps_file), comps_path)
                utils.subprocess_call(self.logger, cmd, shell=True)
                self.found_repos[comps_path] = 1
                # For older distros, if we have a "base" dir parallel with "repodata", we need to copy comps.xml up
                # one...
                p1 = os.path.join(comps_path, "repodata", "comps.xml")
                p2 = os.path.join(comps_path, "base", "comps.xml")
                if os.path.exists(p1) and os.path.exists(p2):
                    shutil.copyfile(p1, p2)
        except:
            self.logger.error("error launching createrepo (not installed?), ignoring")
            utils.log_exc(self.logger)

    # ==========================================================================
    # apt-specific

    def apt_repo_adder(self, distribution: distro.Distro):
        """
        Automatically import apt repositories when importing signatures.

        :param distribution: The distribution to scan for apt repositories.
        """
        self.logger.info("adding apt repo for %s" % distribution.name)
        # Obtain repo mirror from APT if available
        mirror = ""
        if apt_available:
            # Example returned URL: http://us.archive.ubuntu.com/ubuntu
            mirror = self.get_repo_mirror_from_apt()
        # If the mirror is only whitespace then use the default one.
        if mirror.isspace():
            mirror = "http://archive.ubuntu.com/ubuntu"

        repo = item_repo.Repo(self.collection_mgr)
        repo.set_breed("apt")
        repo.set_arch(distribution.arch)
        repo.set_keep_updated(True)
        repo.set_apt_components("main universe")  # TODO: make a setting?
        repo.set_apt_dists("%s %s-updates %s-security" % ((distribution.os_version,) * 3))
        repo.set_name(distribution.name)
        repo.set_os_version(distribution.os_version)

        if distribution.breed == "ubuntu":
            repo.set_mirror(mirror)
        else:
            # NOTE : The location of the mirror should come from timezone
            repo.set_mirror("http://ftp.%s.debian.org/debian/dists/%s" % ('us', distribution.os_version))

        self.logger.info("Added repos for %s" % distribution.name)
        repos = self.collection_mgr.repos()
        repos.add(repo, save=True)
        # FIXME: Add the found/generated repos to the profiles that were created during the import process

    def get_repo_mirror_from_apt(self):
        """
        This tries to determine the apt mirror/archive to use (when processing repos) if the host machine is Debian or
        Ubuntu.

        :return: False if the try fails or otherwise the mirrors.
        """
        try:
            sources = sourceslist.SourcesList()
            release = debdistro.get_distro()
            release.get_sources(sources)
            mirrors = release.get_server_list()
            for mirror in mirrors:
                if mirror[2]:
                    return mirror[1]
        except:
            return False

    # ==========================================================================
    # rhn-specific

    def rhn_repo_adder(self, distribution: distro.Distro):
        """
        Not currently used.

        :param distribution: Not used currently.
        """
        return

    # ==========================================================================
    # rsync-specific

    def rsync_repo_adder(self, distribution: distro.Distro):
        """
        Not currently used.

        :param distribution: Not used currently.
        """
        return

    # ==========================================================================
    # windows-specific

    def import_winpe(self) -> None:
        """
        Preparing a Windows distro for network boot.
        """
        winpe_path = self.extract_winpe(self.path)

        # For Windows, file paths are case-insensitive within a WinPE image, but for wimlib-utils
        # they are not. And wimlib-utils does not provide options for case-insensitive search
        # and extraction of files from this image other than setting the WIMLIB_IMAGEX_IGNORE_CASE
        # environment variable.
        wimdir_result = utils.subprocess_get(
            None,
            ["/usr/bin/wimdir", winpe_path, "1"], shell=False
        )
        wim_file_list = wimdir_result.split("\n")
        file_dict = {
            "/windows/boot/pxe/pxeboot.n12": "",
            "/windows/boot/pxe/bootmgr.exe": "",
            "/windows/boot/efi/bootmgr.efi": "",
            "/windows/system32/config/software": "",
        }
        for wim_file in wim_file_list:
            if wim_file.lower() in file_dict:
                file_dict[wim_file.lower()] = wim_file

        file_list = [
            file_dict["/windows/boot/efi/bootmgr.efi"],
            file_dict["/windows/system32/config/software"],
        ]
        if "wimboot" not in self.signature["kernel_file"]:
            file_list.extend(
                [
                    file_dict["/windows/boot/pxe/pxeboot.n12"],
                    file_dict["/windows/boot/pxe/bootmgr.exe"],
                ]
            )

        self.extract_files_from_wim(winpe_path, file_list)
        self.update_winpe(winpe_path, file_dict["/windows/system32/config/software"])

    def extract_winpe(self, distro_path: str) -> str:
        """
        Extracting winpe.wim from boot.win.

        :param distro_path: The directory where the Windows distro is located.
        :return: The path to the extracted WinPE image.
        :raises CX
        """
        bootwim_path = os.path.join(distro_path, "sources", "boot.wim")
        dest_path = os.path.join(distro_path, "boot")

        if not os.path.exists(bootwim_path):
            error_msg = f"{bootwim_path} not found!"
            self.logger.error(error_msg)
            raise CX(error_msg)

        winpe_path = os.path.join(dest_path, "winpe.wim")
        if not os.path.exists(dest_path):
            utils.mkdir(dest_path)
        if os.path.exists(winpe_path):
            utils.rmfile(winpe_path)
        if (
            utils.subprocess_call(
                None,
                ["/usr/bin/wimexport", bootwim_path, "1", winpe_path, "--boot"],
                shell=False,
            )
            != 0
        ):
            error_msg = f"Cannot extract {winpe_path} from {bootwim_path}!"
            self.logger.error(error_msg)
            raise CX(error_msg)

        return winpe_path

    def update_winpe(self, winpe_path: str, win_registry: str) -> None:
        """
        Update WinPE image for network boot.

        :param winpe_path: The path to WinPE image.
        :param win_registry: The path to the Windows registry in the WinPE image.
        :raises CX
        """
        if not HAS_HIVEX:
            error_msg = (
                "python3-hivex not found. If you need Automatic Windows "
                "Installation support, please install."
            )
            self.logger.error(error_msg)
            raise CX(error_msg)

        software = os.path.join(
            os.path.dirname(winpe_path), os.path.basename(win_registry).lower()
        )
        hivex_obj = hivex.Hivex(software, write=True)  # type: ignore
        nodes: List[Any] = [hivex_obj.root()]  # type: ignore

        while len(nodes) > 0:
            node = nodes.pop()
            nodes.extend(hivex_obj.node_children(node))  # type: ignore
            self.reg_node_update(hivex_obj, node)

        hivex_obj.commit(software)  # type: ignore

        utils.subprocess_call(
            None,
            [
                "/usr/bin/wimupdate",
                winpe_path,
                f"--command=add {software} {win_registry}",
            ],
            shell=False,
        )
        os.remove(software)

    def reg_node_update(self, hivex_obj: Any, node: Any) -> None:
        """
        Replacement of the substring X:\\$windows.~bt with X: in the Windows registry node.

        :param hivex_obj: Hivex object.
        :param node: The registry node.
        """
        new_values: List[Optional[Dict[str, Any]]] = []
        update_flag = False
        key_vals: List[Any] = hivex_obj.node_values(node)  # type: ignore
        pat = "X:\\$windows.~bt"

        for key_val in key_vals:
            key: str = hivex_obj.value_key(key_val)  # type: ignore
            val = hivex_obj.node_get_value(node, key)  # type: ignore
            val_type: int
            val_value: bytes
            val_type, val_value = hivex_obj.value_value(val)  # type: ignore
            if pat in key:
                key = key.replace(pat, "X:")
                update_flag = True
            if val_type in (REG_SZ, REG_EXPAND_SZ):
                val_string: str = hivex_obj.value_string(val)  # type: ignore
                if pat in val_string:
                    val_string = val_string.replace(pat, "X:")
                    val_value = (val_string + "\0").encode(encoding="utf-16le")
                    update_flag = True
            new_values.append(
                {
                    "key": key,
                    "t": val_type,
                    "value": val_value,
                }
            )

        if update_flag:
            hivex_obj.node_set_values(node, new_values)  # type: ignore

    def extract_files_from_wim(self, winpe_path: str, wim_files: List[str]) -> None:
        """
        Extracting files from winpe.win.

        :param winpe_path: The path to the WinPE image.
        :param wim_files: The list of files to extract.
        :raises CX
        """
        dest_path = os.path.dirname(winpe_path)
        cmd_args = [
            "/usr/bin/wimextract",
            winpe_path,
            "1",
        ]
        cmd_args.extend(wim_files)
        cmd_args.extend(
            [
                f"--dest-dir={dest_path}",
                "--no-acls",
                "--no-attributes",
            ]
        )
        if (
            utils.subprocess_call(
                None,
                cmd_args,
                shell=False,
            )
            != 0
        ):
            error_msg = f'Cannot extract "{wim_files}" files from {winpe_path}!'
            self.logger.error(error_msg)
            raise CX(error_msg)

        for wim_file_path in wim_files:
            wim_file = os.path.basename(wim_file_path)
            if wim_file != wim_file.lower():
                os.rename(
                    os.path.join(dest_path, wim_file),
                    os.path.join(dest_path, wim_file.lower()),
                )


# ==========================================================================


def get_import_manager(config, logger):
    """
    Get an instance of the import manager which enables you to import various things.

    :param config: The configuration for the import manager.
    :param logger: The logger to audit all actions with.
    :return: The object to import data with.
    """
    return ImportSignatureManager(config, logger)
