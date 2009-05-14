"""
A Cobbler repesentation of a yum repo.

Copyright 2006-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

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
from cexceptions import *
from utils import _
import time

FIELDS = [
    [ "parent"              , None ],
    [ "name"                , None ],
    [ "uid"                 , None ],
    [ "mirror"              , None ],
    [ "keep_updated"        , True ],
    [ "priority"            , 99   ],
    [ "rpm_list"            , '<<inherit>>' ],
    [ "createrepo_flags"    , '<<inherit>>' ],
    [ "depth"               , 2  ],
    [ "breed"               , "" ],
    [ "os_version"          , "" ],
    [ "arch"                , "" ],
    [ "yumopts"             , {} ],
    [ "owners"              , "SETTINGS:default_ownership" ],
    [ "mirror_locally"      , True ],
    [ "environment"         , {}   ],
    [ "comment"             , ""   ],
    [ "ctime"               , 0    ],
    [ "mtime"               , 0    ]
]

class Repo(item.Item):

    TYPE_NAME = _("repo")
    COLLECTION_TYPE = "repo"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Repo(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        utils.clear_from_fields(self,FIELDS)

    def from_datastruct(self,seed_data):
        return utils.from_datastruct_from_fields(self,seed_data,FIELDS)

    def _guess_breed(self):
        # backwards compatibility
        if (self.breed == "" or self.breed is None):
           if self.mirror.startswith("http://") or self.mirror.startswith("ftp://"):
              self.set_breed("yum")
           elif self.mirror.startswith("rhn://"):
              self.set_breed("rhn")
           else:
              self.set_breed("rsync")

    def set_mirror(self,mirror):
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
           elif mirror.find("ia64") != -1:
              self.set_arch("ia64")
           elif mirror.find("s390") != -1:
              self.set_arch("s390x")
        self._guess_breed()
        return True

    def set_keep_updated(self,keep_updated):
        """
	This allows the user to disable updates to a particular repo for whatever reason.
	"""
        self.keep_updated = utils.input_boolean(keep_updated)
        return True

    def set_yumopts(self,options,inplace=False):
        """
        Kernel options are a space delimited list,
        like 'a=b c=d e=f g h i=j' or a hash.
        """
        (success, value) = utils.input_string_or_hash(options,allow_multiples=False)
        if not success:
            raise CX(_("invalid yum options"))
        else:
            if inplace:
                for key in value.keys():
                    self.yumopts[key] = value[key]
            else:
                self.yumopts = value
            return True

    def set_environment(self,options,inplace=False):
        """
        Yum can take options from the environment.  This puts them there before
        each reposync.
        """
        (success, value) = utils.input_string_or_hash(options,allow_multiples=False)
        if not success:
            raise CX(_("invalid environment options"))
        else:
            if inplace:
                for key in value.keys():
                    self.environment[key] = value[key]
            else:
                self.environment = value
            return True


    def set_priority(self,priority):
        """
        Set the priority of the repository.  1= highest, 99=default
        Only works if host is using priorities plugin for yum.
        """
        try:
           priority = int(str(priority))
        except:
           raise CX(_("invalid priority level: %s") % priority)
        self.priority = priority
        return True

    def set_rpm_list(self,rpms):
        """
        Rather than mirroring the entire contents of a repository (Fedora Extras, for instance,
        contains games, and we probably don't want those), make it possible to list the packages
        one wants out of those repos, so only those packages + deps can be mirrored.
        """
        self.rpm_list = utils.input_string_or_list(rpms)
        return True

    def set_createrepo_flags(self,createrepo_flags):
        """
        Flags passed to createrepo when it is called.  Common flags to use would be
        -c cache or -g comps.xml to generate group information.
        """
        if createrepo_flags is None:
            createrepo_flags = ""
        self.createrepo_flags = createrepo_flags
        return True

    def set_breed(self,breed):
        if breed:
            return utils.set_repo_breed(self,breed)

    def set_os_version(self,os_version):
        if os_version:
            return utils.set_repo_os_version(self,os_version)

    def set_arch(self,arch):
        """
        Override the arch used for reposync
        """
        return utils.set_arch(self,arch,repo=True)

    def set_mirror_locally(self,value):
        self.mirror_locally = utils.input_boolean(value)
        return True

    def to_datastruct(self):
        return utils.to_datastruct_from_fields(self,FIELDS)

    def printable(self):
        buf =       _("repo             : %s\n") % self.name
        buf = buf + _("arch             : %s\n") % self.arch
        buf = buf + _("breed            : %s\n") % self.breed
        buf = buf + _("os_version       : %s\n") % self.os_version
        buf = buf + _("comment          : %s\n") % self.comment
        buf = buf + _("created          : %s\n") % time.ctime(self.ctime)
        buf = buf + _("createrepo_flags : %s\n") % self.createrepo_flags
        buf = buf + _("environment      : %s\n") % self.environment
        buf = buf + _("keep updated     : %s\n") % self.keep_updated
        buf = buf + _("mirror           : %s\n") % self.mirror
        buf = buf + _("mirror locally   : %s\n") % self.mirror_locally
        buf = buf + _("modified         : %s\n") % time.ctime(self.mtime)
        buf = buf + _("owners           : %s\n") % self.owners
        buf = buf + _("priority         : %s\n") % self.priority
        buf = buf + _("rpm list         : %s\n") % self.rpm_list
        buf = buf + _("yum options      : %s\n") % self.yumopts
        return buf

    def get_parent(self):
        """
        currently the Cobbler object space does not support subobjects of this object
        as it is conceptually not useful.  
        """
        return None

    def remote_methods(self):
        return {
            'name'             :  self.set_name,
            'breed'            :  self.set_breed,
            'os_version'       :  self.set_os_version,
            'arch'             :  self.set_arch,
            'mirror_name'      :  self.set_name,            
            'mirror'           :  self.set_mirror,
            'keep_updated'     :  self.set_keep_updated,            
            'priority'         :  self.set_priority,
            'rpm-list'         :  self.set_rpm_list,
            'rpm_list'         :  self.set_rpm_list,            
            'createrepo_flags' :  self.set_createrepo_flags,            
            'yumopts'          :  self.set_yumopts,
            'owners'           :  self.set_owners,
            'mirror_locally'   :  self.set_mirror_locally,            
            'environment'      :  self.set_environment,
            'comment'          :  self.set_comment
        }

