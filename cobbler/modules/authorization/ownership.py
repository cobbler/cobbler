"""
Authorization module that allow users listed in
/etc/cobbler/users.conf to be permitted to access resources, with
the further restriction that Cobbler objects can be edited to only
allow certain users/groups to access those specific objects.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>


from configparser import ConfigParser

import os
from typing import Dict


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authz"
    """
    return "authz"


def __parse_config() -> Dict[str, dict]:
    """
    Parse the "users.conf" of Cobbler and return all data in a dictionary.

    :return: The data separated by sections. Each section has a subdictionary with the key-value pairs.
    :raises FileNotFoundError
    """
    etcfile = '/etc/cobbler/users.conf'
    if not os.path.exists(etcfile):
        raise FileNotFoundError("/etc/cobbler/users.conf does not exist")
    # Make users case sensitive to handle kerberos
    config = ConfigParser()
    config.optionxform = str
    config.read(etcfile)
    alldata = {}
    sections = config.sections()
    for g in sections:
        alldata[str(g)] = {}
        opts = config.options(g)
        for o in opts:
            alldata[g][o] = 1
    return alldata


def __authorize_autoinst(api_handle, groups, user, autoinst) -> int:
    """
    The authorization rules for automatic installation file editing are a bit of a special case. Non-admin users can
    edit a automatic installation file only if all objects that depend on that automatic installation file are editable
    by the user in question.

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

    :param api_handle: The api to resolve required information.
    :param groups: The groups a user is in.
    :param user: The user which is asking for access.
    :param autoinst: The automatic installation in question.
    :return: ``1`` if the user is allowed and otherwise ``0``.
    """

    lst = api_handle.find_profile(autoinst=autoinst, return_list=True)
    lst.extend(api_handle.find_system(autoinst=autoinst, return_list=True))
    for obj in lst:
        if not __is_user_allowed(obj, groups, user, "write_autoinst", autoinst, None):
            return 0
    return 1


def __authorize_snippet(api_handle, groups, user, autoinst) -> int:
    """
    Only allow admins to edit snippets -- since we don't have detection to see where each snippet is in use.

    :param api_handle: Unused parameter.
    :param groups: The group which is asking for access.
    :param user: Unused parameter.
    :param autoinst: Unused parameter.
    :return: ``1`` if the group is allowed, otherwise ``0``.
    """

    for group in groups:
        if group not in ["admins", "admin"]:
            return 0
    return 1


def __is_user_allowed(obj, groups, user, resource, arg1, arg2) -> int:
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


def authorize(api_handle, user: str, resource: str, arg1=None, arg2=None) -> int:
    """
    Validate a user against a resource. All users in the file are permitted by this module.

    :param api_handle: The api to resolve required information.
    :param user: The user to authorize to the resource.
    :param resource: The resource the user is asking for access. This is something abstract like a remove operation.
    :param arg1: This is normally the name of the specific object in question.
    :param arg2: This parameter is pointless currently. Reserved for future code.
    :return: ``1`` if okay, otherwise ``0``.
    """
    if user == "<DIRECT>":
        # CLI should always be permitted
        return 1

    # Everybody can get read-only access to everything if they pass authorization, they don't have to be in users.conf
    if resource is not None:
        # FIXME: /cobbler/web should not be subject to user check in any case
        for x in ["get", "read", "/cobbler/web"]:
            if resource.startswith(x):
                return 1        # read operation is always ok.

    user_groups = __parse_config()

    # classify the type of operation
    modify_operation = False
    for criteria in ["save", "copy", "rename", "remove", "modify", "edit", "xapi", "background"]:
        if resource.find(criteria) != -1:
            modify_operation = True

    # FIXME: is everyone allowed to copy?  I think so.
    # FIXME: deal with the problem of deleted parents and promotion

    found_user = False
    found_groups = []
    grouplist = list(user_groups.keys())
    for g in grouplist:
        for x in user_groups[g]:
            if x == user:
                found_groups.append(g)
                found_user = True
                # if user is in the admin group, always authorize
                # regardless of the ownership of the object.
                if g == "admins" or g == "admin":
                    return 1

    if not found_user:
        # if the user isn't anywhere in the file, reject regardless
        # they can still use read-only XMLRPC
        return 0
    if not modify_operation:
        # sufficient to allow access for non save/remove ops to all
        # users for now, may want to refine later.
        return 1

    # Now we have a modify_operation op, so we must check ownership of the object. Remove ops pass in arg1 as a string
    # name, saves pass in actual objects, so we must treat them differently. Automatic installaton files are even more
    # special so we call those out to another function, rather than going through the rest of the code here.

    if resource.find("write_autoinstall_template") != -1:
        return __authorize_autoinst(api_handle, found_groups, user, arg1)
    elif resource.find("read_autoinstall_template") != -1:
        return 1

    # The API for editing snippets also needs to do something similar. As with automatic installation files, though
    # since they are more widely used it's more restrictive.

    if resource.find("write_autoinstall_snippet") != -1:
        return __authorize_snippet(api_handle, found_groups, user, arg1)
    elif resource.find("read_autoinstall_snipppet") != -1:
        return 1

    obj = None
    if resource.find("remove") != -1:
        if resource == "remove_distro":
            obj = api_handle.find_distro(arg1)
        elif resource == "remove_profile":
            obj = api_handle.find_profile(arg1)
        elif resource == "remove_system":
            obj = api_handle.find_system(arg1)
        elif resource == "remove_repo":
            obj = api_handle.find_repo(arg1)
        elif resource == "remove_image":
            obj = api_handle.find_image(arg1)
    elif resource.find("save") != -1 or resource.find("modify") != -1:
        obj = arg1

    # if the object has no ownership data, allow access regardless
    if obj is None or obj.owners is None or obj.owners == []:
        return 1

    return __is_user_allowed(obj, found_groups, user, resource, arg1, arg2)
