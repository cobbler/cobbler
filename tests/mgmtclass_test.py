"""
Copyright 2009, Red Hat, Inc and Others

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

class MgmtclassTests(CobblerTest):

    def setUp(self):
        CobblerTest.setUp(self)
        (self.package_id, self.package_name) = self.create_package()
        (self.file_id, self.file_name) = self.create_file()

    def test_create_mgmtclass(self):
        """ Test creation of a cobbler mgmtclass. """
        (mgmtclass_id, mgmtclass_name) = self.create_mgmtclass(self.package_name, self.file_name)
        mgmtclasses = self.api.find_mgmtclass({'name': mgmtclass_name})
        self.assertTrue(len(mgmtclasses) > 0)

        
