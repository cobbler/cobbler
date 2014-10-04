"""
An Resource is a serializable thing that can appear in a Collection

Copyright 2006-2009, Red Hat, Inc and Others
Kelsey Hightower <khightower@gmail.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA.
"""

from cexceptions import CX
import item


class Resource(item.Item):
    """
    Base Class for management resources.
    """

    def set_action(self, action):
        """
        All management resources have an action. Action determine
        weather a most resources should be created or removed, and
        if packages should be installed or un-installed.
        """
        action = action.lower()
        valid_actions = ['create', 'remove']
        if action not in valid_actions:
            raise CX('%s is not a valid action' % action)
        self.action = action


    def set_group(self, group):
        """
        Unix group ownership of a file or directory.
        """
        self.group = group


    def set_mode(self, mode):
        """
        Unix file permission mode ie: '0644' assigned to
        file and directory resources.
        """
        self.mode = mode


    def set_owner(self, owner):
        """
        Unix owner of a file or directory
        """
        self.owner = owner


    def set_path(self, path):
        """
        File path used by file and directory resources. Normally
        a absolute path of the file or directory to create or
        manage.
        """
        self.path = path


    def set_template(self, template):
        """
        Path to cheetah template on cobbler's local file system.
        Used to generate file data shipped to koan via json. All
        templates have access to flatten autoinstall_meta data.
        """
        self.template = template
