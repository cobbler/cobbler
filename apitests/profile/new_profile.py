"""
new_profile.py defines a set of methods designed for testing Cobbler's
new_distro method

Copyright 2009, Red Hat, Inc
Steve Salevan <ssalevan@redhat.com>

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

import pdb

from base import *
from distro.new_distro import new_distro

class new_profile(CobblerTest):
    def test_new_working_profile_basic(self):
        """
        Attempts to create a barebones Cobbler profile using information
        contained within config file
        """
        #print "testnewworkingprofilebasic"
        new_distro('test_new_working_distro_basic').run()
        did = self.api.new_profile(self.token)
        self.api.modify_profile(did, "name", cfg["profile_name"], self.token)
        self.api.modify_profile(did, "distro", cfg["distro_name"], self.token)
        self.api.save_profile(did, self.token)
        assert self.api.find_profile({'name': cfg["profile_name"]}) != []
        
    def teat_new_working_profile_detailed(self):
        """
        Attempts to create a barebones Cobbler profile using information
        contained within config file
        """
        new_distro('test_new_working_distro_detailed').run()
        did = self.api.new_profile(self.token)
        self.api.modify_profile(did, "name", cfg["profile_name"], self.token)
        self.api.modify_profile(did, "distro", cfg["distro_name"], self.token)
        self.api.modify_profile(did, "kickstart", cfg["profile_template"], self.token)
        self.api.modify_profile(did, "kopts", { "dog" : "fido", "cat" : "fluffy" }, self.token) # hash or string
        self.api.modify_profile(did, "kopts-post", { "phil" : "collins", "steve" : "hackett" }, self.token) # hash or string
        self.api.modify_profile(did, "ksmeta", "good=sg1 evil=gould", self.token) # hash or string
        self.api.modify_profile(did, "breed", "redhat", self.token)
        self.api.modify_profile(did, "owners", "sam dave", self.token) # array or string
        self.api.modify_profile(did, "mgmt-classes", "blip", self.token) # list or string
        self.api.modify_profile(did, "comment", "test profile", self.token)
        self.api.modify_profile(did, "redhat_management_key", cfg["redhat_mgmt_key"], self.token)
        self.api.modify_profile(did, "redhat_management_server", cfg["redhat_mgmt_server"], self.token)
        self.api.modify_profile(did, "virt_bridge", "virbr0", self.token)
        self.api.modify_profile(did, "virt_cpus", "2", self.token)
        self.api.modify_profile(did, "virt_file_size", "3", self.token)
        self.api.modify_profile(did, "virt_path", "/opt/qemu/%s" % cfg["profile_name"], self.token)
        self.api.modify_profile(did, "virt_ram", "1024", self.token)
        self.api.modify_profile(did, "virt_type", "qemu", self.token)
        self.api.save_profile(did, self.token)
        assert self.api.find_profile({'name': cfg["profile_name"]}) != []
        
    def test_new_nonworking_profile(self):
        """
        Attempts to create a profile lacking required information, passes if
        xmlrpclib returns Fault
        """
        did = self.api.new_profile(self.token)
        self.api.modify_profile(did, "name", cfg["profile_name"], self.token)
        self.api.save_profile(did, self.token)
    #decorators:
    test_new_nonworking_profile = raises(xmlrpclib.Fault)(test_new_nonworking_profile)
