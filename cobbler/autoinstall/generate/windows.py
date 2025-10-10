"""
This module is responsible to generate Wundows unattend.xml files and metadata.

https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/update-windows-settings-and-scripts-create-your-own-answer-file-sxs?view=windows-11
"""

from typing import TYPE_CHECKING, Any, Optional

from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator

if TYPE_CHECKING:
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.template import Template


class WindowsGenerator(AutoinstallBaseGenerator):
    """
    This is the specific implementation to generate files related to a given unattended Windows installation.
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
