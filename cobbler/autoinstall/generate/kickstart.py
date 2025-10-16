"""
This module is responsible to generate kickstart files and metadata.

Resources for kickstart-based installations can be found in the following locations:

* https://docs.fedoraproject.org/en-US/fedora/f36/install-guide/appendixes/Kickstart_Syntax_Reference/
* https://pagure.io/fedora-kickstarts
* https://anaconda-installer.readthedocs.io/en/latest/kickstart.html
"""

from typing import TYPE_CHECKING, Any, Optional

from cobbler import utils
from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator

if TYPE_CHECKING:
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.template import Template


class KickstartGenerator(AutoinstallBaseGenerator):
    """
    This is the specific implementation to generate files related to a given kickstart installation.
    """

    def generate_autoinstall(
        self,
        obj: "BootableItem",
        requested_file: "Template",
        autoinstaller_subfile: str = "",
    ) -> str:
        if obj.TYPE_NAME not in ("profile", "system"):  # type: ignore
            raise ValueError("obj must be either a system or profile!")

        template: Optional["Template"] = obj.autoinstall  # type: ignore
        if template is None:
            raise ValueError(f"No template set for object {obj.name}!")

        meta = utils.blender(self.api, False, obj)
        # make autoinstall_meta metavariable available at top level
        autoinstall_meta = meta.pop("autoinstall_meta")
        meta.update(autoinstall_meta)

        meta["kernel_options"] = utils.dict_to_string(meta["kernel_options"])
        if "kernel_options_post" in meta:
            meta["kernel_options_post"] = utils.dict_to_string(
                meta["kernel_options_post"]
            )

        return self.api.templar.render(template.content, meta, None)  # type: ignore

    def generate_autoinstall_metadata(
        self, obj: "BootableItem", key: str
    ) -> Optional[Any]:
        return None
