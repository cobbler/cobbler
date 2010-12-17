"""
Configuration class.

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

module for configuring repos, ldap, packages, files, and monit
"""

import filecmp
import shutil
import utils
import subprocess
import tempfile
import stat
import os.path
import sys
import time
import yum
import pwd
import grp
import simplejson as json
sys.path.append('/usr/share/yum-cli')
import cli


class KoanConfigure:
    """
    Used for all configuration methods, used by koan
    to configure repos, ldap, files, packages, and monit. 
    """
    
    def __init__(self, config):
        """Constructor. Requires json config object."""
        self.config = json.JSONDecoder().decode(config)
        self.stats = {}
        
    #----------------------------------------------------------------------

    def configure_repos(self):
        """Configure YUM repositories."""
        print "- Configuring Repos"  
        old_repo = '/etc/yum.repos.d/config.repo'
        
        # Stage a tempfile to hold new file contents
        _tempfile = tempfile.NamedTemporaryFile()
        _tempfile.write(self.config['repo_data'])
        _tempfile.flush()
        new_repo = _tempfile.name
        
        # Check if repo resource exist, create if missing
        if os.path.isfile(old_repo):
            if not filecmp.cmp(old_repo, new_repo):
                utils.sync_file(old_repo, new_repo, 0, 0, 644)
                self.stats['repos_status'] = "Success: Repos in sync"
            else:
                self.stats['repos_status'] = "Success: Repos in sync"
        else:
            print "  %s not found, creating..." % (old_repo)
            open(old_repo,'w').close()
            utils.sync_file(old_repo, new_repo, 0, 0, 644)
            self.stats['repos_status'] = "Success: Repos in sync"
        _tempfile.close()
        
    #----------------------------------------------------------------------

    def configure_ldap(self):
        """Configure LDAP by running the specified LDAP command."""
        print "- Configuring LDAP"
        rc = subprocess.call(self.config['ldap_data'],shell="True")
        if rc == 0:
            self.stats['ldap_status'] = "Success: LDAP has been configured"
        else:
            self.stats['ldap_status'] = "ERROR: configuring LDAP failed"
    
    #----------------------------------------------------------------------
        
    def configure_monit(self):
        """Start or reload Monit"""
        print "- Configuring Monit"
        ret = subprocess.call(['/sbin/service', 'monit', 'status'])
        if ret == 0:
            _ret = subprocess.call(['/usr/bin/monit', 'reload'])
            if _ret == 0:
                self.stats['monit_status'] = "Running: Monit has been reloaded"
        else:
            _ret = subprocess.call(['/sbin/service', 'monit', 'start'])
            if _ret == 0:
                self.stats['monit_status'] = "Running: Monit has been started"
            else:
                self.stats['monit_status'] = "Stopped: Failed to start monit"
            
    #----------------------------------------------------------------------
    
    def configure_packages(self):
        """Configure package resources."""
        print "- Configuring Packages"
        runtime_start = time.time()
        nsync = 0
        osync = 0
        fail  = 0
        packages = self.config['packages']

        yb = yum.YumBase()
        yb.preconf.debuglevel = 0
        yb.preconf.errorlevel = 0
        yb.doTsSetup()
        yb.doRpmDBSetup()
        
        ybc = cli.YumBaseCli()
        ybc.preconf.debuglevel = 0
        ybc.preconf.errorlevel = 0
        ybc.conf.assumeyes = True
        ybc.doTsSetup()
        ybc.doRpmDBSetup()
        
        create_pkg_list = []
        remove_pkg_list = []   
        for package in packages:
            action = packages[package]['action']
            # In the near future, will use install_name vs package
            # as it includes a more specific package name: "package-version"
            install_name = packages[package]['install_name']  
                    
            if yb.isPackageInstalled(package):
                if action == 'create':
                    nsync += 1
                if action == 'remove':
                    remove_pkg_list.append(package)
            if not yb.isPackageInstalled(package):
                if action == 'create':
                    create_pkg_list.append(package)
                if action == 'remove':
                    nsync += 1
        
        # Don't waste time with YUM if there is nothing to do.
        doTransaction = False
        
        if create_pkg_list:
            print "  Packages out of sync: %s" % create_pkg_list
            ybc.installPkgs(create_pkg_list)
            osync += len(create_pkg_list)
            doTransaction = True
        if remove_pkg_list:
            print "  Packages out of sync: %s" % remove_pkg_list
            ybc.erasePkgs(remove_pkg_list)
            osync += len(remove_pkg_list)
            doTransaction = True
        if doTransaction:
            ybc.buildTransaction()
            ybc.doTransaction()
            
        runtime_end = time.time()
        runtime = (runtime_end - runtime_start)
        self.stats['pkg'] = {'runtime': runtime,'nsync': nsync,'osync': osync,'fail' : fail}
    
    #----------------------------------------------------------------------
   
    def configure_directories(self):
        """ Configure directory resources."""
        print "- Configuring Directories"
        runtime_start = time.time()
        nsync = 0
        osync = 0
        fail  = 0
        files = self.config['files']
        # Split out directories
        _dirs  = [d for d in files if files[d]['is_dir']]
        
        # Configure directories first
        for dir in _dirs:
            action  = files[dir]['action']
            odir = files[dir]['path']
            
            protected_dirs = ['/','/bin','/boot','/dev','/etc','/lib','/lib64','/proc','/sbin','/sys','/usr','/var']
            if os.path.isdir(odir):
                if os.path.realpath(odir) in protected_dirs:
                    print " %s is a protected directory, skipping..." % os.path.realpath(odir)
                    fail += 1
                    continue          
          
            if action == 'create':
                nmode = int(files[dir]['mode'],8)
                nuid  = pwd.getpwnam(files[dir]['owner'])[2]
                ngid  = grp.getgrnam(files[dir]['group'])[2]  
                
                # Compare old and new directories, sync if permissions mismatch       
                if os.path.isdir(odir):
                    dstat = os.stat(odir)
                    omode = stat.S_IMODE(dstat.st_mode)
                    ouid  = pwd.getpwuid(dstat.st_uid)[2]
                    ogid  = grp.getgrgid(dstat.st_gid)[2]
                    if omode != nmode or ouid != nuid or ogid != ngid:
                        os.chmod(odir,nmode)
                        os.chown(odir,nuid,ngid)
                        osync += 1
                    else:
                        nsync += 1
                else:
                    print "  Directory out of sync, creating %s" % odir
                    os.makedirs(odir,nmode)
                    os.chown(odir,nuid,ngid)
                    osync += 1
            elif action == 'remove':
                if os.path.isdir(odir):
                    print "  Directory out of sync, removing %s" % odir
                    shutil.rmtree(odir)
                    osync += 1
                else:
                    nsync += 1
            else:
                pass
        runtime_end = time.time()
        runtime = (runtime_end - runtime_start)
        self.stats['dir'] = {'runtime': runtime,'nsync': nsync,'osync': osync,'fail': fail}
            
    #----------------------------------------------------------------------
    
    def configure_files(self):
        """ Configure file resources."""
        print "- Configuring Files"
        runtime_start = time.time()
        nsync = 0
        osync = 0
        fail  = 0
        files = self.config['files']
        # Split out files
        _files = [f for f in files if files[f]['is_dir'] is False]
        
        for file in _files:
            action   = files[file]['action']
            ofile = files[file]['path']         
            
            if action == 'create':
                nmode = int(files[file]['mode'],8)
                nuid  = pwd.getpwnam(files[file]['owner'])[2]
                ngid  = grp.getgrnam(files[file]['group'])[2]
                
                # Stage a tempfile to hold new file contents
                _tempfile = tempfile.NamedTemporaryFile()
                _tempfile.write(files[file]['content'])
                _tempfile.flush()
                nfile = _tempfile.name    
                
                # Compare new and old files, sync if permissions or contents mismatch
                if os.path.isfile(ofile):
                    fstat = os.stat(ofile)
                    omode = stat.S_IMODE(fstat.st_mode)
                    ouid  = pwd.getpwuid(fstat.st_uid)[2]
                    ogid  = grp.getgrgid(fstat.st_gid)[2]             
                    if not filecmp.cmp(ofile, nfile) or omode != nmode or ogid != ngid or ouid != nuid:
                        utils.sync_file(ofile, nfile, nuid, ngid, nmode)
                        osync += 1      
                    else:
                        nsync += 1
                elif os.path.dirname(ofile):
                    # Create the file only if the base directory exists
                    open(ofile,'w').close()
                    utils.sync_file(ofile, nfile, nuid, ngid, nmode)
                    osync += 1
                else:
                    print "  Base directory not found, %s required." % (os.path.dirname(ofile))
                    fail += 1
                _tempfile.close()
            elif action == 'remove':
                if os.path.isfile(file):
                    os.remove(ofile)
                    osync += 1
                else:
                    nsync += 1
            else:
                pass
        
        runtime_end = time.time()
        runtime = (runtime_end - runtime_start)
        self.stats['files'] = {'runtime': runtime,'nsync': nsync,'osync': osync,'fail': fail}
    
    #----------------------------------------------------------------------
    
    def run(self):
        # Configure resources in a specific order: repos, ldap, packages, directories, files, monit    
        if self.config['repos_enabled']:
            self.configure_repos()    
        if self.config['ldap_enabled']:
            self.configure_ldap()
        self.configure_packages()
        self.configure_directories()
        self.configure_files()
        if self.config['monit_enabled']:
            self.configure_monit()
            
        return self.stats