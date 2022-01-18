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
        """
        Constructor.
        """
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
        self._remove_depreacted_dict_keys(dictionary)
        super().from_dict(dictionary)

    #
    # specific methods for item.File
    #

    @property
    def action(self) -> enums.ResourceAction:
        """
        Action property.

        :getter: Return the value for ``action``.
        :setter: Sets the value for property ``action``. Raises a ValueError or a TypeError.
        """
        return self._action

    @action.setter
    def action(self, action: Union[str, enums.ResourceAction]):
        """
        All management resources have an action. Actions determine weather most resources should be created or removed,
        and if packages should be installed or uninstalled.

        :param action: The action which should be executed for the management resource. Must be of "create" or
                       "remove". Parameter is case-insensitive.
        :raise ValueError: Raised in case wrong value is provided.
        :raise TypeError: Raised in case ``action`` is no ``enums.ResourceAction``.
        """
        self._action = enums.ResourceAction.to_enum(action)

    @property
    def group(self) -> str:
        """
        Group property.

        :getter: Return the value for ``group``.
        :setter: Sets the value for property ``group``.
        """
        return self._group

    @group.setter
    def group(self, group: str):
        """
        Unix group ownership of a file or directory.

        :param group: The group which the resource will belong to.
        :raise TypeError: Raised in case ``group`` is no string. Raises a TypeError.
        """
        if not isinstance(group, str):
            raise TypeError("Field group of object resource needs to be of type str!")
        self._group = group

    @property
    def mode(self) -> str:
        """
        Mode property.

        :getter: Return the value for ``mode``.
        :setter: Sets the value for property ``mode``. Raises a TypeError.
        """
        return self._mode

    @mode.setter
    def mode(self, mode: str):
        """
        Unix file permission mode ie: '0644' assigned to file and directory resources.

        :param mode: The mode which the resource will have.
        :raise TypeError: Raised in case ``mode`` is no string.
        """
        if not isinstance(mode, str):
            raise TypeError("Field mode in object resource needs to be of type str!")
        self._mode = mode

    @property
    def owner(self) -> str:
        """
        Owner property.

        :getter: Return the value for ``owner``.
        :setter: Sets the value for property ``owner``. Raises a TypeError.
        """
        return self._owner

    @owner.setter
    def owner(self, owner: str):
        """
        Unix owner of a file or directory.

        :param owner: The owner whom the resource will belong to.
        :raise TypeError: Raised in case ``owner`` is no string.
        """
        if not isinstance(owner, str):
            raise TypeError("Field owner in object resource needs to be of type str!")
        self._owner = owner

    @property
    def path(self) -> str:
        """
        Path property.

        :getter: Return the value for ``path``.
        :setter: Sets the value for property ``path``. Raises a TypeError.
        """
        return self._path

    @path.setter
    def path(self, path: str):
        """
        File path used by file and directory resources.

        :param path: Normally an absolute path of the file or directory to create or manage.
        :raise TypeError: Raised in case ``path`` is no string.
        """
        if not isinstance(path, str):
            raise TypeError("Field path in object resource needs to be of type str!")
        self._path = path

    @property
    def template(self) -> str:
        """
        Template property.

        :getter: Return the value for ``template``.
        :setter: Sets the value for property ``template``. Raises a TypeError.
        """
        return self._template

    @template.setter
    def template(self, template: str):
        """
        Path to cheetah template on Cobbler's local file system. Used to generate file data shipped to koan via json.
        All templates have access to flatten autoinstall_meta data.

        :param template: The template to use for the resource.
        :raise TypeError: Raised in case ``template`` is no string.
        """
        if not isinstance(template, str):
            raise TypeError("Field template in object resource needs to be of type str!")
        self._template = template
