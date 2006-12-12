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
import cexceptions

# TODO: if distribution is detected FC6 or greater, auto-add the mirror stanza
# to the kickstart.

class Repo(item.Item):

    def __init__(self,config):
        self.config = config
        self.clear()

    def clear(self):
        self.name = None                             # is required 
        self.mirror = None                           # is required
        self.keep_updated = 1                        # has reasonable defaults
        self.root = "/var/www/cobbler/repo_mirror"   # has reasonable defaults

    def from_datastruct(self,seed_data):
        self.name = self.load_item(seed_data,'name')
        self.mirror = self.load_item(seed_data,'mirror')
        self.keep_updated = self.load_item(seed_data, 'keep_updated')
        self.root = self.load_item(seed_data, 'root')
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
        if mirror.startswith("rsync://") or mirror.startswith("ssh://"):
            self.mirror = mirror
            return True
        else:
            raise cexceptions.CobblerException("no_mirror")

    def set_keep_updated(self,keep_updated):
        """
	This allows the user to disable updates to a particular repo for whatever reason.
	"""
        if not keep_updated.lower() in ["yes","y","yup","yeah","1"]:  
            self.keep_updated = False
        else:
            self.keep_updated = True
        return True

    def set_root(self,root):
        """
        Sets the directory to mirror in.  Directory will include the name of the repo off of the
        given root.  By default, uses /var/www/cobbler/repomirror/.
        """
        if os.path.isdir(root):
           self.root = root
           return True
        raise cexceptions.CobblerException("no_exist2",root)

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
           'name'         : self.name,
           'mirror'       : self.mirror,
           'keep_updated' : self.keep_updated,
           'root'         : self.root
        }

    def printable(self,id):
        buf =       "repo %-4s       : %s\n" % (id, self.name)
        buf = buf + "mirror          : %s\n" % self.mirror
        buf = buf + "keep updated    : %s\n" % self.keep_updated
        buf = buf + "root            : %s\n" % self.root
        return buf

