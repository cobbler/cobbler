"""
This module contains code in order to create the automatic installation files. For example kickstarts, autoyast files
or preseed files.
"""

import logging
import os
from typing import TYPE_CHECKING, Any, List, Optional

from cobbler import autoinstallgen, utils
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.abstract.item_bootable import BootableItem


TEMPLATING_ERROR = 1
KICKSTART_ERROR = 2


class AutoInstallationManager:
    """
    Manage automatic installation templates, snippets and final files
    """

    def __init__(self, api: "CobblerAPI"):
        """
        Constructor for the autoinstall manager.

        :param api: The collection manager which has all objects.
        """
        self.api = api
        self.snippets_base_dir = api.settings().autoinstall_snippets_dir
        self.templates_base_dir = api.settings().autoinstall_templates_dir
        self.autoinstallgen = autoinstallgen.AutoInstallationGen(api)
        self.logger = logging.getLogger()

    def validate_autoinstall_template_file_path(
        self, autoinstall: str, for_item: bool = True, new_autoinstall: bool = False
    ) -> str:
        """
        Validate the automatic installation template's relative file path.

        :param autoinstall: automatic installation template relative file path
        :param for_item: enable/disable special handling for Item objects
        :param new_autoinstall: when set to true new filenames are allowed
        :returns: automatic installation template relative file path
        :raises TypeError: Raised in case ``autoinstall`` is not a string.
        :raises OSError: Raised in case template file not found.
        :raises ValueError: Raised in case template file is invalid.
        """

        if not isinstance(autoinstall, str):  # type: ignore
            raise TypeError("Invalid input, autoinstall must be a string")
        autoinstall = autoinstall.strip()

        if autoinstall == "":
            # empty autoinstall is allowed (interactive installations)
            return autoinstall

        if for_item is True:
            # this autoinstall value has special meaning for Items
            # other callers of this function have no use for this
            if autoinstall == "<<inherit>>":
                return autoinstall

        if autoinstall.find("..") != -1:
            raise ValueError(
                f"Invalid automatic installation template file location {autoinstall}, it must not contain .."
            )

        autoinstall_path = f"{self.templates_base_dir}/{autoinstall}"
        if not os.path.isfile(autoinstall_path) and not new_autoinstall:
            raise OSError(
                f"Invalid automatic installation template file location {autoinstall_path}, file not found"
            )

        return autoinstall

    def get_autoinstall_templates(self) -> List[str]:
        """
        Get automatic OS installation templates

        :returns: A list of automatic installation templates
        """

        files: List[str] = []
        for root, _, filenames in os.walk(self.templates_base_dir):
            for filename in filenames:
                rel_root = root[len(self.templates_base_dir) + 1 :]
                if rel_root:
                    rel_path = f"{rel_root}/{filename}"
                else:
                    rel_path = filename
                files.append(rel_path)

        files.sort()
        return files

    def read_autoinstall_template(self, file_path: str) -> str:
        """
        Read an automatic OS installation template

        :param file_path: automatic installation template relative file path
        :returns: automatic installation template content
        """

        file_path = self.validate_autoinstall_template_file_path(
            file_path, for_item=False
        )

        file_full_path = f"{self.templates_base_dir}/{file_path}"
        with open(file_full_path, "r", encoding="UTF-8") as fileh:
            data = fileh.read()

        return data

    def write_autoinstall_template(self, file_path: str, data: str) -> bool:
        """
        Write an automatic OS installation template

        :param file_path: automatic installation template relative file path
        :param data: automatic installation template content
        """

        file_path = self.validate_autoinstall_template_file_path(
            file_path, for_item=False, new_autoinstall=True
        )

        file_full_path = f"{self.templates_base_dir}/{file_path}"
        try:
            filesystem_helpers.mkdir(os.path.dirname(file_full_path))
        except Exception:
            utils.die(
                f"unable to create directory for automatic OS installation template at {file_path}"
            )

        with open(file_full_path, "w", encoding="UTF-8") as fileh:
            fileh.write(data)

        return True

    def remove_autoinstall_template(self, file_path: str):
        """
        Remove an automatic OS installation template

        :param file_path: automatic installation template relative file path
        """

        file_path = self.validate_autoinstall_template_file_path(
            file_path, for_item=False
        )

        file_full_path = f"{self.templates_base_dir}/{file_path}"
        if not self.is_autoinstall_in_use(file_path):
            os.remove(file_full_path)
        else:
            utils.die("attempt to delete in-use file")

    def validate_autoinstall_snippet_file_path(
        self, snippet: str, new_snippet: bool = False
    ) -> str:
        """
        Validate the snippet's relative file path.

        :param snippet: automatic installation snippet relative file path
        :param new_snippet: when set to true new filenames are allowed
        :returns: Snippet if successful otherwise raises an exception.
        :raises TypeError: Raised in case ``snippet`` is not a string.
        :raises ValueError: Raised in case snippet file is invalid.
        :raises OSError: Raised in case snippet file location is not found.
        """

        if not isinstance(snippet, str):  # type: ignore
            raise TypeError("Invalid input, snippet must be a string")
        snippet = snippet.strip()

        if snippet.find("..") != -1:
            raise ValueError(
                f"Invalid automated installation snippet file location {snippet}, it must not contain .."
            )

        snippet_path = f"{self.snippets_base_dir}/{snippet}"
        if not os.path.isfile(snippet_path) and not new_snippet:
            raise OSError(
                f"Invalid automated installation snippet file location {snippet_path}, file not found"
            )

        return snippet

    def get_autoinstall_snippets(self) -> List[str]:
        """
        Get a list of all autoinstallation snippets.

        :return: The list of snippets
        """
        files: List[str] = []
        for root, _, filenames in os.walk(self.snippets_base_dir):

            for filename in filenames:
                rel_root = root[len(self.snippets_base_dir) + 1 :]
                if rel_root:
                    rel_path = f"{rel_root}/{filename}"
                else:
                    rel_path = filename
                files.append(rel_path)

        files.sort()
        return files

    def read_autoinstall_snippet(self, file_path: str) -> str:
        """
        Reads a autoinstall snippet from underneath the configured snippet base dir.

        :param file_path: The relative file path under the configured snippets base dir.
        :return: The read snippet.
        """
        file_path = self.validate_autoinstall_snippet_file_path(file_path)

        file_full_path = f"{self.snippets_base_dir}/{file_path}"
        with open(file_full_path, "r", encoding="UTF-8") as fileh:
            data = fileh.read()

        return data

    def write_autoinstall_snippet(self, file_path: str, data: str):
        """
        Writes a snippet with the given content to the relative path under the snippet root directory.

        :param file_path: The relative path under the configured snippet base dir.
        :param data: The snippet code.
        """
        file_path = self.validate_autoinstall_snippet_file_path(
            file_path, new_snippet=True
        )

        file_full_path = f"{self.snippets_base_dir}/{file_path}"
        try:
            filesystem_helpers.mkdir(os.path.dirname(file_full_path))
        except Exception:
            utils.die(
                f"unable to create directory for automatic OS installation snippet at {file_path}"
            )

        with open(file_full_path, "w", encoding="UTF-8") as fileh:
            fileh.write(data)

    def remove_autoinstall_snippet(self, file_path: str) -> bool:
        """
        Remove the autoinstall snippet with the given path.

        :param file_path: The path relative to the configured snippet root.
        :return: A boolean indicating the success of the task.
        """
        file_path = self.validate_autoinstall_snippet_file_path(file_path)

        file_full_path = f"{self.snippets_base_dir}/{file_path}"
        os.remove(file_full_path)

        return True

    def is_autoinstall_in_use(self, name: str) -> bool:
        """
        Reports the status if a given system is currently being provisioned.

        :param name: The name of the system.
        :return: Whether the system is in install mode or not.
        """
        for profile in self.api.profiles():
            if profile.autoinstall is not None and profile.autoinstall == name:
                return True
        for profile in self.api.systems():
            if profile.autoinstall is not None and profile.autoinstall == name:
                return True
        return False

    def generate_autoinstall(
        self, profile: Optional[str] = None, system: Optional[str] = None
    ) -> str:
        """
        Generates the autoinstallation for a system or a profile. You may only specifify one parameter. If you specify
        both, the system is generated and the profile argument is ignored.

        :param profile: The Cobbler profile you want an autoinstallation generated for.
        :param system: The Cobbler system you want an autoinstallation generated for.
        :return: The rendered template for the system or profile.
        """
        if system is not None:
            return self.autoinstallgen.generate_autoinstall_for_system(system)
        if profile is not None:
            return self.autoinstallgen.generate_autoinstall_for_profile(profile)
        return ""

    def log_autoinstall_validation_errors(self, errors_type: int, errors: List[Any]):
        """
        Log automatic installation file errors

        :param errors_type: validation errors type
        :param errors: A list with all the errors which occurred.
        """

        if errors_type == TEMPLATING_ERROR:
            self.logger.warning("Potential templating errors:")
            for error in errors:
                (line, col) = error["lineCol"]
                line -= 1  # we add some lines to the template data, so numbering is off
                self.logger.warning(
                    "Unknown variable found at line %d, column %d: '%s'",
                    line,
                    col,
                    error["rawCode"],
                )
        elif errors_type == KICKSTART_ERROR:
            self.logger.warning("Kickstart validation errors: %s", errors[0])

    def validate_autoinstall_file(
        self, obj: "BootableItem", is_profile: bool
    ) -> List[Any]:
        """
        Validate automatic installation file used by a system/profile.

        :param obj: system/profile
        :param is_profile: if obj is a profile
        :returns: [bool, int, list] list with validation result, errors type and list of errors
        """

        blended = utils.blender(self.api, False, obj)  # type: ignore

        # get automatic installation template
        autoinstall = blended["autoinstall"]
        if autoinstall is None or autoinstall == "":
            self.logger.info(
                "%s has no automatic installation template set, skipping", obj.name
            )
            return [True, 0, ()]

        # generate automatic installation file
        os_version = blended["os_version"]
        self.logger.info("----------------------------")
        self.logger.debug("osversion: %s", os_version)
        if is_profile:
            self.generate_autoinstall(profile=obj.name)
        else:
            self.generate_autoinstall(system=obj.name)
        last_errors = self.autoinstallgen.get_last_errors()
        if len(last_errors) > 0:
            return [False, TEMPLATING_ERROR, last_errors]
        return [True, 0, ()]

    def validate_autoinstall_files(self) -> bool:
        """
        Determine if Cobbler automatic OS installation files will be accepted by corresponding Linux distribution
        installers. The presence of an error does not imply that the automatic installation file is bad, only that the
        possibility exists. Automatic installation file validators are not available for all automatic installation file
        types and on all operating systems in which Cobbler may be installed.

        :return: True if all automatic installation files are valid, otherwise false.
        """
        overall_success = True

        for profile in self.api.profiles():
            (success, errors_type, errors) = self.validate_autoinstall_file(
                profile, True
            )
            if not success:
                overall_success = False
            if len(errors) > 0:
                self.log_autoinstall_validation_errors(errors_type, errors)
        for system in self.api.systems():
            (success, errors_type, errors) = self.validate_autoinstall_file(
                system, False
            )
            if not success:
                overall_success = False
            if len(errors) > 0:
                self.log_autoinstall_validation_errors(errors_type, errors)

        if not overall_success:
            self.logger.warning(
                "*** potential errors detected in automatic installation files ***"
            )
        else:
            self.logger.info("*** all automatic installation files seem to be ok ***")

        return overall_success
