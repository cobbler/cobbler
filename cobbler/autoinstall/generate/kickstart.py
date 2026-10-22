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
from cobbler.autoinstall.generate.shared import (
    generate_config_stanza,
    generate_repo_stanza,
)

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
        """
        Renders the object's Kickstart file (``obj.autoinstall``), flattening the ``kernel_options`` and
        ``kernel_options_post`` metavariables into a string before templating.
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

        # add package repositories metadata to autoinstall metavariables
        meta["yum_repo_stanza"] = self.generate_autoinstall_metadata(
            obj, "yum_repo_stanza"
        )
        meta["yum_config_stanza"] = self.generate_autoinstall_metadata(
            obj, "yum_config_stanza"
        )

        meta["kernel_options"] = utils.dict_to_string(meta["kernel_options"])
        if "kernel_options_post" in meta:
            meta["kernel_options_post"] = utils.dict_to_string(
                meta["kernel_options_post"]
            )

        return self.api.templar.render(template.content, meta, None)  # type: ignore

    def generate_autoinstall_metadata(
        self, obj: "BootableItem", key: str
    ) -> Optional[Any]:
        """
        Generates the ``$yum_repo_stanza`` and ``$yum_config_stanza`` substitutions used by Red Hat based automatic
        installation files.

        :param obj: The profile or system to generate the metadata for.
        :param key: Either ``"yum_repo_stanza"`` or ``"yum_config_stanza"``.
        :return: The generated stanza, or None if ``key`` is neither of the two supported values.
        """
        is_profile = obj.TYPE_NAME == "profile"  # type: ignore
        if key == "yum_repo_stanza":
            return generate_repo_stanza(self.api, obj, is_profile)
        if key == "yum_config_stanza":
            return generate_config_stanza(self.api, obj, is_profile)
        return None
