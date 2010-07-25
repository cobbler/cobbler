"""
Copyright 2010, Kelsey Hightower
Kelsey Hightower <kelsey.hightower@gmail.com>

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
from cexceptions import CX
from utils import _

# this datastructure is described in great detail in item_distro.py -- read the comments there.

FIELDS = [
  ["name","",0,"Name",True,"Ex: F10-i386-webserver",0,"str"],
  ["owners","SETTINGS:default_ownership","SETTINGS:default_ownership","Owners",True,"Owners list for authz_ownership (space delimited)",0,"list"],
  ["comment","",0,"Comment",True,"Free form text description",0,"str"],
  ["ctime",0,0,"",False,"",0,"int"],
  ["mtime",0,0,"",False,"",0,"int"],
  ["packages",[],0,"Packages",True,"Package resources",0,"list"],
  ["files",[],0,"Files",True,"File resources",0,"list"],
]

class Mgmtclass(item.Item):

    TYPE_NAME = _("mgmtclass")
    COLLECTION_TYPE = "mgmtclass"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Mgmtclass(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def get_fields(self):
        return FIELDS

    def set_packages(self,packages):
        self.packages = utils.input_string_or_list(packages)    
        return True

    def set_files(self,files):
        self.files = utils.input_string_or_list(files)
        return True

    def check_if_valid(self):
        if self.name is None or self.name == "":
            raise CX("name is required")
