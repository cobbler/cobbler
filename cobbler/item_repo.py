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

from cobbler import item
from cobbler import utils
from cobbler import validate
from cobbler.cexceptions import CX
from cobbler.utils import _


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
    ["arch", "", 0, "Arch", True, "ex: i386, x86_64", ['i386', 'x86_64', 'ppc', 'ppc64', 'ppc64le', 'ppc64el', "arm", 'noarch', 'src'], "str"],
    ["breed", "", 0, "Breed", True, "", validate.REPO_BREEDS, "str"],
    ["comment", "", 0, "Comment", True, "Free form text description", 0, "str"],
    ["createrepo_flags", '<<inherit>>', 0, "Createrepo Flags", True, "Flags to use with createrepo", 0, "dict"],
    ["environment", {}, 0, "Environment Variables", True, "Use these environment variables during commands (key=value, space delimited)", 0, "dict"],
    ["keep_updated", True, 0, "Keep Updated", True, "Update this repo on next 'cobbler reposync'?", 0, "bool"],
    ["mirror", None, 0, "Mirror", True, "Address of yum or rsync repo to mirror", 0, "str"],
    ["mirror_locally", True, 0, "Mirror locally", True, "Copy files or just reference the repo externally?", 0, "bool"],
    ["name", "", 0, "Name", True, "Ex: f10-i386-updates", 0, "str"],
    ["owners", "SETTINGS:default_ownership", 0, "Owners", True, "Owners list for authz_ownership (space delimited)", [], "list"],
    ["priority", 99, 0, "Priority", True, "Value for yum priorities plugin, if installed", 0, "int"],
    ["proxy", "<<inherit>>", 0, "Proxy information", True, "http://example.com:8080, or <<inherit>> to use proxy_url_ext from settings, blank or <<None>> for no proxy", [], "str"],
    ["rpm_list", [], 0, "RPM List", True, "Mirror just these RPMs (yum only)", 0, "list"],
    ["yumopts", {}, 0, "Yum Options", True, "Options to write to yum config file", 0, "dict"],
]


class Repo(item.Item):
    """
    A Cobbler repo object.
    """

    TYPE_NAME = _("repo")
    COLLECTION_TYPE = "repo"

    def __init__(self, *args, **kwargs):
        super(Repo, self).__init__(*args, **kwargs)
        self.breed = None
        self.arch = None
        self.environment = None
        self.yumopts = None

    #
    # override some base class methods first (item.Item)
    #

    def make_clone(self):

        _dict = self.to_dict()
        cloned = Repo(self.collection_mgr)
        cloned.from_dict(_dict)
        return cloned

    def get_fields(self):
        return FIELDS

    def get_parent(self):
        """
        currently the Cobbler object space does not support subobjects of this object
        as it is conceptually not useful.
        """
        return None

    def check_if_valid(self):
        if self.name is None:
            raise CX("name is required")
        if self.mirror is None:
            raise CX("Error with repo %s - mirror is required" % (self.name))

    #
    # specific methods for item.File
    #

    def _guess_breed(self):
        # backwards compatibility
        if (self.breed == "" or self.breed is None):
            if self.mirror.startswith("http://") or self.mirror.startswith("ftp://") or self.mirror.startswith("https://"):
                self.set_breed("yum")
            elif self.mirror.startswith("rhn://"):
                self.set_breed("rhn")
            else:
                self.set_breed("rsync")

    def set_mirror(self, mirror):
        """
        A repo is (initially, as in right now) is something that can be rsynced.
        reposync/repotrack integration over HTTP might come later.
        """
        self.mirror = mirror
        if self.arch is None or self.arch == "":
            if mirror.find("x86_64") != -1:
                self.set_arch("x86_64")
            elif mirror.find("x86") != -1 or mirror.find("i386") != -1:
                self.set_arch("i386")
        self._guess_breed()

    def set_keep_updated(self, keep_updated):
        """
        This allows the user to disable updates to a particular repo for whatever reason.
        """
        self.keep_updated = utils.input_boolean(keep_updated)

    def set_yumopts(self, options):
        """
        Kernel options are a space delimited list,
        like 'a=b c=d e=f g h i=j' or a dictionary.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=False)
        if not success:
            raise CX(_("invalid yum options"))
        else:
            self.yumopts = value

    def set_environment(self, options):
        """
        Yum can take options from the environment.  This puts them there before
        each reposync.
        """
        (success, value) = utils.input_string_or_dict(options, allow_multiples=False)
        if not success:
            raise CX(_("invalid environment options"))
        else:
            self.environment = value

    def set_priority(self, priority):
        """
        Set the priority of the repository.  1= highest, 99=default
        Only works if host is using priorities plugin for yum.
        """
        try:
            priority = int(str(priority))
        except:
            raise CX(_("invalid priority level: %s") % priority)
        self.priority = priority

    def set_rpm_list(self, rpms):
        """
        Rather than mirroring the entire contents of a repository (Fedora Extras, for instance,
        contains games, and we probably don't want those), make it possible to list the packages
        one wants out of those repos, so only those packages + deps can be mirrored.
        """
        self.rpm_list = utils.input_string_or_list(rpms)

    def set_createrepo_flags(self, createrepo_flags):
        """
        Flags passed to createrepo when it is called.  Common flags to use would be
        -c cache or -g comps.xml to generate group information.
        """
        if createrepo_flags is None:
            createrepo_flags = ""
        self.createrepo_flags = createrepo_flags

    def set_breed(self, breed):
        if breed:
            return utils.set_repo_breed(self, breed)

    def set_os_version(self, os_version):
        if os_version:
            return utils.set_repo_os_version(self, os_version)

    def set_arch(self, arch):
        """
        Override the arch used for reposync
        """
        return utils.set_arch(self, arch, repo=True)

    def set_mirror_locally(self, value):
        self.mirror_locally = utils.input_boolean(value)

    def set_apt_components(self, value):
        self.apt_components = utils.input_string_or_list(value)

    def set_apt_dists(self, value):
        self.apt_dists = utils.input_string_or_list(value)
        return True

    def set_proxy(self, value):
        self.proxy = value
        return True


# EOF
