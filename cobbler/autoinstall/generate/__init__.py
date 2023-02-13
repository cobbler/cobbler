"""
This module is responsible to generate dynamically all files required to autoinstall a system.
"""
from typing import TYPE_CHECKING

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from cobbler import templar
from cobbler.autoinstall.generate.autoyast import AutoYastGenerator
from cobbler.autoinstall.generate.cloud_init import CloudInitGenerator
from cobbler.autoinstall.generate.kickstart import KickstartGenerator
from cobbler.autoinstall.generate.legacy import LegacyGenerator
from cobbler.autoinstall.generate.preseed import PreseedGenerator
from cobbler.cexceptions import CX

if TYPE_CHECKING:
    from cobbler.autoinstall.generate.base import AutoinstallBaseGenerator


class AutoInstallationGen:
    """
    Handles conversion of internal state to the tftpboot tree layout
    """

    def __init__(self, api):
        """
        Constructor

        :param api: The API instance which is used for this object. Normally there is only one instance of the API.
        """
        self.api = api
        self.templar = templar.Templar(self.api)

    def __generator_factory(
        self, autoinstaller_type: str
    ) -> "AutoinstallBaseGenerator":
        if autoinstaller_type == "autoyast":
            return AutoYastGenerator(api=self.api)
        if autoinstaller_type == "kickstart":
            return KickstartGenerator(api=self.api)
        if autoinstaller_type == "preseed":
            return PreseedGenerator(api=self.api)
        if autoinstaller_type == "cloud-init":
            return CloudInitGenerator(api=self.api)
        if autoinstaller_type == "legacy":
            return LegacyGenerator(api=self.api, templar=templar)
        raise ValueError("Unknown template type selected!")

    def generate_autoinstall(
        self, obj, autoinstaller_type="", autoinstaller_file=""
    ) -> str:
        """
        This is an internal method for generating an auto-installation config/script. Please use the
        ``generate_autoinstall_for_*`` methods.

        :param obj: The profile to use for generating the auto-installation config/script.
        :param autoinstaller_type: TODO
        :param autoinstaller_file: TODO
        :return: The auto-installation script or configuration file as a string.
        """
        generator = self.__generator_factory(autoinstaller_type)
        return generator.generate_autoinstall(
            obj, "", requested_file=autoinstaller_file
        )

    def generate_autoinstall_for_profile(
        self, profile_name: str, autoinstaller_type="", autoinstaller_file=""
    ) -> str:
        """
        Generate an auto-installation config or script for a profile.

        :param profile_name: The Profile to generate the script/config for.
        :param autoinstaller_type: TODO
        :param autoinstaller_file: TODO
        :return: The generated output or an error message with a human-readable description.
        :raises CX: Raised in case the profile references a missing distro.
        """
        profile = self.api.find_profile(name=profile_name)
        if profile is None:
            return "# profile not found"

        distro = profile.get_conceptual_parent()
        if distro is None:
            raise CX(
                f"profile {profile.name} references missing distro {profile.distro}"
            )

        return self.generate_autoinstall(
            profile,
            autoinstaller_type=autoinstaller_type,
            autoinstaller_file=autoinstaller_file,
        )

    def generate_autoinstall_for_system(
        self, system_name: str, autoinstaller_type="", autoinstaller_file=""
    ) -> str:
        """
        Generate an auto-installation config or script for a system.

        :param system_name: The system name to generate an auto-installation script for.
        :param autoinstaller_type: TODO
        :param autoinstaller_file: TODO
        :return: The generated output or an error message with a human-readable description.
        :raises CX: Raised in case the system references a missing profile.
        """
        system_obj = self.api.find_system(name=system_name)
        if system_obj is None:
            return "# system not found"

        profile_obj = system_obj.get_conceptual_parent()
        if profile_obj is None:
            raise CX(
                f"system {system_obj.name} references missing profile {system_obj.profile}"
            )

        distro = profile_obj.get_conceptual_parent()
        if distro is None:
            # this is an image parented system, no automatic installation file available
            return "# image based systems do not have automatic installation files"

        return self.generate_autoinstall(
            system_obj,
            autoinstaller_type=autoinstaller_type,
            autoinstaller_file=autoinstaller_file,
        )

    def get_last_errors(self) -> list:
        """
        Returns the list of errors generated by the last template render action.

        :return: The list of error messages which are available. This may not only contain error messages related to
                 generating autoinstallation configuration and scripts.
        """
        return self.templar.last_errors
