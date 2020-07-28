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

from cobbler import autoinstall_manager
from cobbler.items import item
from cobbler import utils
from cobbler import validate
from cobbler.cexceptions import CX
from cobbler.utils import _


# this data structure is described in item.py
FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "int"],
    ["depth", 1, 1, "", False, "", 0, "int"],
    ["mtime", 0, 0, "", False, "", 0, "int"],
    ["uid", "", "", "", False, "", 0, "str"],

    # editable in UI
    ["autoinstall", "SETTINGS:default_autoinstall", '<<inherit>>', "Automatic Installation Template", True, "Path to automatic installation template", 0, "str"],
    ["autoinstall_meta", {}, '<<inherit>>', "Automatic Installation Metadata", True, "Ex: dog=fang agent=86", 0, "dict"],
    ["boot_files", {}, '<<inherit>>', "TFTP Boot Files", True, "Files copied into tftpboot beyond the kernel/initrd", 0, "list"],
    ["comment", "", "", "Comment", True, "Free form text description", 0, "str"],
    ["dhcp_tag", "default", '<<inherit>>', "DHCP Tag", True, "See manpage or leave blank", 0, "str"],
    ["distro", None, '<<inherit>>', "Distribution", True, "Parent distribution", [], "str"],
    ["enable_gpxe", "SETTINGS:enable_gpxe", 0, "Enable gPXE?", True, "Use gPXE instead of PXELINUX for advanced booting options", 0, "bool"],
    ["enable_menu", "SETTINGS:enable_menu", '<<inherit>>', "Enable PXE Menu?", True, "Show this profile in the PXE menu?", 0, "bool"],
    ["fetchable_files", {}, '<<inherit>>', "Fetchable Files", True, "Templates for tftp or wget/curl", 0, "dict"],
    ["kernel_options", {}, '<<inherit>>', "Kernel Options", True, "Ex: selinux=permissive", 0, "dict"],
    ["kernel_options_post", {}, '<<inherit>>', "Kernel Options (Post Install)", True, "Ex: clocksource=pit noapic", 0, "dict"],
    ["mgmt_classes", [], '<<inherit>>', "Management Classes", True, "For external configuration management", 0, "list"],
    ["mgmt_parameters", "<<inherit>>", "<<inherit>>", "Management Parameters", True, "Parameters which will be handed to your management application (Must be valid YAML dictionary)", 0, "str"],
    ["name", "", None, "Name", True, "Ex: F10-i386-webserver", 0, "str"],
    ["name_servers", "SETTINGS:default_name_servers", [], "Name Servers", True, "space delimited", 0, "list"],
    ["name_servers_search", "SETTINGS:default_name_servers_search", [], "Name Servers Search Path", True, "space delimited", 0, "list"],
    ["next_server", "<<inherit>>", '<<inherit>>', "Next Server Override", True, "See manpage or leave blank", 0, "str"],
    ["filename", "<<inherit>>", '<<inherit>>', "DHCP Filename Override", True, "Use to boot non-default bootloaders", 0, "str"],
    ["owners", "SETTINGS:default_ownership", "SETTINGS:default_ownership", "Owners", True, "Owners list for authz_ownership (space delimited)", 0, "list"],
    ["parent", '', '', "Parent Profile", True, "", [], "str"],
    ["proxy", "SETTINGS:proxy_url_int", "<<inherit>>", "Proxy", True, "Proxy URL", 0, "str"],
    ["redhat_management_key", "<<inherit>>", "<<inherit>>", "Red Hat Management Key", True, "Registration key for RHN, Spacewalk, or Satellite", 0, "str"],
    ["repos", [], '<<inherit>>', "Repos", True, "Repos to auto-assign to this profile", [], "list"],
    ["server", "<<inherit>>", '<<inherit>>', "Server Override", True, "See manpage or leave blank", 0, "str"],
    ["template_files", {}, '<<inherit>>', "Template Files", True, "File mappings for built-in config management", 0, "dict"],
    ["virt_auto_boot", "SETTINGS:virt_auto_boot", '<<inherit>>', "Virt Auto Boot", True, "Auto boot this VM?", 0, "bool"],
    ["virt_bridge", "SETTINGS:default_virt_bridge", '<<inherit>>', "Virt Bridge", True, "", 0, "str"],
    ["virt_cpus", 1, '<<inherit>>', "Virt CPUs", True, "integer", 0, "int"],
    ["virt_disk_driver", "SETTINGS:default_virt_disk_driver", '<<inherit>>', "Virt Disk Driver Type", True, "The on-disk format for the virtualization disk", validate.VIRT_DISK_DRIVERS, "str"],
    ["virt_file_size", "SETTINGS:default_virt_file_size", '<<inherit>>', "Virt File Size(GB)", True, "", 0, "int"],
    ["virt_path", "", '<<inherit>>', "Virt Path", True, "Ex: /directory OR VolGroup00", 0, "str"],
    ["virt_ram", "SETTINGS:default_virt_ram", '<<inherit>>', "Virt RAM (MB)", True, "", 0, "int"],
    ["virt_type", "SETTINGS:default_virt_type", '<<inherit>>', "Virt Type", True, "Virtualization technology to use", validate.VIRT_TYPES, "str"],
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
        self.autoinstall_meta = {}
        self.fetchable_files = {}
        self.boot_files = {}
        self.template_files = {}

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Profile(self.collection_mgr)
        cloned.from_dict(_dict)
        return cloned

    def get_fields(self):
        """
        Return all fields which this class has with its current values.

        :return: This is a list with lists.
        """
        return FIELDS

    def get_parent(self):
        """
        Return object next highest up the tree.
        """
        if not self.parent:
            if self.distro is None:
                return None
            result = self.collection_mgr.distros().find(name=self.distro)
        else:
            result = self.collection_mgr.profiles().find(name=self.parent)
        return result

    def check_if_valid(self):
        """
        Check if the profile is valid. This checks for an existing name and a distro as a conceptual parent.
        """
        # name validation
        if not self.name:
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
        Instead of a ``--distro``, set the parent of this object to another profile and use the values from the parent
        instead of this one where the values for this profile aren't filled in, and blend them together where they
        are dictionaries. Basically this enables profile inheritance. To use this, the object MUST have been
        constructed with ``is_subobject=True`` or the default values for everything will be screwed up and this will
        likely NOT work. So, API users -- make sure you pass ``is_subobject=True`` into the constructor when using this.

        :param parent_name: The name of the parent object.
        """
        old_parent = self.get_parent()
        if isinstance(old_parent, item.Item):
            old_parent.children.pop(self.name, 'pass')
        if not parent_name:
            self.parent = ''
            return
        if parent_name == self.name:
            # check must be done in two places as set_parent could be called before/after
            # set_name...
            raise CX(_("self parentage is weird"))
        found = self.collection_mgr.profiles().find(name=parent_name)
        if found is None:
            raise CX(_("profile %s not found, inheritance not possible") % parent_name)
        self.parent = parent_name
        self.depth = found.depth + 1
        parent = self.get_parent()
        if isinstance(parent, item.Item):
            parent.children[self.name] = self

    def set_distro(self, distro_name):
        """
        Sets the distro. This must be the name of an existing Distro object in the Distros collection.
        """
        d = self.collection_mgr.distros().find(name=distro_name)
        if d is not None:
            old_parent = self.get_parent()
            if isinstance(old_parent, item.Item):
                old_parent.children.pop(self.name, 'pass')
            self.distro = distro_name
            self.depth = d.depth + 1    # reset depth if previously a subprofile and now top-level
            d.children[self.name] = self
            return
        raise CX(_("distribution not found"))

    def set_name_servers(self, data):
        """
        Set the DNS servers.

        :param data: string or list of nameservers
        :returns: True or throws exception
        :raises CX: If the nameservers are not valid.
        """
        self.name_servers = validate.name_servers(data)

    def set_name_servers_search(self, data):
        """
        Set the DNS search paths.

        :param data: string or list of search domains
        :returns: True or throws exception
        :raises CX: If the search domains are not valid.
        """
        self.name_servers_search = validate.name_servers_search(data)

    def set_proxy(self, proxy):
        """
        Setter for the proxy.

        :param proxy: The new proxy for the profile.
        """
        self.proxy = proxy

    def set_enable_gpxe(self, enable_gpxe):
        """
        Sets whether or not the profile will use gPXE for booting.

        :param enable_gpxe: New boolean value for enabling gPXE.
        """
        self.enable_gpxe = utils.input_boolean(enable_gpxe)

    def set_enable_menu(self, enable_menu):
        """
        Sets whether or not the profile will be listed in the default PXE boot menu. This is pretty forgiving for
        YAML's sake.

        :param enable_menu: New boolean value for enabling the menu.
        """
        self.enable_menu = utils.input_boolean(enable_menu)

    def set_dhcp_tag(self, dhcp_tag):
        """
        Setter for the dhcp tag property.

        :param dhcp_tag:
        """
        if dhcp_tag is None:
            dhcp_tag = ""
        self.dhcp_tag = dhcp_tag

    def set_server(self, server):
        """
        Setter for the server property.

        :param server: If this is None or an emtpy string this will be reset to be inherited from the parent object.
        """
        if server in [None, ""]:
            server = "<<inherit>>"
        self.server = server

    def set_next_server(self, server):
        """
        Setter for the next server value.

        :param server: If this is None or an emtpy string this will be reset to be inherited from the parent object.
        """
        if server in [None, ""]:
            self.next_server = "<<inherit>>"
        else:
            server = server.strip()
            if server != "<<inherit>>":
                self.next_server = validate.ipv4_address(server)
            else:
                self.next_server = server

    def set_filename(self, filename):
        if not filename:
            self.filename = "<<inherit>>"
        else:
            self.filename = filename.strip()

    def set_autoinstall(self, autoinstall):
        """
        Set the automatic OS installation template file path, this must be a local file.

        :param autoinstall: local automatic installation template path
        :type autoinstall: str
        """

        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self.collection_mgr)
        self.autoinstall = autoinstall_mgr.validate_autoinstall_template_file_path(autoinstall)

    def set_virt_auto_boot(self, num):
        """
        Setter for booting a virtual machine automatically.

        :param num: The new value for whether to enable it or not.
        """
        utils.set_virt_auto_boot(self, num)

    def set_virt_cpus(self, num):
        """
        Setter for the number of virtual CPU cores to assign to the virtual machine.

        :param num: The number of cpu cores.
        """
        utils.set_virt_cpus(self, num)

    def set_virt_file_size(self, num):
        """
        Setter for the size of the virtual image size.

        :param num: The new size of the image.
        """
        utils.set_virt_file_size(self, num)

    def set_virt_disk_driver(self, driver):
        """
        Setter for the virtual disk driver that will be used.

        :param driver: The new driver.
        """
        utils.set_virt_disk_driver(self, driver)

    def set_virt_ram(self, num):
        """
        Setter for the virtual RAM used for the VM.

        :param num: The number of RAM to use for the VM.
        """
        utils.set_virt_ram(self, num)

    def set_virt_type(self, vtype):
        """
        Setter for the virtual machine type.

        :param vtype: May be on out of "qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz" or "auto".
        """
        utils.set_virt_type(self, vtype)

    def set_virt_bridge(self, vbridge):
        """
        Setter for the name of the virtual bridge to use.

        :param vbridge: The name of the virtual bridge to use.
        """
        utils.set_virt_bridge(self, vbridge)

    def set_virt_path(self, path):
        """
        Setter of the path to the place where the image will be stored.

        :param path: The path to where the image will be stored.
        """
        utils.set_virt_path(self, path)

    def set_repos(self, repos, bypass_check=False):
        """
        Setter of the repositories for the profile.

        :param repos: The new repositories which will be set.
        :param bypass_check: If repository checks should be checked or not.
        """
        utils.set_repos(self, repos, bypass_check)

    def set_redhat_management_key(self, management_key):
        """
        Setter of the redhat management key.

        :param management_key: The value may be reset by setting it to None.
        """
        if not management_key:
            self.redhat_management_key = "<<inherit>>"
        self.redhat_management_key = management_key

    def get_redhat_management_key(self):
        """
        Getter of the redhat management key of the profile or it's parent.

        :return: Returns the redhat_management_key of the profile.
        """
        return self.redhat_management_key

    def get_arch(self):
        """
        Getter of the architecture of the profile or the parent.

        :return: The architecture.
        """
        parent = self.get_parent()
        if parent:
            return parent.get_arch()
        return None
# EOF
