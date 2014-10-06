"""
Validates rendered automatic OS installation files.

Copyright 2007-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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

import autoinstallgen
import clogger
import utils

TEMPLATING_ERROR = 1
KICKSTART_ERROR = 2

class AutoInstallFilesValidator:

    def __init__(self, collection_mgr, logger=None):
        """
        Constructor

        @param CollectionManager collection_mgr collection manager
        @param Logger logger
        """

        self.collection_mgr = collection_mgr
        self.settings = collection_mgr.settings()
        self.autoinstallgen = autoinstallgen.AutoInstallationGen(collection_mgr)
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger

    def validate_autoinstall_file(self, obj, is_profile):
        """
        Validate automatic installation file used by a system/profile

        @param Item obj system/profile
        @param bool is_profile if obj is a profile
        @return [bool, list] list with validation result and list of errors
        """

        last_errors = []
        blended = utils.blender(self.collection_mgr.api, False, obj)

        # get automatic installation template
        autoinstall = blended["autoinstall"]
        if autoinstall is None or autoinstall == "":
            self.logger.info("%s has no automatic installation template set, skipping" % obj.name)
            return [True, None, None]

        # generate automatic installation file
        server = blended["server"]
        os_version = blended["os_version"]
        self.logger.info("----------------------------")
        self.logger.debug("osversion: %s" % os_version)
        if is_profile:
            url = "http://%s/cblr/svc/op/autoinstall/profile/%s" % (server, obj.name)
            self.autoinstallgen.generate_autoinstall_for_profile(obj.name)
        else:
            url = "http://%s/cblr/svc/op/autoinstall/system/%s" % (server, obj.name)
            self.autoinstallgen.generate_autoinstall_for_system(obj.name)
        last_errors = self.autoinstallgen.get_last_errors()
        if len(last_errors) > 0:
            return [False, TEMPLATING_ERROR, last_errors]

        # run ksvalidator if file is a kickstart file
        breed = blended["breed"]
        if breed != "redhat":
            self.logger.info("%s has a breed of %s, validator only covers automatic installation files of Red Hat based distributions (kickstarts), skipping" % (obj.name, breed))
            return [True, None]
        if not os.path.exists("/usr/bin/ksvalidator"):
            self.logger.info("ksvalidator not installed, please install pykickstart, skipping %s" % obj.name)
            return [True, None, None]
        cmd = "/usr/bin/ksvalidator -v \"%s\" \"%s\"" % (os_version, url)
        out, rc = utils.subprocess_sp(self.logger, cmd)
        if rc != 0:
            return [False, KICKSTART_ERROR, [out]]

        return [True, None, None]


    def log_errors(self, errors_type, errors):
        """
        Log automatic installation file errors

        @param int errors_type validation errors type
        """

        if errors_type == TEMPLATING_ERROR:
            self.logger.warning("Potential templating errors:")
            for error in errors:
                (line, col) = error["lineCol"]
                line -= 1   # we add some lines to the template data, so numbering is off
                self.logger.warning("Unknown variable found at line %d, column %d: '%s'" % (line, col, error["rawCode"]))
        elif errors_type == KICKSTART_ERROR:
            self.logger.warning("Kickstart validation errors: %s" % errors[0])

    def run(self):
        """
        Validate automatic installation files used in all profiles and systems

        @return bool if there are errors
        """

        failed = False
        for x in self.collection_mgr.profiles():
            (success, errors_type, errors) = self.validate_autoinstall_file(x, True)
            if not success:
                overall_success = True
            if len(errors) > 0:
                self.log_errors(errors_type, errors)
        for x in self.collection_mgr.systems():
            (success, errors_type, errors) = self.validate_autoinstall_file(x, False)
            if not success:
                overall_success = False
            if len(errors) > 0:
                self.log_errors(errors_type, errors)

        if not overall_success:
            self.logger.warning("*** potential errors detected in automatic installation files ***")
        else:
            self.logger.info("*** all automatic installation files seem to be ok ***")

        return overall_success


