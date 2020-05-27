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

from cobbler import resource

from cobbler.cexceptions import CX
from cobbler.utils import _


# this data structure is described in item.py
FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 2, 0, "", False, "", 0, "float"],
    ["mtime", 0, 0, "", False, "", 0, "float"],
    ["uid", "", 0, "", False, "", 0, "str"],

    # editable in UI
    ["action", "create", 0, "Action", True, "Install or remove package resource", 0, "str"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["installer", "yum", 0, "Installer", True, "Package Manager", 0, "str"],
    ["name", "", 0, "Name", True, "Name of file resource", 0, "str"],
    ["owners", "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", [], "list"],
    ["version", "", 0, "Version", True, "Package Version", 0, "str"],
]


class Package(resource.Resource):

    TYPE_NAME = _("package")
    COLLECTION_TYPE = "package"

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this package object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Package(self.collection_mgr)
        cloned.from_dict(_dict)
        return cloned

    def get_fields(self):
        """
        Return all fields which this class has with its current values.

        :return: This is a list with lists.
        """
        return FIELDS

    def check_if_valid(self):
        """
        Checks if the object is in a valid state. This only checks currently if the name is present.
        """
        if not self.name:
            raise CX("name is required")

    #
    # specific methods for item.Package
    #

    def set_installer(self, installer):
        """
        Setter for the installer parameter.

        :param installer: This parameter will be lowercased regardless of what string you give it.
        :type installer: str
        """
        self.installer = installer.lower()

    def set_version(self, version):
        """
        Setter for the package version.

        :param version: They may be anything which is suitable for describing the version of a package. Internally this
                        is a string.
        :type version: str
        """
        self.version = version

# EOF
