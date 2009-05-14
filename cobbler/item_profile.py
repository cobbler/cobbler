"""
A Cobbler Profile.  A profile is a reference to a distribution, possibly some kernel options, possibly some Virt options, and some kickstart data.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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

import utils
import item
import time
from cexceptions import *

from utils import _

FIELDS = [
    [ "name"                      , "None",                                   "None",        "Name", True],
    [ "uid"                       , "",                                       "",            "",     False],
    [ "owners"                    , "SETTINGS:default_ownership",             "SETTINGS:self.settings.default_ownership", "Ownership list for authz_ownership", False ],
    [ "distro"                    , None,                                     '<<inherit>>', "Parent distribution", True],
    [ "enable_menu"               , "SETTINGS:enable_menu",                   '<<inherit>>', "Show profile in PXE menu?", True],
    [ "kickstart"                 , "SETTINGS:default_kickstart",             '<<inherit>>', "Kickstart template path", True],  
    [ "kernel_options"            , {},                                       '<<inherit>>', "Kernel options list", True],
    [ "kernel_options_post"       , {},                                       '<<inherit>>', "Post install kernel options", True],
    [ "ks_meta"                   , {},                                       '<<inherit>>', "Kickstart Metadata", True],
    [ "template_files"            , {},                                       '<<inherit>>', "Template Files", True ],
    [ "virt_auto_boot"            , "SETTINGS:virt_auto_boot",                '<<inherit>>', "Autoboot this VM?", True ],
    [ "virt_cpus"                 , 1,                                        '<<inherit>>', "Virt CPU count", True],
    [ "virt_file_size"            , "SETTINGS:default_virt_file_size",        '<<inherit>>', "Virt File size (GB)", True],
    [ "virt_ram"                  , "SETTINGS:default_virt_ram",              '<<inherit>>', "Virt RAM (MB)", True],
    [ "repos"                     , [],                                       '<<inherit>>', "Repos", True],
    [ "depth"                     , 1,                                        1            , "", False],
    [ "virt_type"                 , "SETTINGS:default_virt_type",             '<<inherit>>', "Virt Type", True],
    [ "virt_path"                 , "",                                       '<<inherit>>', "Virt Path", True],
    [ "virt_bridge"               , "SETTINGS:default_virt_bridge",           '<<inherit>>', "Virt Bridge", True],
    [ "dhcp_tag"                  , "default",                                '<<inherit>>', "DHCP Tag", True],
    [ "mgmt_classes"              , [],                                       '<<inherit>>', "Management Classes", True],
    [ "parent"                    , '',                                       '',            "", False   ],
    [ "server"                    , "<<inherit>>",                            '<<inherit>>', "Server Override", True],
    [ "comment"                   , "",                                       ""           , "Free form description", True],
    [ "ctime"                     , 0,                                        0            , "", False],
    [ "mtime"                     , 0,                                        0            , "", False],
    [ "name_servers"              , "SETTINGS:default_name_servers",          []           , "Name Servers", True],
    [ "name_servers_search"       , "SETTINGS:default_name_servers_search",   []           , "Name Servers Search Page", True],
    [ "redhat_management_key"     , "<<inherit>>",                            "<<inherit>>", "Registration key if required", True ],
    [ "redhat_management_server"  , "<<inherit>>",                            "<<inherit>>", "Registration key if required", True ] 
]

class Profile(item.Item):

    TYPE_NAME = _("profile")
    COLLECTION_TYPE = "profile"
 
    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Profile(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        """
        Reset this object.
        """
        utils.clear_from_fields(self,FIELDS)

    def from_datastruct(self,seed_data):
        """
        Load this object's properties based on seed_data
        """
        return utils.from_datastruct_from_fields(self,seed_data,FIELDS)

    def set_parent(self,parent_name):
        """
        Instead of a --distro, set the parent of this object to another profile
        and use the values from the parent instead of this one where the values
        for this profile aren't filled in, and blend them together where they
        are hashes.  Basically this enables profile inheritance.  To use this,
        the object MUST have been constructed with is_subobject=True or the
        default values for everything will be screwed up and this will likely NOT
        work.  So, API users -- make sure you pass is_subobject=True into the
        constructor when using this.
        """
        if parent_name is None or parent_name == '':
           self.parent = ''
           return True
        if parent_name == self.name:
           # check must be done in two places as set_parent could be called before/after
           # set_name...
           raise CX(_("self parentage is weird"))
        found = self.config.profiles().find(name=parent_name)
        if found is None:
           raise CX(_("profile %s not found, inheritance not possible") % parent_name)
        self.parent = parent_name       
        self.depth = found.depth + 1
        return True

    def set_distro(self,distro_name):
        """
	Sets the distro.  This must be the name of an existing
	Distro object in the Distros collection.
	"""
        d = self.config.distros().find(name=distro_name)
        if d is not None:
            self.distro = distro_name
            self.depth  = d.depth +1 # reset depth if previously a subprofile and now top-level
            return True
        raise CX(_("distribution not found"))

    def set_redhat_management_key(self,key):
        return utils.set_redhat_management_key(self,key)

    def set_redhat_management_server(self,server):
        return utils.set_redhat_management_server(self,server)

    def set_name_servers(self,data):
        # FIXME: move to utils since shared with system
        if data == "<<inherit>>":
           data = []
        data = utils.input_string_or_list(data)
        self.name_servers = data
        return True

    def set_name_servers_search(self,data):
        if data == "<<inherit>>":
           data = []
        data = utils.input_string_or_list(data)
        self.name_servers_search = data
        return True

    def set_enable_menu(self,enable_menu):
        """
        Sets whether or not the profile will be listed in the default
        PXE boot menu.  This is pretty forgiving for YAML's sake.
        """
        self.enable_menu = utils.input_boolean(enable_menu)
        return True

    def set_dhcp_tag(self,dhcp_tag):
        if dhcp_tag is None:
           dhcp_tag = ""
        self.dhcp_tag = dhcp_tag
        return True

    def set_server(self,server):
        if server is None or server == "":
           server = "<<inherit>>"
        self.server = server
        return True

  
    def set_kickstart(self,kickstart):
        """
	Sets the kickstart.  This must be a NFS, HTTP, or FTP URL.
	Or filesystem path.  Minor checking of the URL is performed here.
	"""
        if kickstart == "" or kickstart is None:
            self.kickstart = ""
            return True
        if kickstart == "<<inherit>>":
            self.kickstart = kickstart
            return True
        if utils.find_kickstart(kickstart):
            self.kickstart = kickstart
            return True
        raise CX(_("kickstart not found: %s") % kickstart)

    def set_virt_auto_boot(self,num):
        return utils.set_virt_auto_boot(self,num)

    def set_virt_cpus(self,num):
        return utils.set_virt_cpus(self,num)

    def set_virt_file_size(self,num):
        return utils.set_virt_file_size(self,num)
 
    def set_virt_ram(self,num):
        return utils.set_virt_ram(self,num)

    def set_virt_type(self,vtype):
        return utils.set_virt_type(self,vtype)

    def set_virt_bridge(self,vbridge):
        return utils.set_virt_bridge(self,vbridge)

    def set_virt_path(self,path):
        return utils.set_virt_path(self,path)

    def set_repos(self,repos,bypass_check=False):
        return utils.set_repos(self,repos,bypass_check)

    def get_parent(self):
        """
        Return object next highest up the tree.
        """
        if self.parent is None or self.parent == '':
            result = self.config.distros().find(name=self.distro)
        else:
            result = self.config.profiles().find(name=self.parent)
        return result

    def to_datastruct(self):
        return utils.to_datastruct_from_fields(self,FIELDS)

    def printable(self):
        return utils.printable_from_fields(self,FIELDS)
  
    def remote_methods(self):
        return utils.get_remote_methods_from_fields(self,FIELDS)


