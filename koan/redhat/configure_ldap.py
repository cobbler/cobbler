"""
LDAP integration configuration class.

Copyright 2010 Kelsey Hightower
Kelsey Hightower <kelsey.hightower@gmail.com>

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

module for configuring LDAP integration on RedHat based systems.
"""

import subprocess

class ConfigureLDAP:
    def __init__(self,ldap_data):
        # ldap_data comes from the ldap_type specified by the
        # cobbler system entry. LDAP types are located on the 
        # cobbler server under the /etc/cobbler/ldap/ directory.
        #
        # ldap_data contains the LDAP command that should be
        # executed by Koan. This command should provide all options
        # required to configure LDAP for the host.
        self.ldap_data = ldap_data
        
    def configure(self):
        """
        Configure LDAP by running the specified LDAP command.
        """
        print "- Configuring LDAP"
        cmd = self.ldap_data
        rc = subprocess.call(cmd,shell="True")
        
        if rc == 0:
            return "Success: LDAP has been configured"
        else:
            return "ERROR: configuring LDAP failed"