"""
This module is responsible to generate cloud-init files and metadata.

More information can be found `here <https://cloud-init.io/>`_
"""

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

from cobbler import utils
from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator

if TYPE_CHECKING:
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.template import Template


class CloudInitGenerator(AutoinstallBaseGenerator):
    """
    This is the specific implementation to generate files related to a given cloud-init installation. Cobbler implements
    the ``nocloud`` provider.
    """

    def generate_autoinstall(
        self,
        obj: "BootableItem",
        requested_file: "Template",
        autoinstaller_subfile: str = "",
    ) -> str:
        """
        Renders one of the cloud-init ``nocloud`` data source files: ``user-data``, ``meta-data``,
        ``network-config`` or ``vendor-data``, selected via ``autoinstaller_subfile``. ``vendor-data`` is always
        rendered as an empty string since Cobbler folds all provisioning data into ``user-data``/``meta-data``
        instead. If ``requested_file`` is not already tagged with the requested subfile type, a sibling template
        that is tagged with ``requested_file``'s name or UID and with the requested subfile type is looked up and
        used instead.

        :raises ValueError: If ``obj`` is not a profile or system, if ``autoinstaller_subfile`` is not one of the
            four known values, if no matching sibling template can be found, or if the resolved template carries
            none of the known subfile tags.
        """
        if obj.TYPE_NAME not in ("profile", "system"):  # type: ignore
            raise ValueError("obj must be either a system or profile!")

        if autoinstaller_subfile not in (
            "user-data",
            "vendor-data",
            "meta-data",
            "network-config",
        ):
            raise ValueError("cloud-init needs a valid autoinstaller subfile!")

        if autoinstaller_subfile == "vendor-data":
            # vendor-data is not needed as all data is condensed into user and meta-data.
            # To prevent slowing down the installation with retrys, we return an empty string.
            return ""

        if autoinstaller_subfile not in requested_file.tags:
            original_requested_file_uid = requested_file.uid
            search_result = self.api.find_template(
                True, False, tags=autoinstaller_subfile
            )
            if search_result is None or not isinstance(search_result, list):
                raise ValueError("Not enough template candidates!")

            for candidate in search_result:
                if (
                    requested_file.name in candidate.tags
                    or requested_file.uid in candidate.tags
                ):
                    requested_file = candidate

            if original_requested_file_uid == requested_file.uid:
                raise ValueError("Could not identify requested cloud-init template!")

        meta = utils.blender(self.api, False, obj)
        # make autoinstall_meta metavariable available at top level
        autoinstall_meta = meta.pop("autoinstall_meta")
        meta.update(autoinstall_meta)

        # kernel parameter via smbios gives a base-url
        if "user-data" in requested_file.tags:
            return self.__generate_user_data(obj, requested_file, meta)
        if "meta-data" in requested_file.tags:
            return self.__generate_meta_data(obj, requested_file, meta)
        if "network-config" in requested_file.tags:
            return self.__generate_network_config(obj, requested_file, meta)
        raise ValueError("Template didn't have a tag identifing its job!")

    def __generate_user_data(
        self, obj: "BootableItem", requested_file: "Template", meta: Dict[str, Any]
    ) -> str:
        """
        Generate the user-data file for cloud-init

        :returns: The string with the user-data content.
        """
        # Disable network/PXE boot for this system once Subiquity's installer reaches the post-storage-setup
        # stage, mirroring the "pxe_just_once" behavior of the Preseed built-in (cobbler/data/templates/cheetah/
        # autoinstall/snippets/generic/autoinstall_done.template, included there via
        # built-in-preseed_late_default). Subiquity has no equivalent of Debian Installer's preseed/late_command
        # hook, so this is injected directly into Subiquity's own "late-commands" (curtin, runs with network up,
        # before the final reboot) instead.
        #
        # utils.blender()/__consolidate() only shallow-copies dicts merged in from an item's own
        # autoinstall_meta, so meta["cloud_init_ubuntu_autoinstall"] (and its nested "late-commands" list) can
        # still be the very same object a Profile/System keeps in its live autoinstall_meta attribute.
        # Deep-copying before mutating is required here -- otherwise this "generate a preview" call would
        # permanently corrupt that item's persisted autoinstall_meta, and a shared parent Profile's
        # cloud_init_ubuntu_autoinstall could end up carrying one System's nopxe URL baked in for every other
        # System that inherits from it.
        raw_ubuntu_autoinstall = meta.get("cloud_init_ubuntu_autoinstall")
        if obj.TYPE_NAME == "system" and meta.get("pxe_just_once") and isinstance(raw_ubuntu_autoinstall, dict):  # type: ignore
            ubuntu_autoinstall: Dict[str, Any] = copy.deepcopy(
                cast(Dict[str, Any], raw_ubuntu_autoinstall)
            )
            nopxe_url = f'{meta.get("autoinstall_scheme", "http")}://{meta["http_server"]}/cblr/svc/op/nopxe/system/{meta["system_name"]}'
            nopxe_command = f'curl "{nopxe_url}" -o /dev/null'
            # Always replace any pre-existing nopxe late-command rather than skipping when one is already
            # present, so a stale/incorrectly-targeted one (e.g. inherited from a differently-named sibling
            # System) can never survive into the rendered autoinstall config.
            late_commands: List[Any] = [
                command
                for command in cast(
                    List[Any], ubuntu_autoinstall.get("late-commands", [])
                )
                if not (
                    isinstance(command, str) and "/cblr/svc/op/nopxe/system/" in command
                )
            ]
            late_commands.append(nopxe_command)
            ubuntu_autoinstall["late-commands"] = late_commands
            meta["cloud_init_ubuntu_autoinstall"] = ubuntu_autoinstall
        # cloud-config --> The only one supported via kernel parameter cloud-config-url
        # user-data scripts
        # cloud boothook
        # Not supported: include, jinja templates, mime multipart archive, cloud config archive, part-handler, gzip
        return self.api.templar.render(requested_file.content, meta, None)

    def __generate_meta_data(
        self, obj: "BootableItem", requested_file: "Template", meta: Dict[str, Any]
    ) -> str:
        """
        This generates the requested meta-data in the YAML format.

        :returns: The rendered cloud-init ``meta-data`` file content as a string.
        """
        return self.api.templar.render(requested_file.content, meta, None)

    def __generate_network_config(
        self, obj: "BootableItem", requested_file: "Template", meta: Dict[str, Any]
    ) -> str:
        """
        Generates the network-config file that tells cloud-init how to configure networking on first boot.

        :returns: The rendered cloud-init ``network-config`` content as a string.
        """
        return self.api.templar.render(requested_file.content, meta, None)

    def generate_autoinstall_metadata(
        self, obj: "BootableItem", key: str
    ) -> Optional[Any]:
        """
        This format does not define any auxiliary metadata keys; always returns ``None``.
        """
        return None
