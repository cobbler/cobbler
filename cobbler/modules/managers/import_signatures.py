"""
Cobbler Module that contains the code for ``cobbler import`` and provides the magic to automatically detect an ISO image
OS and version.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: John Eckersberg <jeckersb@redhat.com>

import glob
import gzip
import os
import os.path
import re
import shutil
import stat
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterable, List, Optional, Union

import magic  # type: ignore

from cobbler import enums, utils
from cobbler.cexceptions import CX
from cobbler.modules.managers import ManagerModule
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro

try:
    import hivex  # type: ignore
    from hivex.hive_types import REG_SZ  # type: ignore

    HAS_HIVEX = True
except ImportError:
    HAS_HIVEX = False  # type: ignore

# Import aptsources module if available to obtain repo mirror.
try:
    from aptsources import distro as debdistro  # type: ignore
    from aptsources import sourceslist  # type: ignore

    APT_AVAILABLE = True
except ImportError:
    APT_AVAILABLE = False  # type: ignore

MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage/import"


def import_walker(
    top: str, func: Callable[[Any, str, List[str]], None], arg: Any
) -> None:
    """
    Directory tree walk with callback function.

    For each directory in the directory tree rooted at top (including top itself, but excluding '.' and '..'), call
    ``func(arg, dirname, filenames)``. dirname is the name of the directory, and filenames a list of the names of the
    files and subdirectories in dirname (excluding '.' and '..').  ``func`` may modify the ``filenames`` list in-place
    (e.g. via ``del`` or ``slice`` assignment), and walk will only recurse into the subdirectories whose names remain
    in ``filenames``; this can be used to implement a filter, or to impose a specific order of visiting. No semantics
    are defined for, or required of, ``arg``, beyond that arg is always passed to ``func``. It can be used, e.g., to
    pass a filename pattern, or a mutable object designed to accumulate statistics.

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
        path_name = os.path.join(top, name)
        try:
            file_stats = os.lstat(path_name)
        except os.error:
            continue
        if stat.S_ISDIR(file_stats.st_mode):
            import_walker(path_name, func, arg)


