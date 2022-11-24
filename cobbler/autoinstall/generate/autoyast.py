"""
This module is responsible to generate AutoYaST files and metadata.

More information can be found
`here <https://doc.opensuse.org/documentation/leap/autoyast/single-html/book-autoyast/index.html>`_
"""

from typing import TYPE_CHECKING, Any, Optional

from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator

if TYPE_CHECKING:
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.template import Template


class AutoYaSTGenerator(AutoinstallBaseGenerator):
    """
    This is the specific implementation to generate files related to a given AutoYaST installation.
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
