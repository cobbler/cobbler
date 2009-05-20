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
]

USES_CHECKBOX = [
   "enable_menu",
   "netboot_enabled"
]

# FIXME: why not use selects?
USES_RADIO = [
   "virt_type",
   "arch"
]
# FIXME: this list is incomplete and will be evolved
# as we tune/test the webapp


CSS_MAPPINGS = {
   "virt_ram"       : "virtedit",
   "virt_disk"      : "virtedit",
   "virt_cpus"      : "virtedit",
   "virt_bridge"    : "virtedit",
   "virt_type"      : "virtedit",
   "virt_type"      : "virtedit",
   "power_id"       : "poweredit",
   "power_address"  : "poweredit",
   "power_user"     : "poweredit",
   "power_password" : "poweredit",
}
    

