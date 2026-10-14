"""
Authorization module that allow users listed in
/etc/cobbler/users.conf to be permitted to access resources, with
the further restriction that Cobbler objects can be edited to only
allow certain users/groups to access those specific objects.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>


import os
from configparser import ConfigParser
from typing import TYPE_CHECKING, Any, Dict, List, Union

from cobbler.modules.authorization import AuthorizationModule

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.abstract.base_item import BaseItem
    from cobbler.items.profile import Profile
    from cobbler.items.system import System


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authz"
    """
    return "authz"


class OwnershipAuthorizationModule(AuthorizationModule):
    """
    Authorization module that allow users listed in /etc/cobbler/users.conf to be permitted to access resources,
    with the further restriction that Cobbler objects can be edited to only allow certain users/groups to access
    those specific objects.
    """

    def __parse_config(self) -> Dict[str, Dict[str, Any]]:
        """
        Parse the "users.conf" of Cobbler and return all data in a dictionary.

        :return: The data separated by sections. Each section has a subdictionary with the key-value pairs.
        :raises FileNotFoundError: Raised if ``/etc/cobbler/users.conf`` does not exist.
        """
        etcfile = "/etc/cobbler/users.conf"
        if not os.path.exists(etcfile):
            raise FileNotFoundError("/etc/cobbler/users.conf does not exist")
        # Make users case sensitive to handle kerberos
        config = ConfigParser()
        config.optionxform = lambda optionstr: optionstr
        config.read(etcfile)
        alldata: Dict[str, Dict[str, Any]] = {}
        sections = config.sections()
        for group in sections:
            alldata[str(group)] = {}
            options = config.options(group)
            for option in options:
                alldata[group][option] = 1
        return alldata

    def __authorize_autoinst(self, groups: List[str], user: str, autoinst: str) -> int:
        """
        The authorization rules for automatic installation file editing are a bit of a special case. Non-admin users
        can edit a automatic installation file only if all objects that depend on that automatic installation file
        are editable by the user in question.

        Example:
          if Pinky owns ProfileA
          and the Brain owns ProfileB
          and both profiles use the same automatic installation template
          and neither Pinky nor the Brain is an admin
          neither is allowed to edit the automatic installation template
          because they would make unwanted changes to each other

        In the above scenario the UI will explain the problem and ask that the user asks the admin to resolve it if
        required.
        NOTE: this function is only called by authorize so admin users are cleared before this function is called.

        :param groups: The groups a user is in.
        :param user: The user which is asking for access.
        :param autoinst: The automatic installation in question.
        :return: ``1`` if the user is allowed and otherwise ``0``.
        """
        lst: List[Union["Profile", "System"]] = []
        my_profiles = self.api.find_profile(autoinst=autoinst, return_list=True)
        if my_profiles is None or not isinstance(my_profiles, list):
            raise ValueError("list of profile was not a list")
        lst.extend(my_profiles)
        del my_profiles
        my_systems = self.api.find_system(autoinst=autoinst, return_list=True)
        if my_systems is None or not isinstance(my_systems, list):
            raise ValueError("list of profile was not a list")
        lst.extend(my_systems)
        del my_systems
        for obj in lst:
            if not self.__is_user_allowed(
                obj, groups, user, "write_autoinst", autoinst, None
            ):
                return 0
        return 1

    def __authorize_snippet(self, groups: List[str], user: str, autoinst: str) -> int:
        """
        Only allow admins to edit snippets -- since we don't have detection to see where each snippet is in use.

        :param groups: The group which is asking for access.
        :param user: Unused parameter.
        :param autoinst: Unused parameter.
        :return: ``1`` if the group is allowed, otherwise ``0``.
        """
        del user, autoinst  # unused

        for group in groups:
            if group not in ["admins", "admin"]:
                return 0
        return 1

    def __is_user_allowed(
        self,
        obj: "BaseItem",
        groups: List[str],
        user: str,
        resource: Any,
        arg1: Any,
        arg2: Any,
    ) -> int:
        """
        Check if a user is allowed to access the resource in question.

        :param obj: The object which is in question.
        :param groups: The groups a user is belonging to.
        :param user: The user which is demanding access to the ``obj``.
        :param resource: Unused parameter.
        :param arg1: Unused parameter.
        :param arg2: Unused parameter.
        :return: ``1`` if user is allowed, otherwise ``0``.
        """
        del resource, arg1, arg2  # unused

        if user == "<DIRECT>":
            # system user, logged in via web.ss
            return 1
        for group in groups:
            if group in ["admins", "admin"]:
                return 1
        if obj.owners == []:
            return 1
        for allowed in obj.owners:
            if user == allowed:
                # user match
                return 1
            # else look for a group match
            for group in groups:
                if group == allowed:
                    return 1
        return 0

    def authorize(
        self,
        user: str,
        resource: str,
        arg1: Any = None,
        arg2: Any = None,
    ) -> int:
        """
        Validate a user against a resource. All users in the file are permitted by this module.

        :param user: The user to authorize to the resource.
        :param resource: The resource the user is asking for access. This is something abstract like a remove
                          operation.
        :param arg1: For ``save_*``/``modify_*`` resources, this is the actual (possibly not-yet-persisted) object
                     in question. For ``remove_*`` resources, this is still the name of the object (until the
                     ``remove``/``copy``/etc. call sites are migrated too).
        :param arg2: This parameter is pointless currently. Reserved for future code.
        :return: ``1`` if okay, otherwise ``0``.
        """
        if user == "<DIRECT>":
            # CLI should always be permitted
            return 1

        # Everybody can get read-only access to everything if they pass authorization, they don't have to be in
        # users.conf
        if resource is not None:  # type: ignore[reportUnnecessaryComparison]
            # FIXME: /cobbler/web should not be subject to user check in any case
            for user_resource in ["get", "read", "/cobbler/web"]:
                if resource.startswith(user_resource):
                    return 1  # read operation is always ok.

        user_groups = self.__parse_config()

        # classify the type of operation
        modify_operation = False
        for criteria in [
            "save",
            "copy",
            "rename",
            "remove",
            "modify",
            "edit",
            "power",
            "background",
        ]:
            if resource.find(criteria) != -1:
                modify_operation = True

        # FIXME: deal with the problem of deleted parents and promotion

        found_user = False
        found_groups: List[str] = []
        grouplist = list(user_groups.keys())
        for group in grouplist:
            for group_user in user_groups[group]:
                if group_user == user:
                    found_groups.append(group)
                    found_user = True
                    # if user is in the admin group, always authorize
                    # regardless of the ownership of the object.
                    if group in ("admins", "admin"):
                        return 1

        if not found_user:
            # if the user isn't anywhere in the file, reject regardless
            # they can still use read-only XMLRPC
            return 0
        if not modify_operation:
            # sufficient to allow access for non save/remove ops to all
            # users for now, may want to refine later.
            return 1

        # Now we have a modify_operation op, so we must check ownership of the object. Remove ops pass in arg1 as a
        # string name, saves pass in actual objects, so we must treat them differently. Automatic installaton files
        # are even more special so we call those out to another function, rather than going through the rest of the
        # code here.

        if arg1 is None:
            # We require to have an item name available, otherwise no search can be performed.
            return 0

        if resource.find("write_autoinstall_template") != -1:
            return self.__authorize_autoinst(found_groups, user, arg1)
        if resource.find("read_autoinstall_template") != -1:
            return 1

        # The API for editing snippets also needs to do something similar. As with automatic installation files,
        # though since they are more widely used it's more restrictive.

        if resource.find("write_autoinstall_snippet") != -1:
            return self.__authorize_snippet(found_groups, user, arg1)
        if resource.find("read_autoinstall_snipppet") != -1:
            return 1

        obj = None
        if (
            resource.find("remove") != -1
            or resource.find("save") != -1
            or resource.find("modify") != -1
            or resource.find("copy") != -1
            or resource.find("power") != -1
        ):
            # arg1 is the (possibly not-yet-persisted) object itself here, passed in by
            # remote.py's modify_item()/save_item()/remove_item()/copy_item()/power_system() - no
            # by-name lookup is needed (or, for a new item, even possible).
            obj = arg1

        if obj is None or isinstance(obj, list):
            raise ValueError("Object not found or found multiple times!")

        if resource.find("save") != -1 or resource.find("modify") != -1:
            # A name collision with an already-persisted, differently-owned object must not let a
            # self-assigned (e.g. brand-new) object's unenforced ownership stand in for the real
            # owner of that name.
            existing = self.api.find_items(
                what=obj.COLLECTION_TYPE, criteria={"name": obj.name}, return_list=False
            )
            if (
                existing is not None
                and not isinstance(existing, list)
                and existing.uid != obj.uid
                and existing.owners not in (None, [])
                and not self.__is_user_allowed(
                    existing, found_groups, user, resource, arg1, arg2
                )
            ):
                return 0

        # if the object has no ownership data, allow access regardless
        if obj.owners is None or obj.owners == []:  # type: ignore[reportUnnecessaryComparison]
            return 1

        return self.__is_user_allowed(obj, found_groups, user, resource, arg1, arg2)


def get_authorization_handler(api: "CobblerAPI") -> OwnershipAuthorizationModule:
    """
    Factory consumed by :class:`cobbler.api.CobblerAPI` to obtain the authorization handler instance.

    :param api: The API which is used for resolving information.
    :return: The handler instance.
    """
    return OwnershipAuthorizationModule(api)
