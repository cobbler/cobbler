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
import os.path
import sub_process

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

        # coerce types from input file
        self.set_keep_updated(self.keep_updated)
        self.set_mirror_locally(self.mirror_locally)
        self.set_owners(self.owners)

        return self

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
           'yumopts'          : self.yumopts
        }

    def set_mirror_locally(self,value):
        self.mirror_locally = utils.input_boolean(value)
        return True

    def printable(self):
        buf =       _("repo             : %s\n") % self.name
        buf = buf + _("breed            : %s\n") % self.breed
        buf = buf + _("arch             : %s\n") % self.arch
        buf = buf + _("createrepo_flags : %s\n") % self.createrepo_flags
        buf = buf + _("keep updated     : %s\n") % self.keep_updated
        buf = buf + _("mirror           : %s\n") % self.mirror
        buf = buf + _("mirror locally   : %s\n") % self.mirror_locally
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
            'mirror'           :  self.set_mirror,
            'keep-updated'     :  self.set_keep_updated,
            'priority'         :  self.set_priority,
            'rpm-list'         :  self.set_rpm_list,
            'createrepo-flags' :  self.set_createrepo_flags,
            'yumopts'          :  self.set_yumopts,
            'owners'           :  self.set_owners,
            'mirror-locally'   :  self.set_mirror_locally
        }

    def sync(self, repo_mirror, obj_sync):

        """
        Handle copying of http:// and ftp:// repos.
        """

        # warn about not having yum-utils.  We don't want to require it in the package because
        # RHEL4 and RHEL5U0 don't have it.

        if not os.path.exists("/usr/bin/reposync"):
            raise CX(_("no /usr/bin/reposync found, please install yum-utils"))

        cmd = ""                  # command to run
        is_rhn = False            # RHN repositories require extra black magic
        has_rpm_list = False      # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if self.mirror.lower().startswith("rhn://"):
            is_rhn = True
        if self.rpm_list != "":
            has_rpm_list = True

        # create yum config file for use by reposync
        dest_path = os.path.join(repo_mirror, self.name)
        temp_path = os.path.join(repo_mirror, ".origin")
        if not os.path.isdir(temp_path) and self.mirror_locally:
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)
         
        # how we invoke yum-utils depends on whether this is RHN content or not.

       

        if not is_rhn:

            # this is the simple non-RHN case.
            # create the config file that yum will use for the copying

            if self.mirror_locally:
                temp_file = obj_sync.create_local_file(self, temp_path, output=False)

            if not has_rpm_list and self.mirror_locally:
                # if we have not requested only certain RPMs, use reposync
                cmd = "/usr/bin/reposync %s --config=%s --repoid=%s --download_path=%s" % (obj_sync.rflags, temp_file, self.name, repo_mirror)
                if self.arch != "":
                    if self.arch == "x86":
                       self.arch = "i386" # FIX potential arch errors
                    if self.arch == "i386":
                       # counter-intuitive, but we want the newish kernels too
                       cmd = "%s -a i686" % (cmd)
                    else:
                       cmd = "%s -a %s" % (cmd, self.arch)
                    
                print _("- %s") % cmd

            elif self.mirror_locally:

                # create the output directory if it doesn't exist
                if not os.path.exists(dest_path):
                   os.makedirs(dest_path)

                use_source = ""
                if self.arch == "src":
                    use_source = "--source"
 
                # older yumdownloader sometimes explodes on --resolvedeps
                # if this happens to you, upgrade yum & yum-utils
                extra_flags = obj_sync.settings.yumdownloader_flags
                cmd = "/usr/bin/yumdownloader %s %s -c %s --destdir=%s %s" % (extra_flags, use_source, temp_file, dest_path, " ".join(self.rpm_list))
                print _("- %s") % cmd
        else:

            # this is the somewhat more-complex RHN case.
            # NOTE: this requires that you have entitlements for the server and you give the mirror as rhn://$channelname
            if not self.mirror_locally:
                raise CX(_("rhn:// repos do not work with --mirror-locally=1"))

            if has_rpm_list:
                print _("- warning: --rpm-list is not supported for RHN content")
            rest = self.mirror[6:] # everything after rhn://
            cmd = "/usr/bin/reposync %s -r %s --download_path=%s" % (obj_sync.rflags, rest, repo_mirror)
            if self.name != rest:
                args = { "name" : self.name, "rest" : rest }
                raise CX(_("ERROR: repository %(name)s needs to be renamed %(rest)s as the name of the cobbler repository must match the name of the RHN channel") % args)

            if self.arch == "i386":
                # counter-intuitive, but we want the newish kernels too
                self.arch = "i686"

            if self.arch != "":
                cmd = "%s -a %s" % (cmd, self.arch)

        # now regardless of whether we're doing yumdownloader or reposync
        # or whether the repo was http://, ftp://, or rhn://, execute all queued
        # commands here.  Any failure at any point stops the operation.

        if self.mirror_locally:
            rc = sub_process.call(cmd, shell=True)
            if rc !=0:
                raise CX(_("cobbler reposync failed"))

        # some more special case handling for RHN.
        # create the config file now, because the directory didn't exist earlier

        if is_rhn:
            temp_file = obj_sync.create_local_file(self, temp_path, output=False)

        # now run createrepo to rebuild the index

        if self.mirror_locally:
            os.path.walk(dest_path, self.createrepo_walker, self)

        # create the config file the hosts will use to access the repository.

        obj_sync.create_local_file(self, dest_path)
 
    def createrepo_walker(self, repo, dirname, fnames):
        """
        Used to run createrepo on a copied mirror.
        """
        if os.path.exists(dirname) or repo['breed'] == 'rsync':
            utils.remove_yum_olddata(dirname)
            try:
                cmd = "createrepo %s %s" % (repo.createrepo_flags, dirname)
                print _("- %s") % cmd
                sub_process.call(cmd, shell=True)
            except:
                print _("- createrepo failed.  Is it installed?")
            del fnames[:] # we're in the right place


