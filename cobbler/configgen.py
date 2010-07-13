"""
Configuration generation class.

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
from ConfigParser import RawConfigParser
from cexceptions import CX
import cobbler.utils
import cobbler.api as capi
import pprint
import simplejson as json
import string
import utils

class GenConfig:

    def __init__(self,hostname):
        self.hostname    = hostname
        self.handle      = capi.BootAPI()
        self.system      = self.handle.find_system(hostname=self.hostname)
        self.mgmtclasses = self.get_host_mgmtclasses()
        self.resources   = self.get_resources()

    def get_host_vars(self):
        handle = self.handle
        system = self.system
        return cobbler.utils.blender(handle, False, system)['ks_meta']

    def get_host_mgmtclasses(self):
        handle = self.handle
        system = self.system
        return cobbler.utils.blender(handle, False, system)['mgmt_classes']
    
    def repos_enabled(self):
        handle = self.handle
        system = self.system
        return cobbler.utils.blender(handle, False, system)['repos_enabled']
    
    def ldap_enabled(self):
        handle = self.handle
        system = self.system
        return cobbler.utils.blender(handle, False, system)['ldap_enabled']
    
    def monit_enabled(self):
        handle = self.handle
        system = self.system
        return cobbler.utils.blender(handle, False, system)['monit_enabled']

    def resolve_resource_var(self,string_data):
        data = string.Template(string_data).substitute(self.get_host_vars())
        return data
    
    def resolve_resource_list(self,list_data):
        new_list = []
        for item in list_data:
            new_list.append(string.Template(item).substitute(self.get_host_vars()))
        return new_list

    def get_packages(self):
        return self.resources['packages']
    def get_files(self):
        return self.resources['files']

    def get_resources(self):
        handle      = self.handle
        mgmtclasses = self.mgmtclasses
        package_set = set()
        file_set    = set()
        # Construct the resources dictionary
        for mgmtclass in mgmtclasses:
            _mgmtclass = handle.find_mgmtclass(name=mgmtclass)
            for package in _mgmtclass.packages:
                package_set.add(package)
            for file in _mgmtclass.files:
                file_set.add(file)
        resources = {
            'packages': package_set,
            'files'   : file_set,
        } 
        return resources
    
    def gen_repo_data(self):
        """
        Generate repo data. Return repos attached to this system.
        """
        handle = self.handle
        system = self.system
        repo_data = handle.get_repo_config_for_system(system)
        return repo_data

    def gen_ldap_data(self):
        """
        Generate LDAP data
        """
        system = self.system
        if system.ldap_type in [ "", "none" ]:
            utils.die(self.logger,"LDAP management is not enabled for this system")
        template = utils.get_ldap_template(self.system.ldap_type)
        if not template:
            utils.die(self.logger, "Invalid LDAP management type for this system (%s, %s)" % (self.system.ldap_type, self.system.name))
        t = Template(file=template, searchList=[self.get_host_vars()])
        ldap_data = t.respond()
        return ldap_data

    def gen_package_data(self):
        """
        Generate package resources dictionary.
        """
        handle = self.handle
        package_list = self.get_packages()
        pkg_data = {}
        pkg_data['rpm'] = {}
        pkg_data['yum'] = {}
        for package in package_list:
            _package = handle.find_package(name=package)
            if _package is None:
                raise CX('%s package resource is not defined' % package)
            if _package.installer == 'rpm':
                pkg_data['rpm'][package] = {}
                pkg_data['rpm'][package]['action'] = self.resolve_resource_var(_package.action)
                pkg_data['rpm'][package]['url']    = self.resolve_resource_var(_package.url)
            if _package.installer == 'yum':
                pkg_data['yum'][package] = {}
                pkg_data['yum'][package]['action']  = self.resolve_resource_var(_package.action)
                pkg_data['yum'][package]['version'] = self.resolve_resource_var(_package.version)
        return pkg_data
    
    def gen_file_data(self):
        """
        Generate file resources dictionary.
        """
        handle = self.handle
        file_list = self.get_files()
        file_data = {}
        file_data['directories'] = {}
        file_data['files']       = {}
        for file in file_list:
            _file = handle.find_file(name=file)
            if _file is None:
                raise CX('%s file resource is not defined' % file)
            if _file.is_directory:
                file_data['directories'][file] = {}
                file_data['directories'][file]['is_directory'] = _file.is_directory
                file_data['directories'][file]['action']   = self.resolve_resource_var(_file.action)
                file_data['directories'][file]['group']    = self.resolve_resource_var(_file.group)
                file_data['directories'][file]['mode']     = self.resolve_resource_var(_file.mode) 
                file_data['directories'][file]['owner']    = self.resolve_resource_var(_file.owner)
                file_data['directories'][file]['path']     = self.resolve_resource_var(_file.path)
            else:
                file_data['files'][file] = {}
                file_data['files'][file]['is_directory'] = _file.is_directory
                file_data['files'][file]['action']   = self.resolve_resource_var(_file.action)
                file_data['files'][file]['group']    = self.resolve_resource_var(_file.group)
                file_data['files'][file]['mode']     = self.resolve_resource_var(_file.mode) 
                file_data['files'][file]['owner']    = self.resolve_resource_var(_file.owner)
                file_data['files'][file]['path']     = self.resolve_resource_var(_file.path)
                file_data['files'][file]['template'] = self.resolve_resource_var(_file.template)
                if 'template' in file_data['files'][file]:
                    t = Template(file=file_data['files'][file]['template'], searchList=[self.get_host_vars()])
                    file_data['files'][file]['content'] = t.respond()
                    del file_data['files'][file]['template']
        return file_data

    def gen_config_data(self):
        """
        Generate configuration data.
        """
        config_data = {
            'repo_data': self.gen_repo_data(),
            'ldap_data': self.gen_ldap_data(),
            'packages' : self.gen_package_data(),
            'files'    : self.gen_file_data(),           
        }
        return config_data

    def gen_config_data_for_koan(self):
        """
        Encode configuration data. Return json object for Koan.
        """
        json_config_data = json.JSONEncoder(sort_keys=True, indent=4).encode(self.gen_config_data())
        return json_config_data
