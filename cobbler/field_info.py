"""
Describes additional properties of cobbler fields otherwise
defined in item_*.py.  These values are common to all versions
of the fields, so they don't have to be repeated in each file.

Copyright 2009, Red Hat, Inc
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

# fields that display as a text area in the web app
# note: not the same as a text field, this is the big one.

USES_TEXTAREA = [
   "comment",
   "mgmt_parameters",
   "template_files"
   "fetchable_files"
]

# fields that use a multi select in the web app

USES_MULTI_SELECT = [
   "repos",
   "mgmt_classes",
   "packages",
   "files",
]

# fields that use a select in the web app

USES_SELECT = [
   "profile",
   "distro",
   "image",
   "virt_type",
   "arch",
   "*bonding",
   "parent",
   "breed",
   "os_version",
]

# fields that should use the checkbox in the web app

USES_CHECKBOX = [
   "enable_menu",
   "*netboot_enabled",
   "netboot_enabled",
   "*static",
   "ipv6_autoconfiguration",
   "keep_updated",
   "mirror_locally",
   "virt_auto_boot",
   "*repos_enabled",
   "repos_enabled",
   "*ldap_enabled",
   "ldap_enabled",
   "*monit_enabled",
   "monit_enabled"
]

# select killed the radio button
# we should not make anything use a radio button, we hate radio buttons.

USES_RADIO = [
]

# this is the map of what color to color code each field type.
# it may also be used to expand/collapse certain web elements as a set.

BLOCK_MAPPINGS = {
   "virt_ram"        : "Virtualization",
   "virt_disk"       : "Virtualization",
   "virt_cpus"       : "Virtualization",
   "virt_bridge"     : "Virtualization",
   "virt_path"       : "Virtualization",
   "virt_file_size"  : "Virtualization",
   "virt_type"       : "Virtualization",
   "virt_auto_boot"  : "Virtualization",
   "virt_host"       : "Virtualization",
   "virt_group"      : "Virtualization",
   "virt_guests"     : "Virtualization",
   "*virt_ram"       : "Virtualization",
   "*virt_disk"      : "Virtualization",
   "*virt_path"      : "Virtualization",
   "*virt_cpus"      : "Virtualization",
   "*virt_bridge"    : "Networking",
   "*virt_type"      : "Virtualization",
   "*virt_file_size" : "Virtualization",
   "power_id"        : "Power",
   "power_address"   : "Power",
   "power_user"      : "Power",
   "power_pass"      : "Power",
   "power_type"      : "Power",
   "address"         : "Networking", # from network
   "cidr"            : "Networking", # ditto
   "broadcast"       : "Networking", # ..
   "reserved"        : "Networking", # ..
   "*mac_address"    : "Networking",
   "*mtu"            : "Networking",
   "*ip_address"     : "Networking",
   "*dhcp_tag"       : "Networking",
   "*static"         : "Networking",
   "*bonding"        : "Networking",
   "*bonding_opts"   : "Networking",
   "*bonding_master" : "Networking",
   "*dns_name"       : "Networking",
   "*static_routes"  : "Networking",
   "*subnet"         : "Networking",
   "*ipv6_address"   : "Networking",
   "*ipv6_secondaries"      : "Networking",
   "*ipv6_mtu"              : "Networking",
   "*ipv6_static_routes"    : "Networking",
   "*ipv6_default_gateway"  : "Networking",
   "hostname"               : "Networking (Global)",
   "gateway"                : "Networking (Global)",
   "name_servers"           : "Networking (Global)",
   "name_servers_search"    : "Networking (Global)",
   "ipv6_default_device"    : "Networking (Global)",
   "ipv6_autoconfiguration" : "Networking (Global)",
   "repos"                  : "General",
   "dhcp_tag"               : "Advanced",
   "mgmt_classes"           : "Management",
   "mgmt_parameters"        : "Management",
   "template_files"         : "Management",
   "fetchable_files"        : "Management",
   "network_widget_a"       : "Networking",
   "network_widget_b"       : "Networking",
   "server"                 : "Advanced",
   "redhat_management_key"  : "Management",
   "redhat_management_server" : "Management",
   "createrepo_flags"         : "Advanced",
   "environment"              : "Advanced",
   "mirror_locally"           : "Advanced",
   "priority"                 : "Advanced",
   "yumopts"                  : "Advanced",
   "packages" : "Resources",
   "files"    : "Resources",
   "repos_enabled" : "Management",
   "ldap_enabled"  : "Management",
   "ldap_type"     : "Management",
   "monit_enabled" : "Management",
}
   
# Certain legacy fields need to have different CLI options than the direct translation of their
# name in the FIELDS data structure.  We should not add any more of these under any conditions.
 
ALTERNATE_OPTIONS = {
   "ks_meta"             : "--ksmeta",
   "kernel_options"      : "--kopts",
   "kernel_options_post" : "--kopts-post",
}
