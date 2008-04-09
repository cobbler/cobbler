"""
Validates rendered kickstart files.

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import re
import sub_process
from utils import _

class Validate:

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

        if not os.path.exists("/usr/bin/ksvalidator"):
            print _("ksvalidator not installed, please install pykickstart")
            return False 

        failed = False
        for x in self.config.profiles():
            distro = x.get_conceptual_parent()
            if distro.breed != "redhat":
                continue
            if not self.checkfile(x.name, "%s/kickstarts/%s/ks.cfg" % (self.settings.webdir, x.name)):
                failed = True
        for x in self.config.systems():
            distro = x.get_conceptual_parent().get_conceptual_parent()
            if distro.breed != "redhat":
                continue
            if not self.checkfile(x.name, "%s/kickstarts_sys/%s/ks.cfg" % (self.settings.webdir, x.name)):
                failed = True
 
        if failed:
            print _("*** potential errors detected in kickstarts ***")
        else:
            print _("*** all kickstarts seem to be ok ***")

        return failed

    def checkfile(self,name,file):
        # print _("scanning rendered kickstart template: %s" % file)
        if not os.path.exists(file):
            print _("kickstart file does not exist for: %s") % name
            return False
        rc = os.system("/usr/bin/ksvalidator %s" % file)
        if not rc == 0:
            print _("ksvalidator detected a possible problem for: %s") % name
            print _("  rendered kickstart template at: %s" % file)
            return False
        return True

