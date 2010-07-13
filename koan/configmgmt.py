"""
Configuration wrapper class.

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
"""

import simplejson as json
import utils

breed = utils.check_dist()
if breed == 'redhat':
    # Is there a better way to do this?
    from redhat.configure_repos    import ConfigureRepos
    from redhat.configure_ldap     import ConfigureLDAP  
    from redhat.configure_packages import ConfigurePackages
    from redhat.configure_files    import ConfigureFiles
    from redhat.configure_monit    import ConfigureMonit
    
#=======================================================

class Configure:
    def __init__(self,data):
        self.data  = json.JSONDecoder().decode(data)
        self.repo_data = self.data['repo_data']
        self.ldap_data = self.data['ldap_data']
        self.pkgs  = self.data['packages']
        self.files = self.data['files']

    def configure_repos(self):
        repo   = ConfigureRepos(self.repo_data)
        status = repo.configure()
        return status
    def configure_ldap(self):
        ldap = ConfigureLDAP(self.ldap_data)
        status = ldap.configure()
        return status
    def configure_packages(self):
        packages = ConfigurePackages(self.pkgs)
        stats = packages.configure()
        return stats
    def configure_files(self):
        files = ConfigureFiles(self.files)
        stats = files.configure()
        return stats
    def configure_monit(self):
        monit = ConfigureMonit()
        status = monit.configure()
        return status