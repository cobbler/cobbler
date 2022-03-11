"""
Command line interface for Cobbler.

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

import optparse
import os
import sys
import time
import traceback
import xmlrpc.client
from typing import Optional

from cobbler import enums
from cobbler import power_manager
from cobbler import utils

INVALID_TASK = "<<invalid>>"

OBJECT_ACTIONS_MAP = {
    "distro": ["add", "copy", "edit", "find", "list", "remove", "rename", "report"],
    "profile": ["add", "copy", "dumpvars", "edit", "find", "get-autoinstall", "list", "remove", "rename", "report"],
    "system": ["add", "copy", "dumpvars", "edit", "find", "get-autoinstall", "list", "remove", "rename", "report",
               "poweron", "poweroff", "powerstatus", "reboot"],
    "image": ["add", "copy", "edit", "find", "list", "remove", "rename", "report"],
    "repo": ["add", "copy", "edit", "find", "list", "remove", "rename", "report", "autoadd"],
    "mgmtclass": ["add", "copy", "edit", "find", "list", "remove", "rename", "report"],
    "package": ["add", "copy", "edit", "find", "list", "remove", "rename", "report"],
    "file": ["add", "copy", "edit", "find", "list", "remove", "rename", "report"],
    "menu": ["add", "copy", "edit", "find", "list", "remove", "rename", "report"],
    "setting": ["edit", "report"],
    "signature": ["reload", "report", "update"]
}

OBJECT_TYPES = list(OBJECT_ACTIONS_MAP.keys())
# would like to use from_iterable here, but have to support python 2.4
OBJECT_ACTIONS = []
for actions in list(OBJECT_ACTIONS_MAP.values()):
    OBJECT_ACTIONS += actions
DIRECT_ACTIONS = ["aclsetup", "buildiso", "import", "list", "replicate", "report", "reposync", "sync",
                  "validate-autoinstalls", "version", "signature", "hardlink", "mkloaders"]

####################################################

# the fields has controls what data elements are part of each object.  To add a new field, just add a new
# entry to the list following some conventions to be described later.  You must also add a method called
# set_$fieldname.  Do not write a method called get_$fieldname, that will not be called.
#
# name | default | subobject default | display name | editable? | tooltip | values ? | type
#
# name -- what the filed should be called.   For the command line, underscores will be replaced with
#         a hyphen programatically, so use underscores to seperate things that are seperate words
#
# default value -- when a new object is created, what is the default value for this field?
#
# subobject default -- this applies ONLY to subprofiles, and is most always set to <<inherit>>.  If this
#                      is not item_profile.py it does not matter.
#
# display name -- how the field shows up in the web application and the "cobbler report" command
#
# editable -- should the field be editable in the CLI and web app?  Almost always yes unless
#                it is an internalism.  Fields that are not editable are "hidden"
#
# tooltip -- the caption to be shown in the web app or in "commandname --help" in the CLI
#
# values -- for fields that have a limited set of valid options and those options are always fixed
#           (such as architecture type), the list of valid options goes in this field.
#
# type -- the type of the field.  Used to determine which HTML form widget is used in the web interface
#
#
# the order in which the fields appear in the web application (for all non-hidden
# fields) is defined in field_ui_info.py. The CLI sorts fields alphabetically.
#
# field_ui_info.py also contains a set of "Groups" that describe what other fields
# are associated with what other fields.  This affects color coding and other
# display hints.  If you add a field, please edit field_ui_info.py carefully to match.
#
# additional:  see field_ui_info.py for some display hints.  By default, in the
# web app, all fields are text fields unless field_ui_info.py lists the field in
# one of those dictionaries.
#
# hidden fields should not be added without just cause, explanations about these are:
#
#   ctime, mtime -- times the object was modified, used internally by Cobbler for API purposes
#   uid -- also used for some external API purposes
#   source_repos -- an artifiact of import, this is too complicated to explain on IRC so we just hide it for RHEL split
#                   repos, this is a list of each of them in the install tree, used to generate repo lines in the
#                   automatic installation file to allow installation of x>=RHEL5. Otherwise unimportant.
#   depth -- used for "cobbler list" to print the tree, makes it easier to load objects from disk also
#   tree_build_time -- loaded from import, this is not useful to many folks so we just hide it.  Avail over API.
#
# so to add new fields
#   (A) understand the above
#   (B) add a field below
#   (C) add a set_fieldname method
#   (D) if field must be viewable/editable via web UI, add a entry in
#       corresponding *_UI_FIELDS_MAPPING dictionary in field_ui_info.py.
#       If field must not be displayed in a text field in web UI, also add
#       an entry in corresponding USES_* list in field_ui_info.py.
#
# in general the set_field_name method should raise exceptions on invalid fields, always.   There are adtl
# validation fields in is_valid to check to see that two seperate fields do not conflict, but in general
# design issues that require this should be avoided forever more, and there are few exceptions.  Cobbler
# must operate as normal with the default value for all fields and not choke on the default values.

DISTRO_FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 0, 0, "Depth", False, "", 0, "int"],
    ["mtime", 0, 0, "", False, "", 0, "float"],
    ["source_repos", [], 0, "Source Repos", False, "", 0, "list"],
    ["tree_build_time", 0, 0, "Tree Build Time", False, "", 0, "str"],
    ["uid", "", 0, "", False, "", 0, "str"],

    # editable in UI
    ["arch", 'x86_64', 0, "Architecture", True, "", utils.get_valid_archs(), "str"],
    ["autoinstall_meta", {}, 0, "Automatic Installation Template Metadata", True, "Ex: dog=fang agent=86", 0, "dict"],
    ["boot_files", {}, 0, "TFTP Boot Files", True, "Files copied into tftpboot beyond the kernel/initrd", 0, "list"],
    ["boot_loaders", "<<inherit>>", "<<inherit>>", "Boot loaders", True, "Network installation boot loaders", 0,
     "list"],
    ["breed", 'redhat', 0, "Breed", True, "What is the type of distribution?", utils.get_valid_breeds(), "str"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["fetchable_files", {}, 0, "Fetchable Files", True, "Templates for tftp or wget/curl", 0, "list"],
    ["initrd", None, 0, "Initrd", True, "Absolute path to kernel on filesystem", 0, "str"],
    ["kernel", None, 0, "Kernel", True, "Absolute path to kernel on filesystem", 0, "str"],
    ["remote_boot_initrd", None, 0, "Remote Boot Initrd", True, "URL the bootloader directly retrieves and boots from",
     0, "str"],
    ["remote_boot_kernel", None, 0, "Remote Boot Kernel", True, "URL the bootloader directly retrieves and boots from",
     0, "str"],
    ["kernel_options", {}, 0, "Kernel Options", True, "Ex: selinux=permissive", 0, "dict"],
    ["kernel_options_post", {}, 0, "Kernel Options (Post Install)", True, "Ex: clocksource=pit noapic", 0, "dict"],
    ["mgmt_classes", [], 0, "Management Classes", True, "Management classes for external config management", 0, "list"],
    ["name", "", 0, "Name", True, "Ex: Fedora-11-i386", 0, "str"],
    ["os_version", "virtio26", 0, "OS Version", True, "Needed for some virtualization optimizations",
     utils.get_valid_os_versions(), "str"],
    ["owners", "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", 0,
     "list"],
    ["redhat_management_key", "", "", "Redhat Management Key", True,
     "Registration key for RHN, Spacewalk, or Satellite", 0, "str"],
    ["template_files", {}, 0, "Template Files", True, "File mappings for built-in config management", 0, "dict"]
]

FILE_FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 2, 0, "", False, "", 0, "float"],
    ["mtime", 0, 0, "", False, "", 0, "float"],
    ["uid", "", 0, "", False, "", 0, "str"],

    # editable in UI
    ["action", "create", 0, "Action", True, "Create or remove file resource", 0, "str"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["group", "", 0, "Owner group in file system", True, "File owner group in file system", 0, "str"],
    ["is_dir", False, 0, "Is Directory", True, "Treat file resource as a directory", 0, "bool"],
    ["mode", "", 0, "Mode", True, "The mode of the file", 0, "str"],
    ["name", "", 0, "Name", True, "Name of file resource", 0, "str"],
    ["owner", "", 0, "Owner user in file system", True, "File owner user in file system", 0, "str"],
    ["owners", "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", [],
     "list"],
    ["path", "", 0, "Path", True, "The path for the file", 0, "str"],
    ["template", "", 0, "Template", True, "The template for the file", 0, "str"]
]

IMAGE_FIELDS = [
    # non-editable in UI (internal)
    ['ctime', 0, 0, "", False, "", 0, "float"],
    ['depth', 0, 0, "", False, "", 0, "int"],
    ['mtime', 0, 0, "", False, "", 0, "float"],
    ['parent', '', 0, "", False, "", 0, "str"],
    ['uid', "", 0, "", False, "", 0, "str"],

    # editable in UI
    ['arch', 'x86_64', 0, "Architecture", True, "", utils.get_valid_archs(), "str"],
    ['autoinstall', '', 0, "Automatic installation file", True, "Path to autoinst/answer file template", 0, "str"],
    ['breed', 'redhat', 0, "Breed", True, "", utils.get_valid_breeds(), "str"],
    ['comment', '', 0, "Comment", True, "Free form text description", 0, "str"],
    ['file', '', 0, "File", True, "Path to local file or nfs://user@host:path", 0, "str"],
    ['image_type', "iso", 0, "Image Type", True, "", ["iso", "direct", "memdisk", "virt-image"], "str"],
    ['name', '', 0, "Name", True, "", 0, "str"],
    ['network_count', 1, 0, "Virt NICs", True, "", 0, "int"],
    ['os_version', '', 0, "OS Version", True, "ex: rhel4", utils.get_valid_os_versions(), "str"],
    ['owners', "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", [],
     "list"],
    ["menu", '', '', "Parent boot menu", True, "", [], "str"],
    ["boot_loaders", '<<inherit>>', '<<inherit>>', "Boot loaders", True, "Network installation boot loaders", 0,
     "list"],
    ['virt_auto_boot', "SETTINGS:virt_auto_boot", 0, "Virt Auto Boot", True, "Auto boot this VM?", 0, "bool"],
    ['virt_bridge', "SETTINGS:default_virt_bridge", 0, "Virt Bridge", True, "", 0, "str"],
    ['virt_cpus', 1, 0, "Virt CPUs", True, "", 0, "int"],
    ["virt_disk_driver", "SETTINGS:default_virt_disk_driver", 0, "Virt Disk Driver Type", True,
     "The on-disk format for the virtualization disk", "raw", "str"],
    ['virt_file_size', "SETTINGS:default_virt_file_size", 0, "Virt File Size (GB)", True, "", 0, "float"],
    ['virt_path', '', 0, "Virt Path", True, "Ex: /directory or VolGroup00", 0, "str"],
    ['virt_ram', "SETTINGS:default_virt_ram", 0, "Virt RAM (MB)", True, "", 0, "int"],
    ['virt_type', "SETTINGS:default_virt_type", 0, "Virt Type", True, "", ["xenpv", "xenfv", "qemu", "kvm", "vmware"],
     "str"],
]

MENU_FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 1, 1, "", False, "", 0, "int"],
    ["mtime", 0, 0, "", False, "", 0, "int"],
    ["uid", "", "", "", False, "", 0, "str"],

    # editable in UI
    ["comment", "", "", "Comment", True, "Free form text description", 0, "str"],
    ["name", "", None, "Name", True, "Ex: Systems", 0, "str"],
    ["display_name", "", "", "Display Name", True, "Ex: Systems menu", [], "str"],
    ["parent", '', '', "Parent Menu", True, "", [], "str"],
]

MGMTCLASS_FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 2, 0, "", False, "", 0, "float"],
    ["is_definition", False, 0, "Is Definition?", True, "Treat this class as a definition (puppet only)", 0, "bool"],
    ["mtime", 0, 0, "", False, "", 0, "int"],
    ["uid", "", 0, "", False, "", 0, "str"],

    # editable in UI
    ["class_name", "", 0, "Class Name", True, "Actual Class Name (leave blank to use the name field)", 0, "str"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["files", [], 0, "Files", True, "File resources", 0, "list"],
    ["name", "", 0, "Name", True, "Ex: F10-i386-webserver", 0, "str"],
    ["owners", "SETTINGS:default_ownership", "SETTINGS:default_ownership", "Owners", True,
     "Owners list for authz_ownership (space delimited)", 0, "list"],
    ["packages", [], 0, "Packages", True, "Package resources", 0, "list"],
    ["params", {}, 0, "Parameters/Variables", True, "List of parameters/variables", 0, "dict"],
]

PACKAGE_FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 2, 0, "", False, "", 0, "float"],
    ["mtime", 0, 0, "", False, "", 0, "float"],
    ["uid", "", 0, "", False, "", 0, "str"],

    # editable in UI
    ["action", "create", 0, "Action", True, "Install or remove package resource", 0, "str"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["installer", "yum", 0, "Installer", True, "Package Manager", 0, "str"],
    ["name", "", 0, "Name", True, "Name of file resource", 0, "str"],
    ["owners", "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", [],
     "list"],
    ["version", "", 0, "Version", True, "Package Version", 0, "str"],
]

PROFILE_FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 1, 1, "", False, "", 0, "int"],
    ["mtime", 0, 0, "", False, "", 0, "int"],
    ["uid", "", "", "", False, "", 0, "str"],

    # editable in UI
    ["autoinstall", "SETTINGS:autoinstall", '<<inherit>>', "Automatic Installation Template", True,
     "Path to automatic installation template", 0, "str"],
    ["autoinstall_meta", {}, '<<inherit>>', "Automatic Installation Metadata", True, "Ex: dog=fang agent=86", 0,
     "dict"],
    ["boot_files", {}, '<<inherit>>', "TFTP Boot Files", True, "Files copied into tftpboot beyond the kernel/initrd", 0,
     "list"],
    ["boot_loaders", '<<inherit>>', '<<inherit>>', "Boot loaders", True, "Linux installation boot loaders", 0, "list"],
    ["comment", "", "", "Comment", True, "Free form text description", 0, "str"],
    ["dhcp_tag", "default", '<<inherit>>', "DHCP Tag", True, "See manpage or leave blank", 0, "str"],
    ["distro", None, '<<inherit>>', "Distribution", True, "Parent distribution", [], "str"],
    ["enable_ipxe", "SETTINGS:enable_ipxe", 0, "Enable iPXE?", True,
     "Use iPXE instead of PXELINUX for advanced booting options", 0, "bool"],
    ["enable_menu", "SETTINGS:enable_menu", '<<inherit>>', "Enable PXE Menu?", True,
     "Show this profile in the PXE menu?", 0, "bool"],
    ["fetchable_files", {}, '<<inherit>>', "Fetchable Files", True, "Templates for tftp or wget/curl", 0, "dict"],
    ["kernel_options", {}, '<<inherit>>', "Kernel Options", True, "Ex: selinux=permissive", 0, "dict"],
    ["kernel_options_post", {}, '<<inherit>>', "Kernel Options (Post Install)", True, "Ex: clocksource=pit noapic", 0,
     "dict"],
    ["mgmt_classes", [], '<<inherit>>', "Management Classes", True, "For external configuration management", 0, "list"],
    ["mgmt_parameters", "<<inherit>>", "<<inherit>>", "Management Parameters", True,
     "Parameters which will be handed to your management application (Must be valid YAML dictionary)", 0, "str"],
    ["name", "", None, "Name", True, "Ex: F10-i386-webserver", 0, "str"],
    ["name_servers", "SETTINGS:default_name_servers", [], "Name Servers", True, "space delimited", 0, "list"],
    ["name_servers_search", "SETTINGS:default_name_servers_search", [], "Name Servers Search Path", True,
     "space delimited", 0, "list"],
    ["next_server_v4", "<<inherit>>", '<<inherit>>', "Next Server (IPv4) Override", True, "See manpage or leave blank",
     0, "str"],
    ["next_server_v6", "<<inherit>>", '<<inherit>>', "Next Server (IPv6) Override", True, "See manpage or leave blank",
     0, "str"],
    ["filename", "<<inherit>>", '<<inherit>>', "DHCP Filename Override", True, "Use to boot non-default bootloaders", 0,
     "str"],
    ["owners", "SETTINGS:default_ownership", "SETTINGS:default_ownership", "Owners", True,
     "Owners list for authz_ownership (space delimited)", 0, "list"],
    ["parent", '', '', "Parent Profile", True, "", [], "str"],
    ["proxy", "SETTINGS:proxy_url_int", "<<inherit>>", "Proxy", True, "Proxy URL", 0, "str"],
    ["redhat_management_key", "<<inherit>>", "<<inherit>>", "Red Hat Management Key", True,
     "Registration key for RHN, Spacewalk, or Satellite", 0, "str"],
    ["repos", [], '<<inherit>>', "Repos", True, "Repos to auto-assign to this profile", [], "list"],
    ["server", "<<inherit>>", '<<inherit>>', "Server Override", True, "See manpage or leave blank", 0, "str"],
    ["template_files", {}, '<<inherit>>', "Template Files", True, "File mappings for built-in config management", 0,
     "dict"],
    ["menu", None, None, "Parent boot menu", True, "", 0, "str"],
    ["virt_auto_boot", "SETTINGS:virt_auto_boot", '<<inherit>>', "Virt Auto Boot", True, "Auto boot this VM?", 0,
     "bool"],
    ["virt_bridge", "SETTINGS:default_virt_bridge", '<<inherit>>', "Virt Bridge", True, "", 0, "str"],
    ["virt_cpus", 1, '<<inherit>>', "Virt CPUs", True, "integer", 0, "int"],
    ["virt_disk_driver", "SETTINGS:default_virt_disk_driver", '<<inherit>>', "Virt Disk Driver Type", True,
     "The on-disk format for the virtualization disk", [e.value for e in enums.VirtDiskDrivers], "str"],
    ["virt_file_size", "SETTINGS:default_virt_file_size", '<<inherit>>', "Virt File Size(GB)", True, "", 0, "int"],
    ["virt_path", "", '<<inherit>>', "Virt Path", True, "Ex: /directory OR VolGroup00", 0, "str"],
    ["virt_ram", "SETTINGS:default_virt_ram", '<<inherit>>', "Virt RAM (MB)", True, "", 0, "int"],
    ["virt_type", "SETTINGS:default_virt_type", '<<inherit>>', "Virt Type", True, "Virtualization technology to use",
     [e.value for e in enums.VirtType], "str"],
]

REPO_FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 2, 0, "", False, "", 0, "float"],
    ["mtime", 0, 0, "", False, "", 0, "float"],
    ["parent", None, 0, "", False, "", 0, "str"],
    ["uid", None, 0, "", False, "", 0, "str"],

    # editable in UI
    ["apt_components", "", 0, "Apt Components (apt only)", True, "ex: main restricted universe", [], "list"],
    ["apt_dists", "", 0, "Apt Dist Names (apt only)", True, "ex: precise precise-updates", [], "list"],
    ["arch", "x86_64", 0, "Arch", True, "ex: i386, x86_64", [e.value for e in enums.RepoArchs], "str"],
    ["breed", "rsync", 0, "Breed", True, "", [e.value for e in enums.RepoBreeds], "str"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["createrepo_flags", '<<inherit>>', 0, "Createrepo Flags", True, "Flags to use with createrepo", 0, "dict"],
    ["environment", {}, 0, "Environment Variables", True,
     "Use these environment variables during commands (key=value, space delimited)", 0, "dict"],
    ["keep_updated", True, 0, "Keep Updated", True, "Update this repo on next 'cobbler reposync'?", 0, "bool"],
    ["mirror", None, 0, "Mirror", True, "Address of yum or rsync repo to mirror", 0, "str"],
    ["mirror_type", "baseurl", 0, "Mirror Type", True, "", [e.value for e in enums.MirrorType], "str"],
    ["mirror_locally", True, 0, "Mirror locally", True, "Copy files or just reference the repo externally?", 0, "bool"],
    ["name", "", 0, "Name", True, "Ex: f10-i386-updates", 0, "str"],
    ["owners", "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", [],
     "list"],
    ["priority", 99, 0, "Priority", True, "Value for yum priorities plugin, if installed", 0, "int"],
    ["proxy", "SETTINGS:proxy_url_ext", "<<inherit>>", "Proxy information", True,
     "http://example.com:8080, or <<inherit>> to use proxy_url_ext from settings, blank or <<None>> for no proxy", 0,
     "str"],
    ["rpm_list", [], 0, "RPM List", True, "Mirror just these RPMs (yum only)", 0, "list"],
    ["yumopts", {}, 0, "Yum Options", True, "Options to write to yum config file", 0, "dict"],
    ["rsyncopts", "", 0, "Rsync Options", True, "Options to use with rsync repo", 0, "dict"],
]

SYSTEM_FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 2, 0, "", False, "", 0, "int"],
    ["ipv6_autoconfiguration", False, 0, "IPv6 Autoconfiguration", True, "", 0, "bool"],
    ["mtime", 0, 0, "", False, "", 0, "float"],
    ["repos_enabled", False, 0, "Repos Enabled", True,
     "(re)configure local repos on this machine at next config update?", 0, "bool"],
    ["uid", "", 0, "", False, "", 0, "str"],

    # editable in UI
    ["autoinstall", "<<inherit>>", 0, "Automatic Installation Template", True,
     "Path to automatic installation template", 0, "str"],
    ["autoinstall_meta", {}, 0, "Automatic Installation Template Metadata", True, "Ex: dog=fang agent=86", 0, "dict"],
    ["boot_files", {}, '<<inherit>>', "TFTP Boot Files", True, "Files copied into tftpboot beyond the kernel/initrd", 0,
     "list"],
    ["boot_loaders", '<<inherit>>', '<<inherit>>', "Boot loaders", True, "Linux installation boot loaders", 0, "list"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["enable_ipxe", "<<inherit>>", 0, "Enable iPXE?", True, "Use iPXE instead of PXELINUX for advanced booting options",
     0, "bool"],
    ["fetchable_files", {}, '<<inherit>>', "Fetchable Files", True, "Templates for tftp or wget/curl", 0, "dict"],
    ["gateway", "", 0, "Gateway", True, "", 0, "str"],
    ["hostname", "", 0, "Hostname", True, "", 0, "str"],
    ["image", None, 0, "Image", True, "Parent image (if not a profile)", 0, "str"],
    ["ipv6_default_device", "", 0, "IPv6 Default Device", True, "", 0, "str"],
    ["kernel_options", {}, 0, "Kernel Options", True, "Ex: selinux=permissive", 0, "dict"],
    ["kernel_options_post", {}, 0, "Kernel Options (Post Install)", True, "Ex: clocksource=pit noapic", 0, "dict"],
    ["mgmt_classes", "<<inherit>>", 0, "Management Classes", True, "For external config management", 0, "list"],
    ["mgmt_parameters", "<<inherit>>", 0, "Management Parameters", True,
     "Parameters which will be handed to your management application (Must be valid YAML dictionary)", 0, "str"],
    ["name", "", 0, "Name", True, "Ex: vanhalen.example.org", 0, "str"],
    ["name_servers", [], 0, "Name Servers", True, "space delimited", 0, "list"],
    ["name_servers_search", [], 0, "Name Servers Search Path", True, "space delimited", 0, "list"],
    ["netboot_enabled", True, 0, "Netboot Enabled", True, "PXE (re)install this machine at next boot?", 0, "bool"],
    ["next_server_v4", "<<inherit>>", 0, "Next Server (IPv4) Override", True, "See manpage or leave blank", 0, "str"],
    ["next_server_v6", "<<inherit>>", 0, "Next Server (IPv6) Override", True, "See manpage or leave blank", 0, "str"],
    ["filename", "<<inherit>>", '<<inherit>>', "DHCP Filename Override", True, "Use to boot non-default bootloaders", 0,
     "str"],
    ["owners", "<<inherit>>", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", 0, "list"],
    ["power_address", "", 0, "Power Management Address", True, "Ex: power-device.example.org", 0, "str"],
    ["power_id", "", 0, "Power Management ID", True, "Usually a plug number or blade name, if power type requires it",
     0, "str"],
    ["power_pass", "", 0, "Power Management Password", True, "", 0, "str"],
    ["power_type", "SETTINGS:power_management_default_type", 0, "Power Management Type", True,
     "Power management script to use", power_manager.get_power_types(), "str"],
    ["power_user", "", 0, "Power Management Username", True, "", 0, "str"],
    ["power_options", "", 0, "Power Management Options", True, "Additional options, to be passed to the fencing agent",
     0, "str"],
    ["power_identity_file", "", 0, "Power Identity File", True,
     "Identity file to be passed to the fencing agent (ssh key)", 0, "str"],
    ["profile", None, 0, "Profile", True, "Parent profile", [], "str"],
    ["proxy", "<<inherit>>", 0, "Internal Proxy", True, "Internal proxy URL", 0, "str"],
    ["redhat_management_key", "<<inherit>>", 0, "Redhat Management Key", True,
     "Registration key for RHN, Spacewalk, or Satellite", 0, "str"],
    ["server", "<<inherit>>", 0, "Server Override", True, "See manpage or leave blank", 0, "str"],
    ["status", "production", 0, "Status", True, "System status",
     ["", "development", "testing", "acceptance", "production"], "str"],
    ["template_files", {}, 0, "Template Files", True, "File mappings for built-in configuration management", 0, "dict"],
    ["virt_auto_boot", "<<inherit>>", 0, "Virt Auto Boot", True, "Auto boot this VM?", 0, "bool"],
    ["virt_cpus", "<<inherit>>", 0, "Virt CPUs", True, "", 0, "int"],
    ["virt_disk_driver", "<<inherit>>", 0, "Virt Disk Driver Type", True,
     "The on-disk format for the virtualization disk", [e.value for e in enums.VirtDiskDrivers], "str"],
    ["virt_file_size", "<<inherit>>", 0, "Virt File Size(GB)", True, "", 0, "float"],
    ["virt_path", "<<inherit>>", 0, "Virt Path", True, "Ex: /directory or VolGroup00", 0, "str"],
    ["virt_pxe_boot", 0, 0, "Virt PXE Boot", True, "Use PXE to build this VM?", 0, "bool"],
    ["virt_ram", "<<inherit>>", 0, "Virt RAM (MB)", True, "", 0, "int"],
    ["virt_type", "<<inherit>>", 0, "Virt Type", True, "Virtualization technology to use",
     [e.value for e in enums.VirtType], "str"],
    ["serial_device", "", 0, "Serial Device #", True, "Serial Device Number", 0, "int"],
    ["serial_baud_rate", "", 0, "Serial Baud Rate", True, "Serial Baud Rate",
     ["", "2400", "4800", "9600", "19200", "38400", "57600", "115200"], "int"],
]

# network interface fields are in a separate list because a system may contain
# several network interfaces and thus several values for each one of those fields
# (1-N cardinality), while it may contain only one value for other fields
# (1-1 cardinality). This difference requires special handling.
NETWORK_INTERFACE_FIELDS = [
    ["bonding_opts", "", 0, "Bonding Opts", True, "Should be used with --interface", 0, "str"],
    ["bridge_opts", "", 0, "Bridge Opts", True, "Should be used with --interface", 0, "str"],
    ["cnames", [], 0, "CNAMES", True,
     "Cannonical Name Records, should be used with --interface, In quotes, space delimited", 0, "list"],
    ["connected_mode", False, 0, "InfiniBand Connected Mode", True, "Should be used with --interface", 0, "bool"],
    ["dhcp_tag", "", 0, "DHCP Tag", True, "Should be used with --interface", 0, "str"],
    ["dns_name", "", 0, "DNS Name", True, "Should be used with --interface", 0, "str"],
    ["if_gateway", "", 0, "Per-Interface Gateway", True, "Should be used with --interface", 0, "str"],
    ["interface_master", "", 0, "Master Interface", True, "Should be used with --interface", 0, "str"],
    ["interface_type", "na", 0, "Interface Type", True, "Should be used with --interface",
     ["na", "bond", "bond_slave", "bridge", "bridge_slave", "bonded_bridge_slave", "bmc", "infiniband"], "str"],
    ["ip_address", "", 0, "IP Address", True, "Should be used with --interface", 0, "str"],
    ["ipv6_address", "", 0, "IPv6 Address", True, "Should be used with --interface", 0, "str"],
    ["ipv6_default_gateway", "", 0, "IPv6 Default Gateway", True, "Should be used with --interface", 0, "str"],
    ["ipv6_mtu", "", 0, "IPv6 MTU", True, "Should be used with --interface", 0, "str"],
    ["ipv6_prefix", "", 0, "IPv6 Prefix", True, "Should be used with --interface", 0, "str"],
    ["ipv6_secondaries", [], 0, "IPv6 Secondaries", True, "Space delimited. Should be used with --interface", 0,
     "list"],
    ["ipv6_static_routes", [], 0, "IPv6 Static Routes", True, "Should be used with --interface", 0, "list"],
    ["mac_address", "", 0, "MAC Address", True, "(Place \"random\" in this field for a random MAC Address.)", 0, "str"],
    ["management", False, 0, "Management Interface", True,
     "Is this the management interface? Should be used with --interface", 0, "bool"],
    ["mtu", "", 0, "MTU", True, "", 0, "str"],
    ["netmask", "", 0, "Subnet Mask", True, "Should be used with --interface", 0, "str"],
    ["static", False, 0, "Static", True, "Is this interface static? Should be used with --interface", 0, "bool"],
    ["static_routes", [], 0, "Static Routes", True, "Should be used with --interface", 0, "list"],
    ["virt_bridge", "", 0, "Virt Bridge", True, "Should be used with --interface", 0, "str"],
]

SETTINGS_FIELDS = [
    ["name", "", "", "Name", True, "Ex: server", 0, "str"],
    ["value", "", "", "Value", True, "Ex: 127.0.0.1", 0, "str"],
]


####################################################

def to_string_from_fields(item_dict, fields, interface_fields=None) -> str:
    """
    item_dict is a dictionary, fields is something like item_distro.FIELDS
    :param item_dict: The dictionary representation of a Cobbler item.
    :param fields: This is the list of fields a Cobbler item has.
    :param interface_fields: This is the list of fields from a network interface of a system. This is optional.
    :return: The string representation of a Cobbler item with all its values.
    """
    buf = ""
    keys = []
    for elem in fields:
        keys.append((elem[0], elem[3], elem[4]))
    keys.sort()
    buf += "%-30s : %s\n" % ("Name", item_dict["name"])
    for (k, nicename, editable) in keys:
        # FIXME: supress fields users don't need to see?
        # FIXME: interfaces should be sorted
        # FIXME: print ctime, mtime nicely
        if not editable:
            continue

        if k != "name":
            # FIXME: move examples one field over, use description here.
            buf += "%-30s : %s\n" % (nicename, item_dict[k])

    # somewhat brain-melting special handling to print the dicts
    # inside of the interfaces more neatly.
    if "interfaces" in item_dict and interface_fields is not None:
        keys = []
        for elem in interface_fields:
            keys.append((elem[0], elem[3], elem[4]))
        keys.sort()
        for iname in list(item_dict["interfaces"].keys()):
            # FIXME: inames possibly not sorted
            buf += "%-30s : %s\n" % ("Interface ===== ", iname)
            for (k, nicename, editable) in keys:
                if editable:
                    buf += "%-30s : %s\n" % (nicename, item_dict["interfaces"][iname].get(k, ""))

    return buf


def report_items(remote, otype: str):
    """
    Return all items for a given collection.

    :param remote: The remote to use as the query-source. The remote to use as the query-source.
    :param otype: The object type to query.
    """
    if otype == "setting":
        items = remote.get_settings()
        keys = list(items.keys())
        keys.sort()
        for key in keys:
            item = {'name': key, 'value': items[key]}
            report_item(remote, otype, item=item)
    elif otype == "signature":
        items = remote.get_signatures()
        total_breeds = 0
        total_sigs = 0
        if "breeds" in items:
            print("Currently loaded signatures:")
            bkeys = list(items["breeds"].keys())
            bkeys.sort()
            total_breeds = len(bkeys)
            for breed in bkeys:
                total_sigs += report_single_breed(breed, items)
            print("\n%d breeds with %d total signatures loaded" % (total_breeds, total_sigs))
        else:
            print("No breeds found in the signature, a signature update is recommended")
            return 1
    else:
        items = remote.get_items(otype)
        for x in items:
            report_item(remote, otype, item=x)


def report_single_breed(name: str, items: dict) -> int:
    """
    Helper function which prints a single signature breed list to the terminal.
    """
    new_sigs = 0
    print("%s:" % name)
    oskeys = list(items["breeds"][name].keys())
    oskeys.sort()
    if len(oskeys) > 0:
        new_sigs = len(oskeys)
        for osversion in oskeys:
            print("\t%s" % osversion)
    else:
        print("\t(none)")
    return new_sigs


def report_item(remote, otype: str, item=None, name=None):
    """
    Return a single item in a given collection. Either this is an item object or this method searches for a name.

    :param remote: The remote to use as the query-source.
    :param otype: The object type to query.
    :param item: The item to display
    :param name: The name to search for and display.
    """
    if item is None:
        if otype == "setting":
            cur_settings = remote.get_settings()
            try:
                item = {'name': name, 'value': cur_settings[name]}
            except:
                print("Setting not found: %s" % name)
                return 1
        elif otype == "signature":
            items = remote.get_signatures()
            total_sigs = 0
            if "breeds" in items:
                print("Currently loaded signatures:")
                if name in items["breeds"]:
                    total_sigs += report_single_breed(name, items)
                    print("\nBreed '%s' has %d total signatures" % (name, total_sigs))
                else:
                    print("No breed named '%s' found" % name)
                    return 1
            else:
                print("No breeds found in the signature, a signature update is recommended")
                return 1
            return
        else:
            item = remote.get_item(otype, name)
            if item == "~":
                print("No %s found: %s" % (otype, name))
                return 1

    if otype == "distro":
        data = to_string_from_fields(item, DISTRO_FIELDS)
    elif otype == "profile":
        data = to_string_from_fields(item, PROFILE_FIELDS)
    elif otype == "system":
        data = to_string_from_fields(item, SYSTEM_FIELDS, NETWORK_INTERFACE_FIELDS)
    elif otype == "repo":
        data = to_string_from_fields(item, REPO_FIELDS)
    elif otype == "image":
        data = to_string_from_fields(item, IMAGE_FIELDS)
    elif otype == "mgmtclass":
        data = to_string_from_fields(item, MGMTCLASS_FIELDS)
    elif otype == "package":
        data = to_string_from_fields(item, PACKAGE_FIELDS)
    elif otype == "file":
        data = to_string_from_fields(item, FILE_FIELDS)
    elif otype == "menu":
        data = to_string_from_fields(item, MENU_FIELDS)
    elif otype == "setting":
        data = "%-40s: %s" % (item['name'], item['value'])
    else:
        data = "Unknown item type selected!"
    print(data)


def list_items(remote, otype):
    """
    List all items of a given object type and print it to stdout.

    :param remote: The remote to use as the query-source.
    :param otype: The object type to query.
    """
    items = remote.get_item_names(otype)
    items.sort()
    for x in items:
        print("   %s" % x)


def n2s(data):
    """
    Return spaces for None

    :param data: The data to check for.
    :return: The data itself or an empty string.
    """
    if data is None:
        return ""
    return data


def opt(options, k, defval=""):
    """
    Returns an option from an Optparse values instance

    :param options: The options object to search in.
    :param k: The key which is in the optparse values instance.
    :param defval: The default value to return.
    :return: The value for the specified key.
    """
    try:
        data = getattr(options, k)
    except:
        # FIXME: debug only
        # traceback.print_exc()
        return defval
    return n2s(data)


def _add_parser_option_from_field(parser, field, settings):
    """
    Add options from a field dynamically to an optparse instance.

    :param parser: The optparse instance to add the options to.
    :param field: The field to parse.
    :param settings: Global cobbler settings as returned from ``CollectionManager.settings()``
    """
    # extract data from field dictionary
    name = field[0]
    default = field[1]
    if isinstance(default, str) and default.startswith("SETTINGS:"):
        setting_name = default.replace("SETTINGS:", "", 1)
        default = settings[setting_name]
    description = field[3]
    tooltip = field[5]
    choices = field[6]
    if choices and default not in choices:
        raise Exception("field %s default value (%s) is not listed in choices (%s)" % (name, default, str(choices)))
    if tooltip != "":
        description += " (%s)" % tooltip

    # generate option string
    option_string = "--%s" % name.replace("_", "-")

    # add option to parser
    if isinstance(choices, list) and len(choices) != 0:
        description += " (valid options: %s)" % ",".join(choices)
        parser.add_option(option_string, dest=name, help=description, choices=choices)
    else:
        parser.add_option(option_string, dest=name, help=description)


def add_options_from_fields(object_type, parser, fields, network_interface_fields, settings, object_action):
    """
    Add options to the command line from the fields queried from the Cobbler server.

    :param object_type: The object type to add options for.
    :param parser: The optparse instance to add options to.
    :param fields: The list of fields to add options for.
    :param network_interface_fields: The list of network interface fields if the object type is a system.
    :param settings: Global cobbler settings as returned from ``CollectionManager.settings()``
    :param object_action: The object action to add options for. May be "add", "edit", "find", "copy", "rename",
                          "remove". If none of these options is given then this method does nothing.
    """
    if object_action in ["add", "edit", "find", "copy", "rename"]:
        for field in fields:
            _add_parser_option_from_field(parser, field, settings)

        # system object
        if object_type == "system":
            for field in network_interface_fields:
                _add_parser_option_from_field(parser, field, settings)

            parser.add_option("--interface", dest="interface", help="the interface to operate on (can only be "
                                                                    "specified once per command line)")
            if object_action in ["add", "edit"]:
                parser.add_option("--delete-interface", dest="delete_interface", action="store_true")
                parser.add_option("--rename-interface", dest="rename_interface")

        if object_action in ["copy", "rename"]:
            parser.add_option("--newname", help="new object name")

        if object_action not in ["find"] and object_type != "setting":
            parser.add_option("--in-place", action="store_true", dest="in_place",
                              help="edit items in kopts or autoinstall without clearing the other items")

    elif object_action == "remove":
        parser.add_option("--name", help="%s name to remove" % object_type)
        parser.add_option("--recursive", action="store_true", dest="recursive", help="also delete child objects")


def get_comma_separated_args(option: optparse.Option, opt_str, value: str, parser: optparse.OptionParser):
    """
    Simple callback function to achieve option split with comma.

    Reference for the method signature can be found at:
      https://docs.python.org/3/library/optparse.html#defining-a-callback-option

    :param option: The option the callback is executed for
    :param opt_str: Unused for this callback function. Would be the extended option if the user used the short version.
    :param value: The value which should be split by comma.
    :param parser: The optparse instance which the callback should be added to.
    """
    # TODO: Migrate to argparse
    if not isinstance(option, optparse.Option):
        raise optparse.OptionValueError("Option is not an optparse.Option object!")
    if not isinstance(value, str):
        raise optparse.OptionValueError("Value is not a string!")
    if not isinstance(parser, optparse.OptionParser):
        raise optparse.OptionValueError("Parser is not an optparse.OptionParser object!")
    setattr(parser.values, str(option.dest), value.split(','))


class CobblerCLI:
    """
    Main CLI Class which contains the logic to communicate with the Cobbler Server.
    """

    def __init__(self, cliargs):
        """
        The constructor to create a Cobbler CLI.
        """
        # Load server ip and ports from local config
        self.url_cobbler_api = utils.local_get_cobbler_api_url()
        self.url_cobbler_xmlrpc = utils.local_get_cobbler_xmlrpc_url()

        # FIXME: allow specifying other endpoints, and user+pass
        self.parser = optparse.OptionParser()
        self.remote = xmlrpc.client.Server(self.url_cobbler_api)
        self.shared_secret = utils.get_shared_secret()
        self.args = cliargs

    def start_task(self, name: str, options: dict) -> str:
        r"""
        Start an asynchronous task in the background.

        :param name: "background\_" % name function must exist in remote.py. This function will be called in a
                      subthread.
        :param options: Dictionary of options passed to the newly started thread
        :return: Id of the newly started task
        """
        options = utils.strip_none(vars(options), omit_none=True)
        fn = getattr(self.remote, "background_%s" % name)
        return fn(options, self.token)

    def get_object_type(self, args) -> Optional[str]:
        """
        If this is a CLI command about an object type, e.g. "cobbler distro add", return the type, like "distro"

        :param args: The args from the CLI.
        :return: The object type or None
        """
        if len(args) < 2:
            return None
        elif args[1] in OBJECT_TYPES:
            return args[1]
        return None

    def get_object_action(self, object_type, args) -> Optional[str]:
        """
        If this is a CLI command about an object type, e.g. "cobbler distro add", return the action, like "add"

        :param object_type: The object type.
        :param args: The args from the CLI.
        :return: The action or None.
        """
        if object_type is None or len(args) < 3:
            return None
        if args[2] in OBJECT_ACTIONS_MAP[object_type]:
            return args[2]
        return None

    def get_direct_action(self, object_type, args) -> Optional[str]:
        """
        If this is a general command, e.g. "cobbler hardlink", return the action, like "hardlink"

        :param object_type: Must be None or None is returned.
        :param args: The arg from the CLI.
        :return: The action key, "version" or None.
        """
        if object_type is not None:
            return None
        elif len(args) < 2:
            return None
        elif args[1] == "--help":
            return None
        elif args[1] == "--version":
            return "version"
        else:
            return args[1]

    def check_setup(self) -> int:
        """
        Detect permissions and service accessibility problems and provide nicer error messages for them.
        """

        with xmlrpc.client.ServerProxy(self.url_cobbler_xmlrpc) as s:
            try:
                s.ping()
            except Exception as e:
                print("cobblerd does not appear to be running/accessible: %s" % repr(e), file=sys.stderr)
                return 411

        with xmlrpc.client.ServerProxy(self.url_cobbler_api) as s:
            try:
                s.ping()
            except:
                print("httpd does not appear to be running and proxying Cobbler, or SELinux is in the way. Original "
                      "traceback:", file=sys.stderr)
                traceback.print_exc()
                return 411

        if not os.path.exists("/var/lib/cobbler/web.ss"):
            print("Missing login credentials file.  Has cobblerd failed to start?", file=sys.stderr)
            return 411

        if not os.access("/var/lib/cobbler/web.ss", os.R_OK):
            print("User cannot run command line, need read access to /var/lib/cobbler/web.ss", file=sys.stderr)
            return 411

        return 0

    def run(self, args) -> int:
        """
        Process the command line and do what the user asks.

        :param args: The args of the CLI
        """
        self.token = self.remote.login("", self.shared_secret)
        object_type = self.get_object_type(args)
        object_action = self.get_object_action(object_type, args)
        direct_action = self.get_direct_action(object_type, args)

        try:
            if object_type is not None:
                if object_action is not None:
                    return self.object_command(object_type, object_action)
                else:
                    return self.print_object_help(object_type)
            elif direct_action is not None:
                return self.direct_command(direct_action)
            else:
                return self.print_help()
        except xmlrpc.client.Fault as err:
            if err.faultString.find("cobbler.cexceptions.CX") != -1:
                print(self.cleanup_fault_string(err.faultString))
            else:
                print("### ERROR ###")
                print("Unexpected remote error, check the server side logs for further info")
                print(err.faultString)
            return 1

    def cleanup_fault_string(self, fault_str: str) -> str:
        """
        Make a remote exception nicely readable by humans so it's not evident that is a remote fault. Users should not
        have to understand tracebacks.

        :param fault_str: The stacktrace to niceify.
        :return: A nicer error messsage.
        """
        if fault_str.find(">:") != -1:
            (first, rest) = fault_str.split(">:", 1)
            if rest.startswith("\"") or rest.startswith("\'"):
                rest = rest[1:]
            if rest.endswith("\"") or rest.endswith("\'"):
                rest = rest[:-1]
            return rest
        else:
            return fault_str

    def get_fields(self, object_type: str) -> list:
        """
        For a given name of an object type, return the FIELDS data structure.

        :param object_type: The object to return the fields of.
        :return: The fields or None
        """
        if object_type == "distro":
            return DISTRO_FIELDS
        elif object_type == "profile":
            return PROFILE_FIELDS
        elif object_type == "system":
            return SYSTEM_FIELDS
        elif object_type == "repo":
            return REPO_FIELDS
        elif object_type == "image":
            return IMAGE_FIELDS
        elif object_type == "mgmtclass":
            return MGMTCLASS_FIELDS
        elif object_type == "package":
            return PACKAGE_FIELDS
        elif object_type == "file":
            return FILE_FIELDS
        elif object_type == "menu":
            return MENU_FIELDS
        elif object_type == "setting":
            return SETTINGS_FIELDS
        return []

    def object_command(self, object_type: str, object_action: str) -> int:
        """
        Process object-based commands such as "distro add" or "profile rename"

        :param object_type: The object type to execute an action for.
        :param object_action: The action to execute.
        :return: Depending on the object and action.
        :raises NotImplementedError:
        :raises RuntimeError:
        """
        # if assigned, we must tail the logfile
        task_id = INVALID_TASK
        settings = self.remote.get_settings()

        fields = self.get_fields(object_type)
        network_interface_fields = None
        if object_type == "system":
            network_interface_fields = NETWORK_INTERFACE_FIELDS
        if object_action in ["add", "edit", "copy", "rename", "find", "remove"]:
            add_options_from_fields(object_type, self.parser, fields,
                                    network_interface_fields, settings, object_action)
        elif object_action in ["list", "autoadd"]:
            pass
        elif object_action not in ("reload", "update"):
            self.parser.add_option("--name", dest="name", help="name of object")
        elif object_action == "reload":
            self.parser.add_option("--filename", dest="filename", help="filename to load data from")
        (options, args) = self.parser.parse_args(self.args)

        # the first three don't require a name
        if object_action == "report":
            if options.name is not None:
                report_item(self.remote, object_type, None, options.name)
            else:
                report_items(self.remote, object_type)
        elif object_action == "list":
            list_items(self.remote, object_type)
        elif object_action == "find":
            items = self.remote.find_items(object_type, utils.strip_none(vars(options), omit_none=True), "name", False)
            for item in items:
                print(item)
        elif object_action == "autoadd" and object_type == "repo":
            try:
                self.remote.auto_add_repos(self.token)
            except xmlrpc.client.Fault as err:
                (_, emsg) = err.faultString.split(":", 1)
                print("exception on server: %s" % emsg)
                return 1
        elif object_action in OBJECT_ACTIONS:
            if opt(options, "name") == "" and object_action not in ("reload", "update"):
                print("--name is required")
                return 1
            if object_action in ["add", "edit", "copy", "rename", "remove"]:
                try:
                    if object_type == "setting":
                        settings = self.remote.get_settings()
                        if options.value is None:
                            raise RuntimeError("You must specify a --value when editing a setting")
                        elif not settings.get('allow_dynamic_settings', False):
                            raise RuntimeError("Dynamic settings changes are not enabled. Change the "
                                               "allow_dynamic_settings to True and restart cobblerd to enable dynamic "
                                               "settings changes")
                        elif options.name == 'allow_dynamic_settings':
                            raise RuntimeError("Cannot modify that setting live")
                        elif self.remote.modify_setting(options.name, options.value, self.token):
                            raise RuntimeError("Changing the setting failed")
                    else:
                        self.remote.xapi_object_edit(object_type, options.name, object_action,
                                                     utils.strip_none(vars(options), omit_none=True), self.token)
                except xmlrpc.client.Fault as error:
                    (_, emsg) = error.faultString.split(":", 1)
                    print("exception on server: %s" % emsg)
                    return 1
                except RuntimeError as error:
                    print(error.args[0])
                    return 1
            elif object_action == "get-autoinstall":
                if object_type == "profile":
                    data = self.remote.generate_profile_autoinstall(options.name)
                elif object_type == "system":
                    data = self.remote.generate_system_autoinstall(options.name)
                else:
                    print('Invalid object type selected! Allowed are "profile" and "system".')
                    return 1
                print(data)
            elif object_action == "dumpvars":
                if object_type == "profile":
                    data = self.remote.get_blended_data(options.name, "")
                elif object_type == "system":
                    data = self.remote.get_blended_data("", options.name)
                else:
                    print('Invalid object type selected! Allowed are "profile" and "system".')
                    return 1
                # FIXME: pretty-printing and sorting here
                keys = list(data.keys())
                keys.sort()
                for x in keys:
                    print("%s: %s" % (x, data[x]))
            elif object_action in ["poweron", "poweroff", "powerstatus", "reboot"]:
                power = {
                    "power": object_action.replace("power", ""),
                    "systems": [options.name]
                }
                task_id = self.remote.background_power_system(power, self.token)
            elif object_action == "update":
                task_id = self.remote.background_signature_update(utils.strip_none(vars(options), omit_none=True),
                                                                  self.token)
            elif object_action == "reload":
                filename = opt(options, "filename", "/var/lib/cobbler/distro_signatures.json")
                try:
                    utils.load_signatures(filename, cache=True)
                except:
                    print("There was an error loading the signature data in %s." % filename)
                    print("Please check the JSON file or run 'cobbler signature update'.")
                    return 1
                else:
                    print("Signatures were successfully loaded")
            else:
                raise NotImplementedError()
        else:
            raise NotImplementedError()

        # FIXME: add tail/polling code here
        if task_id != INVALID_TASK:
            self.print_task(task_id)
            return self.follow_task(task_id)

        return 0

    def direct_command(self, action_name: str):
        """
        Process non-object based commands like "sync" and "hardlink".

        :param action_name: The action to execute.
        :return: Depending on the action.
        """
        task_id = INVALID_TASK

        self.parser.set_usage('Usage: %%prog %s [options]' % (action_name))

        if action_name == "buildiso":

            defaultiso = os.path.join(os.getcwd(), "generated.iso")
            self.parser.add_option("--iso", dest="iso", default=defaultiso, help="(OPTIONAL) output ISO to this file")
            self.parser.add_option("--profiles", dest="profiles", help="(OPTIONAL) use these profiles only")
            self.parser.add_option("--systems", dest="systems", help="(OPTIONAL) use these systems only")
            self.parser.add_option("--tempdir", dest="buildisodir", help="(OPTIONAL) working directory")
            self.parser.add_option("--distro", dest="distro", help="(OPTIONAL) used with --standalone and --airgapped "
                                                                   "to create a distro-based ISO including all "
                                                                   "associated profiles/systems")
            self.parser.add_option("--standalone", dest="standalone", action="store_true",
                                   help="(OPTIONAL) creates a standalone ISO with all required distro files, "
                                        "but without any added repos")
            self.parser.add_option("--airgapped", dest="airgapped", action="store_true",
                                   help="(OPTIONAL) creates a standalone ISO with all distro and repo files for "
                                        "disconnected system installation")
            self.parser.add_option("--source", dest="source", help="(OPTIONAL) used with --standalone to specify a "
                                                                   "source for the distribution files")
            self.parser.add_option("--exclude-dns", dest="exclude_dns", action="store_true",
                                   help="(OPTIONAL) prevents addition of name server addresses to the kernel boot "
                                        "options")
            self.parser.add_option("--mkisofs-opts", dest="mkisofs_opts", help="(OPTIONAL) extra options for mkisofs")

            (options, args) = self.parser.parse_args(self.args)
            task_id = self.start_task("buildiso", options)

        elif action_name == "replicate":
            self.parser.add_option("--master", dest="master", help="Cobbler server to replicate from.")
            self.parser.add_option("--port", dest="port", help="Remote port.")
            self.parser.add_option("--distros", dest="distro_patterns", help="patterns of distros to replicate")
            self.parser.add_option("--profiles", dest="profile_patterns", help="patterns of profiles to replicate")
            self.parser.add_option("--systems", dest="system_patterns", help="patterns of systems to replicate")
            self.parser.add_option("--repos", dest="repo_patterns", help="patterns of repos to replicate")
            self.parser.add_option("--image", dest="image_patterns", help="patterns of images to replicate")
            self.parser.add_option("--mgmtclasses", dest="mgmtclass_patterns",
                                   help="patterns of mgmtclasses to replicate")
            self.parser.add_option("--packages", dest="package_patterns", help="patterns of packages to replicate")
            self.parser.add_option("--files", dest="file_patterns", help="patterns of files to replicate")
            self.parser.add_option("--omit-data", dest="omit_data", action="store_true", help="do not rsync data")
            self.parser.add_option("--sync-all", dest="sync_all", action="store_true", help="sync all data")
            self.parser.add_option("--prune", dest="prune", action="store_true",
                                   help="remove objects (of all types) not found on the master")
            self.parser.add_option("--use-ssl", dest="use_ssl", action="store_true",
                                   help="use ssl to access the Cobbler master server api")
            (options, args) = self.parser.parse_args(self.args)
            task_id = self.start_task("replicate", options)

        elif action_name == "aclsetup":
            self.parser.add_option("--adduser", dest="adduser", help="give acls to this user")
            self.parser.add_option("--addgroup", dest="addgroup", help="give acls to this group")
            self.parser.add_option("--removeuser", dest="removeuser", help="remove acls from this user")
            self.parser.add_option("--removegroup", dest="removegroup", help="remove acls from this group")
            (options, args) = self.parser.parse_args(self.args)
            task_id = self.start_task("aclsetup", options)

        elif action_name == "version":
            version = self.remote.extended_version()
            print("Cobbler %s" % version["version"])
            print("  source: %s, %s" % (version["gitstamp"], version["gitdate"]))
            print("  build time: %s" % version["builddate"])

        elif action_name == "hardlink":
            (options, args) = self.parser.parse_args(self.args)
            task_id = self.start_task("hardlink", options)
        elif action_name == "status":
            (options, args) = self.parser.parse_args(self.args)
            print(self.remote.get_status("text", self.token))
        elif action_name == "validate-autoinstalls":
            (options, args) = self.parser.parse_args(self.args)
            task_id = self.start_task("validate_autoinstall_files", options)
        elif action_name == "import":
            self.parser.add_option("--arch", dest="arch", help="OS architecture being imported")
            self.parser.add_option("--breed", dest="breed", help="the breed being imported")
            self.parser.add_option("--os-version", dest="os_version", help="the version being imported")
            self.parser.add_option("--path", dest="path", help="local path or rsync location")
            self.parser.add_option("--name", dest="name", help="name, ex 'RHEL-5'")
            self.parser.add_option("--available-as", dest="available_as", help="tree is here, don't mirror")
            self.parser.add_option("--autoinstall", dest="autoinstall_file", help="assign this autoinstall file")
            self.parser.add_option("--rsync-flags", dest="rsync_flags", help="pass additional flags to rsync")
            (options, args) = self.parser.parse_args(self.args)
            if options.path and "rsync://" not in options.path:
                # convert relative path to absolute path
                options.path = os.path.abspath(options.path)
            task_id = self.start_task("import", options)
        elif action_name == "reposync":
            self.parser.add_option("--only", dest="only", help="update only this repository name")
            self.parser.add_option("--tries", dest="tries", help="try each repo this many times", default=1)
            self.parser.add_option("--no-fail", dest="nofail", help="don't stop reposyncing if a failure occurs",
                                   action="store_true")
            (options, args) = self.parser.parse_args(self.args)
            task_id = self.start_task("reposync", options)
        elif action_name == "check":
            results = self.remote.check(self.token)
            ct = 0
            if len(results) > 0:
                print("The following are potential configuration items that you may want to fix:\n")
                for r in results:
                    ct += 1
                    print("%s: %s" % (ct, r))
                print("\nRestart cobblerd and then run 'cobbler sync' to apply changes.")
            else:
                print("No configuration problems found.  All systems go.")

        elif action_name == "sync":
            self.parser.add_option("--verbose", dest="verbose", action="store_true",
                                   help="run sync with more output")
            self.parser.add_option("--dhcp", dest="dhcp", action="store_true",
                                   help="write DHCP config files and restart service")
            self.parser.add_option("--dns", dest="dns", action="store_true",
                                   help="write DNS config files and restart service")
            self.parser.add_option("--systems", dest="systems", type='string', action="callback",
                                   callback=get_comma_separated_args,
                                   help="run a sync only on specified systems")
            # ToDo: Add tftp syncing when it's cleaned up
            (options, args) = self.parser.parse_args(self.args)
            if options.systems is not None:
                task_id = self.start_task("syncsystems", options)
            else:
                task_id = self.start_task("sync", options)
        elif action_name == "report":
            (options, args) = self.parser.parse_args(self.args)
            print("distros:\n==========")
            report_items(self.remote, "distro")
            print("\nprofiles:\n==========")
            report_items(self.remote, "profile")
            print("\nsystems:\n==========")
            report_items(self.remote, "system")
            print("\nrepos:\n==========")
            report_items(self.remote, "repo")
            print("\nimages:\n==========")
            report_items(self.remote, "image")
            print("\nmgmtclasses:\n==========")
            report_items(self.remote, "mgmtclass")
            print("\npackages:\n==========")
            report_items(self.remote, "package")
            print("\nfiles:\n==========")
            report_items(self.remote, "file")
            print("\nmenus:\n==========")
            report_items(self.remote, "menu")
        elif action_name == "list":
            # no tree view like 1.6?  This is more efficient remotely
            # for large configs and prevents xfering the whole config
            # though we could consider that...
            (options, args) = self.parser.parse_args(self.args)
            print("distros:")
            list_items(self.remote, "distro")
            print("\nprofiles:")
            list_items(self.remote, "profile")
            print("\nsystems:")
            list_items(self.remote, "system")
            print("\nrepos:")
            list_items(self.remote, "repo")
            print("\nimages:")
            list_items(self.remote, "image")
            print("\nmgmtclasses:")
            list_items(self.remote, "mgmtclass")
            print("\npackages:")
            list_items(self.remote, "package")
            print("\nfiles:")
            list_items(self.remote, "file")
            print("\nmenus:")
            list_items(self.remote, "menu")
        elif action_name == "mkloaders":
            (options, _) = self.parser.parse_args(self.args)
            task_id = self.start_task("mkloaders", options)
        else:
            print("No such command: %s" % action_name)
            return 1

        # FIXME: add tail/polling code here
        if task_id != INVALID_TASK:
            self.print_task(task_id)
            return self.follow_task(task_id)

        return 0

    def print_task(self, task_id):
        """
        Pretty print a task executed on the server. This prints to stdout.

        :param task_id: The id of the task to be pretty printed.
        """
        print("task started: %s" % task_id)
        events = self.remote.get_events()
        (etime, name, status, who_viewed) = events[task_id]
        atime = time.asctime(time.localtime(etime))
        print("task started (id=%s, time=%s)" % (name, atime))

    def follow_task(self, task_id):
        """
        Parse out this task's specific messages from the global log

        :param task_id: The id of the task to follow.
        """
        logfile = "/var/log/cobbler/cobbler.log"
        # adapted from:  http://code.activestate.com/recipes/157035/
        with open(logfile, 'r') as file:
            # Find the size of the file and move to the end
            # st_results = os.stat(filename)
            # st_size = st_results[6]
            # file.seek(st_size)

            while 1:
                where = file.tell()
                line = file.readline()
                if not line.startswith("[" + task_id + "]"):
                    continue
                if line.find("### TASK COMPLETE ###") != -1:
                    print("*** TASK COMPLETE ***")
                    return 0
                if line.find("### TASK FAILED ###") != -1:
                    print("!!! TASK FAILED !!!")
                    return 1
                if not line:
                    time.sleep(1)
                    file.seek(where)
                else:
                    if line.find(" | "):
                        line = line.split(" | ")[-1]
                    print(line, end='')

    def print_object_help(self, object_type) -> int:
        """
        Prints the subcommands for a given object, e.g. "cobbler distro --help"

        :param object_type: The object type to print the help for.
        """
        commands = OBJECT_ACTIONS_MAP[object_type]
        commands.sort()
        print("usage\n=====")
        for c in commands:
            print("cobbler %s %s" % (object_type, c))
        return 2

    def print_help(self) -> int:
        """
        Prints general-top level help, e.g. "cobbler --help" or "cobbler" or "cobbler command-does-not-exist"
        """
        print("usage\n=====")
        print("cobbler <distro|profile|system|repo|image|mgmtclass|package|file|menu> ... ")
        print("        [add|edit|copy|get-autoinstall*|list|remove|rename|report] [options|--help]")
        print("cobbler setting [edit|report]")
        print("cobbler <%s> [options|--help]" % "|".join(DIRECT_ACTIONS))
        return 2


def main() -> int:
    """
    CLI entry point
    """
    cli = CobblerCLI(sys.argv)
    return_code = cli.check_setup()
    if return_code != 0:
        return return_code
    return_code = cli.run(sys.argv)
    if return_code is None:
        return 0
    return return_code


if __name__ == "__main__":
    sys.exit(main())
