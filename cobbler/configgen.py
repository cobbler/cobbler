"""
configgen.py: Generate configuration data.

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

module for generating configuration manifest using ksmeta data,
mgmtclasses, resources, and templates for a given system (hostname)
"""

from Cheetah.Template import Template
from cexceptions import CX
import cobbler.utils
import cobbler.api as capi
import simplejson as json
import string
import utils
import clogger


class ConfigGen:
    """
    Generate configuration data for Cobbler's management resources: 
    repos, ldap, files, packages, and monit. Mainly used by Koan to 
    configure remote systems.
    """

    def __init__(self,hostname):
        """Constructor. Requires a Cobbler API handle."""
        self.hostname    = hostname
        self.handle      = capi.BootAPI()
        self.system      = self.handle.find_system(hostname=self.hostname)
        self.host_vars   = self.get_cobbler_resource('ks_meta')
        self.logger      = clogger.Logger("/var/log/cobbler/cobbler.log")
        self.mgmtclasses = self.get_cobbler_resource('mgmt_classes')
        
    #----------------------------------------------------------------------

    def resolve_resource_var(self,string_data):
        """Substitute variables in strings."""
        data = string.Template(string_data).substitute(self.host_vars)
        return data
    
    #----------------------------------------------------------------------
    
    def resolve_resource_list(self,list_data):
        """Substitute variables in lists. Return new list."""
        new_list = []
        for item in list_data:
            new_list.append(string.Template(item).substitute(self.host_vars))
        return new_list
    
    #----------------------------------------------------------------------
    
    def get_cobbler_resource(self,resource):
        """Wrapper around cobbler blender method"""
        return cobbler.utils.blender(self.handle, False, self.system)[resource]
    
    #----------------------------------------------------------------------

    def gen_config_data(self):
        """
        Generate configuration data for repos, ldap, files,
        packages, and monit. Returns a dict. 
        """
        config_data = {
            'repo_data'    : self.handle.get_repo_config_for_system(self.system),
            'repos_enabled': self.get_cobbler_resource('repos_enabled'),
            'ldap_enabled' : self.get_cobbler_resource('ldap_enabled'),
            'monit_enabled': self.get_cobbler_resource('monit_enabled')           
        }
        package_set = set()
        file_set    = set()

        for mgmtclass in self.mgmtclasses:
            _mgmtclass = self.handle.find_mgmtclass(name=mgmtclass)
            for package in _mgmtclass.packages:
                package_set.add(package)
            for file in _mgmtclass.files:
                file_set.add(file)
    
        # Generate LDAP data
        if self.get_cobbler_resource("ldap_enabled"):
            if self.system.ldap_type in [ "", "none" ]:
                utils.die(self.logger, "LDAP management type not set for this system (%s, %s)" % (self.system.ldap_type, self.system.name))
            else:
                template = utils.get_ldap_template(self.system.ldap_type)
                t = Template(file=template, searchList=[self.host_vars])
                print t
                config_data['ldap_data'] = t.respond()
        
        # Generate Package data
        pkg_data = {}
        for package in package_set:
            _package = self.handle.find_package(name=package)
            if _package is None:
                raise CX('%s package resource is not defined' % package)
            else:
                pkg_data[package] = {}
                pkg_data[package]['action']    = self.resolve_resource_var(_package.action)
                pkg_data[package]['installer'] = _package.installer
                pkg_data[package]['version']   = self.resolve_resource_var(_package.version)
                if pkg_data[package]['version'] != "":
                    pkg_data[package]["install_name"] = "%s-%s" % (package, pkg_data[package]['version'])
                else:
                    pkg_data[package]["install_name"] = package
        config_data['packages'] = pkg_data
    
        # Generate File data
        file_data = {}    
        for file in file_set:
            _file = self.handle.find_file(name=file)
        
            if _file is None:
                raise CX('%s file resource is not defined' % file)
            
            file_data[file] = {}
            file_data[file]['is_dir'] = _file.is_dir
            file_data[file]['action'] = self.resolve_resource_var(_file.action)
            file_data[file]['group']  = self.resolve_resource_var(_file.group)
            file_data[file]['mode']   = self.resolve_resource_var(_file.mode) 
            file_data[file]['owner']  = self.resolve_resource_var(_file.owner)
            file_data[file]['path']   = self.resolve_resource_var(_file.path)
            
            if not _file.is_dir:
                file_data[file]['template'] = self.resolve_resource_var(_file.template)
                try:
                    t = Template(file=file_data[file]['template'], searchList=[self.host_vars])
                    file_data[file]['content'] = t.respond()
                except:
                    utils.die(self.logger, "Missing template for this file resource %s" % (file_data[file]))
                    
        config_data['files'] = file_data
        return config_data
    
    #----------------------------------------------------------------------

    def gen_config_data_for_koan(self):
        """Encode configuration data. Return json object for Koan."""
        json_config_data = json.JSONEncoder(sort_keys=True, indent=4).encode(self.gen_config_data())
        return json_config_data