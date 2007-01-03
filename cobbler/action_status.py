"""
Reports on kickstart activity by examining the logs in
/var/log/cobbler.

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
#import re
import cobbler_msg

class BootStatusReport:

   def __init__(self,config):
       """
       Constructor
       """
       self.config   = config
       self.settings = config.settings()

   def run(self):
       """
       Returns None if there are no errors, otherwise returns a list
       of things to correct prior to running application 'for real'.
       (The CLI usage is "cobbler check" before "cobbler sync")
       """
       print "..."
       return True


