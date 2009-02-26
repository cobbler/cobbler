"""
network acl engine for cobbler

Copyright 2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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

import sys
import api
import os
import os.path
import commands
import cexceptions
import utils
import fnmatch
import yaml
from cexceptions import *
from utils import _

####################################################

class AclEngine:

    def __init__(self, verbose=False):
        yfh = open("/etc/cobbler/acls.conf")
        data = yfh.read()
        yfh.close()
        self.data = yaml.load(data)
        self.verbose = verbose
 
    def __match(self, needle, haystack):
        data = fnmatch.filter([needle], haystack)
        if len(data) == 0:
           return False
        #if self.verbose:
        #   print "matched %s with %s" % (haystack,needle)
        return True

    def can_access(self,found_group,user,resource,arg1,arg2):
        if self.verbose:
            msg = "can_access(%s,%s,%s,%s,%s)" % (found_group,user,resource,arg1,arg2)
        rc = self.__can_access(found_group,user,resource,arg1,arg2)
        if self.verbose:
            print "%s -> %s" % (msg, rc)
        return rc

    def __can_access(self,found_group,user,resource,arg1,arg2):
        
        # since processing is fnmatch based, make sure we are dealing
        # with predicatible strings
        
        # find the rules for the group.  if group is not listed
        # use "unmatched" for the group
        group = found_group
        if not self.data.has_key(found_group):
           group = "unmatched"
        acldata = self.data[group]

        # for all top level patterns 
        patterns = acldata.keys()
        for p in patterns:

            # skip this pattern if it's not matched
            if not self.__match(resource,p):
                continue

            # if matched, what rules do we have under this pattern?
            subpatterns = acldata[p]

            if subpatterns == {}:
                return False


            # if we have subrules, we must look through them
            subkeys = subpatterns.keys()

            # just to keep things happy
            for sk in subkeys:

                if arg1 is not None and self.__match(arg1,sk):

                    subkeys2 = acldata[p][sk]

                    if subkeys2 == {}:
                        # direct match, fail
                        return False

                    else:

                        # FIXME: there are two scenarios here.  Comparing to the basic
                        # values and also comparing based on whether it's "modify-interface"
                        # behavior in which case arg2 is going to be a hash, not a simple
                        # value.  We need to fundamentally rewrite this section.

                        if arg2 is not None and type(arg2) != type({}):
                            # the basic case of setting the value to a normal type
                            # like a string
                            for sk2 in subkeys2:
                                if self.__match(arg2, sk):
                                    # match is a reject, actual value of the key
                                    # is not dealt with.
                                    return False 

                        elif arg2 is not None:

                            # the more advanced case where we're passing in a hash,
                            # check all keys of the hash against the pattern
                            arg_keys = arg2.keys()
                            for sk2 in subkeys2:
                                for arg2 in arg_keys:
                                    if self.__match(arg2, sk2):
                                        return False
        return True                    

if __name__ == "__main__":
   engine = AclEngine(verbose=True)
   engine.can_access("jradmin","foo","sync",None,None)
   engine.can_access("jradmin","foo","save_system",None,None)
   engine.can_access("jradmin","foo","save_profile",None,None)
   engine.can_access("lesstrusted","foo","save_system",None,None)
   engine.can_access("lesstrusted","foo","modify_system","name",None)
   intf_hash = { "ip-address-intf0" : "192.168.1.1" }
   intf_hash1 = { "foosball" : "192.168.1.1" }
   print engine.can_access("lesstrusted","foo","modify_system","modify-interface",intf_hash)
   print engine.can_access("lesstrusted","foo","modify_system","modify-interface",intf_hash1)
   print engine.can_access("admin","foo","modify_system","modify-interface",intf_hash)
   print engine.can_access("jradmin","foo","modify_system","modify-interface",intf_hash)

