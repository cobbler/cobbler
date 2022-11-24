"""
This module is responsible to generate preseed files and metadata.

Documentation for Debian Preseed can be found `in the wiki <https://wiki.debian.org/DebianInstaller/Preseed>`_ and
`in the guide <https://www.debian.org/releases/stable/amd64/apb.en.html>`_
"""

from typing import TYPE_CHECKING, Any, Optional

from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator

if TYPE_CHECKING:
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.template import Template


class PreseedGenerator(AutoinstallBaseGenerator):
    """
    This is the specific implementation to generate files related to a given preseed installation.
    """

    def generate_autoinstall(
        self,
        obj: "BootableItem",
        requested_file: "Template",
        autoinstaller_subfile: str = "",
    ) -> str:
        return ""

    def generate_autoinstall_metadata(
        self, obj: "BootableItem", key: str
    ) -> Optional[Any]:
        return None
