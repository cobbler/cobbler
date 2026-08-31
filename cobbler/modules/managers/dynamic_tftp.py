"""
This is some of the code behind 'cobbler sync' when TFTP content is served dynamically (e.g. by the separate
cobbler-tftp daemon) instead of being materialized into the TFTP root directory.
"""

# SPDX-License-Identifier: GPL-2.0-or-later

from typing import TYPE_CHECKING, Dict, List, Optional, Union

from cobbler.modules.managers import TftpManagerModule

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro
    from cobbler.items.image import Image
    from cobbler.items.system import System


MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


class _DynamicTftpManager(TftpManagerModule):
    @staticmethod
    def what() -> str:
        """
        Static method to identify the manager.

        :return: Always "dynamic_tftp".
        """
        return "dynamic_tftp"

    def __init__(self, api: "CobblerAPI"):
        super().__init__(api)

    def write_boot_files(self) -> int:
        """
        No-op: bootable files referenced by ``template_files`` are served on demand by
        :meth:`cobbler.tftpgen.TFTPGen.generate_tftp_file`, so nothing needs to be written to the TFTP root.

        :return: Always ``0``.
        """
        self.logger.info(
            "dynamic TFTP manager selected, skipping write_boot_files: "
            "boot files are served on demand instead"
        )
        return 0

    def sync_single_system(
        self,
        system: "System",
        menu_items: Optional[Dict[str, Union[str, Dict[str, str]]]] = None,
    ) -> int:
        """
        No-op: per-system PXE/GRUB configuration is rendered on demand by
        :meth:`cobbler.tftpgen.TFTPGen.generate_tftp_file`, so nothing needs to be written to the TFTP root.

        :param system: The system that would have been synced.
        :param menu_items: Unused.
        """
        del system, menu_items  # unused
        self.logger.info(
            "dynamic TFTP manager selected, skipping sync_single_system: "
            "system configuration is generated on demand instead"
        )
        return 0

    def add_single_distro(self, distro: "Distro") -> None:
        """
        No-op: distro kernel/initrd files are served on demand by
        :meth:`cobbler.tftpgen.TFTPGen.generate_tftp_file`, so nothing needs to be copied into the TFTP root.

        :param distro: The distro that would have been added.
        """
        del distro  # unused
        self.logger.info(
            "dynamic TFTP manager selected, skipping add_single_distro: "
            "distro files are served on demand instead"
        )

    def add_single_image(self, image: "Image") -> None:
        """
        No-op: image files are served on demand by :meth:`cobbler.tftpgen.TFTPGen.generate_tftp_file`, so nothing
        needs to be copied into the TFTP root.

        :param image: The image that would have been added.
        """
        del image  # unused
        self.logger.info(
            "dynamic TFTP manager selected, skipping add_single_image: "
            "image files are served on demand instead"
        )

    def sync_systems(self, systems: List["System"], verbose: bool = True) -> None:
        """
        No-op: system configuration is rendered on demand by
        :meth:`cobbler.tftpgen.TFTPGen.generate_tftp_file`, so nothing needs to be written to the TFTP root.

        :param systems: Unused.
        :param verbose: Unused.
        """
        del systems, verbose  # unused
        self.logger.info(
            "dynamic TFTP manager selected, skipping sync_systems: "
            "system configuration is generated on demand instead"
        )

    def sync(self) -> int:
        """
        No-op: bootloaders, distro kernels/initrds, images and per-system configuration are all served on demand by
        :meth:`cobbler.tftpgen.TFTPGen.generate_tftp_file`/:meth:`cobbler.api.CobblerAPI.get_tftp_file`, so nothing
        needs to be materialized into the TFTP root.

        :return: Always ``0``.
        """
        self.logger.info(
            "dynamic TFTP manager selected, skipping sync: "
            "TFTP content is served on demand instead of being copied to the TFTP root"
        )
        return 0


def get_manager(api: "CobblerAPI") -> _DynamicTftpManager:
    """
    Creates a manager object to manage TFTP content that is served dynamically instead of being copied into the
    TFTP root.

    :param api: The API which holds all information in the current Cobbler instance.
    :return: The object to manage the server with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _DynamicTftpManager(api)  # type: ignore
    return MANAGER
