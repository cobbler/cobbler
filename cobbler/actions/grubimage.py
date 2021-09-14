"""Cobbler action to create bootable Grub2 images.

This action calls grub2-mkimage for all bootloader formats configured in
Cobbler's settings. See man(1) grub2-mkimage for available formats.
"""
import pathlib
import subprocess
import typing

from cobbler import utils


# NOTE: does not warrant being a class, but all Cobbler actions use a class's
# .run() as the entrypoint
class GrubImage:
    """Action to create bootable GRUB 2 images."""

    COMMON_LINKS = {
        pathlib.Path("/usr/share/efi/x86_64/shim.efi"): pathlib.Path("grub/shim.efi"),
        pathlib.Path("/usr/share/efi/x86_64/grub.efi"): pathlib.Path("grub/grub.efi"),
        # TODO: do this properly if still used
        pathlib.Path("/usr/share/*pxe/undionly.kpxe"): pathlib.Path("undionly.pxe"),
    }

    def __init__(self, api):
        """GrubImage constructor.

        :param api: CobblerAPI instance for accessing settings
        """
        self.bootloaders_dir = pathlib.Path(api.settings().bootloaders_dir)
        self.grub2_mod_dir = pathlib.Path(api.settings().grub2_mod_dir)
        self.boot_loaders_formats: typing.Dict = api.settings().bootloaders_formats
        self.modules: typing.List = api.settings().bootloaders_modules
        self.syslinux_dir = pathlib.Path(api.settings().syslinux_dir)
        self.syslinux_links = {
            self.syslinux_dir.joinpath(f): self.bootloaders_dir.joinpath(f)
            for f in ["pxelinux.0", "menu.c32", "ldlinux.c32", "memdisk"]
        }

    def run(
        self,
    ):
        """Run GrubImages action."""

        for target, link in GrubImage.COMMON_LINKS.items():
            symlink(target, self.bootloaders_dir.joinpath(link), skip_existing=True)

        for target, link in self.syslinux_links.items():
            symlink(target, self.bootloaders_dir.joinpath(link), skip_existing=True)

        for image_format, options in self.boot_loaders_formats.items():
            bl_mod_dir = options.get("mod_dir", image_format)
            try:
                mkimage(
                    image_format,
                    self.bootloaders_dir.joinpath(options["binary_name"]),
                    self.modules + options.get("extra_modules", []),
                )
            except subprocess.CalledProcessError:
                utils.log_exc()
                # don't create module symlinks if grub2-mkimage is unsuccessful
                continue

            # Create a symlink for GRUB 2 modules
            # assumes a single GRUB can be used to boot all kinds of distros
            # if this assumption turns out incorrect, individual "grub" subdirectories are needed
            symlink(
                self.grub2_mod_dir.joinpath(bl_mod_dir),
                self.bootloaders_dir.joinpath("grub", bl_mod_dir),
            )


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
    :return: None
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
    image_format: str, image_filename: pathlib.Path, modules: typing.List
) -> None:
    """Create a bootable image of GRUB using grub2-mkimage.

    :param image_format: Format of the image that is being created. See man(1)
        grub2-mkimage for a list of supported formats.
    :param image_filename: Location of the image that is being created.
    :param modules: List of GRUB modules to include into the image
    :raises subprocess.CalledProcessError: Error raised by ``subprocess.run``.
    :return: None
    """

    if not image_filename.parent.exists():
        image_filename.parent.mkdir(parents=True)

    cmd = ["grub2-mkimage"]
    cmd.extend(("--format", image_format))
    cmd.extend(("--output", str(image_filename)))
    cmd.extend(modules)

    # The Exception raised by subprocess already contains everything useful,
    # it's simpler to use that than roll our own custom exception together
    # with cobbler.utils.subprocess_* functions
    subprocess.run(cmd, check=True)
