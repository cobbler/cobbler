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

# FIXME: presumably incomplete.

USES_TEXTAREA = [
   "comment",
   "mgmt_classes",
   "template_files"
]

USES_MULTI_SELECT = [
   "repos"
]

USES_SELECT = [
   "profile",
   "distro",
   "network",
   "image",
   "virt_type",
   "arch",
   "*bonding",
   "parent",
   "breed",
   "os_version",
]

USES_CHECKBOX = [
   "enable_menu",
   "*netboot_enabled",
   "netboot_enabled",
   "*static"
]

# select killed the radio button
USES_RADIO = [
]

CSS_MAPPINGS = {
   "virt_ram"        : "virtedit",
   "virt_disk"       : "virtedit",
   "virt_cpus"       : "virtedit",
   "virt_bridge"     : "virtedit",
   "virt_path"       : "virtedit",
   "virt_file_size"  : "virtedit",
   "virt_type"       : "virtedit",
   "virt_auto_boot"  : "virtedit",
   "virt_host"       : "virtedit",
   "virt_group"      : "virtedit",
   "virt_guests"     : "virtedit",
   "*virt_ram"       : "virtedit",
   "*virt_disk"      : "virtedit",
   "*virt_path"      : "virtedit",
   "*virt_cpus"      : "virtedit",
   "*virt_bridge"    : "netedit",
   "*virt_type"      : "virtedit",
   "*virt_file_size" : "virtedit",
   "*virt_auto_boot" : "virtedit",
   "power_id"        : "poweredit",
   "power_address"   : "poweredit",
   "power_user"      : "poweredit",
   "power_pass"      : "poweredit",
   "power_type"      : "poweredit",
   "address"         : "netedit", # from network
   "cidr"            : "netedit", # ditto
   "broadcast"       : "netedit", # ..
   "reserved"        : "netedit", # ..
   "*mac_address"    : "netedit",
   "*ip_address"     : "netedit",
   "*dhcp_tag"       : "netedit",
   "*static"         : "netedit",
   "*bonding"        : "netedit",
   "*bonding_opts"   : "netedit",
   "*bonding_master" : "netedit",
   "*dns_name"       : "netedit",
   "*static_routes"  : "netedit",
   "*network"        : "netedit",
   "*subnet"         : "netedit",
   "hostname"        : "netedit",
   "gateway"         : "netedit",
   "name_servers"         : "netedit",
   "name_servers_search"  : "netedit"
}
    
ALTERNATE_OPTIONS = {
   "ks_meta"             : "--ksmeta",
   "kernel_options"      : "--kopts",
   "kernel_options_post" : "--kopts-post",
}