class _ImportSignatureManager(ManagerModule):
    @staticmethod
    def what() -> str:
        """
        Identifies what service this manages.

        :return: Always will return ``import/signatures``.
        """
        return "import/signatures"

    def __init__(self, api: "CobblerAPI") -> None:
        super().__init__(api)

        self.signature: Any = None
        self.found_repos: Dict[str, int] = {}

    def get_file_lines(self, filename: str) -> Union[List[str], List[bytes]]:
        """
        Get lines from a file, which may or may not be compressed. If compressed then it will be uncompressed using
        ``gzip`` as the algorithm.

        :param filename: The name of the file to be read.
        :return: An array with all the lines.
        """
        ftype = magic.detect_from_filename(filename)  # type: ignore
        if ftype.mime_type == "application/gzip":  # type: ignore
            try:
                with gzip.open(filename, "r") as file_fd:
                    return file_fd.readlines()
            except Exception:
                pass
        if ftype.mime_type == "application/x-ms-wim":  # type: ignore
            cmd = "/usr/bin/wiminfo"
            if os.path.exists(cmd):
                cmd = f"{cmd} {filename}"
                return utils.subprocess_get(cmd).splitlines()

            self.logger.info("no %s found, please install wimlib-utils", cmd)
        elif ftype.mime_type == "text/plain":  # type: ignore
            with open(filename, "r", encoding="UTF-8") as file_fd:
                return file_fd.readlines()
        else:
            self.logger.info(
                'Could not detect the filetype and read the content of file "%s". Returning nothing.',
                filename,
            )
        return []

    def run(
        self,
        path: str,
        name: str,
        network_root: Optional[str] = None,
        autoinstall_file: Optional[str] = None,
        arch: Optional[str] = None,
        breed: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> None:
        """
        This is the main entry point in a manager. It is a required function for import modules.

        :param path: the directory we are scanning for files
        :param name: the base name of the distro
        :param network_root: the remote path (nfs/http/ftp) for the distro files
        :param autoinstall_file: user-specified response file, which will override the default
        :param arch: user-specified architecture
        :param breed: user-specified breed
        :param os_version: user-specified OS version
        :raises CX
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

        if self.os_version == "":  # type: ignore
            self.os_version = None

        if self.network_root == "":
            self.network_root = None

        if self.os_version and not self.breed:  # type: ignore
            utils.die(
                "OS version can only be specified when a specific breed is selected"
            )

        self.signature = self.scan_signatures()
        if not self.signature:
            error_msg = f"No signature matched in {path}"
            self.logger.error(error_msg)
            raise CX(error_msg)

        # now walk the filesystem looking for distributions that match certain patterns
        self.logger.info("Adding distros from path %s:", self.path)
        distros_added: List["Distro"] = []
        import_walker(self.path, self.distro_adder, distros_added)

        if len(distros_added) == 0:
            if self.breed == "windows":  # type: ignore
                cmd_path = "/usr/bin/wimexport"
                bootwim_path = os.path.join(self.path, "sources", "boot.wim")
                dest_path = os.path.join(self.path, "boot")
                if os.path.exists(cmd_path) and os.path.exists(bootwim_path):
                    winpe_path = os.path.join(dest_path, "winpe.wim")
                    if not os.path.exists(dest_path):
                        filesystem_helpers.mkdir(dest_path)
                    if os.path.exists(winpe_path):
                        filesystem_helpers.rmfile(winpe_path)
                    return_code = utils.subprocess_call(
                        [cmd_path, bootwim_path, "1", winpe_path, "--boot"], shell=False
                    )
                    if return_code == 0:
                        cmd = ["/usr/bin/wimdir", winpe_path, "1"]
                        wimdir_result = utils.subprocess_get(cmd, shell=False)
                        wimdir_file_list = wimdir_result.split("\n")
                        pxe_path = "/Windows/Boot/PXE"
                        config_path = "/Windows/System32/config/SOFTWARE"

                        for file in wimdir_file_list:
                            if file.lower() == pxe_path.lower():
                                pxe_path = file
                            elif file.lower() == config_path.lower():
                                config_path = file

                        cmd_path = "/usr/bin/wimextract"
                        return_code = utils.subprocess_call(
                            [
                                cmd_path,
                                bootwim_path,
                                "1",
                                f"{pxe_path}/pxeboot.n12",
                                f"{pxe_path}/bootmgr.exe",
                                config_path,
                                f"--dest-dir={dest_path}",
                                "--no-acls",
                                "--no-attributes",
                            ],
                            shell=False,
                        )
                        if return_code == 0:
                            if HAS_HIVEX:
                                software = os.path.join(
                                    dest_path, os.path.basename(config_path)
                                )
                                hivex_obj = hivex.Hivex(software, write=True)  # type: ignore
                                root = hivex_obj.root()  # type: ignore
                                node = hivex_obj.node_get_child(root, "Microsoft")  # type: ignore
                                node = hivex_obj.node_get_child(node, "Windows NT")  # type: ignore
                                node = hivex_obj.node_get_child(node, "CurrentVersion")  # type: ignore
                                hivex_obj.node_set_value(  # type: ignore
                                    node,
                                    {
                                        "key": "SystemRoot",
                                        "t": REG_SZ,
                                        "value": "x:\\Windows\0".encode(
                                            encoding="utf-16le"
                                        ),
                                    },
                                )
                                node = hivex_obj.node_get_child(node, "WinPE")  # type: ignore

                                # remove the key InstRoot from the registry
                                values = hivex_obj.node_values(node)  # type: ignore
                                new_values = []

                                for value in values:  # type: ignore
                                    keyname = hivex_obj.value_key(value)  # type: ignore

                                    if keyname == "InstRoot":
                                        continue

                                    val = hivex_obj.node_get_value(node, keyname)  # type: ignore
                                    valtype = hivex_obj.value_type(val)[0]  # type: ignore
                                    value2 = hivex_obj.value_value(val)[1]  # type: ignore
                                    valobject = {  # type: ignore
                                        "key": keyname,
                                        "t": int(valtype),  # type: ignore
                                        "value": value2,
                                    }
                                    new_values.append(valobject)  # type: ignore

                                hivex_obj.node_set_values(node, new_values)  # type: ignore
                                hivex_obj.commit(software)  # type: ignore

                                cmd_path = "/usr/bin/wimupdate"
                                return_code = utils.subprocess_call(
                                    [
                                        cmd_path,
                                        winpe_path,
                                        f"--command=add {software} {config_path}",
                                    ],
                                    shell=False,
                                )
                                os.remove(software)
                            else:
                                self.logger.info(
                                    "python3-hivex not found. If you need Automatic Windows "
                                    "Installation support, please install."
                                )
                            import_walker(self.path, self.distro_adder, distros_added)

        if len(distros_added) == 0:
            self.logger.warning("No distros imported, bailing out")
            return

        # find out if we can auto-create any repository records from the install tree
        if self.network_root is None:
            self.logger.info("associating repos")
            # FIXME: this automagic is not possible (yet) without mirroring
            self.repo_finder(distros_added)

    def scan_signatures(self) -> Optional[Any]:
        """
        Loop through the signatures, looking for a match for both the signature directory and the version file.
        """
        sigdata = self.api.get_signatures()
        # self.logger.debug("signature cache: %s" % str(sigdata))
        for breed in list(sigdata["breeds"].keys()):
            if self.breed and self.breed != breed:  # type: ignore
                continue
            for version in list(sigdata["breeds"][breed].keys()):
                if self.os_version and self.os_version != version:  # type: ignore
                    continue
                for sig in sigdata["breeds"][breed][version].get("signatures", []):
                    pkgdir = os.path.join(self.path, sig)
                    if os.path.exists(pkgdir):
                        self.logger.debug(
                            "Found a candidate signature: breed=%s, version=%s",
                            breed,
                            version,
                        )
                        f_re = re.compile(
                            sigdata["breeds"][breed][version]["version_file"]
                        )
                        for (root, subdir, fnames) in os.walk(self.path):
                            for fname in fnames + subdir:
                                if f_re.match(fname):
                                    # if the version file regex exists, we use it to scan the contents of the target
                                    # version file to ensure it's the right version
                                    if sigdata["breeds"][breed][version][
                                        "version_file_regex"
                                    ]:
                                        vf_re = re.compile(
                                            sigdata["breeds"][breed][version][
                                                "version_file_regex"
                                            ]
                                        )
                                        vf_lines = self.get_file_lines(
                                            os.path.join(root, fname)
                                        )
                                        for line in vf_lines:
                                            if vf_re.match(line):
                                                break
                                        else:
                                            continue
                                    self.logger.debug(
                                        "Found a matching signature: breed=%s, version=%s",
                                        breed,
                                        version,
                                    )
                                    if not self.breed:  # type: ignore
                                        self.breed = breed
                                    if not self.os_version:  # type: ignore
                                        self.os_version = version
                                    if not self.autoinstall_file:
                                        self.autoinstall_file = sigdata["breeds"][
                                            breed
                                        ][version]["default_autoinstall"]
                                    self.pkgdir = pkgdir
                                    return sigdata["breeds"][breed][version]
        return None

    # required function for import modules
    def get_valid_arches(self) -> List[Any]:
        """
        Get all valid architectures from the signature file.

        :return: An empty list or all valid architectures.
        """
        if self.signature:
            return sorted(self.signature["supported_arches"], key=lambda s: -1 * len(s))
        return []

    def get_valid_repo_breeds(self) -> List[Any]:
        """
        Get all valid repository architectures from the signatures file.

        :return: An empty list or all valid architectures.
        """
        if self.signature:
            return self.signature["supported_repo_breeds"]
        return []

    def distro_adder(
        self, distros_added: List["Distro"], dirname: str, filenames: List[str]
    ) -> None:
        """
        This is an import_walker routine that finds distributions in the directory to be scanned and then creates them.

        :param distros_added: Unknown what this currently does.
        :param dirname: Unknown what this currently does.
        :param filenames: Unknown what this currently does.
        """

        re_krn = re.compile(self.signature["kernel_file"])
        re_img = re.compile(self.signature["initrd_file"])

        # make sure we don't mismatch PAE and non-PAE types
        initrd = None
        kernel = None
        pae_initrd = None
        pae_kernel = None

        for filename in filenames:
            adtls: List["Distro"] = []

            # Most of the time we just want to ignore isolinux directories, unless this is one of the oddball distros
            # where we do want it.
            if dirname.find("isolinux") != -1 and not self.signature["isolinux_ok"]:
                continue

            fullname = os.path.join(dirname, filename)
            if os.path.islink(fullname) and os.path.isdir(fullname):
                if fullname.startswith(self.path):
                    # Prevent infinite loop with Sci Linux 5
                    # self.logger.warning("avoiding symlink loop")
                    continue
                self.logger.info("following symlink: %s", fullname)
                import_walker(fullname, self.distro_adder, distros_added)

            if re_img.match(filename):
                if filename.find("PAE") == -1:
                    initrd = os.path.join(dirname, filename)
                else:
                    pae_initrd = os.path.join(dirname, filename)

            if re_krn.match(filename):
                if filename.find("PAE") == -1:
                    kernel = os.path.join(dirname, filename)
                else:
                    pae_kernel = os.path.join(dirname, filename)

            # if we've collected a matching kernel and initrd pair, turn them in and add them to the list
            if initrd is not None and kernel is not None:
                adtls.extend(self.add_entry(dirname, kernel, initrd))
                kernel = None
                initrd = None
            elif pae_initrd is not None and pae_kernel is not None:
                adtls.extend(self.add_entry(dirname, pae_kernel, pae_initrd))
                pae_kernel = None
                pae_initrd = None

            distros_added.extend(adtls)

    def add_entry(self, dirname: str, kernel: str, initrd: str) -> List["Distro"]:
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
                utils.die(
                    f"Given arch ({self.arch}) not found on imported tree {self.path}"
                )

        if len(archs) == 0:
            self.logger.error(
                "No arch could be detected in %s, and none was specified via the --arch option",
                dirname,
            )
            return []
        if len(archs) > 1:
            self.logger.warning("- Warning : Multiple archs found : %s", archs)

        distros_added: List["Distro"] = []
        for pxe_arch in archs:
            name = proposed_name + "-" + pxe_arch
            existing_distro = self.distros.find(name=name)

            if existing_distro is not None:
                self.logger.warning(
                    "skipping import, as distro name already exists: %s", name
                )
                continue
            new_distro = self.api.new_distro()

            if name.find("-autoboot") != -1:
                # this is an artifact of some EL-3 imports
                continue

            new_distro.name = name
            new_distro.kernel = kernel
            new_distro.initrd = initrd
            new_distro.arch = pxe_arch
            new_distro.breed = self.breed  # type: ignore
            new_distro.os_version = self.os_version  # type: ignore
            new_distro.kernel_options = self.signature.get("kernel_options", "")
            new_distro.kernel_options_post = self.signature.get(
                "kernel_options_post", ""
            )
            new_distro.template_files = self.signature.get("template_files", "")

            boot_files: Dict[str, str] = {}
            for boot_file in self.signature["boot_files"]:
                boot_files[f"$local_img_path/{boot_file}"] = f"{self.path}/{boot_file}"
            new_distro.boot_files = boot_files

            self.configure_tree_location(new_distro)

            self.distros.add(new_distro, save=True)
            distros_added.append(new_distro)

            # see if the profile name is already used, if so, skip it and
            # do not modify the existing profile

            existing_profile = self.profiles.find(name=name)

            if existing_profile is None:
                new_profile = self.api.new_profile()
            else:
                self.logger.info(
                    "skipping existing profile, name already exists: %s", name
                )
                continue

            new_profile.name = name
            new_profile.distro = name
            new_profile.autoinstall = self.autoinstall_file  # type: ignore

            # depending on the name of the profile we can
            # define a good virt-type for usage with koan
            if name.find("-xen") != -1:
                new_profile.virt_type = enums.VirtType.XENPV
            elif name.find("vmware") != -1:
                new_profile.virt_type = enums.VirtType.VMWARE
            else:
                new_profile.virt_type = enums.VirtType.KVM

            if self.breed == "windows":  # type: ignore
                dest_path = os.path.join(self.path, "boot")
                bootmgr_path = os.path.join(dest_path, "bootmgr.exe")
                bcd_path = os.path.join(dest_path, "bcd")
                winpe_path = os.path.join(dest_path, "winpe.wim")
                if (
                    os.path.exists(bootmgr_path)
                    and os.path.exists(bcd_path)
                    and os.path.exists(winpe_path)
                ):
                    new_profile.autoinstall_meta = {
                        "kernel": os.path.basename(kernel),
                        "bootmgr": "bootmgr.exe",
                        "bcd": "bcd",
                        "winpe": "winpe.wim",
                        "answerfile": "autounattended.xml",
                    }

            self.profiles.add(new_profile, save=True)

        return distros_added

    def learn_arch_from_tree(self) -> List[Any]:
        """
        If a distribution is imported from DVD, there is a good chance the path doesn't contain the arch and we should
        add it back in so that it's part of the meaningful name ... so this code helps figure out the arch name.  This
        is important for producing predictable distro names (and profile names) from differing import sources.

        :return: The guessed architecture from a distribution dvd.
        """

        result: Dict[str, int] = {}

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

    def arch_walker(self, foo: Dict[Any, Any], dirname: str, fnames: List[Any]) -> None:
        """
        Function for recursively searching through a directory for a kernel file matching a given architecture, called
        by ``learn_arch_from_tree()``

        :param foo: Into this dict there will be put additional meta information.
        :param dirname: The directory name where the kernel can be found.
        :param fnames: This should be a list like object which will be looped over.
        """

        re_krn = re.compile(self.signature["kernel_arch"])

        # try to find a kernel header RPM and then look at it's arch.
        for fname in fnames:
            if re_krn.match(fname):
                if self.signature["kernel_arch_regex"]:
                    re_krn2 = re.compile(self.signature["kernel_arch_regex"])
                    krn_lines = self.get_file_lines(os.path.join(dirname, fname))
                    for line in krn_lines:
                        match_obj = re_krn2.match(line)
                        if match_obj:
                            for group in match_obj.groups():
                                group = group.lower()
                                if group in self.get_valid_arches():
                                    foo[group] = 1
                else:
                    for arch in self.get_valid_arches():
                        if fname.find(arch) != -1:
                            foo[arch] = 1
                            break
                    for arch in ["i686", "amd64"]:
                        if fname.find(arch) != -1:
                            foo[arch] = 1
                            break

    def get_proposed_name(self, dirname: str, kernel: Optional[str] = None) -> str:
        """
        Given a directory name where we have a kernel/initrd pair, try to autoname the distribution (and profile) object
        based on the contents of that path.

        :param dirname: The directory where the distribution is living in.
        :param kernel: The kernel of that distro.
        :return: The name which is recommended.
        """

        if self.name is None:
            raise ValueError("Name cannot be None!")

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
        for name_suffix in (
            "-netboot",
            "-ubuntu-installer",
            "-amd64",
            "-i386",
            "-images",
            "-pxeboot",
            "-install",
            "-isolinux",
            "-boot",
            "-suseboot",
            "-loader",
            "-os",
            "-tree",
            "var-www-cobbler-",
            "distro_mirror-",
        ):
            name = name.replace(name_suffix, "")

        # remove any architecture name related string, as real arch will be appended later
        name = name.replace("chrp", "ppc64")
        for separator in ["-", "_", "."]:
            for arch in [
                "i386",
                "x86_64",
                "ia64",
                "ppc64le",
                "ppc64el",
                "ppc64",
                "ppc32",
                "ppc",
                "x86",
                "s390x",
                "s390",
                "386",
                "amd",
            ]:
                name = name.replace(f"{separator}{arch}", "")

        return name

    def configure_tree_location(self, distribution: "Distro") -> None:
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
                    self.logger.info(
                        "trying symlink: %s -> %s", str(base), str(dest_link)
                    )
                    os.symlink(base, dest_link)
                except Exception:
                    # FIXME: This shouldn't happen but I've seen it ... debug ...
                    self.logger.warning(
                        "symlink creation failed: %s, %s", base, dest_link
                    )
            protocol = self.api.settings().autoinstall_scheme
            tree = f"{protocol}://@@http_server@@/cblr/links/{distribution.name}"
            self.set_install_tree(distribution, tree)
        else:
            # Where we assign the automated installation file source is relative to our current directory and the input
            # start directory in the crawl. We find the path segments between and tack them on the network source
            # path to find the explicit network path to the distro that Anaconda can digest.
            tail = filesystem_helpers.path_tail(self.path, base)
            tree = self.network_root[:-1] + tail
            self.set_install_tree(distribution, tree)

    def set_install_tree(self, distribution: "Distro", url: str) -> None:
        """
        Simple helper function to set the tree automated installation metavariable.

        :param distribution: The distribution object for which the install tree should be set.
        :param url: The url for the tree.
        """
        # mypy cannot handle subclassed setters
        distribution.autoinstall_meta = {"tree": url}  # type: ignore

    # ==========================================================================
    # Repo Functions

    def repo_finder(self, distros_added: List["Distro"]) -> None:
        """
        This routine looks through all distributions and tries to find any applicable repositories in those
        distributions for post-install usage.

        :param distros_added: This is an iteratable set of distributions.
        """
        for repo_breed in self.get_valid_repo_breeds():
            self.logger.info("checking for %s repo(s)", repo_breed)
            repo_adder: Optional[Callable[["Distro"], None]] = None
            if repo_breed == "yum":
                repo_adder = self.yum_repo_adder
            elif repo_breed == "rhn":
                repo_adder = self.rhn_repo_adder
            elif repo_breed == "rsync":
                repo_adder = self.rsync_repo_adder
            elif repo_breed == "apt":
                repo_adder = self.apt_repo_adder
            else:
                self.logger.warning(
                    "skipping unknown/unsupported repo breed: %s", repo_breed
                )
                continue

            for current_distro_added in distros_added:
                if current_distro_added.kernel.find("distro_mirror") != -1:
                    repo_adder(current_distro_added)
                    self.distros.add(
                        current_distro_added, save=True, with_triggers=False
                    )
                else:
                    self.logger.info(
                        "skipping distro %s since it isn't mirrored locally",
                        current_distro_added.name,
                    )

    # ==========================================================================
    # yum-specific

    def yum_repo_adder(self, distro: "Distro") -> None:
        """
        For yum, we recursively scan the rootdir for repos to add

        :param distro: The distribution object to scan and possibly add.
        """
        self.logger.info("starting descent into %s for %s", self.rootdir, distro.name)
        import_walker(self.rootdir, self.yum_repo_scanner, distro)

    def yum_repo_scanner(
        self, distro: "Distro", dirname: str, fnames: Iterable[str]
    ) -> None:
        """
        This is an import_walker routine that looks for potential yum repositories to be added to the configuration for
        post-install usage.

        :param distro: The distribution object to check for.
        :param dirname: The folder with repositories to check.
        :param fnames: Unkown what this does exactly.
        """

        matches = {}
        for fname in fnames:
            if fname in ("base", "repodata"):
                self.logger.info("processing repo at : %s", dirname)
                # only run the repo scanner on directories that contain a comps.xml
                gloob1 = glob.glob(f"{dirname}/{fname}/*comps*.xml")
                if len(gloob1) >= 1:
                    if dirname in matches:
                        self.logger.info(
                            "looks like we've already scanned here: %s", dirname
                        )
                        continue
                    self.logger.info("need to process repo/comps: %s", dirname)
                    self.yum_process_comps_file(dirname, distro)
                    matches[dirname] = 1
                else:
                    self.logger.info(
                        "directory %s is missing xml comps file, skipping", dirname
                    )
                    continue

    def yum_process_comps_file(self, comps_path: str, distribution: "Distro") -> None:
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
        self.logger.info("looking for %s/%s/*comps*.xml", comps_path, masterdir)
        files = glob.glob(f"{comps_path}/{masterdir}/*comps*.xml")
        if len(files) == 0:
            self.logger.info(
                "no comps found here: %s", os.path.join(comps_path, masterdir)
            )
            return  # no comps xml file found

        # pull the filename from the longer part
        comps_file = files[0].split("/")[-1]

        try:
            # Store the yum configs on the filesystem so we can use them later. And configure them in the automated
            # installation file post section, etc.

            counter = len(distribution.source_repos)

            # find path segment for yum_url (changing filesystem path to http:// trailing fragment)
            seg = comps_path.rfind("distro_mirror")
            urlseg = comps_path[(seg + len("distro_mirror") + 1) :]

            fname = os.path.join(
                self.settings.webdir,
                "distro_mirror",
                "config",
                f"{distribution.name}-{counter}.repo",
            )

            protocol = self.api.settings().autoinstall_scheme
            repo_url = f"{protocol}://@@http_server@@/cobbler/distro_mirror/config/{distribution.name}-{counter}.repo"
            repo_url2 = f"{protocol}://@@http_server@@/cobbler/distro_mirror/{urlseg}"

            distribution.source_repos.append([repo_url, repo_url2])

            config_dir = os.path.dirname(fname)
            if not os.path.exists(config_dir):
                os.makedirs(config_dir)

            # NOTE: the following file is now a Cheetah template, so it can be remapped during sync, that's why we have
            # the @@http_server@@ left as templating magic.
            # repo_url2 is actually no longer used. (?)

            with open(fname, "w+", encoding="UTF-8") as config_file:
                config_file.write(f"[core-{counter}]\n")
                config_file.write(f"name=core-{counter}\n")
                config_file.write(
                    f"baseurl={protocol}://@@http_server@@/cobbler/distro_mirror/{urlseg}\n"
                )
                config_file.write("enabled=1\n")
                config_file.write("gpgcheck=0\n")
                config_file.write("priority=$yum_distro_priority\n")

            # Don't run creatrepo twice -- this can happen easily for Xen and PXE, when they'll share same repo files.
            if keeprepodata:
                self.logger.info("Keeping repodata as-is :%s/repodata", comps_path)
                self.found_repos[comps_path] = 1

            elif comps_path not in self.found_repos:
                utils.remove_yum_olddata(comps_path)
                cmd = [
                    "createrepo",
                    self.settings.createrepo_flags,
                    "--groupfile",
                    os.path.join(comps_path, masterdir, comps_file),
                    comps_path,
                ]
                utils.subprocess_call(cmd, shell=False)
                self.found_repos[comps_path] = 1
                # For older distros, if we have a "base" dir parallel with "repodata", we need to copy comps.xml up
                # one...
                path_1 = os.path.join(comps_path, "repodata", "comps.xml")
                path_2 = os.path.join(comps_path, "base", "comps.xml")
                if os.path.exists(path_1) and os.path.exists(path_2):
                    shutil.copyfile(path_1, path_2)
        except Exception:
            self.logger.error("error launching createrepo (not installed?), ignoring")
            utils.log_exc()

    # ==========================================================================
    # apt-specific

    def apt_repo_adder(self, distribution: "Distro") -> None:
        """
        Automatically import apt repositories when importing signatures.

        :param distribution: The distribution to scan for apt repositories.
        """
        self.logger.info("adding apt repo for %s", distribution.name)
        # Obtain repo mirror from APT if available
        mirror = ""
        if APT_AVAILABLE:
            # Example returned URL: http://us.archive.ubuntu.com/ubuntu
            mirror = self.get_repo_mirror_from_apt()
        if not mirror:
            mirror = "http://archive.ubuntu.com/ubuntu"

        repo = self.api.new_repo()
        repo.breed = enums.RepoBreeds.APT
        repo.arch = enums.RepoArchs.to_enum(distribution.arch.value)
        repo.keep_updated = True
        repo.apt_components = "main universe"  # TODO: make a setting?
        repo.apt_dists = (
            f"{distribution.os_version} {distribution.os_version}-updates"
            f"{distribution.os_version}-security"
        )
        repo.name = distribution.name
        repo.os_version = distribution.os_version

        if distribution.breed == "ubuntu":
            repo.mirror = mirror
        else:
            # NOTE : The location of the mirror should come from timezone
            repo.mirror = (
                f"http://ftp.{'us'}.debian.org/debian/dists/{distribution.os_version}"
            )

        self.logger.info("Added repos for %s", distribution.name)
        self.api.add_repo(repo)
        # FIXME: Add the found/generated repos to the profiles that were created during the import process

    def get_repo_mirror_from_apt(self) -> Any:
        """
        This tries to determine the apt mirror/archive to use (when processing repos) if the host machine is Debian or
        Ubuntu.

        :return: False if the try fails or otherwise the mirrors.
        """
        try:
            sources = sourceslist.SourcesList()  # type: ignore
            release = debdistro.get_distro()  # type: ignore
            release.get_sources(sources)  # type: ignore
            mirrors = release.get_server_list()  # type: ignore
            for mirror in mirrors:  # type: ignore
                if mirror[2]:
                    return mirror[1]  # type: ignore
        except Exception:  # type: ignore
            return False

    # ==========================================================================
    # rhn-specific

    @staticmethod
    def rhn_repo_adder(distribution: "Distro") -> None:
        """
        Not currently used.

        :param distribution: Not used currently.
        """
        return

    # ==========================================================================
    # rsync-specific

    @staticmethod
    def rsync_repo_adder(distribution: "Distro") -> None:
        """
        Not currently used.

        :param distribution: Not used currently.
        """
        return


# ==========================================================================


def get_import_manager(api: "CobblerAPI") -> _ImportSignatureManager:
    """
    Get an instance of the import manager which enables you to import various things.

    :param api: The API instance of Cobbler
    :return: The object to import data with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _ImportSignatureManager(api)  # type: ignore
    return MANAGER
