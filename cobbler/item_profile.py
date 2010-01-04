"""
A Cobbler Profile.  A profile is a reference to a distribution, possibly some kernel options, possibly some Virt options, and some kickstart data.

Copyright 2006-2009, Red Hat, Inc
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

# this datastructure is described in great detail in item_distro.py -- read the comments there.

FIELDS = [
  ["name","",None,"Name",True,"Ex: F10-i386-webserver",0,"str"],
  ["uid","","","",False,"",0,"str"],
  ["owners","SETTINGS:default_ownership","SETTINGS:default_ownership","Owners",True,"Owners list for authz_ownership (space delimited)",0,"list"],
  ["distro",None,'<<inherit>>',"Distribution",True,"Parent distribution",[],"str"],
  ["enable_menu","SETTINGS:enable_menu",'<<inherit>>',"Enable PXE Menu?",True,"Show this profile in the PXE menu?",0,"bool"],
  ["kickstart","SETTINGS:default_kickstart",'<<inherit>>',"Kickstart",True,"Path to kickstart template",0,"str"],
  ["kernel_options",{},'<<inherit>>',"Kernel Options",True,"Ex: selinux=permissive",0,"dict"],
  ["kernel_options_post",{},'<<inherit>>',"Kernel Options (Post Install)",True,"Ex: clocksource=pit noapic",0,"dict"],
  ["ks_meta",{},'<<inherit>>',"Kickstart Metadata",True,"Ex: dog=fang agent=86",0,"dict"],
  ["repos",[],'<<inherit>>',"Repos",True,"Repos to auto-assign to this profile",[],"list"],
  ["comment","","","Comment",True,"Free form text description",0,"str"],
  ["virt_auto_boot","SETTINGS:virt_auto_boot",'<<inherit>>',"Virt Auto Boot",True,"Auto boot this VM?",0,"bool"],
  ["virt_cpus",1,'<<inherit>>',"Virt CPUs",True,"integer",0,"int"],
  ["virt_file_size","SETTINGS:default_virt_file_size",'<<inherit>>',"Virt File Size(GB)",True,"",0,"int"],
  ["virt_ram","SETTINGS:default_virt_ram",'<<inherit>>',"Virt RAM (MB)",True,"",0,"int"],
  ["depth",1,1,"",False,"",0,"int"],
  ["virt_type","SETTINGS:default_virt_type",'<<inherit>>',"Virt Type",True,"Virtualization technology to use",["xenpv","xenfv","qemu", "vmware"],"str"],
  ["virt_path","",'<<inherit>>',"Virt Path",True,"Ex: /directory OR VolGroup00",0,"str"],
  ["virt_bridge","SETTINGS:default_virt_bridge",'<<inherit>>',"Virt Bridge",True,"",0,"str"],
  ["dhcp_tag","default",'<<inherit>>',"DHCP Tag",True,"See manpage or leave blank",0,"str"],
  ["parent",'','',"",True,"",0,"str"],
  ["server","<<inherit>>",'<<inherit>>',"Server Override",True,"See manpage or leave blank",0,"str"],
  ["ctime",0,0,"",False,"",0,"int"],
  ["mtime",0,0,"",False,"",0,"int"],
  ["name_servers","SETTINGS:default_name_servers",[],"Name Servers",True,"space delimited",0,"list"],
  ["name_servers_search","SETTINGS:default_name_servers_search",[],"Name Servers Search Path",True,"space delimited",0,"list"],
  ["mgmt_classes",[],'<<inherit>>',"Management Classes",True,"For external configuration management",0,"list"],
  ["template_files",{},'<<inherit>>',"Template Files",True,"File mappings for built-in config management",0,"dict"],
  ["redhat_management_key","<<inherit>>","<<inherit>>","Red Hat Management Key",True,"Registration key for RHN, Spacewalk, or Satellite",0,"str"],
  ["redhat_management_server","<<inherit>>","<<inherit>>","Red Hat Management Server",True,"Address of Spacewalk or Satellite Server",0,"str"],
  ["template_remote_kickstarts", "SETTINGS:template_remote_kickstarts", "SETTINGS:template_remote_kickstarts", "", False, "", 0, "bool"]
]

class Profile(item.Item):

    TYPE_NAME = _("profile")
    COLLECTION_TYPE = "profile"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Profile(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def get_fields(self):
        return FIELDS

 
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
            if self.distro is None:
                return None
            result = self.config.distros().find(name=self.distro)
        else:
            result = self.config.profiles().find(name=self.parent)
        return result

    def check_if_valid(self):
        if self.name is None or self.name == "":
            raise CX("name is required")
        distro = self.get_conceptual_parent()
        if distro is None:
            raise CX("Error with profile %s - distro is required" % (self.name))
