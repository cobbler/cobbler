"""
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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

from cobbler import utils
from cobbler import item
from cobbler import validate

from cobbler.utils import _
from cobbler.cexceptions import CX


# this datastructure is described in great detail in item_distro.py -- read the comments there.
FIELDS = [
    ["name", "", None, "Name", True, "Ex: F10-i386-webserver", 0, "str"],
    ["uid", "", "", "", False, "", 0, "str"],
    ["owners", "SETTINGS:default_ownership", "SETTINGS:default_ownership", "Owners", True, "Owners list for authz_ownership (space delimited)", 0, "list"],
    ["distro", None, '<<inherit>>', "Distribution", True, "Parent distribution", [], "str"],
    ["parent", '', '', "Parent Profile", True, "", [], "str"],
    ["enable_gpxe", "SETTINGS:enable_gpxe", 0, "Enable gPXE?", True, "Use gPXE instead of PXELINUX for advanced booting options", 0, "bool"],
    ["enable_menu", "SETTINGS:enable_menu", '<<inherit>>', "Enable PXE Menu?", True, "Show this profile in the PXE menu?", 0, "bool"],
    ["kickstart", "SETTINGS:default_kickstart", '<<inherit>>', "Kickstart", True, "Path to kickstart template", 0, "str"],
    ["kernel_options", {}, '<<inherit>>', "Kernel Options", True, "Ex: selinux=permissive", 0, "dict"],
    ["kernel_options_post", {}, '<<inherit>>', "Kernel Options (Post Install)", True, "Ex: clocksource=pit noapic", 0, "dict"],
    ["ks_meta", {}, '<<inherit>>', "Kickstart Metadata", True, "Ex: dog=fang agent=86", 0, "dict"],
    ["proxy", "", None, "Proxy", True, "Proxy URL", 0, "str"],
    ["repos", [], '<<inherit>>', "Repos", True, "Repos to auto-assign to this profile", [], "list"],
    ["comment", "", "", "Comment", True, "Free form text description", 0, "str"],
    ["virt_auto_boot", "SETTINGS:virt_auto_boot", '<<inherit>>', "Virt Auto Boot", True, "Auto boot this VM?", 0, "bool"],
    ["virt_cpus", 1, '<<inherit>>', "Virt CPUs", True, "integer", 0, "int"],
    ["virt_file_size", "SETTINGS:default_virt_file_size", '<<inherit>>', "Virt File Size(GB)", True, "", 0, "int"],
    ["virt_disk_driver", "SETTINGS:default_virt_disk_driver", '<<inherit>>', "Virt Disk Driver Type", True, "The on-disk format for the virtualization disk", "raw", "str"],
    ["virt_ram", "SETTINGS:default_virt_ram", '<<inherit>>', "Virt RAM (MB)", True, "", 0, "int"],
    ["virt_type", "SETTINGS:default_virt_type", '<<inherit>>', "Virt Type", True, "Virtualization technology to use", validate.VIRT_TYPES, "str"],
    ["virt_path", "", '<<inherit>>', "Virt Path", True, "Ex: /directory OR VolGroup00", 0, "str"],
    ["virt_bridge", "SETTINGS:default_virt_bridge", '<<inherit>>', "Virt Bridge", True, "", 0, "str"],
    ["dhcp_tag", "default", '<<inherit>>', "DHCP Tag", True, "See manpage or leave blank", 0, "str"],
    ["server", "<<inherit>>", '<<inherit>>', "Server Override", True, "See manpage or leave blank", 0, "str"],
    ["next_server", "<<inherit>>", '<<inherit>>', "Next Server Override", True, "See manpage or leave blank", 0, "str"],
    ["depth", 1, 1, "", False, "", 0, "int"],
    ["ctime", 0, 0, "", False, "", 0, "int"],
    ["mtime", 0, 0, "", False, "", 0, "int"],
    ["name_servers", "SETTINGS:default_name_servers", [], "Name Servers", True, "space delimited", 0, "list"],
    ["name_servers_search", "SETTINGS:default_name_servers_search", [], "Name Servers Search Path", True, "space delimited", 0, "list"],
    ["mgmt_classes", [], '<<inherit>>', "Management Classes", True, "For external configuration management", 0, "list"],
    ["mgmt_parameters", "<<inherit>>", "<<inherit>>", "Management Parameters", True, "Parameters which will be handed to your management application (Must be valid YAML dictionary)", 0, "str"],
    ["boot_files", {}, '<<inherit>>', "TFTP Boot Files", True, "Files copied into tftpboot beyond the kernel/initrd", 0, "list"],
    ["fetchable_files", {}, '<<inherit>>', "Fetchable Files", True, "Templates for tftp or wget", 0, "dict"],
    ["template_files", {}, '<<inherit>>', "Template Files", True, "File mappings for built-in config management", 0, "dict"]
]


class Profile(item.Item):
    """
    A Cobbler profile object.
    """

    TYPE_NAME = _("profile")
    COLLECTION_TYPE = "profile"

    def __init__(self, *args, **kwargs):
        super(Profile, self).__init__(*args, **kwargs)
        self.kernel_options = {}
        self.kernel_options_post = {}
        self.ks_meta = {}
        self.fetchable_files = {}
        self.boot_files = {}
        self.template_files = {}


    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Profile(self.config)
        cloned.from_datastruct(ds)
        return cloned


    def get_fields(self):
        """
        Return the list of fields and their properties
        """
        return FIELDS


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
        # name validation
        if self.name is None or self.name == "":
            raise CX("Name is required")

        # distro validation
        distro = self.get_conceptual_parent()
        if distro is None:
            raise CX("Error with profile %s - distro is required" % (self.name))


    #
    # specific methods for item.Profile
    #

    def set_parent(self, parent_name):
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
        old_parent = self.get_parent()
        if isinstance(old_parent, item.Item):
            old_parent.children.pop(self.name, 'pass')
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
        parent = self.get_parent()
        if isinstance(parent, item.Item):
            parent.children[self.name] = self
        return True


    def set_distro(self, distro_name):
        """
        Sets the distro.  This must be the name of an existing
        Distro object in the Distros collection.
        """
        d = self.config.distros().find(name=distro_name)
        if d is not None:
            old_parent = self.get_parent()
            if isinstance(old_parent, item.Item):
                old_parent.children.pop(self.name, 'pass')
            self.distro = distro_name
            self.depth = d.depth + 1    # reset depth if previously a subprofile and now top-level
            d.children[self.name] = self
            return True
        raise CX(_("distribution not found"))


    def set_name_servers(self, data):
        """
        Set the DNS servers.

        @param: str/list data (string or list of nameservers)
        @returns: True or CX
        """
        self.name_servers = validate.name_servers(data)
        return True


    def set_name_servers_search(self, data):
        """
        Set the DNS search paths.

        @param: str/list data (string or list of search domains)
        @returns: True or CX
        """
        self.name_servers_search = validate.name_servers_search(data)
        return True


    def set_proxy(self, proxy):
        self.proxy = proxy
        return True


    def set_enable_gpxe(self, enable_gpxe):
        """
        Sets whether or not the profile will use gPXE for booting.
        """
        self.enable_gpxe = utils.input_boolean(enable_gpxe)
        return True


    def set_enable_menu(self, enable_menu):
        """
        Sets whether or not the profile will be listed in the default
        PXE boot menu.  This is pretty forgiving for YAML's sake.
        """
        self.enable_menu = utils.input_boolean(enable_menu)
        return True


    def set_dhcp_tag(self, dhcp_tag):
        if dhcp_tag is None:
            dhcp_tag = ""
        self.dhcp_tag = dhcp_tag
        return True


    def set_server(self, server):
        if server in [None, ""]:
            server = "<<inherit>>"
        self.server = server
        return True


    def set_next_server(self, server):
        if server in [None, ""]:
            self.next_server = "<<inherit>>"
        else:
            self.next_server = validate.ipv4_address(server)
        return True


    def set_kickstart(self, kickstart):
        """
        Set the kickstart path, this must be a local file.

        @param: str kickstart path to a local kickstart file
        @returns: True or CX
        """
        self.kickstart = validate.kickstart_file_path(kickstart)
        return True


    def set_virt_auto_boot(self, num):
        return utils.set_virt_auto_boot(self, num)


    def set_virt_cpus(self, num):
        return utils.set_virt_cpus(self, num)


    def set_virt_file_size(self, num):
        return utils.set_virt_file_size(self, num)


    def set_virt_disk_driver(self, driver):
        return utils.set_virt_disk_driver(self, driver)


    def set_virt_ram(self, num):
        return utils.set_virt_ram(self, num)


    def set_virt_type(self, vtype):
        return utils.set_virt_type(self, vtype)


    def set_virt_bridge(self, vbridge):
        return utils.set_virt_bridge(self, vbridge)


    def set_virt_path(self, path):
        return utils.set_virt_path(self, path)


    def set_repos(self, repos, bypass_check=False):
        return utils.set_repos(self, repos, bypass_check)

# EOF
