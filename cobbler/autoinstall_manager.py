"""
This module contains code in order to create the automatic installation files. For example kickstarts, autoyast files
or preseed files.
"""

import logging
from typing import TYPE_CHECKING, Any, List, Optional

from cobbler import utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.abstract.base_item import BaseItem


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
        self.autoinstallgen = api.autoinstallgen
        self.logger = logging.getLogger()

    def is_autoinstall_in_use(self, name: str) -> bool:
        """
        Reports the status if a given system is currently being provisioned.

        :param name: The name of the system.
        :return: Whether the system is in install mode or not.
        """
        for profile in self.api.profiles():
            if profile.autoinstall == name:
                return True
        for system in self.api.systems():
            if system.autoinstall == name:
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

    def validate_autoinstall_file(self, obj: "BaseItem", is_profile: bool) -> List[Any]:
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
