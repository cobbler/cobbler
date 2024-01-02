"""
configgen.py: Generate configuration data.

module for generating configuration manifest using autoinstall_meta data and templates for a given system (hostname)
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2010 Kelsey Hightower <kelsey.hightower@gmail.com>

import json
import string
from typing import TYPE_CHECKING, Any, Dict, List, Union

from cobbler import utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.enums import ResourceAction

# FIXME: This is currently getting the blendered data. Make use of the object and only process the required data.
# FIXME: Obsolete this class. All methods are wrappers or tailcalls except gen_config_data and this can be integrated
#        somewhere else (educated guess: System or Koan directly).


class ConfigGen:
    """
    Generate configuration data for Cobbler's management resource "repos".
    Mainly used by Koan to configure systems.
    """

    def __init__(self, cobbler_api: "CobblerAPI", hostname: str):
        """
        Constructor. Requires a Cobbler API handle.

        :param hostname: The hostname to run config-generation for.
        """
        # FIXME: This should work via the system name or system record and if that doesn't exist it should not fail.
        self.hostname = hostname
        self.__api = cobbler_api
        target_system = self.__api.find_system(hostname=self.hostname)
        if target_system is None or isinstance(target_system, list):
            raise ValueError("The specified hostname did not exist or was ambigous!")
        self.system = target_system
        # This below var needs a dict but the method may possibly return an empty str.
        self.host_vars = self.get_cobbler_resource("autoinstall_meta")

    # ----------------------------------------------------------------------

    def resolve_resource_var(self, string_data: Union["ResourceAction", str]) -> str:
        """
        Substitute variables in strings with data from the ``autoinstall_meta`` dictionary of the system.

        :param string_data: The template which will then be substituted by the variables in this class.
        :return: A str with the substituted data. If the host_vars are not of type dict then this will return an empty
                 str.
        :raises KeyError: When the autoinstall_meta variable does not contain the required Keys in the dict.
        """
        if not isinstance(self.host_vars, dict):
            return ""
        return string.Template(str(string_data)).substitute(self.host_vars)

    # ----------------------------------------------------------------------

    def get_cobbler_resource(
        self, resource_key: str
    ) -> Union[List[Any], str, Dict[Any, Any]]:
        """
        Wrapper around Cobbler blender method

        :param resource_key: Not known what this actually is doing.
        :return: The blendered data. In some cases this is a str, in others it is a list or it might be a dict. In case
                 the key is not found it will return an empty string.
        """
        system_resource = utils.blender(self.__api, False, self.system)
        if resource_key not in system_resource:
            return ""
        return system_resource[resource_key]

    # ----------------------------------------------------------------------

    def gen_config_data(self) -> Dict[Any, Any]:
        """
        Generate configuration data for repos.

        :return: A dict which has all config data in it.
        """
        config_data = {
            "repo_data": self.__api.get_repo_config_for_system(self.system),
            "repos_enabled": self.get_cobbler_resource("repos_enabled"),
        }

        return config_data

    # ----------------------------------------------------------------------

    def gen_config_data_for_koan(self) -> str:
        """
        Encode configuration data. Return json object for Koan.

        :return: A json string for koan.
        """
        # TODO: This can be merged with the above method if we want to obsolete this class. If not, we need to create
        #       helper objects instead of just having a nested dictionary.
        json_config_data = json.JSONEncoder(sort_keys=True, indent=4).encode(
            self.gen_config_data()
        )
        return json_config_data
