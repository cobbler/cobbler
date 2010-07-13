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
        if group is None or group == "":
            raise CX("group not specified")
        self.group = group
        return True
    
    def set_mode(self,mode):
        """
        Unix file permission mode ie: '644' assigned to
        file and directory resources.
        """
        if mode is None or mode == "":
            raise CX("mode not specified")
        self.mode = mode
        return True
    
    def set_owner(self,owner):
        """
        Unix owner of a file or directory
        """
        if owner is None or owner == "":
            raise CX("owner not specified")
        self.owner = owner
        return True
    
    def set_path(self,path):
        """
        File path used by file and directory resources. Normally 
        a absolute path of the file or directory to create or
        manage.
        """
        if path is None or path == "":
            raise CX("path not specified")
        self.path = path
        return True
    
    def set_template(self,template):
        """
        Path to cheetah template on cobbler's local file system. 
        Used to generate file data shipped to koan via json. All
        templates have access to flatten ksmeta data.
        """
        if template is None or template == "":
            raise CX("template not specified")
        self.template = template
        return True