"""
Authorization module that allow users listed in
/etc/cobbler/users.conf to be permitted to access resources, with
the further restriction that cobbler objects can be edited to only
allow certain users/groups to access those specific objects.

Copyright 2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import distutils.sysconfig
import ConfigParser
import sys
import os
from rhpl.translate import _, N_, textdomain, utf8

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

def __authorize_kickstart(api_handle, user, user_groups, file):
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
       if not __is_user_allowed(obj, user, user_groups):
          return 0
    return 1

def __is_user_allowed(obj, user, user_groups):
    if obj.owners == []:
        # no ownership restrictions, cleared
        return 1
    for allowed in obj.owners:
        if user == allowed:
           # user match
           return 1
        # else look for a group match
        for group in user_groups:
           if group == allowed and user in user_groups[group]:
              return 1
    return 0



def authorize(api_handle,user,resource,arg1=None,arg2=None):
    """
    Validate a user against a resource.
    All users in the file are permitted by this module.
    """

    user_groups = __parse_config()

    # classify the type of operation
    modify_operation = False
    for criteria in ["save","remove","modify","write","edit"]:
        if resource.find(criteria) != -1:
           modify_operation = True

    # FIXME: is everyone allowed to copy?  I think so.
    # FIXME: deal with the problem of deleted parents and promotion

    found_user = False
    for g in user_groups:
        for x in user_groups[g]:
           if x == user:
               found_user = True
               # if user is in the admin group, always authorize
               # regardless of the ownership of the object.
               if g == "admins" or g == "admin":
                   return 1
               break

    if not found_user:
        # if the user isn't anywhere in the file, reject regardless
        # they can still use read-only XMLRPC
        return 0
    if not modify_operation:
        # sufficient to allow access for non save/remove ops to all
        # users for now, may want to refine later.
        return 1 

    # now we have a modify_operation op, so we must check ownership
    # of the object.  remove ops pass in arg1 as a string name, 
    # saves pass in actual objects, so we must treat them differently.
    # kickstarts are even more special so we call those out to another
    # function, rather than going through the rest of the code here.

    if resource.find("kickstart"):
        return authorize_kickstart(api_handle,user,user_groups,arg1)

    obj = None
    if resource.find("remove") != -1:
        if resource == "remove_distro":
           obj = api_handle.find_distro(arg1)
        elif resource == "remove_profile":
           obj = api_handle.find_profile(arg1)
        elif resource == "remove_system":
           obj = api_handle.find_system(arg1)
        elif resource == "remove_repo":
           obj = api_handle.find_system(arg1)
    elif resource.find("save") != -1 or resource.find("modify") != -1:
        obj = arg1

    # if the object has no ownership data, allow access regardless
    if obj.owners is None or obj.owners == []:
        return 1
     
    return __is_user_allowed(user,group,user_groups)
           

if __name__ == "__main__":
    # real tests are contained in tests/tests.py
    import api as cobbler_api
    api = cobbler_api.BootAPI()
    print __parse_config()
    print authorize(api, "admin1", "sync")
    d = api.find_distro("F9B-i386")
    d.set_owners(["allowed"])
    api.add_distro(d)
    print authorize(api, "admin1", "save_distro", d)
    print authorize(api, "basement2", "save_distro", d)
