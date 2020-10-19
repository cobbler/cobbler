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


class Repo(item.Item):
    """
    A Cobbler repo object.
    """

    TYPE_NAME = "repo"
    COLLECTION_TYPE = "repo"

    def __init__(self, api, *args, **kwargs):
        super().__init__(api, *args, **kwargs)
        self._breed = enums.RepoBreeds.NONE
        self._arch = enums.RepoArchs.X86_64
        self._environment = {}
        self._yumopts = {}
        self._rsyncopts = {}
        self._mirror_type = enums.MirrorType.NONE
        self._apt_components = []
        self._apt_dists = []
        self._createrepo_flags = {}
        self._keep_updated = False
        self._mirror = ""
        self._mirror_locally = False
        self._priority = 0
        self._proxy = ""
        self._rpm_list = []
        self._os_version = ""

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

    def from_dict(self, dictionary: dict):
        """
        Initializes the object with attributes from the dictionary.

        :param dictionary: The dictionary with values.
        """
        item.Item._remove_depreacted_dict_keys(dictionary)
        dictionary.pop("parent")
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

    def check_if_valid(self):
        """
        Checks if the object is valid. Currently checks for name and mirror to be present.

        :raises CX
        """
        if self.name is None:
            raise CX("name is required")
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
                self.breed = "yum"
            elif self.mirror.startswith("rhn://"):
                self.breed = "rhn"
            else:
                self.breed = "rsync"

    @property
    def mirror(self):
        """
        TODO

        :return:
        """
        return self._mirror

    @mirror.setter
    def mirror(self, mirror):
        """
        A repo is (initially, as in right now) is something that can be rsynced.
        reposync/repotrack integration over HTTP might come later.

        :param mirror: The mirror URI.
        """
        self._mirror = mirror
        if not self.arch:
            if mirror.find("x86_64") != -1:
                self.arch = "x86_64"
            elif mirror.find("x86") != -1 or mirror.find("i386") != -1:
                self.arch = "i386"
        self._guess_breed()

    @property
    def mirror_type(self):
        """
        TODO

        :return:
        """
        return self._mirror_type

    @mirror_type.setter
    def mirror_type(self, mirror_type: Union[str, enums.MirrorType]):
        """
        Override the mirror_type used for reposync

        :param mirror_type: The new mirror_type which will be used.
        """
        # Convert an mirror_type which came in as a string
        if isinstance(mirror_type, str):
            try:
                mirror_type = enums.MirrorType[mirror_type.upper()]
            except KeyError as e:
                raise ValueError("mirror_type choices include: %s" % list(map(str, enums.MirrorType))) from e
        # Now the mirror_type MUST be from the type for the enum.
        if not isinstance(mirror_type, enums.MirrorType):
            raise TypeError("mirror_type needs to be of type enums.MirrorType")
        self._mirror_type = mirror_type

    @property
    def keep_updated(self):
        """
        TODO

        :return:
        """
        return self._keep_updated

    @keep_updated.setter
    def keep_updated(self, keep_updated: bool):
        """
        This allows the user to disable updates to a particular repo for whatever reason.

        :param keep_updated: This may be a bool-like value if the repository shall be keept up to date or not.
        """
        self._keep_updated = keep_updated

    @property
    def yumopts(self):
        """
        TODO

        :return:
        """
        return self._yumopts

    @yumopts.setter
    def yumopts(self, options: Union[str, dict]):
        """
        Kernel options are a space delimited list.

        :param options: Something like 'a=b c=d e=f g h i=j' or a dictionary.
        :raises CX
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=False)
        if not success:
            raise ValueError("invalid yum options")
        else:
            self._yumopts = value

    @property
    def rsyncopts(self):
        """
        TODO

        :return:
        """
        return self._rsyncopts

    @rsyncopts.setter
    def rsyncopts(self, options: Union[str, dict]):
        """
        rsync options are a space delimited list

        :param options: Something like '-a -S -H -v'
        :raises CX
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=False)
        if not success:
            raise ValueError("invalid rsync options")
        else:
            self._rsyncopts = value

    @property
    def environment(self):
        """
        TODO

        :return:
        """
        return self._environment

    @environment.setter
    def environment(self, options: Union[str, dict]):
        """
        Yum can take options from the environment. This puts them there before each reposync.

        :param options: These are environment variables which are set before each reposync.
        :raises CX
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=False)
        if not success:
            raise ValueError("invalid environment options")
        else:
            self._environment = value

    @property
    def priority(self):
        """
        TODO

        :return:
        """
        return self._priority

    @priority.setter
    def priority(self, priority: int):
        """
        Set the priority of the repository. Only works if host is using priorities plugin for yum.

        :param priority: Must be a value between 1 and 99. 1 is the highest whereas 99 is the default and lowest.
        :raises CX
        """
        if not isinstance(priority, int):
            raise TypeError("Repository priority must be of type int.")
        if priority < 0 or priority > 99:
            raise ValueError("Repository priority must be between 0 and 99 (inclusive)!")
        self._priority = priority

    @property
    def rpm_list(self):
        """
        TODO

        :return:
        """
        return self._rpm_list

    @rpm_list.setter
    def rpm_list(self, rpms: Union[str, list]):
        """
        Rather than mirroring the entire contents of a repository (Fedora Extras, for instance, contains games, and we
        probably don't want those), make it possible to list the packages one wants out of those repos, so only those
        packages and deps can be mirrored.

        :param rpms: The rpm to mirror. This may be a string or list.
        """
        self._rpm_list = utils.input_string_or_list(rpms)

    @property
    def createrepo_flags(self):
        """
        TODO

        :return:
        """
        return self._createrepo_flags

    @createrepo_flags.setter
    def createrepo_flags(self, createrepo_flags):
        """
        Flags passed to createrepo when it is called. Common flags to use would be ``-c cache`` or ``-g comps.xml`` to
        generate group information.

        :param createrepo_flags: The createrepo flags which are passed additionally to the default ones.
        """
        if createrepo_flags is None:
            createrepo_flags = ""
        self._createrepo_flags = createrepo_flags

    @property
    def breed(self):
        """
        TODO

        :return:
        """
        return self._breed

    @breed.setter
    def breed(self, breed: Union[str, enums.RepoBreeds]):
        """
        Setter for the operating system breed.

        :param breed: The new breed to set. If this argument evaluates to false then nothing will be done.
        """
        # Convert an arch which came in as a string
        if isinstance(breed, str):
            try:
                breed = enums.RepoBreeds[breed.upper()]
            except KeyError as e:
                raise ValueError("invalid value for --breed (%s), must be one of %s, different breeds have different "
                                 "levels of support " % (breed, list(map(str, enums.RepoBreeds)))) from e
        # Now the arch MUST be from the type for the enum.
        if not isinstance(breed, enums.RepoBreeds):
            raise TypeError("arch needs to be of type enums.Archs")
        self._breed = breed

    @property
    def os_version(self):
        """
        TODO

        :return:
        """
        return self._os_version

    @os_version.setter
    def os_version(self, os_version):
        """
        Setter for the operating system version.

        :param os_version: The new operating system version. If this argument evaluates to false then nothing will be
                           done.
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

    @property
    def arch(self):
        """
        TODO

        :return:
        """
        return self._arch

    @arch.setter
    def arch(self, arch: Union[str, enums.RepoArchs]):
        """
        Override the arch used for reposync

        :param arch: The new arch which will be used.
        """
        # Convert an arch which came in as a string
        if isinstance(arch, str):
            try:
                arch = enums.RepoArchs[arch.upper()]
            except KeyError as e:
                raise ValueError("arch choices include: %s" % list(map(str, enums.RepoArchs))) from e
        # Now the arch MUST be from the type for the enum.
        if not isinstance(arch, enums.RepoArchs):
            raise TypeError("arch needs to be of type enums.Archs")
        self._arch = arch

    @property
    def mirror_locally(self):
        """
        TODO

        :return:
        """
        return self._mirror_locally

    @mirror_locally.setter
    def mirror_locally(self, value: bool):
        """
        Setter for the local mirror property.

        :param value: The new value for ``mirror_locally``.
        """
        if not isinstance(value, bool):
            raise TypeError("mirror_locally needs to be of type bool")
        self._mirror_locally = value

    @property
    def apt_components(self):
        """
        TODO

        :return:
        """
        return self._apt_components

    @apt_components.setter
    def apt_components(self, value: Union[str, list]):
        """
        Setter for the apt command property.

        :param value: The new value for ``apt_components``.
        """
        self._apt_components = utils.input_string_or_list(value)

    @property
    def apt_dists(self):
        """
        TODO

        :return:
        """
        return self._apt_dists

    @apt_dists.setter
    def apt_dists(self, value: Union[str, list]):
        """
        Setter for the apt dists.

        :param value: The new value for ``apt_dists``.
        """
        self._apt_dists = utils.input_string_or_list(value)

    @property
    def proxy(self):
        """
        TODO

        :return:
        """
        return self._proxy

    @proxy.setter
    def proxy(self, value):
        """
        Setter for the proxy setting of the repository.

        :param value: The new proxy which will be used for the repository.
        """
        self._proxy = value
