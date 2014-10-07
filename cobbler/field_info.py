"""
Describes additional properties of cobbler fields otherwise
defined in item_*.py.  These values are common to all versions
of the fields, so they don't have to be repeated in each file.

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
    "*interface_type",
    "arch",
    "autoinstall",
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
]

# fields that should use the checkbox in the web app

USES_CHECKBOX = [
    "*management",
    "*netboot_enabled",
    "*repos_enabled",
    "*static",
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
]

# select killed the radio button
# we should not make anything use a radio button, we hate radio buttons.

USES_RADIO = [
]

# this is the map of what color to color code each field type.
# it may also be used to expand/collapse certain web elements as a set.

BLOCK_MAPPINGS = {
    "*bonding_opts": "Networking",
    "*bridge_opts": "Networking",
    "*cnames": "Networking",
    "*dhcp_tag": "Networking",
    "*dns_name": "Networking",
    "*if_gateway": "Networking",
    "*interface_master": "Networking",
    "*interface_type": "Networking",
    "*ip_address": "Networking",
    "*ipv6_address": "Networking",
    "*ipv6_default_gateway": "Networking",
    "*ipv6_mtu": "Networking",
    "*ipv6_prefix": "Networking",
    "*ipv6_secondaries": "Networking",
    "*ipv6_static_routes": "Networking",
    "*mac_address": "Networking",
    "*management": "Networking",
    "*mtu": "Networking",
    "*netmask": "Networking",
    "*static": "Networking",
    "*static_routes": "Networking",
    "*virt_bridge": "Networking",
    "*virt_cpus": "Virtualization",
    "*virt_disk": "Virtualization",
    "*virt_disk_driver": "Virtualization",
    "*virt_file_size": "Virtualization",
    "*virt_path": "Virtualization",
    "*virt_ram": "Virtualization",
    "*virt_type": "Virtualization",
    "address": "Networking",         # from network
    "apt_components": "Advanced",
    "apt_dists": "Advanced",
    "boot_files": "Management",
    "broadcast": "Networking",       # ..
    "cidr": "Networking",            # ditto
    "createrepo_flags": "Advanced",
    "dhcp_tag": "Advanced",
    "enable_gpxe": "Advanced",
    "environment": "Advanced",
    "fetchable_files": "Management",
    "files": "Resources",
    "gateway": "Networking (Global)",
    "hostname": "Networking (Global)",
    "ipv6_autoconfiguration": "Networking (Global)",
    "ipv6_default_device": "Networking (Global)",
    "mgmt_classes": "Management",
    "mgmt_parameters": "Management",
    "mirror_locally": "Advanced",
    "name_servers": "Networking (Global)",
    "name_servers_search": "Networking (Global)",
    "next_server": "Advanced",
    "packages": "Resources",
    "power_address": "Power Management",
    "power_id": "Power Management",
    "power_pass": "Power Management",
    "power_type": "Power Management",
    "power_user": "Power Management",
    "priority": "Advanced",
    "proxy": "General",
    "repos": "General",
    "repos_enabled": "Management",
    "reserved": "Networking",        # ..
    "server": "Advanced",
    "template_files": "Management",
    "virt_auto_boot": "Virtualization",
    "virt_bridge": "Virtualization",
    "virt_cpus": "Virtualization",
    "virt_disk": "Virtualization",
    "virt_disk_driver": "Virtualization",
    "virt_file_size": "Virtualization",
    "virt_group": "Virtualization",
    "virt_guests": "Virtualization",
    "virt_host": "Virtualization",
    "virt_path": "Virtualization",
    "virt_pxe_boot": "Virtualization",
    "virt_ram": "Virtualization",
    "virt_type": "Virtualization",
    "yumopts": "Advanced",
}

BLOCK_MAPPINGS_ORDER = {
    "General": 0,
    "Advanced": 1,
    "Networking (Global)": 2,
    "Networking": 3,
    "Management": 4,
    "Virtualization": 5,
    "Power Management": 6,
    "Resources": 7,
}

# Certain legacy fields need to have different CLI options than the direct translation of their
# name in the FIELDS data structure.  We should not add any more of these under any conditions.

ALTERNATE_OPTIONS = {
    "kernel_options": "--kopts",
    "kernel_options_post": "--kopts-post",
}


# Deprecated fields that have been renamed, but we need to account for them appearing in older
# datastructs that may not have been saved since the code change

DEPRECATED_FIELDS = {
}
