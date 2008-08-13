"""
Validates rendered kickstart files.

Copyright 2007-2008, Red Hat, Inc
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

import os
import re
import sub_process
from utils import _
import utils

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
            if not self.checkfile(x, True):
                failed = True
        for x in self.config.systems():
            if not self.checkfile(x, False):
                failed = True
 
        if failed:
            print _("*** potential errors detected in kickstarts ***")
        else:
            print _("*** all kickstarts seem to be ok ***")

        return failed

    def checkfile(self,obj,is_profile):
        blended = utils.blender(self.config.api, False, obj)
        ks = blended["kickstart"]
        breed = blended["breed"]
        if breed != "redhat":
            print "%s has a breed of %s, skipping" % (obj.name, breed)
            return True
        if ks is None or ks == "":
            print "%s has no kickstart, skipping" % obj.name
            return True

        server = blended["server"] 
        if not ks.startswith("/"):
            url = self.kickstart
        elif is_profile:
            url = "http://%s/cblr/svc/op/ks/profile/%s" % (server,obj.name)
        else:
            url = "http://%s/cblr/svc/op/ks/system/%s" % (server,obj.name)

        print "----------------------------"
        print "checking url: %s" % url


        rc = os.system("/usr/bin/ksvalidator \"%s\"" % url)
        if rc != 0:
            return False
       
        return True

