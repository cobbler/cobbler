"""
Repository resource configuration class.

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

module for configuring repository resources on RedHat based systems.
"""

import filecmp
import shutil
import subprocess
import tempfile
import stat
import os.path

class ConfigureRepos:
    def __init__(self, repo_data):
        self.repo_data = repo_data
        self.status    = ""

    def configure(self):
        """
        Configure YUM repositories. Mainly creating YUM configuration
        files under /etc/yum.repos.d/
        """
        print "- Configuring Repos"
        
        old_repo = '/etc/yum.repos.d/config.repo'
        
        # Setup and write incoming repo content to tempfile.
        r = tempfile.NamedTemporaryFile()
        r.write(self.repo_data)
        r.flush()
        new_repo = r.name
        # Check if the repository resource exist on the client
        if os.path.isfile(old_repo):
            # Compare existing file and incoming changes
            if not filecmp.cmp(old_repo, new_repo):
                self.status = self.sync(old_repo, new_repo)
            else:
                self.status = "Success: Repos in sync"
        else:
            self.status = self.create(old_repo, new_repo)
        # Close temporary file.
        r.close()
                
        return self.status

    def create(self,old_file,new_file):
        """
        Create YUM configuration files
        """
        print "  %s not found, creating..." % (old_file)
        open(old_file,'w').close()
        self.diff_files(old_file, new_file)
        open(old_file, 'w').close()
        shutil.copy(new_file, old_file)
        # Set file ownership and mode to RedHat defaults for yum repositories.
        os.chmod(old_file,644)
        os.chown(old_file,0,0)
        return "Success: Repos in sync"

    def remove(self,file):
        """
        Remove YUM configuration files
        """
        print "  removing %s" % file
        os.remove(file)
        return "Success: Repos in sync"

    def sync(self,old_file,new_file):
        """
        Sync YUM configuration files
        """
        # Show diff and overwrite existing file with temp
        self.diff_files(old_file, new_file)
        shutil.copy(new_file, old_file)
        os.chmod(old_file,644)
        os.chown(old_file,0,0)
        return "Success: Repos in sync"

    # Make this configurable? Enable or disable
    def diff_files(self, file1, file2):
        """
        Diff two files by shelling out to local system diff command.
        """
        subprocess.call(['/usr/bin/diff', file1, file2])
