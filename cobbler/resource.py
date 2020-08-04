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

from cobbler.cexceptions import CX
from cobbler.items import item


class Resource(item.Item):
    """
    Base Class for management resources.
    """

    def set_action(self, action):
        """
        All management resources have an action. Action determine weather a most resources should be created or removed,
        and if packages should be installed or uninstalled.

        :param action: The action which should be executed for the management resource. Must be on of "create" or
                       "remove". Parameter is case-insensitive.
        :type action: str
        """
        action = action.lower()
        valid_actions = ['create', 'remove']
        if action not in valid_actions:
            raise CX('%s is not a valid action' % action)
        self.action = action

    def set_group(self, group):
        """
        Unix group ownership of a file or directory.

        :param group: The group which the resource will belong to.
        """
        self.group = group

    def set_mode(self, mode):
        """
        Unix file permission mode ie: '0644' assigned to file and directory resources.

        :param mode: The mode which the resource will have.
        """
        self.mode = mode

    def set_owner(self, owner):
        """
        Unix owner of a file or directory.

        :param owner: The owner which the resource will belong to.
        """
        self.owner = owner

    def set_path(self, path):
        """
        File path used by file and directory resources.

        :param path: Normally a absolute path of the file or directory to create or manage.
        """
        self.path = path

    def set_template(self, template):
        """
        Path to cheetah template on Cobbler's local file system. Used to generate file data shipped to koan via json.
        All templates have access to flatten autoinstall_meta data.

        :param template: The template to use for the resource.
        """
        self.template = template
