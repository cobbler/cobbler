"""Cobbler action to create bootable Grub2 images.

This action calls grub2-mkimage for all bootloader formats configured in
Cobbler's settings. See man(1) grub2-mkimage for available formats.
"""

import logging
import pathlib
import re
import subprocess
import sys
import typing

from cobbler import utils

if typing.TYPE_CHECKING:
    from cobbler.api import CobblerAPI


# NOTE: does not warrant being a class, but all Cobbler actions use a class's ".run()" as the entrypoint
class MkLoaders:
    """
    Action to create bootloader images.
    """

    def __init__(self, api: "CobblerAPI") -> None:
        """
        MkLoaders constructor.

        :param api: CobblerAPI instance for accessing settings
        """
        self.logger = logging.getLogger()
        self.bootloaders_dir = pathlib.Path(api.settings().bootloaders_dir)
        # GRUB 2
        self.grub2_mod_dir = pathlib.Path(api.settings().grub2_mod_dir)
        self.boot_loaders_formats: typing.Dict[
            typing.Any, typing.Any
        ] = api.settings().bootloaders_formats
        self.modules: typing.List[str] = api.settings().bootloaders_modules
        # UEFI GRUB
        self.secure_boot_grub_path_glob = pathlib.Path(
            api.settings().secure_boot_grub_folder
        )
        self.secure_boot_grub_regex = re.compile(api.settings().secure_boot_grub_file)
        # Syslinux
        self.syslinux_folder = pathlib.Path(api.settings().syslinux_dir)
        self.syslinux_memdisk_folder = pathlib.Path(
            api.settings().syslinux_memdisk_folder
        )
        self.syslinux_pxelinux_folder = pathlib.Path(
            api.settings().syslinux_pxelinux_folder
        )
        # Shim
        self.shim_glob = pathlib.Path(api.settings().bootloaders_shim_folder)
        self.shim_regex = re.compile(api.settings().bootloaders_shim_file)
        # iPXE
        self.ipxe_folder = pathlib.Path(api.settings().bootloaders_ipxe_folder)

    def run(self) -> None:
        """
        Run GrubImages action. If the files or executables for the bootloader is not available we bail out and skip the
        creation after it is logged that this is not available.
        """
        self.create_directories()

        self.make_shim()
        self.make_ipxe()
        self.make_syslinux()
        self.make_grub()

    def make_shim(self) -> None:
        """
        Create symlink of the shim bootloader in case it is available on the system.
        """
        target_shim = find_file(self.shim_glob, self.shim_regex)
        if target_shim is None:
            self.logger.info(
                'Unable to find "shim.efi" file. Please adjust "bootloaders_shim_file" regex. Bailing out '
                "of linking the shim!"
            )
            return
        # Symlink the absolute target of the match
        symlink(
            target_shim,
            self.bootloaders_dir.joinpath(pathlib.Path("grub/shim.efi")),
            skip_existing=True,
        )

    def make_ipxe(self) -> None:
        """
        Create symlink of the iPXE bootloader in case it is available on the system.
        """
        if not self.ipxe_folder.exists():
            self.logger.info(
                'ipxe directory did not exist. Please adjust the "bootloaders_ipxe_folder". Bailing out '
                "of iPXE setup!"
            )
            return
        symlink(
            self.ipxe_folder.joinpath("undionly.kpxe"),
            self.bootloaders_dir.joinpath(pathlib.Path("undionly.pxe")),
            skip_existing=True,
        )

    def make_syslinux(self) -> None:
        """
        Create symlink of the important syslinux bootloader files in case they are available on the system.
        """
        if not utils.command_existing("syslinux"):
            self.logger.info(
                "syslinux command not available. Bailing out of syslinux setup!"
            )
            return
        syslinux_version = get_syslinux_version()
        # Make modules
        symlink(
            self.syslinux_folder.joinpath("menu.c32"),
            self.bootloaders_dir.joinpath("menu.c32"),
            skip_existing=True,
        )
        # According to https://wiki.syslinux.org/wiki/index.php?title=Library_modules,
        # 'menu.c32' depends on 'libutil.c32'.
        libutil_c32_path = self.syslinux_folder.joinpath("libutil.c32")
        if syslinux_version > 4 and libutil_c32_path.exists():
            symlink(
                libutil_c32_path,
                self.bootloaders_dir.joinpath("libutil.c32"),
                skip_existing=True,
            )
        if syslinux_version < 5:
            # This file is only required for Syslinux 5 and newer.
            # Source: https://wiki.syslinux.org/wiki/index.php?title=Library_modules
            self.logger.info(
                'syslinux version 4 detected! Skip making symlink of "ldlinux.c32" file!'
            )
        else:
            symlink(
                self.syslinux_folder.joinpath("ldlinux.c32"),
                self.bootloaders_dir.joinpath("ldlinux.c32"),
                skip_existing=True,
            )
        # Make memdisk
        symlink(
            self.syslinux_memdisk_folder.joinpath("memdisk"),
            self.bootloaders_dir.joinpath("memdisk"),
            skip_existing=True,
        )
        # Make pxelinux.0
        symlink(
            self.syslinux_pxelinux_folder.joinpath("pxelinux.0"),
            self.bootloaders_dir.joinpath("pxelinux.0"),
            skip_existing=True,
        )
        # Make linux.c32 for syslinux + wimboot
        libcom32_c32_path = self.syslinux_folder.joinpath("libcom32.c32")
        if syslinux_version > 4 and libcom32_c32_path.exists():
            symlink(
                self.syslinux_folder.joinpath("linux.c32"),
                self.bootloaders_dir.joinpath("linux.c32"),
                skip_existing=True,
            )
            # Make libcom32.c32
            # 'linux.c32' depends on 'libcom32.c32'
            symlink(
                self.syslinux_folder.joinpath("libcom32.c32"),
                self.bootloaders_dir.joinpath("libcom32.c32"),
                skip_existing=True,
            )

    def make_grub(self) -> None:
        """
        Create symlink of the GRUB 2 bootloader in case it is available on the system. Additionally build the loaders
        for other architectures if the modules to do so are available.
        """
        if not utils.command_existing("grub2-mkimage"):
            self.logger.info(
                "grub2-mkimage command not available. Bailing out of GRUB2 generation!"
            )
            return

        for image_format, options in self.boot_loaders_formats.items():
            secure_boot = options.get("use_secure_boot_grub", None)
            if secure_boot:
                binary_name = options["binary_name"]
                target_grub = find_file(
                    self.secure_boot_grub_path_glob, self.secure_boot_grub_regex
                )
                if not target_grub:
                    self.logger.info(
                        (
                            "Could not find secure bootloader in the provided location.",
                            'Skipping linking secure bootloader for "%s".',
                        ),
                        image_format,
                    )
                    continue
                symlink(
                    target_grub,
                    self.bootloaders_dir.joinpath("grub", binary_name),
                    skip_existing=True,
                )
                self.logger.info(
                    'Successfully copied secure bootloader for arch "%s"!', image_format
                )
                continue

            bl_mod_dir = options.get("mod_dir", image_format)
            mod_dir = self.grub2_mod_dir.joinpath(bl_mod_dir)
            if not mod_dir.exists():
                self.logger.info(
                    'GRUB2 modules directory for arch "%s" did no exist. Skipping GRUB2 creation',
                    image_format,
                )
                continue
            try:
                mkimage(
                    image_format,
                    self.bootloaders_dir.joinpath("grub", options["binary_name"]),
                    self.modules + options.get("extra_modules", []),
                )
            except subprocess.CalledProcessError:
                self.logger.info(
                    'grub2-mkimage failed for arch "%s"! Maybe you did forget to install the grub modules '
                    "for the architecture?",
                    image_format,
                )
                utils.log_exc()
                # don't create module symlinks if grub2-mkimage is unsuccessful
                continue
            self.logger.info(
                'Successfully built bootloader for arch "%s"!', image_format
            )

            # Create a symlink for GRUB 2 modules
            # assumes a single GRUB can be used to boot all kinds of distros
            # if this assumption turns out incorrect, individual "grub" subdirectories are needed
            symlink(
                mod_dir,
                self.bootloaders_dir.joinpath("grub", bl_mod_dir),
                skip_existing=True,
            )

    def create_directories(self) -> None:
        """
        Create the required directories so that this succeeds. If existing, do nothing. This should create the tree for
        all supported bootloaders, regardless of the capabilities to symlink/install/build them.
        """
        if not self.bootloaders_dir.exists():
            raise FileNotFoundError(
                "Main bootloader directory not found! Please create it yourself!"
            )

        grub_dir = self.bootloaders_dir.joinpath("grub")
        if not grub_dir.exists():
            grub_dir.mkdir(mode=0o644)


