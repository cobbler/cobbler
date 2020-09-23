"""
Describes additional web UI properties of Cobbler fields defined in item_*.py.

Copyright 2009, Red Hat, Inc and Others
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

# fields that display as a text area in the web app
# note: not the same as a text field, this is the big one.

USES_TEXTAREA = [
    "boot_files",
    "comment",
    "fetchable_files",
    "mgmt_parameters",
    "template_files",
]

# fields that use a multi select in the web app

USES_MULTI_SELECT = [
    "files",
    "mgmt_classes",
    "packages",
    "repos",
]

# fields that use a select in the web app

USES_SELECT = [
    "arch",
    "autoinstall",
    "boot_loader",
    "breed",
    "distro",
    "image",
    "image_type",
    "os_version",
    "parent",
    "power_type",
    "profile",
    "status",
    "virt_type",

    # network interface specific
    "interface_type",
]

# fields that should use the checkbox in the web app

USES_CHECKBOX = [
    "enable_gpxe",
    "enable_menu",
    "ipv6_autoconfiguration",
    "is_definition",
    "keep_updated",
    "management",
    "mirror_locally",
    "netboot_enabled",
    "repos_enabled",
    "virt_auto_boot",
    "virt_pxe_boot",

    # network interface specific
    "management",
    "netboot_enabled",
    "repos_enabled",
    "static",
]

# select killed the radio button
# we should not make anything use a radio button, we hate radio buttons.

USES_RADIO = [
]

# UI fields grouped by section
DISTRO_UI_FIELDS_MAPPING = [
    {"General": ["name", "owners", "kernel", "initrd", "kernel_options",
                 "kernel_options_post", "autoinstall_meta", "arch", "breed",
                 "os_version", "boot_loader", "comment"]},
    {"Management": ["mgmt_classes", "boot_files", "fetchable_files",
                    "template_files"]},
]

FILE_UI_FIELDS_MAPPING = [
    {"General": ["name", "owners", "is_dir", "action", "group", "mode",
                 "owner", "path", "template", "comment"]}
]

IMAGE_UI_FIELDS_MAPPING = [
    {"General": ["name", "owners", "arch", "breed", "file", "image_type",
                 "network_count", "os_version", "autoinstall", "comment"]},
    {"Virtualization": ["virt_auto_boot", "virt_bridge", "virt_cpus",
                        "virt_file_size", "virt_disk_driver", "virt_path",
                        "virt_ram", "virt_type"]}
]

MGMTCLASS_UI_FIELDS_MAPPING = [
    {"General": ["name", "owners", "class_name", "is_definition", "params",
                 "comment"]},
    {"Resources": ["packages", "files"]}
]

PACKAGE_UI_FIELDS_MAPPING = [
    {"General": ["name", "owners", "action", "installer", "version",
                 "comment"]}
]

PROFILE_UI_FIELDS_MAPPING = [
    {"General": ["name", "owners", "distro", "parent", "enable_menu",
                 "autoinstall", "kernel_options", "kernel_options_post",
                 "autoinstall_meta", "proxy", "repos", "comment"]},
    {"Advanced": ["enable_gpxe", "dhcp_tag", "server", "next_server", "filename"]},
    {"Networking Global": ["name_servers", "name_servers_search"]},
    {"Management": ["mgmt_classes", "mgmt_parameters", "boot_files",
                    "fetchable_files", "template_files"]},
    {"Virtualization": ["virt_auto_boot", "virt_cpus", "virt_file_size",
                        "virt_disk_driver", "virt_ram", "virt_type",
                        "virt_path", "virt_bridge"]}
]

REPO_UI_FIELDS_MAPPING = [
    {"General": ["name", "owners", "arch", "breed", "keep_updated",
                 "mirror", "rpm_list", "comment"]},
    {"Advanced": ["apt_components", "apt_dists", "createrepo_flags",
                  "environment", "mirror_locally", "priority", "yumopts", "rsyncopts"]}
]

SYSTEM_UI_FIELDS_MAPPING = [
    {"General": ["name", "owners", "profile", "image", "status",
                 "kernel_options", "kernel_options_post",
                 "autoinstall_meta", "boot_loader", "proxy",
                 "netboot_enabled", "autoinstall", "comment"]},
    {"Advanced": ["enable_gpxe", "server", "next_server", "filename"]},
    {"Networking (Global)": ["hostname", "gateway", "name_servers",
                             "name_servers_search", "ipv6_default_device",
                             "ipv6_autoconfiguration"]},
    {"Networking": ["mac_address", "mtu", "ip_address", "interface_type",
                    "interface_master", "bonding_opts", "bridge_opts",
                    "management", "static", "netmask", "if_gateway",
                    "dhcp_tag", "dns_name", "static_routes", "virt_bridge",
                    "ipv6_address", "ipv6_prefix", "ipv6_secondaries",
                    "ipv6_mtu", "ipv6_static_routes", "ipv6_default_gateway",
                    "cnames"]},
    {"Management": ["mgmt_classes", "mgmt_parameters", "boot_files",
                    "fetchable_files", "template_files", "repos_enabled"]},
    {"Virtualization": ["virt_path", "virt_type", "virt_cpus",
                        "virt_file_size", "virt_disk_driver", "virt_ram",
                        "virt_auto_boot", "virt_pxe_boot"]},
    {"Power management": ["power_type", "power_address", "power_user",
                          "power_pass", "power_id"]}
]

SETTING_UI_FIELDS_MAPPING = [
    {"General": ["name", "value"]}
]
