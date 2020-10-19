"""
An Resource is a serializable thing that can appear in a Collection

Copyright 2006-2009, Red Hat, Inc and Others
Kelsey Hightower <khightower@gmail.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA.
"""
import uuid
from typing import Union

from cobbler import enums

from cobbler.items import item


class Resource(item.Item):
    """
    Base Class for management resources.

    TODO: Type declarations in the method signatures and type checks in the bodys.
    """

    def __init__(self, api, *args, **kwargs):
        super().__init__(api, *args, **kwargs)
        self._action = enums.ResourceAction.CREATE
        self._mode = ""
        self._owner = ""
        self._group = ""
        self._path = ""
        self._template = ""

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all values yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Resource(self.api)
        cloned.from_dict(_dict)
        cloned.uid = uuid.uuid4().hex
        return cloned

    def from_dict(self, dictionary: dict):
        """
        Initializes the object with attributes from the dictionary.

        :param dictionary: The dictionary with values.
        """
        item.Item._remove_depreacted_dict_keys(dictionary)
        to_pass = dictionary.copy()
        for key in dictionary:
            lowered_key = key.lower()
            if hasattr(self, "_" + lowered_key):
                try:
                    setattr(self, lowered_key, dictionary[key])
                except AttributeError as e:
                    raise AttributeError("Attribute \"%s\" could not be set!" % lowered_key) from e
                to_pass.pop(key)
        super().from_dict(to_pass)

    #
    # specific methods for item.File
    #

    @property
    def action(self):
        """
        TODO

        :return:
        """
        return self._action

    @action.setter
    def action(self, action: Union[str, enums.ResourceAction]):
        """
        All management resources have an action. Action determine weather a most resources should be created or removed,
        and if packages should be installed or uninstalled.

        :param action: The action which should be executed for the management resource. Must be on of "create" or
                       "remove". Parameter is case-insensitive.
        """
        # Convert an arch which came in as a string
        if isinstance(action, str):
            try:
                action = enums.ResourceAction[action.upper()]
            except KeyError as e:
                raise ValueError("action choices include: %s" % list(map(str, enums.ResourceAction))) from e
        # Now the arch MUST be from the type for the enum.
        if not isinstance(action, enums.ResourceAction):
            raise TypeError("action needs to be of type enums.ResourceAction")
        self._action = action

    @property
    def group(self):
        """
        TODO

        :return:
        """
        return self._group

    @group.setter
    def group(self, group):
        """
        Unix group ownership of a file or directory.

        :param group: The group which the resource will belong to.
        """
        self._group = group

    @property
    def mode(self):
        """
        TODO

        :return:
        """
        return self._mode

    @mode.setter
    def mode(self, mode):
        """
        Unix file permission mode ie: '0644' assigned to file and directory resources.

        :param mode: The mode which the resource will have.
        """
        self._mode = mode

    @property
    def owner(self):
        """
        TODO

        :return:
        """
        return self._owner

    @owner.setter
    def owner(self, owner):
        """
        Unix owner of a file or directory.

        :param owner: The owner which the resource will belong to.
        """
        self._owner = owner

    @property
    def path(self):
        """
        TODO

        :return:
        """
        return self._path

    @path.setter
    def path(self, path):
        """
        File path used by file and directory resources.

        :param path: Normally a absolute path of the file or directory to create or manage.
        """
        self._path = path

    @property
    def template(self):
        """
        TODO

        :return:
        """
        return self._template

    @template.setter
    def template(self, template):
        """
        Path to cheetah template on Cobbler's local file system. Used to generate file data shipped to koan via json.
        All templates have access to flatten autoinstall_meta data.

        :param template: The template to use for the resource.
        """
        self._template = template