class RsyncRepo(Repo):

    def sync(self, repo_mirror, obj_sync):

        """
        Handle copying of rsync:// and rsync-over-ssh repos.
        """

        if not self.mirror_locally:
            raise CX(_("rsync:// urls must be mirrored locally, yum cannot access them directly"))

        if self.rpm_list != "":
            print _("- warning: --rpm-list is not supported for rsync'd repositories")
        dest_path = os.path.join(repo_mirror, self.name)
        spacer = ""
        if not self.mirror.startswith("rsync://") and not self.mirror.startswith("/"):
            spacer = "-e ssh"
        if not self.mirror.endswith("/"):
            self.mirror = "%s/" % self.mirror
        cmd = "rsync -rltDv %s --delete --delete-excluded --exclude-from=/etc/cobbler/rsync.exclude %s %s" % (spacer, self.mirror, dest_path)       
        print _("- %s") % cmd
        rc = sub_process.call(cmd, shell=True)
        if rc !=0:
            raise CX(_("cobbler reposync failed"))
        print _("- walking: %s") % dest_path
        os.path.walk(dest_path, self.createrepo_walker, self)
        obj_sync.create_local_file(self, dest_path)
    
class RhnRepo(Repo):

    def sync(self, repo_mirror, obj_sync):

        """
        Handle copying of http:// and ftp:// RHN repos.
        """

        # warn about not having yum-utils.  We don't want to require it in the package because
        # RHEL4 and RHEL5U0 don't have it.

        if not os.path.exists("/usr/bin/reposync"):
            raise CX(_("no /usr/bin/reposync found, please install yum-utils"))

        cmd = ""                  # command to run
        has_rpm_list = False      # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if self.rpm_list != "":
            has_rpm_list = True

        # create yum config file for use by reposync
        dest_path = os.path.join(repo_mirror, self.name)
        temp_path = os.path.join(repo_mirror, ".origin")
        if not os.path.isdir(temp_path) and self.mirror_locally:
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)
         
        # how we invoke yum-utils depends on whether this is RHN content or not.

       
        # this is the somewhat more-complex RHN case.
        # NOTE: this requires that you have entitlements for the server and you give the mirror as rhn://$channelname
        if not self.mirror_locally:
            raise CX(_("rhn:// repos do not work with --mirror-locally=1"))

        if has_rpm_list:
            print _("- warning: --rpm-list is not supported for RHN content")
        rest = self.mirror[6:] # everything after rhn://
        cmd = "/usr/bin/reposync %s -r %s --download_path=%s" % (obj_sync.rflags, rest, repo_mirror)
        if self.name != rest:
            args = { "name" : self.name, "rest" : rest }
            raise CX(_("ERROR: repository %(name)s needs to be renamed %(rest)s as the name of the cobbler repository must match the name of the RHN channel") % args)

        if self.arch == "i386":
            # counter-intuitive, but we want the newish kernels too
            self.arch = "i686"

        if self.arch != "":
            cmd = "%s -a %s" % (cmd, self.arch)

        # now regardless of whether we're doing yumdownloader or reposync
        # or whether the repo was http://, ftp://, or rhn://, execute all queued
        # commands here.  Any failure at any point stops the operation.

        if self.mirror_locally:
            rc = sub_process.call(cmd, shell=True)
            if rc !=0:
                raise CX(_("cobbler reposync failed"))

        # some more special case handling for RHN.
        # create the config file now, because the directory didn't exist earlier

        temp_file = obj_sync.create_local_file(self, temp_path, output=False)

        # now run createrepo to rebuild the index

        if self.mirror_locally:
            os.path.walk(dest_path, self.createrepo_walker, self)

        # create the config file the hosts will use to access the repository.

        obj_sync.create_local_file(self, dest_path)
 

