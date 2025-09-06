"""
TODO
"""

from typing import TYPE_CHECKING
from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator

if TYPE_CHECKING:
    from cobbler.items.abstract.bootable_item import BootableItem


class KickstartGenerator(AutoinstallBaseGenerator):
    """
    TODO
    """

    def generate_autoinstall(
        self, obj: "BootableItem", template: str, requested_file: str
    ) -> str:
        return ""
