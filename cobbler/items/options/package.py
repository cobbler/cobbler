"""
This module defines the `Option` classes for managing repository settings within Cobbler's Repo items.
"""

from typing import TYPE_CHECKING, List, Union

from cobbler.items.options.base import ItemOption

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.repo import Repo

    LazyProperty = property
else:
    from cobbler.decorator import LazyProperty


class APTOption(ItemOption["Repo"]):
    """
    Option class for managing APT repository settings for a Cobbler Repo item.

    Handles configuration of components and distributions for Debian-based mirrors.
    """

    def __init__(self, api: "CobblerAPI", item: "Repo") -> None:
        super().__init__(api, item=item)
        self._components: List[str] = []
        self._dists: List[str] = []

    @property
    def parent_name(self) -> str:
        return "apt"

    @LazyProperty
    def components(self) -> List[str]:
        """
        Specify the section of Debian to mirror. Defaults to "main,contrib,non-free,main/debian-installer".

        :getter: If empty the default is used.
        :setter: May be a comma delimited ``str`` or a real ``list``.
        """
        return self._components

    @components.setter
    def components(self, value: Union[str, List[str]]) -> None:
        """
        Setter for the apt command property.

        :param value: The new value for ``apt_components``.
        """
        self._components = self._api.input_string_or_list_no_inherit(value)

    @LazyProperty
    def dists(self) -> List[str]:
        r"""
        This decides which installer images are downloaded. For more information please see:
        https://www.debian.org/CD/mirroring/index.html or the manpage of ``debmirror``.

        :getter: Per default no images are mirrored.
        :setter: Either a comma delimited ``str`` or a real ``list``.
        """
        return self._dists

    @dists.setter
    def dists(self, value: Union[str, List[str]]) -> None:
        """
        Setter for the apt dists.

        :param value: The new value for ``apt_dists``.
        """
        self._dists = self._api.input_string_or_list_no_inherit(value)
