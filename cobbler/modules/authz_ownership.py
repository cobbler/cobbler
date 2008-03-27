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

def __parse_config(debug=False):
    etcfile='/etc/cobbler/users.conf'
    if not os.path.exists(etcfile):
        raise CX(_("/etc/cobbler/users.conf does not exist"))
    config = ConfigParser.ConfigParser()
    config.read(etcfile)
    alldata = {}
    sections = config.sections()
    if debug:
       print "[OWNERSHIP] sections=%s" % sections
    for g in sections:
       alldata[str(g)] = {}
       opts = config.options(g)
       if debug:
          print "[OWNERSHIP] for group %s, users: %s" % (g,opts)
       for o in opts:
           alldata[g][o] = 1
    return alldata 


def authorize(api_handle,user,resource,arg1=None,arg2=None,debug=False):
    """
    Validate a user against a resource.
    All users in the file are permitted by this module.
    """

    user_groups = __parse_config(debug)
    if debug:
        print "[OWNERSHIP] ------------"
        print "can user %s do %s (arg1=%s)?" % (user,resource,arg1)
        print "consult db: %s" % user_groups

    # classify the type of operation
    save_or_remove = False
    for criteria in ["save_","remove_","modify_"]:
        if resource.find(criteria) != -1:
           save_or_remove = True

    # FIXME: is everyone allowed to copy?  I think so.
    # FIXME: deal with the problem of deleted parents and promotion

    found_user = False
    for g in user_groups:
        for x in user_groups[g]:
           if debug:
               print "[OWNERSHIP] noted user %s in group %s" % (x,g)
           if x == user:
               found_user = True
               # if user is in the admin group, always authorize
               # regardless of the ownership of the object.
               if g == "admins" or g == "admin":
                   if debug:
                       print "[OWNERSHIP] user %s is an admin, PASS" % user
                   return 1
               break

    if not found_user:
        # if the user isn't anywhere in the file, reject regardless
        # they can still use read-only XMLRPC
        if debug:
           print "[OWNERSHIP] user %s not found in list, FAIL" % user
        return 0
    if not save_or_remove:
        # sufficient to allow access for non save/remove ops to all
        # users for now, may want to refine later.
        if debug:
           print "[OWNERSHIP] user %s is cleared for non-edit ops, PASS" % user
        return 1 

    # now we have a save_or_remove op, so we must check ownership
    # of the object.  remove ops pass in arg1 as a string name, 
    # saves pass in actual objects, so we must treat them differently.

    obj = None
    if resource.find("remove") != -1:
        if debug:
           print "[OWNERSHIP] looking up object %s" % (arg1)
        if resource == "remove_distro":
           obj = api_handle.find_distro(arg1)
        elif resource == "remove_profile":
           obj = api_handle.find_profile(arg1)
        elif resource == "remove_system":
           obj = api_handle.find_system(arg1)
        elif resource == "remove_repo":
           obj = api_handle.find_system(arg1)
    elif resource.find("save") != -1 or resource.find("modify") != -1:
        if debug:
           print "[OWNERSHIP] object being considered is: %s for %s" % (arg1, resource)
        obj = arg1

    # if the object has no ownership data, allow access regardless
    if obj.owners is None or obj.owners == []:
        if debug:
           print "[OWNERSHIP] user %s is cleared, object is not owned, PASS" % user
        return 1
     
    # otherwise, ownership by user/group
    for allowed in obj.owners:
        if user == allowed:
           # user match
           if debug:
              print "[OWNERSHIP] user %s in match list, PASS" % user
           return 1
        for group in user_groups:
           if group == allowed and user in user_groups[group]:
              if debug:
                 print "[OWNERSHIP] user %s matched by group (%s), PASS" % (user, group)
              return 1
    
    # can't find user or group in ownership list and ownership is defined
    # so reject the operation 
    if debug:
       print "[OWNERSHIP] user %s rejected by default policy, FAIL" % user
    return 0
           

if __name__ == "__main__":
    # real tests are contained in tests/tests.py
    import api as cobbler_api
    api = cobbler_api.BootAPI()
    print __parse_config()
    print authorize(api, "admin1", "sync")
    d = api.find_distro("F9B-i386")
    d.set_owners(["allowed"])
    api.add_distro(d)
    print authorize(api, "admin1", "save_distro", d, debug=True)
    print authorize(api, "basement2", "save_distro", d, debug=True)
