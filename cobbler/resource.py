"""
An Resource is a serializable thing that can appear in a Collection

Copyright 2006-2009, Red Hat, Inc
Kelsey Hightower <khightower@gmail.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import item
import utils
from cexceptions import CX

class Resource(item.Item):
    """
    Base Class for management resources.
    """
        
    def set_action(self,action):
        """
        All management resources have an action. Action determine 
        weather a most resources should be created or removed, and
        if packages should be installed or un-installed.
        """
        action = action.lower()
        valid_actions = ['create','remove']
        if action not in valid_actions:
            raise CX('%s is not a valid action' % action)
        self.action = action
        return True
    
    def set_group(self,group):
        """
        Unix group ownership of a file or directory.
        """
        self.group = group
        return True
    
    def set_mode(self,mode):
        """
        Unix file permission mode ie: '0644' assigned to
        file and directory resources.
        """
        self.mode = mode
        return True
    
    def set_owner(self,owner):
        """
        Unix owner of a file or directory
        """
        self.owner = owner
        return True
    
    def set_path(self,path):
        """
        File path used by file and directory resources. Normally 
        a absolute path of the file or directory to create or
        manage.
        """
        self.path = path
        return True
    
    def set_template(self,template):
        """
        Path to cheetah template on cobbler's local file system. 
        Used to generate file data shipped to koan via json. All
        templates have access to flatten ksmeta data.
        """
        self.template = template
        return True