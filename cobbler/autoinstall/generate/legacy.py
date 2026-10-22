"""
This module is responsible to generate auto-installation files and metadata. This is the legacy "mixed" way that
combines AutoYAST, Kickstart and Preseed.
"""

from typing import TYPE_CHECKING, Any, Optional

from cobbler import utils
from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator
from cobbler.autoinstall.generate.shared import (
    generate_config_stanza,
    generate_repo_stanza,
    resolve_install_source_directory,
)

if TYPE_CHECKING:
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.distro import Distro
    from cobbler.items.template import Template


# TODO: Check changes from main branch from Template refactoring
class LegacyGenerator(AutoinstallBaseGenerator):
    """
    This is the legacy way of requesting auto-installation templates. New features will not be added and only bugs will
    be fixed.
    """

    def generate_autoinstall(
        self,
        obj: "BootableItem",
        requested_file: "Template",
        autoinstaller_subfile: str = "",
    ) -> str:
        """
        Renders the auto-installation file using the legacy code path that predates the per-format generators. This
        combines logic that is otherwise split across the AutoYaST, Kickstart and Preseed generators: it resolves
        the autoinstall tree path, flattens ``kernel_options``/``kernel_options_post`` into a string, injects the
        ``yum_repo_stanza`` and ``yum_config_stanza`` metavariables for Red Hat based distros, and derives
        ``install_source_directory`` for Debian/Ubuntu based distros. No new features will be added to this code
        path; only bugs will be fixed.
        """
        meta = utils.blender(self.api, False, obj)
        autoinstall_rel_path = meta["autoinstall"]

        if obj.TYPE_NAME not in ("profile", "system"):  # type: ignore
            raise ValueError("obj must be either a system or profile!")

        if not autoinstall_rel_path:
            return f"# automatic installation file value missing or invalid at {obj.TYPE_NAME} {obj.name}"

        # make autoinstall_meta metavariable available at top level
        autoinstall_meta = meta["autoinstall_meta"]
        del meta["autoinstall_meta"]
        meta.update(autoinstall_meta)

        # get parent distro
        if obj.TYPE_NAME == "system":
            distro: "Distro" = obj.get_conceptual_parent().get_conceptual_parent()  # type: ignore
        else:  # must be a profile then
            distro = obj.get_conceptual_parent()  # type: ignore

        # add package repositories metadata to autoinstall metavariables
        if distro.breed == "redhat":
            meta["yum_repo_stanza"] = self.generate_autoinstall_metadata(
                obj, "yum_repo_stanza"
            )
            meta["yum_config_stanza"] = self.generate_autoinstall_metadata(
                obj, "yum_config_stanza"
            )

        meta["kernel_options"] = utils.kernel_options_to_string(meta["kernel_options"])
        if "kernel_options_post" in meta:
            meta["kernel_options_post"] = utils.kernel_options_to_string(
                meta["kernel_options_post"]
            )

        # add install_source_directory metavariable to autoinstall metavariables if distro is based on Preseed
        if distro.breed in ["debian", "ubuntu"] and "tree" in meta:
            meta["install_source_directory"] = resolve_install_source_directory(
                meta["tree"]
            )

        if obj.autoinstall is None:  # type: ignore
            return "# no automatic installation template set"

        return self.api.templar.render(obj.autoinstall.content, meta, None)  # type: ignore

    def generate_autoinstall_metadata(
        self, obj: "BootableItem", key: str
    ) -> Optional[Any]:
        """
        Generates the legacy ``$yum_repo_stanza`` and ``$yum_config_stanza`` substitutions used by Red Hat based
        automatic installation files.

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