class YumRepo(Repo):

    def sync(self, repo_mirror, obj_sync):

        """
        Handle copying of http:// and ftp:// yum repos.
        """

        # warn about not having yum-utils.  We don't want to require it in the package because
        # RHEL4 and RHEL5U0 don't have it.

        if not os.path.exists("/usr/bin/reposync"):
            raise CX(_("no /usr/bin/reposync found, please install yum-utils"))

        cmd = ""                  # command to run
        has_rpm_list = False      # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if self.rpm_list != "":
            has_rpm_list = True

        # create yum config file for use by reposync
        dest_path = os.path.join(repo_mirror, self.name)
        temp_path = os.path.join(repo_mirror, ".origin")
        if not os.path.isdir(temp_path) and self.mirror_locally:
            # FIXME: there's a chance this might break the RHN D/L case
            os.makedirs(temp_path)
         
        # create the config file that yum will use for the copying

        if self.mirror_locally:
            temp_file = obj_sync.create_local_file(self, temp_path, output=False)

        if not has_rpm_list and self.mirror_locally:
            # if we have not requested only certain RPMs, use reposync
            cmd = "/usr/bin/reposync %s --config=%s --repoid=%s --download_path=%s" % (obj_sync.rflags, temp_file, self.name, repo_mirror)
            if self.arch != "":
                if self.arch == "x86":
                   self.arch = "i386" # FIX potential arch errors
                if self.arch == "i386":
                   # counter-intuitive, but we want the newish kernels too
                   cmd = "%s -a i686" % (cmd)
                else:
                   cmd = "%s -a %s" % (cmd, self.arch)
                    
            print _("- %s") % cmd

        elif self.mirror_locally:

            # create the output directory if it doesn't exist
            if not os.path.exists(dest_path):
               os.makedirs(dest_path)

            use_source = ""
            if self.arch == "src":
                use_source = "--source"
 
            # older yumdownloader sometimes explodes on --resolvedeps
            # if this happens to you, upgrade yum & yum-utils
            extra_flags = obj_sync.settings.yumdownloader_flags
            cmd = "/usr/bin/yumdownloader %s %s -c %s --destdir=%s %s" % (extra_flags, use_source, temp_file, dest_path, " ".join(self.rpm_list))
            print _("- %s") % cmd

        # now regardless of whether we're doing yumdownloader or reposync
        # or whether the repo was http://, ftp://, or rhn://, execute all queued
        # commands here.  Any failure at any point stops the operation.

        if self.mirror_locally:
            rc = sub_process.call(cmd, shell=True)
            if rc !=0:
                raise CX(_("cobbler reposync failed"))

        # now run createrepo to rebuild the index

        if self.mirror_locally:
            os.path.walk(dest_path, self.createrepo_walker, self)

        # create the config file the hosts will use to access the repository.

        obj_sync.create_local_file(self, dest_path)
 
class AptRepo(Repo):

    def sync(self, repo_mirror, obj_sync):

        """
        Handle copying of http:// and ftp:// debian repos.
        """

        # warn about not having mirror program.

        mirror_program = "/usr/bin/debmirror"
        if not os.path.exists(mirror_program):
            raise CX(_("no %s found, please install it")%(mirror_program))

        cmd = ""                  # command to run
        has_rpm_list = False      # flag indicating not to pull the whole repo

        # detect cases that require special handling

        if self.rpm_list != "":
            raise CX(_("has_rpm_list not yet supported on apt repos"))

        # create yum config file for use by reposync
        dest_path = os.path.join(repo_mirror, self.name)
         
        if self.mirror_locally:
            mirror = self.mirror

            idx = mirror.find("://")
            method = mirror[:idx]
            mirror = mirror[idx+3:]

            idx = mirror.find("/")
            host = mirror[:idx]
            mirror = mirror[idx+1:]

            idx = mirror.rfind("/")
            suite = mirror[idx+1:]
            mirror = mirror[:idx]

            mirror_data = "--method=%s --host=%s --root=%s --dist=%s " % ( method , host , mirror , suite )

            # FIXME : flags should come from obj_sync instead of being hardcoded
            rflags = "--passive --nocleanup --ignore-release-gpg --verbose"
            cmd = "%s %s %s %s" % (mirror_program, rflags, mirror_data, dest_path)
            if not self.arch:
                raise CX(_("Architecture is required for apt repositories"))
            if self.arch == "src":
                cmd = "%s --source"
            else:
                use_source = "--source"
                if self.arch == "x86":
                   self.arch = "i386" # FIX potential arch errors
                cmd = "%s -a %s" % (cmd, self.arch)
                    
            print _("- %s") % cmd

            rc = sub_process.call(cmd, shell=True)
            if rc !=0:
                raise CX(_("cobbler reposync failed"))
 
