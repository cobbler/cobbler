"""
This module is responsible to generate Agama files and metadata.

More information can be found in the following places:

* https://agama-project.github.io/docs/overview/unattended
* https://agama-project.github.io/docs/user/profile
"""

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

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
        """
        Renders ``requested_file`` into an Agama installation profile. Agama profiles may be written in JSON or
        Jsonnet, so the output is produced purely via templating rather than constructed with the JSON library,
        which would corrupt a Jsonnet document.
        """
        if obj.TYPE_NAME not in ("profile", "system"):  # type: ignore
            raise ValueError("obj must be either a system or profile!")

        meta = utils.blender(self.api, False, obj)
        # make autoinstall_meta metavariable available at top level
        autoinstall_meta = meta.pop("autoinstall_meta")
        meta.update(autoinstall_meta)

        # Disable network/PXE boot for this system once the installer reaches the post-storage-setup stage,
        # mirroring the "pxe_just_once" behavior of the AutoYaST built-in (cobbler/data/templates/cheetah/
        # autoinstall/snippets/generic/autoinstall_done.template, included there via
        # built-in-suse_scriptwrapper.xml). Agama has no equivalent of AutoYaST's init-scripts/scriptwrapper
        # mechanism, so this is merged directly into the admin's own "agama_scripts"/"post" list (rather than
        # emitted as a second top-level "scripts" key, which would silently clobber or be clobbered by one
        # already configured by the admin) and "scripts" is added to "agama_modules" if not already present, so
        # built-in-agama-scripts actually gets rendered.
        #
        # utils.blender()/__consolidate() only shallow-copies dicts/lists merged in from an item's own
        # autoinstall_meta, so meta["agama_scripts"] (and nested lists inside it) can still be the very same
        # object a Profile/System keeps in its live autoinstall_meta attribute. Deep-copying before mutating is
        # required here -- otherwise this "generate a preview" call would permanently corrupt that item's
        # persisted autoinstall_meta, and a shared parent Profile's agama_scripts could end up carrying one
        # System's nopxe URL baked in for every other System that inherits from it.
        if obj.TYPE_NAME == "system" and meta.get("pxe_just_once"):  # type: ignore
            nopxe_script = {
                "name": "nopxe",
                "chroot": False,
                "content": (
                    "#!/bin/sh\n"
                    f'curl "{meta.get("autoinstall_scheme", "http")}://{meta["http_server"]}'
                    f'/cblr/svc/op/nopxe/system/{meta["system_name"]}" -o /dev/null\n'
                ),
            }
            raw_agama_scripts = meta.get("agama_scripts")
            agama_scripts: Dict[str, Any] = (
                copy.deepcopy(cast(Dict[str, Any], raw_agama_scripts))
                if isinstance(raw_agama_scripts, dict)
                else {}
            )
            # Always replace any pre-existing "nopxe" entry rather than skipping when one is already present, so
            # a stale/incorrectly-targeted entry (e.g. inherited from a differently-named sibling System) can
            # never survive into the rendered profile.
            post_scripts: List[Any] = [
                entry
                for entry in cast(List[Any], agama_scripts.get("post", []))
                if not (
                    isinstance(entry, dict)
                    and cast(Dict[str, Any], entry).get("name") == "nopxe"
                )
            ]
            post_scripts.append(nopxe_script)
            agama_scripts["post"] = post_scripts
            meta["agama_scripts"] = agama_scripts

            # agama_modules only ever holds immutable strings, so a shallow copy is sufficient here.
            agama_modules = list(meta.get("agama_modules") or [])
            if "scripts" not in agama_modules:
                agama_modules.append("scripts")
            meta["agama_modules"] = agama_modules

        # We cannot use the JSON library to contruct a pretty-printed string since a user might choose to use JSONNET.
        return self.api.templar.render(requested_file.content, meta, None)

    def generate_autoinstall_metadata(
        self, obj: "BootableItem", key: str
    ) -> Optional[Any]:
        """
        This format does not define any auxiliary metadata keys; always returns ``None``.
        """
        return None
