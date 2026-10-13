"""
This module is responsible to generate Windows unattend.xml files and metadata.

https://learn.microsoft.com/en-us/windows-hardware/manufacture/desktop/update-windows-settings-and-scripts-create-your-own-answer-file-sxs?view=windows-11
"""

from typing import TYPE_CHECKING, Any, Optional

from cobbler import utils
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
        """
        Renders the object's unattend.xml answer file (``obj.autoinstall``). Unlike the other generators, the
        ``kernel_options``/``kernel_options_post`` metavariables are left as dictionaries rather than being
        flattened into a string, since Windows unattend files do not use a Linux-style kernel command line.
        """
        if obj.TYPE_NAME not in ("profile", "system"):  # type: ignore
            raise ValueError("obj must be either a system or profile!")

        template: Optional["Template"] = obj.autoinstall  # type: ignore
        if template is None:
            raise ValueError(f"No template set for object {obj.name}!")

        meta = utils.blender(self.api, False, obj)
        # make autoinstall_meta metavariable available at top level
        autoinstall_meta = meta.pop("autoinstall_meta")
        meta.update(autoinstall_meta)

        return self.api.templar.render(template.content, meta, None)  # type: ignore

    def generate_autoinstall_metadata(
        self, obj: "BootableItem", key: str
    ) -> Optional[Any]:
        """
        This format does not define any auxiliary metadata keys; always returns ``None``.
        """
        return None
