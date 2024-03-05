"""
Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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
import uuid
from typing import Union

from cobbler import enums
from cobbler import utils
from cobbler.cexceptions import CX
from cobbler.items import item
from cobbler.decorator import InheritableProperty, LazyProperty


class Repo(item.Item):
    """
    A Cobbler repo object.
    """

    TYPE_NAME = "repo"
    COLLECTION_TYPE = "repo"

    def __init__(self, api, *args, **kwargs):
        """

        :param api: The Cobbler API object which is used for resolving information.
        :param args: The arguments which should be passed additionally to the base Item class constructor.
        :param kwargs: The keyword arguments which should be passed additionally to the base Item class constructor.
        """
        super().__init__(api, *args, **kwargs)
        self._has_initialized = False

        self._breed = enums.RepoBreeds.NONE
        self._arch = enums.RepoArchs.NONE
        self._environment = {}
        self._yumopts = {}
        self._rsyncopts = {}
        self._mirror_type = enums.MirrorType.BASEURL
        self._apt_components = []
        self._apt_dists = []
        self._createrepo_flags = enums.VALUE_INHERITED
        self._keep_updated = False
        self._mirror = ""
        self._mirror_locally = False
        self._priority = 0
        self._proxy = enums.VALUE_INHERITED
        self._rpm_list = []
        self._os_version = ""

        if not self._has_initialized:
            self._has_initialized = True

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Repo(self.api)
        cloned.from_dict(_dict)
        cloned.uid = uuid.uuid4().hex
        return cloned

    def check_if_valid(self):
        """
        Checks if the object is valid. Currently checks for name and mirror to be present.

        :raises CX: In case the name or mirror is missing.
        """
        super().check_if_valid()
        if not self.inmemory:
            return
        if self.mirror is None:
            raise CX("Error with repo %s - mirror is required" % self.name)

    #
    # specific methods for item.Repo
    #

    def _guess_breed(self):
        """
        Guess the breed of a mirror.
        """
        # backwards compatibility
        if not self.breed:
            if self.mirror.startswith("http://") or self.mirror.startswith("https://") \
                    or self.mirror.startswith("ftp://"):
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
    def mirror(self, mirror: str):
        r"""
        Setter for the mirror property.

        :param mirror: The mirror URI.
        :raises TypeError: In case mirror is not of type ``str``.
        """
        if not isinstance(mirror, str):
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
    def mirror_type(self, mirror_type: Union[str, enums.MirrorType]):
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
                raise ValueError("mirror_type choices include: %s" % list(map(str, enums.MirrorType))) from error
        # Now the mirror_type MUST be of the type of enums.
        if not isinstance(mirror_type, enums.MirrorType):
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
    def keep_updated(self, keep_updated: bool):
        """
        Setter for the keep_updated property.

        :param keep_updated: This may be a bool-like value if the repository shall be kept up to date or not.
        :raises TypeError: In case the conversion to a bool was unsuccessful.
        """
        keep_updated = utils.input_boolean(keep_updated)
        if not isinstance(keep_updated, bool):
            raise TypeError("Field keep_updated of object repo needs to be of type bool!")
        self._keep_updated = keep_updated

    @LazyProperty
    def yumopts(self) -> dict:
        r"""
        Options for the yum tool. Should be presented in the same way as the ``kernel_options``.

        :getter: The dict with the parsed options.
        :setter: Either the dict or a str which is then parsed. If parsing is unsuccessful then a ValueError is raised.
        """
        return self._yumopts

    @yumopts.setter
    def yumopts(self, options: Union[str, dict]):
        """
        Kernel options are a space delimited list.

        :param options: Something like ``a=b c=d e=f g h i=j`` or a dictionary.
        :raises ValueError: In case the presented data could not be parsed into a dictionary.
        """
        try:
            self._yumopts = utils.input_string_or_dict(options, allow_multiples=False)
        except TypeError as e:
            raise TypeError("invalid yum options") from e

    @LazyProperty
    def rsyncopts(self) -> dict:
        r"""
        Options for ``rsync`` when being used for repo management.

        :getter: The options to apply to the generated ones.
        :setter: A str or dict to replace the old options with. If the str can't be parsed we throw a ``ValueError``.
        """
        return self._rsyncopts

    @rsyncopts.setter
    def rsyncopts(self, options: Union[str, dict]):
        """
        Setter for the ``rsyncopts`` property.

        :param options: Something like '-a -S -H -v'
        :raises ValueError: In case the options provided can't be parsed.
        """
        try:
            self._rsyncopts = utils.input_string_or_dict(options, allow_multiples=False)
        except TypeError as e:
            raise TypeError("invalid rsync options") from e

    @LazyProperty
    def environment(self) -> dict:
        """
        Yum can take options from the environment. This puts them there before each reposync.

        :getter: The options to be attached to the environment.
        :setter: May raise a ``ValueError`` in case the data provided is not parsable.
        """
        return self._environment

    @environment.setter
    def environment(self, options: Union[str, dict]):
        r"""
        Setter for the ``environment`` property.

        :param options: These are environment variables which are set before each reposync.
        :raises ValueError: In case the variables provided could not be parsed.
        """
        try:
            self._environment = utils.input_string_or_dict(
                options, allow_multiples=False
            )
        except TypeError as e:
            raise TypeError("invalid environment") from e

    @LazyProperty
    def priority(self) -> int:
        """
        Set the priority of the repository. Only works if host is using priorities plugin for yum.

        :getter: The priority of the repo.
        :setter: A number between 1 & 99. May raise otherwise ``TypeError`` or ``ValueError``.
        """
        return self._priority

    @priority.setter
    def priority(self, priority: int):
        r"""
        Setter for the ``priority`` property.

        :param priority: Must be a value between 1 and 99. 1 is the highest whereas 99 is the default and lowest.
        :raises TypeError: Raised in case the value is not of type ``int``.
        :raises ValueError: In case the priority is not between 1 and 99.
        """
        if not isinstance(priority, int):
            raise TypeError("Repository priority must be of type int.")
        if priority < 0 or priority > 99:
            raise ValueError("Repository priority must be between 0 and 99 (inclusive)!")
        self._priority = priority

    @LazyProperty
    def rpm_list(self) -> list:
        """
        Rather than mirroring the entire contents of a repository (Fedora Extras, for instance, contains games, and we
        probably don't want those), make it possible to list the packages one wants out of those repos, so only those
        packages and deps can be mirrored.

        :getter: The list of packages to be mirrored.
        :setter: May be a space delimited list or a real one.
        """
        return self._rpm_list

    @rpm_list.setter
    def rpm_list(self, rpms: Union[str, list]):
        """
        Setter for the ``rpm_list`` property.

        :param rpms: The rpm to mirror. This may be a string or list.
        """
        self._rpm_list = utils.input_string_or_list(rpms)

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

    @createrepo_flags.setter
    def createrepo_flags(self, createrepo_flags: str):
        """
        Setter for the ``createrepo_flags`` property.

        :param createrepo_flags: The createrepo flags which are passed additionally to the default ones.
        :raises TypeError: In case the flags were not of the correct type.
        """
        if not isinstance(createrepo_flags, str):
            raise TypeError("Field createrepo_flags of object repo needs to be of type str!")
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
    def breed(self, breed: Union[str, enums.RepoBreeds]):
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
    def os_version(self, os_version: str):
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
    def arch(self, arch: Union[str, enums.RepoArchs]):
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
                raise ValueError("arch choices include: %s" % list(map(str, enums.RepoArchs))) from error
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
    def mirror_locally(self, value: bool):
        """
        Setter for the local mirror property.

        :param value: The new value for ``mirror_locally``.
        :raises TypeError: In case the value is not of type ``bool``.
        """
        value = utils.input_boolean(value)
        if not isinstance(value, bool):
            raise TypeError("mirror_locally needs to be of type bool")
        self._mirror_locally = value

    @LazyProperty
    def apt_components(self) -> list:
        """
        Specify the section of Debian to mirror. Defaults to "main,contrib,non-free,main/debian-installer".

        :getter: If empty the default is used.
        :setter: May be a comma delimited ``str`` or a real ``list``.
        """
        return self._apt_components

    @apt_components.setter
    def apt_components(self, value: Union[str, list]):
        """
        Setter for the apt command property.

        :param value: The new value for ``apt_components``.
        """
        self._apt_components = utils.input_string_or_list(value)

    @LazyProperty
    def apt_dists(self) -> list:
        r"""
        This decides which installer images are downloaded. For more information please see:
        https://www.debian.org/CD/mirroring/index.html or the manpage of ``debmirror``.

        :getter: Per default no images are mirrored.
        :setter: Either a comma delimited ``str`` or a real ``list``.
        """
        return self._apt_dists

    @apt_dists.setter
    def apt_dists(self, value: Union[str, list]):
        """
        Setter for the apt dists.

        :param value: The new value for ``apt_dists``.
        """
        self._apt_dists = utils.input_string_or_list(value)

    @InheritableProperty
    def proxy(self) -> str:
        """
        Override the default external proxy which is used for accessing the internet.

        .. note:: This property can be set to ``<<inherit>>``.

        :getter: Returns the default one or the specific one for this repository.
        :setter: May raise a ``TypeError`` in case the wrong value is given.
        """
        return self._resolve("proxy_url_ext")

    @proxy.setter
    def proxy(self, value: str):
        r"""
        Setter for the proxy setting of the repository.

        :param value: The new proxy which will be used for the repository.
        :raises TypeError: In case the new value is not of type ``str``.
        """
        if not isinstance(value, str):
            raise TypeError("Field proxy in object repo needs to be of type str!")
        self._proxy = value
