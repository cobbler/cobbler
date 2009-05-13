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
from utils import _
import utils
import kickgen

class Validate:

    def __init__(self,config):
        """
        Constructor
        """
        self.config   = config
        self.settings = config.settings()
        self.kickgen  = kickgen.KickGen(config)
        self.ks_cache = []

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
            (result, errors) = self.checkfile(x, True)
            if not result:
                failed = True
            if len(errors) > 0:
                self.print_errors(errors)
        for x in self.config.systems():
            (result, errors) = self.checkfile(x, False)
            if not result:
                failed = True
            if len(errors) > 0:
                self.print_errors(errors)
 
        if failed:
            print _("*** potential errors detected in kickstarts ***")
        else:
            print _("*** all kickstarts seem to be ok ***")

        return failed

    def checkfile(self,obj,is_profile):
        last_errors = []
        blended = utils.blender(self.config.api, False, obj)

        os_version = blended["os_version"]

        print "----------------------------"

        ks = blended["kickstart"]
        if ks is None or ks == "":
            print "%s has no kickstart, skipping" % obj.name
            return [True, last_errors]

        if ks in self.ks_cache:
            print "Skipping kickstart %s, already checked previously" % ks
            return [True, ()]
        else: 
            self.ks_cache.append(ks)

        breed = blended["breed"]
        if breed != "redhat":
            print "%s has a breed of %s, skipping" % (obj.name, breed)
            return [True, last_errors]

        server = blended["server"] 
        if not ks.startswith("/"):
            url = self.kickstart
        else:
            if is_profile:
                url = "http://%s/cblr/svc/op/ks/profile/%s" % (server,obj.name)
                self.kickgen.generate_kickstart_for_profile(obj.name)
            else:
                url = "http://%s/cblr/svc/op/ks/system/%s" % (server,obj.name)
                self.kickgen.generate_kickstart_for_system(obj.name)
            last_errors = self.kickgen.get_last_errors()

        print "checking url: %s" % url

        rc = utils.os_system("/usr/bin/ksvalidator \"%s\"" % url)
        if rc != 0:
            return [False, last_errors]
       
        return [True, last_errors]


    def print_errors(self, errors):
        print _("Potential templating errors:")
        for error in errors:
            (line,col) = error["lineCol"]
            line -= 1 # we add some lines to the template data, so numbering is off
            print _("Unknown variable found at line %d, column %d: '%s'" % (line,col,error["rawCode"]))
