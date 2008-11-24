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

class Repo(item.Item):

    TYPE_NAME = _("repo")
    COLLECTION_TYPE = "repo"

    def make_clone(self):
        ds = self.to_datastruct()
        cloned = Repo(self.config)
        cloned.from_datastruct(ds)
        return cloned

    def clear(self,is_subobject=False):
        self.parent           = None
        self.name             = None
        self.uid              = ""
        # FIXME: subobject code does not really make sense for repos
        self.mirror           = (None,       '<<inherit>>')[is_subobject]
        self.keep_updated     = (True,        '<<inherit>>')[is_subobject]
        self.priority         = (99,         '<<inherit>>')[is_subobject]
        self.rpm_list         = ("",         '<<inherit>>')[is_subobject]
        self.createrepo_flags = ("-c cache", '<<inherit>>')[is_subobject]
        self.depth            = 2  # arbitrary, as not really apart of the graph
        self.breed            = ""
        self.arch             = "" # use default arch
        self.yumopts          = {}
        self.owners           = self.settings.default_ownership
        self.mirror_locally   = True
        self.environment      = {}
        self.comment          = ""
        self.ctime            = 0
        self.mtime            = 0

    def from_datastruct(self,seed_data):
        self.parent           = self.load_item(seed_data, 'parent')
        self.name             = self.load_item(seed_data, 'name')
        self.mirror           = self.load_item(seed_data, 'mirror')
        self.keep_updated     = self.load_item(seed_data, 'keep_updated',True)
        self.priority         = self.load_item(seed_data, 'priority',99)
        self.rpm_list         = self.load_item(seed_data, 'rpm_list')
        self.createrepo_flags = self.load_item(seed_data, 'createrepo_flags', '-c cache')
        self.breed            = self.load_item(seed_data, 'breed')
        self.arch             = self.load_item(seed_data, 'arch')
        self.depth            = self.load_item(seed_data, 'depth', 2)
        self.yumopts          = self.load_item(seed_data, 'yumopts', {})
        self.owners           = self.load_item(seed_data, 'owners', self.settings.default_ownership)
        self.mirror_locally   = self.load_item(seed_data, 'mirror_locally', True)
        self.environment      = self.load_item(seed_data, 'environment', {})
        self.comment          = self.load_item(seed_data, 'comment', '')

        self.ctime            = self.load_item(seed_data, 'ctime', 0)
        self.mtime            = self.load_item(seed_data, 'mtime', 0)

        # coerce types/values from input file
        self.set_keep_updated(self.keep_updated)
        self.set_mirror_locally(self.mirror_locally)
        self.set_owners(self.owners)
        self.set_environment(self.environment)
        self._guess_breed()

        self.uid = self.load_item(seed_data,'uid','')
        if self.uid == '':
           self.uid = self.config.generate_uid()

        return self

    def _guess_breed(self):
        # backwards compatibility
        if (self.breed == "" or self.breed is None) and self.mirror is not None:
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
        (success, value) = utils.input_string_or_hash(options,None,allow_multiples=False)
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
        (success, value) = utils.input_string_or_hash(options,None,allow_multiples=False)
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
        if type(rpms) != list:
            rpmlist = rpms.split(None)
        else:
            rpmlist = rpms
        try:
            rpmlist.remove('')
        except:
            pass
        self.rpm_list = rpmlist 
        return True

    def set_createrepo_flags(self,createrepo_flags):
        """
        Flags passed to createrepo when it is called.  Common flags to use would be
        -c cache or -g comps.xml to generate group information.
        """
        self.createrepo_flags = createrepo_flags
        return True

    def set_breed(self,breed):
        if breed:
            return utils.set_repo_breed(self,breed)

    def set_arch(self,arch):
        """
        Override the arch used for reposync
        """
        return utils.set_arch(self,arch)

    def is_valid(self):
        """
	A repo is valid if it has a name and a mirror URL
	"""
        if self.name is None:
            raise CX(_("name is required"))
        if self.mirror is None:
            raise CX(_("mirror is required"))
        if self.mirror.startswith("rhn://"):
            # reposync creates directories based on the channel name so this 
            # prevents a lot of ugly special case handling if we make the
            # requirement that repo names match the channels.  It makes sense too.
            if self.mirror != "rhn://%s" % self.name:
                args = { "m1" : self.mirror, "m2" : self.mirror.replace("rhn://","") }
                raise CX(_("Since mirror is RHN %(m1)s, the repo must also be named %(m2)s") % args)
        return True

    def to_datastruct(self):
        return {
           'name'             : self.name,
           'owners'           : self.owners,
           'mirror'           : self.mirror,
           'mirror_locally'   : self.mirror_locally,
           'keep_updated'     : self.keep_updated,
           'priority'         : self.priority,
           'rpm_list'         : self.rpm_list,
           'createrepo_flags' : self.createrepo_flags,
           'breed'            : self.breed,
           'arch'             : self.arch,
           'parent'           : self.parent,
           'depth'            : self.depth,
           'yumopts'          : self.yumopts,
           'environment'      : self.environment,
           'comment'          : self.comment,
           'ctime'            : self.ctime,
           'mtime'            : self.mtime,
           'uid'              : self.uid
        }

    def set_mirror_locally(self,value):
        self.mirror_locally = utils.input_boolean(value)
        return True

    def printable(self):
        buf =       _("repo             : %s\n") % self.name
        buf = buf + _("arch             : %s\n") % self.arch
        buf = buf + _("breed            : %s\n") % self.breed
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
            'arch'             :  self.set_arch,
            'mirror-name'      :  self.set_name,
            'mirror_name'      :  self.set_name,            
            'mirror'           :  self.set_mirror,
            'keep-updated'     :  self.set_keep_updated,
            'keep_updated'     :  self.set_keep_updated,            
            'priority'         :  self.set_priority,
            'rpm-list'         :  self.set_rpm_list,
            'rpm_list'         :  self.set_rpm_list,            
            'createrepo-flags' :  self.set_createrepo_flags,
            'createrepo_flags' :  self.set_createrepo_flags,            
            'yumopts'          :  self.set_yumopts,
            'owners'           :  self.set_owners,
            'mirror-locally'   :  self.set_mirror_locally,
            'mirror_locally'   :  self.set_mirror_locally,            
            'environment'      :  self.set_environment,
            'comment'          :  self.set_comment
        }

