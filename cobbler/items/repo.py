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
from typing import Union

from cobbler.items import item
from cobbler import utils
from cobbler import validate
from cobbler.cexceptions import CX


# this data structure is described in item.py
FIELDS = [
    # non-editable in UI (internal)
    ["ctime", 0, 0, "", False, "", 0, "float"],
    ["depth", 2, 0, "", False, "", 0, "float"],
    ["mtime", 0, 0, "", False, "", 0, "float"],
    ["parent", None, 0, "", False, "", 0, "str"],
    ["uid", None, 0, "", False, "", 0, "str"],

    # editable in UI
    ["apt_components", "", 0, "Apt Components (apt only)", True, "ex: main restricted universe", [], "list"],
    ["apt_dists", "", 0, "Apt Dist Names (apt only)", True, "ex: precise precise-updates", [], "list"],
    ["arch", "x86_64", 0, "Arch", True, "ex: i386, x86_64", ['i386', 'x86_64', 'ia64', 'ppc', 'ppc64', 'ppc64le', 'ppc64el', 's390', 's390x', 'arm', 'aarch64', 'noarch', 'src'], "str"],
    ["breed", "rsync", 0, "Breed", True, "", validate.REPO_BREEDS, "str"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["createrepo_flags", '<<inherit>>', 0, "Createrepo Flags", True, "Flags to use with createrepo", 0, "dict"],
    ["environment", {}, 0, "Environment Variables", True, "Use these environment variables during commands (key=value, space delimited)", 0, "dict"],
    ["keep_updated", True, 0, "Keep Updated", True, "Update this repo on next 'cobbler reposync'?", 0, "bool"],
    ["mirror", None, 0, "Mirror", True, "Address of yum or rsync repo to mirror", 0, "str"],
    ["mirror_type", "baseurl", 0, "Mirror Type", True, "", ["metalink", "mirrorlist", "baseurl"], "str"],
    ["mirror_locally", True, 0, "Mirror locally", True, "Copy files or just reference the repo externally?", 0, "bool"],
    ["name", "", 0, "Name", True, "Ex: f10-i386-updates", 0, "str"],
    ["owners", "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", [], "list"],
    ["priority", 99, 0, "Priority", True, "Value for yum priorities plugin, if installed", 0, "int"],
    ["proxy", "<<inherit>>", 0, "Proxy information", True, "http://example.com:8080, or <<inherit>> to use proxy_url_ext from settings, blank or <<None>> for no proxy", [], "str"],
    ["rpm_list", [], 0, "RPM List", True, "Mirror just these RPMs (yum only)", 0, "list"],
    ["yumopts", {}, 0, "Yum Options", True, "Options to write to yum config file", 0, "dict"],
    ["rsyncopts", "", 0, "Rsync Options", True, "Options to use with rsync repo", 0, "dict"],
]


class Repo(item.Item):
    """
    A Cobbler repo object.
    """

    TYPE_NAME = "repo"
    COLLECTION_TYPE = "repo"

    def __init__(self, *args, **kwargs):
        super(Repo, self).__init__(*args, **kwargs)
        self.breed = None
        self.arch = None
        self.environment = {}
        self.yumopts = {}
        self.rsyncopts = {}
        self.mirror_type = "baseurl"

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):
        """
        Clone this file object. Please manually adjust all value yourself to make the cloned object unique.

        :return: The cloned instance of this object.
        """
        _dict = self.to_dict()
        cloned = Repo(self.collection_mgr)
        cloned.from_dict(_dict)
        return cloned

    def get_fields(self):
        """
        Return all fields which this class has with its current values.

        :return: This is a list with lists.
        """
        return FIELDS

    def get_parent(self):
        """
        Currently the Cobbler object space does not support subobjects of this object as it is conceptually not useful.
        """
        return None

    def check_if_valid(self):
        """
        Checks if the object is valid. Currently checks for name and mirror to be present.
        """
        if self.name is None:
            raise CX("name is required")
        if self.mirror is None:
            raise CX("Error with repo %s - mirror is required" % (self.name))

    #
    # specific methods for item.File
    #

    def _guess_breed(self):
        """
        Guess the breed of a mirror.
        """
        # backwards compatibility
        if not self.breed:
            if self.mirror.startswith("http://") or self.mirror.startswith("https://") or self.mirror.startswith("ftp://"):
                self.set_breed("yum")
            elif self.mirror.startswith("rhn://"):
                self.set_breed("rhn")
            else:
                self.set_breed("rsync")

    def set_mirror(self, mirror):
        """
        A repo is (initially, as in right now) is something that can be rsynced.
        reposync/repotrack integration over HTTP might come later.

        :param mirror: The mirror URI.
        """
        self.mirror = mirror
        if not self.arch:
            if mirror.find("x86_64") != -1:
                self.set_arch("x86_64")
            elif mirror.find("x86") != -1 or mirror.find("i386") != -1:
                self.set_arch("i386")
        self._guess_breed()

    def set_mirror_type(self, mirror_type: str):
        """
        Override the mirror_type used for reposync

        :param mirror_type: The new mirror_type which will be used.
        """
        return utils.set_mirror_type(self, mirror_type)

    def set_keep_updated(self, keep_updated: bool):
        """
        This allows the user to disable updates to a particular repo for whatever reason.

        :param keep_updated: This may be a bool-like value if the repository shall be keept up to date or not.
        """
        self.keep_updated = utils.input_boolean(keep_updated)

    def set_yumopts(self, options: Union[str, dict]):
        """
        Kernel options are a space delimited list.

        :param options: Something like 'a=b c=d e=f g h i=j' or a dictionary.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=False)
        if not success:
            raise CX("invalid yum options")
        else:
            self.yumopts = value

    def set_rsyncopts(self, options: Union[str, dict]):
        """
        rsync options are a space delimited list

        :param options: Something like '-a -S -H -v'
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=False)
        if not success:
            raise CX("invalid rsync options")
        else:
            self.rsyncopts = value

    def set_environment(self, options: Union[str, dict]):
        """
        Yum can take options from the environment. This puts them there before each reposync.

        :param options: These are environment variables which are set before each reposync.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=False)
        if not success:
            raise CX("invalid environment options")
        else:
            self.environment = value

    def set_priority(self, priority: int):
        """
        Set the priority of the repository. Only works if host is using priorities plugin for yum.

        :param priority: Must be a value between 1 and 99. 1 is the highest whereas 99 is the default and lowest.
        """
        try:
            priority = int(str(priority))
        except:
            raise CX("invalid priority level: %s" % priority)
        self.priority = priority

    def set_rpm_list(self, rpms: Union[str, list]):
        """
        Rather than mirroring the entire contents of a repository (Fedora Extras, for instance, contains games, and we
        probably don't want those), make it possible to list the packages one wants out of those repos, so only those
        packages and deps can be mirrored.

        :param rpms: The rpm to mirror. This may be a string or list.
        """
        self.rpm_list = utils.input_string_or_list(rpms)

    def set_createrepo_flags(self, createrepo_flags):
        """
        Flags passed to createrepo when it is called. Common flags to use would be ``-c cache`` or ``-g comps.xml`` to
        generate group information.

        :param createrepo_flags: The createrepo flags which are passed additionally to the default ones.
        """
        if createrepo_flags is None:
            createrepo_flags = ""
        self.createrepo_flags = createrepo_flags

    def set_breed(self, breed: str):
        """
        Setter for the operating system breed.

        :param breed: The new breed to set. If this argument evaluates to false then nothing will be done.
        """
        if breed:
            return utils.set_repo_breed(self, breed)

    def set_os_version(self, os_version):
        """
        Setter for the operating system version.

        :param os_version: The new operating system version. If this argument evaluates to false then nothing will be
                           done.
        """
        if os_version:
            return utils.set_repo_os_version(self, os_version)

    def set_arch(self, arch: str):
        """
        Override the arch used for reposync

        :param arch: The new arch which will be used.
        """
        return utils.set_arch(self, arch, repo=True)

    def set_mirror_locally(self, value: bool):
        """
        Setter for the local mirror property.

        :param value: The new value for ``mirror_locally``.
        """
        self.mirror_locally = utils.input_boolean(value)

    def set_apt_components(self, value: Union[str, list]):
        """
        Setter for the apt command property.

        :param value: The new value for ``apt_components``.
        """
        self.apt_components = utils.input_string_or_list(value)

    def set_apt_dists(self, value: Union[str, list]):
        """
        Setter for the apt dists.

        :param value: The new value for ``apt_dists``.
        :return: ``True`` if everything went correctly.
        """
        self.apt_dists = utils.input_string_or_list(value)
        return True

    def set_proxy(self, value):
        """
        Setter for the proxy setting of the repository.

        :param value: The new proxy which will be used for the repository.
        :return: ``True`` if this succeeds.
        """
        self.proxy = value
        return True
