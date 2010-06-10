"""
Base.py defines a base set of helper methods for running automated Cobbler
XMLRPC API tests

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

import yaml
import xmlrpclib
import unittest
import traceback
import random
import commands
import urlgrabber
import os.path

cfg = None

CONFIG_LOC = "./apitests.conf"
def read_config():
    global cfg
    f = open(CONFIG_LOC, 'r')
    cfg = yaml.load(f)
    f.close()

read_config()


TEST_DISTRO_PREFIX = "TEST-DISTRO-"
TEST_PROFILE_PREFIX = "TEST-PROFILE-"
TEST_SYSTEM_PREFIX = "TEST-SYSTEM-"

FAKE_KS_CONTENTS = "HELLO WORLD"

# Files to pretend are kernel/initrd, don't point to anything real.
# These will be created if they don't already exist.
FAKE_KERNEL = "/tmp/cobbler-testing-fake-kernel"
FAKE_INITRD = "/tmp/cobbler-testing-fake-initrd"
FAKE_KICKSTART = "/tmp/cobbler-testing-kickstart"

class CobblerTest(unittest.TestCase):

    def __cleanUpObjects(self):
        """ Cleanup the test objects we created during testing. """
        for system_name in self.cleanup_systems:
            try:
                self.api.remove_system(system_name, self.token)
            except Exception, e:
                print("ERROR: unable to delete system: %s" % system_name)
                print(e)
                pass

        for profile_name in self.cleanup_profiles:
            try:
                self.api.remove_profile(profile_name, self.token)
            except Exception, e:
                print("ERROR: unable to delete profile: %s" % profile_name)
                print(e)
                pass

        for distro_name in self.cleanup_distros:
            try:
                self.api.remove_distro(distro_name, self.token)
                print("Removed distro: %s" % distro_name)
            except Exception, e:
                print("ERROR: unable to delete distro: %s" % distro_name)
                print(e)
                pass

    def setUp(self):
        """
        Sets up Cobbler API connection and logs in
        """
        self.api = xmlrpclib.Server("http://%s/cobbler_api" % cfg["cobbler_server"])
        self.token = self.api.login(cfg["cobbler_user"],
            cfg["cobbler_pass"])

        # Store object names to clean up in teardown. Be sure not to 
        # store anything in here unless we're sure it was successfully
        # created by the tests.
        self.cleanup_distros = []
        self.cleanup_profiles = []
        self.cleanup_systems = []

        # Create a fake kernel/init pair in /tmp, Cobbler doesn't care what
        # these files actually contain.
        if not os.path.exists(FAKE_KERNEL):
            commands.getstatusoutput("touch %s" % FAKE_KERNEL)
        if not os.path.exists(FAKE_INITRD):
            commands.getstatusoutput("touch %s" % FAKE_INITRD)
        if not os.path.exists(FAKE_KICKSTART):
            f = open(FAKE_KICKSTART, 'w')
            f.write(FAKE_KS_CONTENTS)
            f.close()

    def tearDown(self):
        """
        Removes any Cobbler objects created during a test
        """
        self.__cleanUpObjects()
        
    def create_distro(self):
        """
        Create a test distro with a random name, store it for cleanup 
        during teardown.

        Returns a tuple of the objects ID and name.
        """
        distro_name = "%s%s" % (TEST_DISTRO_PREFIX, random.randint(1, 1000000))
        did = self.api.new_distro(self.token)
        self.api.modify_distro(did, "name", distro_name, self.token)
        self.api.modify_distro(did, "kernel", FAKE_KERNEL, self.token) 
        self.api.modify_distro(did, "initrd", FAKE_INITRD, self.token) 
        
        self.api.modify_distro(did, "kopts", 
                { "dog" : "fido", "cat" : "fluffy" }, self.token) 
        self.api.modify_distro(did, "ksmeta", "good=sg1 evil=gould", self.token) 

        self.api.modify_distro(did, "breed", "redhat", self.token)
        self.api.modify_distro(did, "os-version", "rhel5", self.token)
        self.api.modify_distro(did, "owners", "sam dave", self.token) 
        self.api.modify_distro(did, "mgmt-classes", "blip", self.token) 
        self.api.modify_distro(did, "comment", "test distro", self.token)
        self.api.modify_distro(did, "redhat_management_key", 
                "1-ABC123", self.token)
        self.api.modify_distro(did, "redhat_management_server", 
                "mysatellite.example.com", self.token)
        self.api.save_distro(did, self.token)
        self.cleanup_distros.append(distro_name)

        url = "http://%s/cblr/svc/op/list/what/distros" % cfg['cobbler_server'] 
        data = urlgrabber.urlread(url)
        self.assertNotEquals(-1, data.find(distro_name))

        return (did, distro_name)

    def create_profile(self, distro_name):
        """
        Create a test profile with random name associated with the given distro.

        Returns a tuple of profile ID and name.
        """
        profile_name = "%s%s" % (TEST_PROFILE_PREFIX, 
                random.randint(1, 1000000))
        profile_id = self.api.new_profile(self.token)
        self.api.modify_profile(profile_id, "name", profile_name, self.token)
        self.api.modify_profile(profile_id, "distro", distro_name, self.token)
        self.api.modify_profile(profile_id, "kickstart", 
                FAKE_KICKSTART, self.token)
        self.api.modify_profile(profile_id, "kopts", 
                { "dog" : "fido", "cat" : "fluffy" }, self.token) 
        self.api.modify_profile(profile_id, "kopts-post", 
                { "phil" : "collins", "steve" : "hackett" }, self.token) 
        self.api.modify_profile(profile_id, "ksmeta", "good=sg1 evil=gould", 
                self.token)
        self.api.modify_profile(profile_id, "breed", "redhat", self.token)
        self.api.modify_profile(profile_id, "owners", "sam dave", self.token)
        self.api.modify_profile(profile_id, "mgmt-classes", "blip", self.token)
        self.api.modify_profile(profile_id, "comment", "test profile", 
                self.token)
        self.api.modify_profile(profile_id, "redhat_management_key", 
                "1-ABC123", self.token)
        self.api.modify_profile(profile_id, "redhat_management_server", 
                "mysatellite.example.com", self.token)
        self.api.modify_profile(profile_id, "virt_bridge", "virbr0", 
                self.token)
        self.api.modify_profile(profile_id, "virt_cpus", "2", self.token)
        self.api.modify_profile(profile_id, "virt_file_size", "3", self.token)
        self.api.modify_profile(profile_id, "virt_path", "/opt/qemu/%s" % 
                profile_name, self.token)
        self.api.modify_profile(profile_id, "virt_ram", "1024", self.token)
        self.api.modify_profile(profile_id, "virt_type", "qemu", self.token)
        self.api.save_profile(profile_id, self.token)
        self.cleanup_profiles.append(profile_name)

        # Check cobbler services URLs:
        url = "http://%s/cblr/svc/op/ks/profile/%s" % (cfg['cobbler_server'], 
                profile_name)
        data = urlgrabber.urlread(url)
        self.assertEquals(FAKE_KS_CONTENTS, data)

        url = "http://%s/cblr/svc/op/list/what/profiles" % cfg['cobbler_server'] 
        data = urlgrabber.urlread(url)
        self.assertNotEquals(-1, data.find(profile_name))

        return (profile_id, profile_name)

    def create_system(self, profile_name):
        """ 
        Create a system record. 
        
        Returns a tuple of system name
        """
        system_name = "%s%s" % (TEST_SYSTEM_PREFIX, 
                random.randint(1, 1000000))
        system_id = self.api.new_system(self.token)
        self.api.modify_system(system_id, "name", system_name, self.token)
        self.api.modify_system(system_id, "profile", profile_name, self.token)
        self.api.save_system(system_id, self.token)
        return (system_id, system_name)

        
    
