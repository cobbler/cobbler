"""
This module is responsible to generate Agama files and metadata.

More information can be found in the following places:

* https://agama-project.github.io/docs/overview/unattended
* https://agama-project.github.io/docs/user/profile
"""

from typing import TYPE_CHECKING, Any, Optional

from cobbler import utils
from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator

if TYPE_CHECKING:
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.template import Template


class AgamaGenerator(AutoinstallBaseGenerator):
    """
    This is the specific implementation to generate files related to a given Agama installation.
    """

    def generate_autoinstall(
        self,
        obj: "BootableItem",
        requested_file: "Template",
        autoinstaller_subfile: str = "",
    ) -> str:
        if obj.TYPE_NAME not in ("profile", "system"):  # type: ignore
            raise ValueError("obj must be either a system or profile!")

        meta = utils.blender(self.api, False, obj)
        # make autoinstall_meta metavariable available at top level
        autoinstall_meta = meta.pop("autoinstall_meta")
        meta.update(autoinstall_meta)

        # We cannot use the JSON library to contruct a pretty-printed string since a user might choose to use JSONNET.
        return self.api.templar.render(requested_file.content, meta, None)

    def generate_autoinstall_metadata(
        self, obj: "BootableItem", key: str
    ) -> Optional[Any]:
        return None
