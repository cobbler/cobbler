"""
A Cobbler repesentation of an User preference

Copyright 2009, Red Hat, Inc

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

class Userpref(item.Item):

    TYPE_NAME = _("userpref")
    COLLECTION_TYPE = "userpref"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Userpref(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        self.name     = None
        self.filters  = {}
        self.webui    = {}
        self.reports  = {}

    def is_valid(self):
        return True
                                                                                                                                
    def from_datastruct(self,seed_data):
        self.name     = self.load_item(seed_data, 'name')
        self.filters  = self.load_item(seed_data, 'filters',{})
        self.webui    = self.load_item(seed_data, 'webui', {})
        self.reports  = self.load_item(seed_data, 'reports', {})
        return self

    def get_filter(self, hash):
        name=hash.get('name',None)
        if name is None:
            raise CX(_("missing name"))
        what=hash.get('what',None)
        if what is None:
            raise CX(_("missing what"))
        filtername="%s::%s" % (what,name)
        return self.filters.get(filtername,None)

    def add_filter(self, hash):
        name=hash.get('name',None)
        if name is None:
            raise CX(_("missing name"))
        what=hash.get('what',None)
        if what is None:
            raise CX(_("missing what"))
        if hash.get('matchtype',None) is None:
            raise CX(_("missing matchtype"))
        if hash.get('criteria',None) is None:
            raise CX(_("missing criteria"))
        filtername="%s::%s" % (what,name)
        self.filters[filtername]=hash
        return True

    def delete_filter(self, hash):
        name=hash.get('name',None)
        if name is None:
            raise CX(_("missing name"))
        what=hash.get('what',None)
        if what is None:
            raise CX(_("missing what"))
        filtername="%s::%s" % (what,name)
        del self.filters[filtername]
        return True

    def get_webui(self, name):
        return self.webui.get(name,{"name":name})

    def set_webui(self, hash):
        name=hash.get('name',None)
        if name is None:
            raise CX(_("missing name"))
        self.webui[name]=hash
        return True

    def to_datastruct(self):
        return {
            'name'      : self.name,
            'filters'   : self.filters,
            'webui'     : self.webui,
            'reports'   : self.reports
        }

    def printable(self):
        buf =       _("name             : %s\n") % self.name
#TODO
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
            'get_filter'     : self.get_filter,
            'add_filter'     : self.add_filter,
            'delete_filter'  : self.delete_filter,
            'get_webui'      : self.get_webui,
            'set_webui'      : self.set_webui,
        }
