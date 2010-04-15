"""
new_distro.py defines a set of methods designed for testing Cobbler's
distros.

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

from base import *

class DistroTests(CobblerTest):

    def test_new_working_distro_basic(self):
        """
        Attempts to create a barebones Cobbler distro using information
        contained within config file
        """
        name = self.create_distro()[1]
        distro = self.api.find_distro({'name': name})
        self.assertTrue(distro != None)
        
    def test_new_working_distro_detailed(self):
        """
        Attempts to create a Cobbler distro with a bevy of options, using
        information contained within config file
        """
        did, distro_name = self.create_distro()
        self.assertTrue(self.api.find_distro({'name': distro_name}) != None)

    def test_new_nonworking_distro(self):
        """
        Attempts to create a distro lacking required information, passes if
        xmlrpclib returns Fault
        """
        did = self.api.new_distro(self.token)
        self.api.modify_distro(did, "name", "whatever", self.token)
        self.assertRaises(xmlrpclib.Fault, self.api.save_distro, did, self.token)
    
    def test_new_distro_without_token(self):
        """
        Attempts to run new_distro method without supplying authenticated token
        """
        self.assertRaises(xmlrpclib.Fault, self.api.new_distro)

