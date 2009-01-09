"""
A Cobbler repesentation of an IP network.

Copyright 2009, Red Hat, Inc
John Eckersberg <jeckersb@redhat.com>

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
from cexceptions import *
from utils import _
import netaddr

class Network(item.Item):

    TYPE_NAME = _("network")
    COLLECTION_TYPE = "network"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Network(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        self.name             = None
        self.cidr             = None
        self.address          = None
        self.gateway          = None
        self.broadcast        = None
        self.nameservers      = []
        self.reserved         = []
        self.used_addresses   = []
        self.free_addresses   = []
        self.comment          = ""

    def from_datastruct(self,seed_data):
        self.name             = self.load_item(seed_data, 'name')
        self.cidr             = self.load_item(seed_data, 'cidr')
        self.address          = self.load_item(seed_data, 'address', self.cidr[0])
        self.gateway          = self.load_item(seed_data, 'gateway', self.cidr[-2])
        self.broadcast        = self.load_item(seed_data, 'broadcast', self.cidr[-1])
        self.nameservers      = self.load_item(seed_data, 'nameservers', [])
        self.reserved         = self.load_item(seed_data, 'reserved', [])
        self.used_addresses   = self.load_item(seed_data, 'used_addresses', [])
        self.free_addresses   = self.load_item(seed_data, 'free_addresses', [])
        self.comment          = self.load_item(seed_data, 'comment', '')

        return self

    def set_cidr(self, cidr):
        pass

    def set_address(self, address):
        pass

    def set_gateway(self, gateway):
        pass

    def set_broadcast(self, broadcast):
        pass

    def set_nameservers(self, nameservers):
        pass

    def set_reserved(self, reserved):
        pass

    def set_used_addresses(self, used_addresses):
        pass

    def set_free_addresses(self, free_addresses):
        pass

    def is_valid(self):
        """
	A network is valid if it has a name and a CIDR
	"""
        if self.name is None:
            raise CX(_("name is required"))
        if self.cidr is None:
            raise CX(_("cidr is required"))
        return True

    def to_datastruct(self):
        return {
            'name'           : self.name,
            'cidr'           : self.cidr,
            'address'        : self.address,
            'gateway'        : self.gateway,
            'broadcast'      : self.broadcast,
            'nameservers'    : self.nameservers,
            'reserved'       : self.reserved,
            'used_addresses' : self.used_addresses,
            'free_addresses' : self.free_addresses,
            'comment'        : self.comment
        }

    def printable(self):
        buf =       _("network          : %s\n") % self.name
        buf = buf + _("CIDR             : %s\n") % self.cidr
        buf = buf + _("network address  : %s\n") % self.address
        buf = buf + _("broadcast        : %s\n") % self.broadcast
        buf = buf + _("nameservers      : %s\n") % self.nameservers
        buf = buf + _("reserved         : %s\n") % self.reserved
        buf = buf + _("free addresses   : %s\n") % len(self.free_addresses)
        buf = buf + _("used addresses   : %s\n") % len(self.used_addresses)
        buf = buf + _("comment          : %s\n") % self.comment
        return buf

    def get_parent(self):
        """
        currently the Cobbler object space does not support subobjects of this object
        as it is conceptually not useful.
        """
        return None

    def remote_methods(self):
        return {
            'name'           : self.set_name,
            'cidr'           : self.set_cidr,
            'address'        : self.set_address,
            'gateway'        : self.set_gateway,
            'broadcast'      : self.set_broadcast,
            'nameservers'    : self.set_nameservers,
            'reserved'       : self.set_reserved,
            'used_addresses' : self.set_used_addresses,
            'free_addresses' : self.set_free_addresses,
            'comment'        : self.set_comment
        }
