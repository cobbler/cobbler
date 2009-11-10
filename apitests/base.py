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

from nose.tools import *

cfg = None

CONFIG_LOC = "./apitests.conf"

def read_config():
    global cfg
    f = open(CONFIG_LOC, 'r')
    cfg = yaml.load(f)
    f.close()
    
class CobblerTest(unittest.TestCase):
    def __cleanUpObjects(self):
        try:
            self.api.remove_distro(cfg["distro_name"], self.token)
        except:
            pass
        try:
            self.api.remove_profile(cfg["profile_name"], self.token)
        except:
            pass
        try:
            self.api.remove_system(cfg["system_name"], self.token)
        except:
            pass

    def setUp(self):
        """
        Sets up Cobbler API connection and logs in
        """
        self.api = xmlrpclib.Server(cfg["cobbler_server"])
        self.token = self.api.login(cfg["cobbler_user"],
            cfg["cobbler_pass"])
        self.__cleanUpObjects()
        assert self.api.find_distro({'name': cfg["distro_name"]}) == []
        assert self.api.find_profile({'name': cfg["profile_name"]}) == []
        assert self.api.find_profile({'name': cfg["system_name"]}) == []
        
    def tearDown(self):
        """
        Removes any Cobbler objects created during a test
        """
        self.__cleanUpObjects()
        
read_config()
