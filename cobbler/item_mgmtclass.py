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
    ["uid", "", 0, "", False, "", 0, "str"],
    ["depth", 2, 0, "", False, "", 0, "float"],
    ["name", "", 0, "Name", True, "Ex: F10-i386-webserver", 0, "str"],
    ["owners", "SETTINGS:default_ownership", "SETTINGS:default_ownership", "Owners", True, "Owners list for authz_ownership (space delimited)", 0, "list"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["ctime", 0, 0, "", False, "", 0, "int"],
    ["mtime", 0, 0, "", False, "", 0, "int"],
    ["class_name", "", 0, "Class Name", True, "Actual Class Name (leave blank to use the name field)", 0, "str"],
    ["is_definition", False, 0, "Is Definition?", True, "Treat this class as a definition (puppet only)", 0, "bool"],
    ["params", {}, 0, "Parameters/Variables", True, "List of parameters/variables", 0, "dict"],
    ["packages", [], 0, "Packages", True, "Package resources", 0, "list"],
    ["files", [], 0, "Files", True, "File resources", 0, "list"],
]


class Mgmtclass(item.Item):

    TYPE_NAME = _("mgmtclass")
    COLLECTION_TYPE = "mgmtclass"

    def __init__(self, *args, **kwargs):
        super(Mgmtclass, self).__init__(*args, **kwargs)
        self.params = None

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Mgmtclass(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def get_fields(self):
        return FIELDS

    def set_packages(self, packages):
        self.packages = utils.input_string_or_list(packages)
        return True

    def set_files(self, files):
        self.files = utils.input_string_or_list(files)
        return True

    def set_params(self, params, inplace=False):
        (success, value) = utils.input_string_or_hash(params, allow_multiples=True)
        if not success:
            raise CX(_("invalid parameters"))
        else:
            if inplace:
                for key in value.keys():
                    if key.startswith("~"):
                        del self.params[key[1:]]
                    else:
                        self.params[key] = value[key]
            else:
                self.params = value
            return True

    def set_is_definition(self, isdef):
        self.is_definition = utils.input_boolean(isdef)
        return True

    def set_class_name(self, name):
        if not isinstance(name, basestring):
            raise CX(_("class name must be a string"))
        for x in name:
            if not x.isalnum() and x not in ["_", "-", ".", ":", "+"]:
                raise CX(_("invalid characters in class name: '%s'" % name))
        self.class_name = name
        return True

    def check_if_valid(self):
        if self.name is None or self.name == "":
            raise CX("name is required")
