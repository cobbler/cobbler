"""
Cobbler module that contains the code for a Cobbler repo object.

Changelog:

V3.4.0 (unreleased):
    * Changed:
        * Constructor: ``kwargs`` can now be used to seed the item during creation.
        * ``children``: The property was moved to the base class.
        * ``from_dict()``: The method was moved to the base class.
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * No changes
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Added:
        * os_version: str
        * ``from_dict()``
    * Moved to base class (Item):
        * ``ctime``: float
        * ``depth``: float
        * ``mtime``: float
        * ``parent``: str
        * ``uid``: str
        * ``comment``: str
        * ``name``: str
        * ``owners``: Union[list, SETTINGS:default_ownership]
    * Changes:
        * ``breed``: str -> enums.RepoBreeds
        * ``arch``: str -> enums.RepoArchs
        * ``rsyncopts``: dict/str? -> dict
        * ``mirror_type``: str -> enums.MirrorType
        * ``apt_components``: list/str? -> list
        * ``apt_dists``: list/str? -> list
        * ``createrepo_flags``: Union[dict, inherit] -> enums.VALUE_INHERITED
        * ``proxy``: Union[str, inherit] -> enums.VALUE_INHERITED
V3.2.2:
    * No changes
V3.2.1:
    * Added:
        * ``mirror_type``: str
        * ``set_mirror_type()``
V3.2.0:
    * Added:
        * ``rsyncopts``: dict/str
        * ``set_rsyncopts()``
V3.1.2:
    * No changes
V3.1.1:
    * No changes
V3.1.0:
    * Changed:
        * ``arch``: New valid value ``s390x`` as an architecture.
V3.0.1:
    * File was moved from ``cobbler/item_repo.py`` to ``cobbler/items/repo.py``.
V3.0.0:
    * Changes:
        * ``proxy``: Union[str, inherit, SETTINGS:proxy_url_ext] -> Union[str, inherit]
V2.8.5:
    * Inital tracking of changes for the changelog.
    * Added:
        * ``ctime``: float
        * ``depth``: float
        * ``mtime``: float
        * ``parent``: str
        * ``uid``: str

        * ``apt_components``: list/str?
        * ``apt_dists``: list/str?
        * ``arch``: str
        * ``breed``: str
        * ``comment``: str
        * ``createrepo_flags``: Union[dict, inherit]
        * ``environment``: dict
        * ``keep_updated``: bool
        * ``mirror``: str
        * ``mirror_locally``: bool
        * ``name``: str
        * ``owners``: Union[list, SETTINGS:default_ownership]
        * ``priority``: int
        * ``proxy``: Union[str, inherit, SETTINGS:proxy_url_ext]
        * ``rpm_list``: list
        * ``yumopts``: dict
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import copy
from typing import TYPE_CHECKING, Any, Dict, List, Union

from cobbler import enums
from cobbler.cexceptions import CX
from cobbler.decorator import InheritableProperty, LazyProperty
from cobbler.items.abstract import item_inheritable
from cobbler.utils import input_converters

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class Repo(item_inheritable.InheritableItem):
    """
    A Cobbler repo object.
    """

    TYPE_NAME = "repo"
    COLLECTION_TYPE = "repo"

    def __init__(self, api: "CobblerAPI", *args: Any, **kwargs: Any) -> None:
        """
        Constructor

        :param api: The Cobbler API object which is used for resolving information.
        """
        super().__init__(api)
        # Prevent attempts to clear the to_dict cache before the object is initialized.
        self._has_initialized = False

        self._breed = enums.RepoBreeds.NONE
        self._arch = enums.RepoArchs.NONE
        self._environment: Dict[Any, Any] = {}
        self._yumopts: Dict[str, str] = {}
        self._rsyncopts: Dict[str, Any] = {}
        self._mirror_type = enums.MirrorType.BASEURL
        self._apt_components: List[str] = []
        self._apt_dists: List[str] = []
        self._createrepo_flags = enums.VALUE_INHERITED
        self._keep_updated = False
        self._mirror = ""
        self._mirror_locally = False
        self._priority = 0
        self._proxy = enums.VALUE_INHERITED
        self._rpm_list: List[str] = []
        self._os_version = ""

        if len(kwargs) > 0:
            self.from_dict(kwargs)
        if not self._has_initialized:
            self._has_initialized = True

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self) -> "Repo":
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = copy.deepcopy(self.to_dict())
        _dict.pop("uid", None)
        return Repo(self.api, **_dict)

    def check_if_valid(self) -> None:
        """
        Checks if the object is valid. Currently checks for name and mirror to be present.

        :raises CX: In case the name or mirror is missing.
        """
        super().check_if_valid()
        if not self.inmemory:
            return
        if self.mirror is None:  # pyright: ignore [reportUnnecessaryComparison]
            raise CX(f"Error with repo {self.name} - mirror is required")

    #
    # specific methods for item.Repo
    #

    def _guess_breed(self) -> None:
        """
        Guess the breed of a mirror.
        """
        # backwards compatibility
        if not self.breed:
            if (
                self.mirror.startswith("http://")
                or self.mirror.startswith("https://")
                or self.mirror.startswith("ftp://")
            ):
                self.breed = enums.RepoBreeds.YUM
            elif self.mirror.startswith("rhn://"):
                self.breed = enums.RepoBreeds.RHN
            else:
                self.breed = enums.RepoBreeds.RSYNC

    @LazyProperty
    def mirror(self) -> str:
        r"""
        A repo is (initially, as in right now) is something that can be rsynced. reposync/repotrack integration over
        HTTP might come later.

        :getter: The mirror uri.
        :setter: May raise a ``TypeError`` in case we run into
        """
        return self._mirror

    @mirror.setter
    def mirror(self, mirror: str) -> None:
        r"""
        Setter for the mirror property.

        :param mirror: The mirror URI.
        :raises TypeError: In case mirror is not of type ``str``.
        """
        if not isinstance(mirror, str):  # type: ignore
            raise TypeError("Field mirror of object repo needs to be of type str!")
        self._mirror = mirror
        if not self.arch:
            if mirror.find("x86_64") != -1:
                self.arch = enums.RepoArchs.X86_64
            elif mirror.find("x86") != -1 or mirror.find("i386") != -1:
                self.arch = enums.RepoArchs.I386
        self._guess_breed()

    @LazyProperty
    def mirror_type(self) -> enums.MirrorType:
        r"""
        Override the mirror_type used for reposync

        :getter: The mirror type. Is one of the predefined ones.
        :setter: Hand over a str or enum type value to this. May raise ``TypeError`` or ``ValueError`` in case there are
                 conversion or type problems.
        """
        return self._mirror_type

    @mirror_type.setter
    def mirror_type(self, mirror_type: Union[str, enums.MirrorType]) -> None:
        r"""
        Setter for the ``mirror_type`` property.

        :param mirror_type: The new mirror_type which will be used.
        :raises TypeError: In case the value was not of the enum type.
        :raises ValueError: In case the conversion from str to enum type was not possible.
        """
        # Convert an mirror_type which came in as a string
        if isinstance(mirror_type, str):
            try:
                mirror_type = enums.MirrorType[mirror_type.upper()]
            except KeyError as error:
                raise ValueError(
                    f"mirror_type choices include: {list(map(str, enums.MirrorType))}"
                ) from error
        # Now the mirror_type MUST be of the type of enums.
        if not isinstance(mirror_type, enums.MirrorType):  # type: ignore
            raise TypeError("mirror_type needs to be of type enums.MirrorType")
        self._mirror_type = mirror_type

    @LazyProperty
    def keep_updated(self) -> bool:
        r"""
        This allows the user to disable updates to a particular repo for whatever reason.

        :getter: True in case the repo is updated automatically and False otherwise.
        :setter: Is auto-converted to a bool via multiple types. Raises a ``TypeError`` if this was not possible.
        """
        return self._keep_updated

    @keep_updated.setter
    def keep_updated(self, keep_updated: bool) -> None:
        """
        Setter for the keep_updated property.

        :param keep_updated: This may be a bool-like value if the repository shall be kept up to date or not.
        :raises TypeError: In case the conversion to a bool was unsuccessful.
        """
        keep_updated = input_converters.input_boolean(keep_updated)
        if not isinstance(keep_updated, bool):  # type: ignore
            raise TypeError(
                "Field keep_updated of object repo needs to be of type bool!"
            )
        self._keep_updated = keep_updated

    @LazyProperty
    def yumopts(self) -> Dict[Any, Any]:
        r"""
        Options for the yum tool. Should be presented in the same way as the ``kernel_options``.

        :getter: The dict with the parsed options.
        :setter: Either the dict or a str which is then parsed. If parsing is unsuccessful then a ValueError is raised.
        """
        return self._yumopts

    @yumopts.setter
    def yumopts(self, options: Union[str, Dict[Any, Any]]) -> None:
        """
        Kernel options are a space delimited list.

        :param options: Something like ``a=b c=d e=f g h i=j`` or a dictionary.
        :raises ValueError: In case the presented data could not be parsed into a dictionary.
        """
        try:
            self._yumopts = input_converters.input_string_or_dict_no_inherit(
                options, allow_multiples=False
            )
        except TypeError as error:
            raise TypeError("invalid yum options") from error

    @LazyProperty
    def rsyncopts(self) -> Dict[Any, Any]:
        r"""
        Options for ``rsync`` when being used for repo management.

        :getter: The options to apply to the generated ones.
        :setter: A str or dict to replace the old options with. If the str can't be parsed we throw a ``ValueError``.
        """
        return self._rsyncopts

    @rsyncopts.setter
    def rsyncopts(self, options: Union[str, Dict[Any, Any]]) -> None:
        """
        Setter for the ``rsyncopts`` property.

        :param options: Something like '-a -S -H -v'
        :raises ValueError: In case the options provided can't be parsed.
        """
        try:
            self._rsyncopts = input_converters.input_string_or_dict_no_inherit(
                options, allow_multiples=False
            )
        except TypeError as error:
            raise TypeError("invalid rsync options") from error

    @LazyProperty
    def environment(self) -> Dict[Any, Any]:
        """
        Yum can take options from the environment. This puts them there before each reposync.

        :getter: The options to be attached to the environment.
        :setter: May raise a ``ValueError`` in case the data provided is not parsable.
        """
        return self._environment

    @environment.setter
    def environment(self, options: Union[str, Dict[Any, Any]]) -> None:
        r"""
        Setter for the ``environment`` property.

        :param options: These are environment variables which are set before each reposync.
        :raises ValueError: In case the variables provided could not be parsed.
        """
        try:
            self._environment = input_converters.input_string_or_dict_no_inherit(
                options, allow_multiples=False
            )
        except TypeError as error:
            raise TypeError("invalid environment") from error

    @LazyProperty
    def priority(self) -> int:
        """
        Set the priority of the repository. Only works if host is using priorities plugin for yum.

        :getter: The priority of the repo.
        :setter: A number between 1 & 99. May raise otherwise ``TypeError`` or ``ValueError``.
        """
        return self._priority

    @priority.setter
    def priority(self, priority: int) -> None:
        r"""
        Setter for the ``priority`` property.

        :param priority: Must be a value between 1 and 99. 1 is the highest whereas 99 is the default and lowest.
        :raises TypeError: Raised in case the value is not of type ``int``.
        :raises ValueError: In case the priority is not between 1 and 99.
        """
        try:
            converted_value = input_converters.input_int(priority)
        except TypeError as type_error:
            raise TypeError("Repository priority must be of type int.") from type_error
        if converted_value < 0 or converted_value > 99:
            raise ValueError(
                "Repository priority must be between 1 and 99 (inclusive)!"
            )
        self._priority = converted_value

    @LazyProperty
    def rpm_list(self) -> List[str]:
        """
        Rather than mirroring the entire contents of a repository (Fedora Extras, for instance, contains games, and we
        probably don't want those), make it possible to list the packages one wants out of those repos, so only those
        packages and deps can be mirrored.

        :getter: The list of packages to be mirrored.
        :setter: May be a space delimited list or a real one.
        """
        return self._rpm_list

    @rpm_list.setter
    def rpm_list(self, rpms: Union[str, List[str]]) -> None:
        """
        Setter for the ``rpm_list`` property.

        :param rpms: The rpm to mirror. This may be a string or list.
        """
        self._rpm_list = input_converters.input_string_or_list_no_inherit(rpms)

    @InheritableProperty
    def createrepo_flags(self) -> str:
        r"""
        Flags passed to createrepo when it is called. Common flags to use would be ``-c cache`` or ``-g comps.xml`` to
        generate group information.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: The createrepo_flags to apply to the repo.
        :setter: The new flags. May raise a ``TypeError`` in case the options are not a ``str``.
        """
        return self._resolve("createrepo_flags")

    @createrepo_flags.setter  # type: ignore[no-redef]
    def createrepo_flags(self, createrepo_flags: str):
        """
        Setter for the ``createrepo_flags`` property.

        :param createrepo_flags: The createrepo flags which are passed additionally to the default ones.
        :raises TypeError: In case the flags were not of the correct type.
        """
        if not isinstance(createrepo_flags, str):  # type: ignore
            raise TypeError(
                "Field createrepo_flags of object repo needs to be of type str!"
            )
        self._createrepo_flags = createrepo_flags

    @LazyProperty
    def breed(self) -> enums.RepoBreeds:
        """
        The repository system breed. This decides some defaults for most actions with a repo in Cobbler.

        :getter: The breed detected.
        :setter: May raise a ``ValueError`` or ``TypeError`` in case the given value is wrong.
        """
        return self._breed

    @breed.setter
    def breed(self, breed: Union[str, enums.RepoBreeds]) -> None:
        """
        Setter for the repository system breed.

        :param breed: The new breed to set. If this argument evaluates to false then nothing will be done.
        :raises TypeError: In case the value was not of the corresponding enum type.
        :raises ValueError: In case a ``str`` with could not be converted to a valid breed.
        """
        self._breed = enums.RepoBreeds.to_enum(breed)

    @LazyProperty
    def os_version(self) -> str:
        r"""
        The operating system version which is compatible with this repository.

        :getter: The os version.
        :setter: The version as a ``str``.
        """
        return self._os_version

    @os_version.setter
    def os_version(self, os_version: str) -> None:
        r"""
        Setter for the operating system version.

        :param os_version: The new operating system version. If this argument evaluates to false then nothing will be
                           done.
        :raises CX: In case ``breed`` has not been set before.
        """
        if not os_version:
            self._os_version = ""
            return
        self._os_version = os_version.lower()
        if not self.breed:
            raise CX("cannot set --os-version without setting --breed first")
        if self.breed not in enums.RepoBreeds:
            raise CX("fix --breed first before applying this setting")
        self._os_version = os_version
        return

    @LazyProperty
    def arch(self) -> enums.RepoArchs:
        r"""
        Override the arch used for reposync

        :getter: The repo arch enum object.
        :setter: May throw a ``ValueError`` or ``TypeError`` in case the conversion of the value is unsuccessful.
        """
        return self._arch

    @arch.setter
    def arch(self, arch: Union[str, enums.RepoArchs]) -> None:
        r"""
        Override the arch used for reposync

        :param arch: The new arch which will be used.
        :raises TypeError: In case the wrong type is given.
        :raises ValueError: In case the value could not be converted from ``str`` to the enum type.
        """
        # Convert an arch which came in as an enums.Archs
        if isinstance(arch, enums.Archs):
            try:
                arch = enums.RepoArchs[arch.name.upper()]
            except KeyError as error:
                raise ValueError(
                    f"arch choices include: {list(map(str, enums.RepoArchs))}"
                ) from error
        self._arch = enums.RepoArchs.to_enum(arch)

    @LazyProperty
    def mirror_locally(self) -> bool:
        r"""
        If this property is set to ``True`` then all content of the source is mirrored locally. This may take up a lot
        of disk space.

        :getter: Whether the mirror is locally available or not.
        :setter: Raises a ``TypeError`` in case after the conversion of the value is not of type ``bool``.
        """
        return self._mirror_locally

    @mirror_locally.setter
    def mirror_locally(self, value: bool) -> None:
        """
        Setter for the local mirror property.

        :param value: The new value for ``mirror_locally``.
        :raises TypeError: In case the value is not of type ``bool``.
        """
        value = input_converters.input_boolean(value)
        if not isinstance(value, bool):  # type: ignore
            raise TypeError("mirror_locally needs to be of type bool")
        self._mirror_locally = value

    @LazyProperty
    def apt_components(self) -> List[str]:
        """
        Specify the section of Debian to mirror. Defaults to "main,contrib,non-free,main/debian-installer".

        :getter: If empty the default is used.
        :setter: May be a comma delimited ``str`` or a real ``list``.
        """
        return self._apt_components

    @apt_components.setter
    def apt_components(self, value: Union[str, List[str]]) -> None:
        """
        Setter for the apt command property.

        :param value: The new value for ``apt_components``.
        """
        self._apt_components = input_converters.input_string_or_list_no_inherit(value)

    @LazyProperty
    def apt_dists(self) -> List[str]:
        r"""
        This decides which installer images are downloaded. For more information please see:
        https://www.debian.org/CD/mirroring/index.html or the manpage of ``debmirror``.

        :getter: Per default no images are mirrored.
        :setter: Either a comma delimited ``str`` or a real ``list``.
        """
        return self._apt_dists

    @apt_dists.setter
    def apt_dists(self, value: Union[str, List[str]]) -> None:
        """
        Setter for the apt dists.

        :param value: The new value for ``apt_dists``.
        """
        self._apt_dists = input_converters.input_string_or_list_no_inherit(value)

    @InheritableProperty
    def proxy(self) -> str:
        """
        Override the default external proxy which is used for accessing the internet.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the default one or the specific one for this repository.
        :setter: May raise a ``TypeError`` in case the wrong value is given.
        """
        return self._resolve("proxy_url_ext")

    @proxy.setter  # type: ignore[no-redef]
    def proxy(self, value: str):
        r"""
        Setter for the proxy setting of the repository.

        :param value: The new proxy which will be used for the repository.
        :raises TypeError: In case the new value is not of type ``str``.
        """
        if not isinstance(value, str):  # type: ignore
            raise TypeError("Field proxy in object repo needs to be of type str!")
        self._proxy = value