# NOTE: move this to cobbler.utils?
# cobbler.utils.linkfile does a lot of things, it might be worth it to have a
# function just for symbolic links
def symlink(
    target: pathlib.Path, link: pathlib.Path, skip_existing: bool = False
) -> None:
    """Create a symlink LINK pointing to TARGET.

    :param target: File/directory that the link will point to. The file/directory must exist.
    :param link: Filename for the link.
    :param skip_existing: Controls if existing links are skipped, defaults to False.
    :raises FileNotFoundError: ``target`` is not an existing file.
    :raises FileExistsError: ``skip_existing`` is False and ``link`` already exists.
    """

    if not target.exists():
        raise FileNotFoundError(
            f"{target} does not exist, can't create a symlink to it."
        )
    try:
        link.symlink_to(target)
    except FileExistsError:
        if not skip_existing:
            raise


def mkimage(
    image_format: str, image_filename: pathlib.Path, modules: typing.List[str]
) -> None:
    """Create a bootable image of GRUB using grub2-mkimage.

    :param image_format: Format of the image that is being created. See man(1)
        grub2-mkimage for a list of supported formats.
    :param image_filename: Location of the image that is being created.
    :param modules: List of GRUB modules to include into the image
    :raises subprocess.CalledProcessError: Error raised by ``subprocess.run``.
    """

    if not image_filename.parent.exists():
        image_filename.parent.mkdir(parents=True)

    cmd = ["grub2-mkimage"]
    cmd.extend(("--format", image_format))
    cmd.extend(("--output", str(image_filename)))
    cmd.append("--prefix=")
    cmd.extend(modules)

    # The Exception raised by subprocess already contains everything useful, it's simpler to use that than roll our
    # own custom exception together with cobbler.utils.subprocess_* functions
    subprocess.run(cmd, check=True)


