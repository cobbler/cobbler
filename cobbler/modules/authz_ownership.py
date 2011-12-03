"""
Authorization module that allow users listed in
/etc/cobbler/users.conf to be permitted to access resources, with
the further restriction that cobbler objects can be edited to only
allow certain users/groups to access those specific objects.

Copyright 2008-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import distutils.sysconfig
import ConfigParser
import sys
import os
from cobbler.utils import _

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

import cexceptions
import utils


def register():
    """
    The mandatory cobbler module registration hook.
    """
    return "authz"

def __parse_config():
    etcfile='/etc/cobbler/users.conf'
    if not os.path.exists(etcfile):
        raise CX(_("/etc/cobbler/users.conf does not exist"))
    config = ConfigParser.ConfigParser()
    config.read(etcfile)
    alldata = {}
    sections = config.sections()
    for g in sections:
       alldata[str(g)] = {}
       opts = config.options(g)
       for o in opts:
           alldata[g][o] = 1
    return alldata 

def __authorize_kickstart(api_handle, group, user, kickstart):
    # the authorization rules for kickstart editing are a bit
    # of a special case.  Non-admin users can edit a kickstart
    # only if all objects that depend on that kickstart are
    # editable by the user in question.
    #
    # Example:
    #   if Pinky owns ProfileA
    #   and the Brain owns ProfileB
    #   and both profiles use the same kickstart template
    #   and neither Pinky nor the Brain is an admin
    #   neither is allowed to edit the kickstart template
    #   because they would make unwanted changes to each other
    #
    # In the above scenario the UI will explain the problem
    # and ask that the user asks the admin to resolve it if required.
    # NOTE: this function is only called by authorize so admin users are
    # cleared before this function is called.

    lst = api_handle.find_profile(kickstart=kickstart, return_list=True)
    lst.extend(api_handle.find_system(kickstart=kickstart, return_list=True))
    for obj in lst:
       if not __is_user_allowed(obj, group, user, "write_kickstart", kickstart, None):
          return 0
    return 1

def __authorize_snippet(api_handle, group, user, kickstart):
    # only allow admins to edit snippets -- since we don't have detection to see
    # where each snippet is in use
    if group not in [ "admins", "admin" ]:
       return False
    return True

def __is_user_allowed(obj, group, user, resource, arg1, arg2):
    if user == "<DIRECT>":
        # system user, logged in via web.ss
        return True
    if group in [ "admins", "admin" ]:
        return True
    if obj.owners == []:
        return True
    for allowed in obj.owners:
        if user == allowed:
           # user match
           return True
        # else look for a group match
        if group == allowed:
           return True
    return 0



def authorize(api_handle,user,resource,arg1=None,arg2=None):
    """
    Validate a user against a resource.
    All users in the file are permitted by this module.
    """
    if user == "<DIRECT>":
        # CLI should always be permitted
        return True

    # everybody can get read-only access to everything
    # if they pass authorization, they don't have to be in users.conf
    if resource is not None:
       # FIXME: /cobbler/web should not be subject to user check in any case
       for x in [ "get", "read", "/cobbler/web" ]:
          if resource.startswith(x):
             return 1 # read operation is always ok.

    user_groups = __parse_config()

    # classify the type of operation
    modify_operation = False
    for criteria in ["save","copy","rename","remove","modify","edit","xapi","background"]:
        if resource.find(criteria) != -1:
           modify_operation = True

    # FIXME: is everyone allowed to copy?  I think so.
    # FIXME: deal with the problem of deleted parents and promotion

    found_user = False
    found_group = None
    grouplist = user_groups.keys()
    for g in grouplist:
        for x in user_groups[g]:
           if x == user:
               found_group = g
               found_user = True
               # if user is in the admin group, always authorize
               # regardless of the ownership of the object.
               if g == "admins" or g == "admin":
                   return True
               break

    if not found_user:
        # if the user isn't anywhere in the file, reject regardless
        # they can still use read-only XMLRPC
        return 0
    if not modify_operation:
        # sufficient to allow access for non save/remove ops to all
        # users for now, may want to refine later.
        return True

    # now we have a modify_operation op, so we must check ownership
    # of the object.  remove ops pass in arg1 as a string name, 
    # saves pass in actual objects, so we must treat them differently.
    # kickstarts are even more special so we call those out to another
    # function, rather than going through the rest of the code here.

    if resource.find("write_kickstart") != -1:
        return __authorize_kickstart(api_handle,found_group,user,arg1)
    elif resource.find("read_kickstart") != -1:
        return True

    # the API for editing snippets also needs to do something similar.
    # as with kickstarts, though since they are more widely used it's more
    # restrictive   
 
    if resource.find("write_snippet") != -1:
        return __authorize_snippet(api_handle,found_group,user,arg1)
    elif resource.find("read_snipppet") != -1:
        return True

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
        return True
     
    return __is_user_allowed(obj,found_group,user,resource,arg1,arg2)
           

