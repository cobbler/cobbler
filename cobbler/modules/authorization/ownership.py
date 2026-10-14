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
from typing import TYPE_CHECKING, Any, Dict, List

from cobbler import enums
from cobbler.modules.authorization import AuthorizationModule

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.abstract.base_item import BaseItem


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
            for user_resource in ["get_", "read_"]:
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

        # Now we have a modify_operation op, so we must check ownership of the object.

        if arg1 is None:
            # We require to have an item available, otherwise no search can be performed.
            return 0

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
            existing_is_obj = (
                existing is not None
                and not isinstance(existing, list)
                and existing.uid == obj.uid
            )
            if (
                existing is not None
                and not isinstance(existing, list)
                and not existing_is_obj
                and existing.owners not in (None, [])
                and not self.__is_user_allowed(
                    existing, found_groups, user, resource, arg1, arg2
                )
            ):
                return 0

            if (
                not existing_is_obj
                and getattr(obj, "_owners", None) == enums.VALUE_INHERITED
            ):
                # Brand-new object, owners never customized by the caller: decide ownership from
                # the creating user's own group membership so they don't immediately lock
                # themselves out of what they just created.
                non_admin_groups = [
                    group for group in found_groups if group not in ("admins", "admin")
                ]
                if len(non_admin_groups) == 1:
                    obj.owners = non_admin_groups
                    return 1
                if len(non_admin_groups) > 1:
                    raise ValueError(
                        f'Cannot automatically assign ownership of new object "{obj.name}" for '
                        f'user "{user}": they belong to multiple groups {non_admin_groups}. Set '
                        '"owners" explicitly before saving.'
                    )

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
