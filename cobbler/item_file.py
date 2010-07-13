"""
Copyright 2006-2009, MadHatter
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

import resource
import utils
from cexceptions import CX
from utils import _

# this datastructure is described in great detail in item_distro.py -- read the comments there.

FIELDS = [
  ["comment","",0,"Comment",True,"Free form text description",0,"str"],
  ["ctime",0,0,"",False,"",0,"float"],
  ["mtime",0,0,"",False,"",0,"float"],
  ["owners","SETTINGS:default_ownership",0,"Owners",False,"Owners list for authz_ownership (space delimited)",[],"list"],
  ["name","",0,"Name",True,"Name of file resource",0,"str"],
  ["is_directory",False,0,"Is Directory",True,"Treat file resource as a directory",0,"bool"],
  ["action","create",0,"Action",True,"Create or remove file resource",0,"str"],
  ["group","",0,"Group",True,"The group owner of the file",0,"str"],
  ["mode","",0,"Mode",True,"The mode of the file",0,"str"],
  ["owner","",0,"Owner",True,"The owner for the file",0,"str"],
  ["path","",0,"Path",True,"The path for the file",0,"str"],
  ["template","",0,"Template",True,"The template for the file",0,"str"]
]

class File(resource.Resource):

    TYPE_NAME = _("file")
    COLLECTION_TYPE = "file"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = File(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def get_fields(self):
        return FIELDS
    
    def set_is_directory(self,is_directory):
        """
        If true, treat file resource as a directory. Templates are ignored.
        """
        self.is_directory = utils.input_boolean(is_directory)
        return True

    def check_if_valid(self):
        if self.name is None:
            raise CX("name is required")
