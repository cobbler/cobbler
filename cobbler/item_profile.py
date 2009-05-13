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
    [ "name"                      , "None",                                   "None",     ],
    [ "uid"                       , "",                                       ""          ],
    [ "random_id"                 , "",                                       ""          ],
    [ "owners"                    , "SETTINGS:default_ownership",             "SETTINGS:self.settings.default_ownership" ],
    [ "distro"                    , None,                                     '<<inherit>>'],
    [ "enable_menu"               , "SETTINGS:enable_menu",                   '<<inherit>>'],
    [ "kickstart"                 , "SETTINGS:default_kickstart",             '<<inherit>>'],  
    [ "kernel_options"            , {},                                       '<<inherit>>'],
    [ "kernel_options_post"       , {},                                       '<<inherit>>'],
    [ "ks_meta"                   , {},                                       '<<inherit>>'],
    [ "template_files"            , {},                                       '<<inherit>>'],
    [ "virt_auto_boot"            , "SETTINGS:virt_auto_boot",                '<<inherit>>'],
    [ "virt_cpus"                 , 1,                                        '<<inherit>>'],
    [ "virt_file_size"            , "SETTINGS:default_virt_file_size",        '<<inherit>>'],
    [ "virt_ram"                  , "SETTINGS:default_virt_ram",              '<<inherit>>'],
    [ "repos"                     , [],                                       '<<inherit>>'],
    [ "depth"                     , 1,                                        1            ],
    [ "virt_type"                 , "SETTINGS:default_virt_type",             '<<inherit>>'],
    [ "virt_path"                 , "",                                       '<<inherit>>'],
    [ "virt_bridge"               , "SETTINGS:default_virt_bridge",           '<<inherit>>'],
    [ "dhcp_tag"                  , "default",                                '<<inherit>>'],
    [ "mgmt_classes"              , [],                                       '<<inherit>>'],
    [ "parent"                    , '',                                       ''           ],
    [ "server"                    , "<<inherit>>",                            '<<inherit>>'],
    [ "comment"                   , "",                                       ""           ],
    [ "ctime"                     , 0,                                        0            ],
    [ "mtime"                     , 0,                                        0            ],
    [ "name_servers"              , "SETTINGS:default_name_servers",          []],
    [ "name_servers_search"       , "SETTINGS:default_name_servers_search",   []],
    [ "redhat_management_key"     , "<<inherit>>",                            "<<inherit>>" ],
    [ "redhat_management_server"  , "<<inherit>>",                            "<<inherit>>" ] 
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

    def is_valid(self):
        """
	A profile only needs a name and a distro.  Kickstart info,
	as well as Virt info, are optional.  (Though I would say provisioning
	without a kickstart is *usually* not a good idea).
	"""
        if self.parent is None or self.parent == '':
            # all values must be filled in if not inheriting from another profile
            if self.name is None:
                raise CX(_("no name specified"))
            if self.distro is None:
                raise CX(_("no distro specified"))
        else:
            # if inheriting, specifying distro is not allowed, and
            # name is required, but there are no other rules.
            if self.name is None:
                raise CX(_("no name specified"))
            if self.distro != "<<inherit>>":
                raise CX(_("cannot override distro when inheriting a profile"))
        return True

    def to_datastruct(self):
        return utils.to_datastruct_from_fields(self,FIELDS)

    def printable(self):
        """
        A human readable representaton
        """
        buf =       _("profile              : %s\n") % self.name
        if self.distro == "<<inherit>>":
            buf = buf + _("parent               : %s\n") % self.parent
        else:
            buf = buf + _("distro               : %s\n") % self.distro
        buf = buf + _("comment              : %s\n") % self.comment
        buf = buf + _("created              : %s\n") % time.ctime(self.ctime)
        buf = buf + _("dhcp tag             : %s\n") % self.dhcp_tag
        buf = buf + _("enable menu          : %s\n") % self.enable_menu
        buf = buf + _("kernel options       : %s\n") % self.kernel_options
        buf = buf + _("kickstart            : %s\n") % self.kickstart
        buf = buf + _("ks metadata          : %s\n") % self.ks_meta
        buf = buf + _("mgmt classes         : %s\n") % self.mgmt_classes
        buf = buf + _("modified             : %s\n") % time.ctime(self.mtime)
        buf = buf + _("name servers         : %s\n") % self.name_servers
        buf = buf + _("name servers search  : %s\n") % self.name_servers_search
        buf = buf + _("owners               : %s\n") % self.owners
        buf = buf + _("post kernel options  : %s\n") % self.kernel_options_post
        buf = buf + _("redhat mgmt key      : %s\n") % self.redhat_management_key
        buf = buf + _("redhat mgmt server   : %s\n") % self.redhat_management_server
        buf = buf + _("repos                : %s\n") % self.repos
        buf = buf + _("server               : %s\n") % self.server
        buf = buf + _("template_files       : %s\n") % self.template_files
        buf = buf + _("virt auto boot       : %s\n") % self.virt_auto_boot
        buf = buf + _("virt bridge          : %s\n") % self.virt_bridge
        buf = buf + _("virt cpus            : %s\n") % self.virt_cpus
        buf = buf + _("virt file size       : %s\n") % self.virt_file_size
        buf = buf + _("virt path            : %s\n") % self.virt_path
        buf = buf + _("virt ram             : %s\n") % self.virt_ram
        buf = buf + _("virt type            : %s\n") % self.virt_type
        return buf

  
    def remote_methods(self):
        return {           
            'name'                     :  self.set_name,
            'parent'                   :  self.set_parent,
            'profile'                  :  self.set_name,
            'distro'                   :  self.set_distro,
            'enable-menu'              :  self.set_enable_menu,
            'enable_menu'              :  self.set_enable_menu,            
            'kickstart'                :  self.set_kickstart,
            'kopts'                    :  self.set_kernel_options,
            'kopts-post'               :  self.set_kernel_options_post,
            'kopts_post'               :  self.set_kernel_options_post,            
            'virt-auto-boot'           :  self.set_virt_auto_boot,
            'virt_auto_boot'           :  self.set_virt_auto_boot,            
            'virt-file-size'           :  self.set_virt_file_size,
            'virt_file_size'           :  self.set_virt_file_size,            
            'virt-ram'                 :  self.set_virt_ram,
            'virt_ram'                 :  self.set_virt_ram,            
            'ksmeta'                   :  self.set_ksmeta,
            'template-files'           :  self.set_template_files,
            'template_files'           :  self.set_template_files,            
            'repos'                    :  self.set_repos,
            'virt-path'                :  self.set_virt_path,
            'virt_path'                :  self.set_virt_path,            
            'virt-type'                :  self.set_virt_type,
            'virt_type'                :  self.set_virt_type,            
            'virt-bridge'              :  self.set_virt_bridge,
            'virt_bridge'              :  self.set_virt_bridge,            
            'virt-cpus'                :  self.set_virt_cpus,
            'virt_cpus'                :  self.set_virt_cpus,            
            'dhcp-tag'                 :  self.set_dhcp_tag,
            'dhcp_tag'                 :  self.set_dhcp_tag,            
            'server'                   :  self.set_server,
            'owners'                   :  self.set_owners,
            'mgmt-classes'             :  self.set_mgmt_classes,
            'mgmt_classes'             :  self.set_mgmt_classes,            
            'comment'                  :  self.set_comment,
            'name_servers'             :  self.set_name_servers,
            'name_servers_search'      :  self.set_name_servers_search,
            'redhat_management_key'    :  self.set_redhat_management_key,
            'redhat_management_server' :  self.set_redhat_management_server
        }