def get_syslinux_version() -> int:
    """
    This calls syslinux and asks for the version number.

    :return: The major syslinux release number.
    :raises subprocess.CalledProcessError: Error raised by ``subprocess.run`` in case syslinux does not return zero.
    """
    # Example output: "syslinux 4.04  Copyright 1994-2011 H. Peter Anvin et al"
    cmd = ["syslinux", "-v"]
    completed_process = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding=sys.getdefaultencoding(),
    )
    output = completed_process.stdout.split()
    return int(float(output[1]))


def find_file(
    glob_path: pathlib.Path, file_regex: typing.Pattern[str]
) -> typing.Optional[pathlib.Path]:
    """
    Given a path glob and a file regex, return a full path of the file.

    :param: glob_path: Glob of a path, e.g. ``Path('/var/*/rhn')``
    :param: file_regex: A regex for a filename in the path
    :return: The full file path or None if no file was found
    """
    # Absolute paths are not supported BUT we can get around that: https://stackoverflow.com/a/51108375/4730773
    parts = glob_path.parts
    start_at = 1 if glob_path.is_absolute() else 0
    bootloader_path_parts = pathlib.Path(*parts[start_at:])
    results = sorted(pathlib.Path(glob_path.root).glob(str(bootloader_path_parts)))
    # If no match, then report and bail out.
    if len(results) <= 0:
        logging.getLogger().info('Unable to find the "%s" folder.', glob_path)
        return None

    # Now scan the folders with the regex
    target_shim = None
    for possible_folder in results:
        for child in possible_folder.iterdir():
            if file_regex.search(str(child)):
                target_shim = child.resolve()
                break
    # If no match is found report and return
    return target_shim
