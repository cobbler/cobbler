"""
This module contains code to create the automatic installation files. For example kickstarts, autoyast files or preseed
files.
"""

import logging
from typing import TYPE_CHECKING, Any, List, NamedTuple, Optional, Sequence, Union

from cobbler import enums, utils
from cobbler.autoinstall.generate.autoyast import AutoYaSTGenerator
from cobbler.autoinstall.generate.kickstart import KickstartGenerator
from cobbler.autoinstall.generate.legacy import LegacyGenerator
from cobbler.autoinstall.generate.preseed import PreseedGenerator
from cobbler.autoinstall.generate.windows import WindowsGenerator

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator
    from cobbler.items.abstract.bootable_item import BootableItem
    from cobbler.items.profile import Profile
    from cobbler.items.system import System
    from cobbler.items.template import Template


class AutoinstallValidationResult(NamedTuple):
    """
    This named tuple makes it easier to work with the results of a validating a single template.
    """

    success: bool
    errors_type: enums.AutoinstallValidationError
    errors: Sequence[Any]


class AutoInstallationManager:
    """
    Manage automatic installation templates, snippets and final files
    """

    def __init__(self, api: "CobblerAPI"):
        """
        Constructor for the auto-installation manager.

        :param api: The collection manager which has all objects.
        """
        self.logger = logging.getLogger()
        self.api = api

    def is_autoinstall_in_use(self, name: str) -> bool:
        """
        Check if the auto-installation template is referenced by at least one Profile or System.

        :param name: The name of the template.
        :returns: True if the template is referenced by at least a single object.
        """
        search_result_template = self.api.find_template(False, False, name=name)
        if search_result_template is None or isinstance(search_result_template, list):
            raise ValueError("Requested autoinstall template not found!")

        search_result_profile = self.api.find_profile(
            True, False, autoinstall=search_result_template.uid
        )
        if search_result_profile is not None and not isinstance(
            search_result_profile, list
        ):
            raise TypeError(
                "Searching for profiles resulted in unexepected return type!"
            )
        if search_result_profile is not None and len(search_result_profile) > 0:
            return True

        search_result_system = self.api.find_system(
            True, False, autoinstall=search_result_template.uid
        )
        if search_result_system is not None and not isinstance(
            search_result_system, list
        ):
            raise TypeError(
                "Searching for systems resulted in unexepected return type!"
            )
        if search_result_system is not None and len(search_result_system) > 0:
            return True

        return False

    def __log_autoinstall_validation_errors(
        self, errors_type: enums.AutoinstallValidationError, errors: Sequence[Any]
    ):
        """
        Log automatic installation file errors

        :param errors_type: validation errors type
        :param errors: A collection with all the errors which occurred.
        """

        if errors_type == enums.AutoinstallValidationError.TEMPLATING:
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
        elif errors_type == enums.AutoinstallValidationError.KICKSTART:
            self.logger.warning("Kickstart validation errors: %s", errors[0])

    def validate_autoinstall_file(
        self, obj: Union["Profile", "System"]
    ) -> AutoinstallValidationResult:
        """
        Validate automatic installation file used by a system/profile.

        :param obj: system/profile
        :returns: An instance of the named tuple :class:`~cobbler.autoinstall.manager.AutoinstallValidationResult`.
        """
        # get automatic installation template
        if obj.autoinstall is None:
            self.logger.info(
                "%s has no automatic installation template set, skipping", obj.name
            )
            return AutoinstallValidationResult(
                True, enums.AutoinstallValidationError.NONE, ()
            )

        # generate automatic installation file
        blended = utils.blender(self.api, False, obj)
        os_version = blended["os_version"]
        self.logger.info("----------------------------")
        self.logger.debug("osversion: %s", os_version)
        self.generate_autoinstall(obj, obj.autoinstall)
        last_errors = self.get_last_errors()
        if len(last_errors) > 0:
            return AutoinstallValidationResult(
                False, enums.AutoinstallValidationError.TEMPLATING, last_errors
            )
        return AutoinstallValidationResult(
            True, enums.AutoinstallValidationError.NONE, ()
        )

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
            (success, errors_type, errors) = self.validate_autoinstall_file(profile)
            if not success:
                overall_success = False
            if len(errors) > 0:
                self.__log_autoinstall_validation_errors(errors_type, errors)
        for system in self.api.systems():
            (success, errors_type, errors) = self.validate_autoinstall_file(system)
            if not success:
                overall_success = False
            if len(errors) > 0:
                self.__log_autoinstall_validation_errors(errors_type, errors)

        if not overall_success:
            self.logger.warning(
                "*** potential errors detected in automatic installation files ***"
            )
        else:
            self.logger.info("*** all automatic installation files seem to be ok ***")

        return overall_success

    def __generator_factory(
        self, autoinstaller_type: enums.AutoinstallerType
    ) -> "AutoinstallBaseGenerator":
        if autoinstaller_type == enums.AutoinstallerType.KICKSTART:
            return KickstartGenerator(api=self.api)
        elif autoinstaller_type == enums.AutoinstallerType.PRESEED:
            return PreseedGenerator(api=self.api)
        elif autoinstaller_type == enums.AutoinstallerType.LEGACY:
            return LegacyGenerator(api=self.api)
        elif autoinstaller_type == enums.AutoinstallerType.AUTOYAST:
            return AutoYaSTGenerator(api=self.api)
        elif autoinstaller_type == enums.AutoinstallerType.WINDOWS:
            return WindowsGenerator(api=self.api)
        raise ValueError("Unknown template type selected!")

    def generate_autoinstall(
        self,
        obj: "BootableItem",
        autoinstall_template: "Template",
        autoinstaller_subfile: str = "",
    ) -> str:
        """
        This is an internal method for generating an auto-installation config/script. Please use the
        ``generate_autoinstall_for_*`` methods.

        :param obj: The profile to use for generating the auto-installation config/script.
        :param autoinstaller_type: All currently available types can be found at
            :class:`cobbler.enums.AutoinstallerType`.
        :param autoinstall_template: If empty, the default file is returned. Specific flavors may use this variable to
            generate secondary files (e.g. cloud-init & the different metadata files).
        :param autoinstaller_subfile: TODO
        :return: The auto-installation script or configuration file as a string.
        """
        target_autoinstall_type: Optional[enums.AutoinstallerType] = None
        for autoinstall_type in enums.AutoinstallerType:
            if autoinstall_type.value in autoinstall_template.tags:
                target_autoinstall_type = autoinstall_type
        if target_autoinstall_type is None:
            raise ValueError(
                f"{obj.name} has an automatic installation template ({autoinstall_template.name}) but no tag indicates"
                " which type of template it is!"
            )

        generator = self.__generator_factory(target_autoinstall_type)
        return generator.generate_autoinstall(
            obj,
            autoinstall_template,
            autoinstaller_subfile,
        )

    def get_last_errors(self) -> List[Any]:
        """
        Returns the list of errors generated by the last template render action.

        :return: The list of error messages which are available. This may not only contain error messages related to
                 generating autoinstallation configuration and scripts.
        """
        return self.api.templar.last_errors
