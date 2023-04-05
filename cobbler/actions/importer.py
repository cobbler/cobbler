"""
This module contains the logic that kicks of the ``cobbler import`` process. This is extracted logic from ``api.py``
that is essentially calling ``modules/mangers/import_signatures.py`` with some preparatory code.
"""
import logging
import os
from typing import TYPE_CHECKING, Optional

from cobbler import utils
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Importer:
    """
    Wrapper class to adhere to the style of all other actions.
    """

    def __init__(self, api: "CobblerAPI") -> None:
        """
        Constructor to initialize the class.

        :param api: The CobblerAPI.
        """
        self.api = api
        self.logger = logging.getLogger()

    def run(
        self,
        mirror_url: str,
        mirror_name: str,
        network_root: Optional[str] = None,
        autoinstall_file: Optional[str] = None,
        rsync_flags: Optional[str] = None,
        arch: Optional[str] = None,
        breed: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> bool:
        """
        Automatically import a directory tree full of distribution files.

        :param mirror_url: Can be a string that represents a path, a user@host syntax for SSH, or an rsync:// address.
                           If mirror_url is a filesystem path and mirroring is not desired, set network_root to
                           something like "nfs://path/to/mirror_url/root"
        :param mirror_name: The name of the mirror.
        :param network_root: the remote path (nfs/http/ftp) for the distro files
        :param autoinstall_file: user-specified response file, which will override the default
        :param rsync_flags: Additional flags that will be passed to the rsync call that will sync everything to the
                            Cobbler webroot.
        :param arch: user-specified architecture
        :param breed: user-specified breed
        :param os_version: user-specified OS version
        """
        self.api.log(
            "import_tree",
            [mirror_url, mirror_name, network_root, autoinstall_file, rsync_flags],
        )

        # Both --path and --name are required arguments.
        if mirror_url is None or not mirror_url:
            self.logger.info("import failed.  no --path specified")
            return False
        if not mirror_name:
            self.logger.info("import failed.  no --name specified")
            return False

        path = os.path.normpath(
            f"{self.api.settings().webdir}/distro_mirror/{mirror_name}"
        )
        if arch is not None:
            arch = arch.lower()
            if arch == "x86":
                # be consistent
                arch = "i386"
            if path.split("-")[-1] != arch:
                path += f"-{arch}"

        # We need to mirror (copy) the files.
        self.logger.info(
            "importing from a network location, running rsync to fetch the files first"
        )

        filesystem_helpers.mkdir(path)

        # Prevent rsync from creating the directory name twice if we are copying via rsync.

        if not mirror_url.endswith("/"):
            mirror_url = f"{mirror_url}/"

        if (
            mirror_url.startswith("http://")
            or mirror_url.startswith("https://")
            or mirror_url.startswith("ftp://")
            or mirror_url.startswith("nfs://")
        ):
            # HTTP mirrors are kind of primitive. rsync is better. That's why this isn't documented in the manpage and
            # we don't support them.
            # TODO: how about adding recursive FTP as an option?
            self.logger.info("unsupported protocol")
            return False

        # Good, we're going to use rsync.. We don't use SSH for public mirrors and local files.
        # Presence of user@host syntax means use SSH
        spacer = ""
        if not mirror_url.startswith("rsync://") and not mirror_url.startswith("/"):
            spacer = ' -e "ssh" '
        rsync_cmd = ["rsync", "--archive"]
        if spacer != "":
            rsync_cmd.append(spacer)
        rsync_cmd.append("--progress")
        if rsync_flags:
            rsync_cmd.append(rsync_flags)

        # If --available-as was specified, limit the files we pull down via rsync to just those that are critical
        # to detecting what the distro is
        if network_root is not None:
            rsync_cmd.append("--include-from=/etc/cobbler/import_rsync_whitelist")

        rsync_cmd += [mirror_url, path]

        # kick off the rsync now
        rsync_return_code = utils.subprocess_call(rsync_cmd, shell=False)
        if rsync_return_code != 0:
            raise RuntimeError(
                f"rsync import failed with return code {rsync_return_code}!"
            )

        if network_root is not None:
            # In addition to mirroring, we're going to assume the path is available over http, ftp, and nfs, perhaps on
            # an external filer. Scanning still requires --mirror is a filesystem path, but --available-as marks the
            # network path. This allows users to point the path at a directory containing just the network boot files
            # while the rest of the distro files are available somewhere else.

            # Find the filesystem part of the path, after the server bits, as each distro URL needs to be calculated
            # relative to this.

            if not network_root.endswith("/"):
                network_root += "/"
            valid_roots = ["nfs://", "ftp://", "http://", "https://"]
            for valid_root in valid_roots:
                if network_root.startswith(valid_root):
                    break
            else:
                self.logger.info(
                    "Network root given to --available-as must be nfs://, ftp://, http://, or https://"
                )
                return False

            if network_root.startswith("nfs://"):
                try:
                    (_, _, _) = network_root.split(":", 3)
                except ValueError:
                    self.logger.info(
                        "Network root given to --available-as is missing a colon, please see the manpage example."
                    )
                    return False

        import_module = self.api.get_module_by_name("managers.import_signatures")
        if import_module is None:
            raise ImportError("Could not retrieve import signatures module!")
        import_manager = import_module.get_import_manager(self.api)
        import_manager.run(
            path, mirror_name, network_root, autoinstall_file, arch, breed, os_version
        )
        return True
