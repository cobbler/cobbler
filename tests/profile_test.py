"""
new_profile.py defines a set of methods designed for testing Cobbler
profiles.

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

import urllib2

from base import *

class ProfileTests(CobblerTest):

    def test_new_working_profile_basic(self):
        """
        Attempt to create a Cobbler profile.
        """
        distro_name = self.create_distro()[1]
        profile_name = self.create_profile(distro_name)[1]
        self.assertTrue(self.api.find_profile({'name': profile_name}) != [])
        
    def test_new_nonworking_profile(self):
        """
        Attempts to create a profile lacking required information.
        """
        did = self.api.new_profile(self.token)
        self.api.modify_profile(did, "name", "anythinggoes", self.token)
        self.assertRaises(xmlrpclib.Fault, self.api.save_profile, did, self.token)

    def test_getks_no_such_profile(self):
        url = "http://%s/cblr/svc/op/ks/profile/%s" % (cfg['cobbler_server'], 
                "doesnotexist")
        try:
            response = urllib2.urlopen(url)
            self.fail()
        except urllib2.HTTPError, e:
            self.assertEquals(404, e.code)
