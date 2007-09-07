"""
A Cobbler repesentation of a yum repo.

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import utils
import item
from cexceptions import *
from rhpl.translate import _, N_, textdomain, utf8

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
        self.mirror           = (None,       '<<inherit>>')[is_subobject]
        self.keep_updated     = ('y',        '<<inherit>>')[is_subobject]
        self.local_filename   = ("",         '<<inherit>>')[is_subobject]
        self.rpm_list         = ("",         '<<inherit>>')[is_subobject]
        self.createrepo_flags = ("-c cache", '<<inherit>>')[is_subobject]
        self.depth            = 2  # arbitrary, as not really apart of the graph         

    def from_datastruct(self,seed_data):
        self.parent           = self.load_item(seed_data, 'parent')
        self.name             = self.load_item(seed_data, 'name')
        self.mirror           = self.load_item(seed_data, 'mirror')
        self.keep_updated     = self.load_item(seed_data, 'keep_updated','y')
        self.local_filename   = self.load_item(seed_data, 'local_filename')
        self.rpm_list         = self.load_item(seed_data, 'rpm_list')
        self.createrepo_flags = self.load_item(seed_data, 'createrepo_flags', '-c cache')
        self.depth            = self.load_item(seed_data, 'depth', 2)

        # force this to be saved as a boolean 
        self.set_keep_updated(self.keep_updated)

        return self

    def set_name(self,name):
        """
        A name can be anything.  It's a string, though best values are something like "fc6extras"
        or "myrhel4stuff"
        """
        self.name = name  # we check it add time, but store the original value.
        return True

    def set_mirror(self,mirror):
        """
        A repo is (initially, as in right now) is something that can be rsynced.
        reposync/repotrack integration over HTTP might come later.
        """
        self.mirror = mirror
        return True

    def set_keep_updated(self,keep_updated):
        """
	This allows the user to disable updates to a particular repo for whatever reason.
	"""
        if type(keep_updated) == bool:
            self.keep_updated = keep_updated
            return True
        if not str(keep_updated).lower() in ["yes","y","yup","yeah","1","true"]:  
            self.keep_updated = False
        else:
            self.keep_updated = True
        return True

    def set_local_filename(self,fname):
        """
        If this repo is to be automatically configured to be "in use" for profiles that reference it,
        the local filename must be specified.  This allows, for instance, to define a repo foo and autocreate
        a foo.repo on the system that corresponds to it in /etc/yum.repos.d.  

        You can overwrite default repos by doing this, so
        setting a value of something like "fedora-updates" has some significance.  If you just name it foo, it's 
        a bonus repo of your own special stuff.   This is only used if the distro has set_repos() called on it
        with the name of this repo.

        NOTE: this should not contain the ".repo" in the filename.  The kickstart will add that part.
        """
        self.local_filename = fname
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

    def set_createrepo_flags(self,createrepo_flags):
        """
        Flags passed to createrepo when it is called.  Common flags to use would be
        -c cache or -g comps.xml to generate group information.
        """
        self.createrepo_flags = createrepo_flags
        return True

    def is_valid(self):
        """
	A repo is valid if it has a name and a mirror URL
	"""
        if self.name is None:
            return False
        if self.mirror is None:
            return False
        return True

    def to_datastruct(self):
        return {
           'name'             : self.name,
           'mirror'           : self.mirror,
           'keep_updated'     : self.keep_updated,
           'local_filename'   : self.local_filename,
           'rpm_list'         : self.rpm_list,
           'createrepo_flags' : self.createrepo_flags,
           'parent'           : self.parent,
           'depth'            : self.depth
        }

    def printable(self):
        buf =       _("repo             : %s\n") % self.name
        buf = buf + _("mirror           : %s\n") % self.mirror
        buf = buf + _("keep updated     : %s\n") % self.keep_updated
        buf = buf + _("local filename   : %s\n") % self.local_filename
        buf = buf + _("rpm list         : %s\n") % self.rpm_list
        buf = buf + _("createrepo_flags : %s\n") % self.createrepo_flags
        return buf

    def get_parent(self):
        """
        currently the Cobbler object space does not support subobjects of this object
        as it is conceptually not useful.  
        """
        return None

    def is_rsync_mirror(self):
        """
        Returns True if this mirror is synchronized using rsync, False otherwise
        """
        lower = self.mirror.lower()
        if lower.startswith("http://") or lower.startswith("ftp://") or lower.startswith("rhn://"):
            return False
        else:
            return True

