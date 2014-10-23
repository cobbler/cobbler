import os

from cobbler import autoinstallgen
from cobbler import clogger
from cobbler import utils
from cobbler.cexceptions import CX

TEMPLATING_ERROR = 1
KICKSTART_ERROR = 2


class AutoInstallationManager:
    """
    Manage automatic installation templates, snippets and final files
    """

    def __init__(self, collection_mgr, logger=None):
        """
        Constructor

        @param CollectionManager collection_mgr collection manager
        @param Logger logger logger
        """

        self.collection_mgr = collection_mgr
        self.snippets_base_dir = self.collection_mgr.settings().autoinstall_snippets_dir
        self.templates_base_dir = self.collection_mgr.settings().autoinstall_templates_dir
        self.autoinstallgen = autoinstallgen.AutoInstallationGen(self.collection_mgr)
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger

    def validate_autoinstall_template_file_path(self, autoinstall, for_item=True, new_autoinstall=False):
        """
        Validate the automatic installation template's relative file path.

        @param: str autoinstall automatic installation template relative file path
        @param: bool for_item (enable/disable special handling for Item objects)
        @param: bool new_autoinstall (when set to true new filenames are allowed)
        @returns str automatic installation template relative file path
        """

        if not isinstance(autoinstall, basestring):
            raise CX("Invalid input, autoinstall must be a string")
        else:
            autoinstall = autoinstall.strip()

        if autoinstall == "":
            # empty autoinstall is allowed (interactive installations)
            return autoinstall

        if for_item is True:
            # this autoinstall value has special meaning for Items
            # other callers of this function have no use for this
            if autoinstall == "<<inherit>>":
                return autoinstall

        if autoinstall.find("..") != -1:
            raise CX("Invalid automatic installation template file location %s, it must not contain .." % autoinstall)

        autoinstall_path = "%s/%s" % (self.templates_base_dir, autoinstall)
        if not os.path.isfile(autoinstall_path) and not new_autoinstall:
            raise CX("Invalid automatic installation template file location %s, file not found" % autoinstall_path)

        return autoinstall

    def get_autoinstall_templates(self):
        """
        Get automatic OS installation templates

        @return list automatic installation templates
        """

        files = []
        for root, dirnames, filenames in os.walk(self.templates_base_dir):
            for filename in filenames:
                rel_root = root[len(self.templates_base_dir) + 1:]
                if rel_root:
                    rel_path = "%s/%s" % (rel_root, filename)
                else:
                    rel_path = filename
                files.append(rel_path)

        files.sort()
        return files

    def read_autoinstall_template(self, file_path):
        """
        Read an automatic OS installation template

        @param str file_path automatic installation template relative file path
        @return str automatic installation template content
        """

        file_path = self.validate_autoinstall_template_file_path(file_path, for_item=False)

        file_full_path = "%s/%s" % (self.templates_base_dir, file_path)
        fileh = open(file_full_path, "r")
        data = fileh.read()
        fileh.close()

        return data

    def write_autoinstall_template(self, file_path, data):
        """
        Write an automatic OS installation template

        @param str file_path automatic installation template relative file path
        @param str data automatic installation template content
        """

        file_path = self.validate_autoinstall_template_file_path(file_path, for_item=False, new_autoinstall=True)

        file_full_path = "%s/%s" % (self.templates_base_dir, file_path)
        try:
            utils.mkdir(os.path.dirname(file_full_path))
        except:
            utils.die(self.logger, "unable to create directory for automatic OS installation template at %s" % file_path)

        fileh = open(file_full_path, "w+")
        fileh.write(data)
        fileh.close()

        return True

    def remove_autoinstall_template(self, file_path):
        """
        Remove an automatic OS installation template

        @param str file_path automatic installation template relative file path
        """

        file_path = self.validate_autoinstall_template_file_path(file_path, for_item=False)

        file_full_path = "%s/%s" % (self.templates_base_dir, file_path)
        if not self.is_autoinstall_in_use(file_path):
            os.remove(file_full_path)
        else:
            utils.die(self.logger, "attempt to delete in-use file")

    def validate_autoinstall_snippet_file_path(self, snippet, new_snippet=False):
        """
        Validate the snippet's relative file path.

        @param: str snippet automatic installation snippet relative file path
        @param: bool new_snippet (when set to true new filenames are allowed)
        @returns: str snippet or CX
        """

        if not isinstance(snippet, basestring):
            raise CX("Invalid input, snippet must be a string")
        else:
            snippet = snippet.strip()

        if snippet.find("..") != -1:
            raise CX("Invalid automated installation snippet file location %s, it must not contain .." % snippet)

        snippet_path = "%s/%s" % (self.snippets_base_dir, snippet)
        if not os.path.isfile(snippet_path) and not new_snippet:
            raise CX("Invalid automated installation snippet file location %s, file not found" % snippet_path)

        return snippet

    def get_autoinstall_snippets(self):

        files = []
        for root, dirnames, filenames in os.walk(self.snippets_base_dir):

            for filename in filenames:
                rel_root = root[len(self.snippets_base_dir) + 1:]
                if rel_root:
                    rel_path = "%s/%s" % (rel_root, filename)
                else:
                    rel_path = filename
                files.append(rel_path)

        files.sort()
        return files

    def read_autoinstall_snippet(self, file_path):

        file_path = self.validate_autoinstall_snippet_file_path(file_path)

        file_full_path = "%s/%s" % (self.snippets_base_dir, file_path)
        fileh = open(file_full_path, "r")
        data = fileh.read()
        fileh.close()

        return data

    def write_autoinstall_snippet(self, file_path, data):

        file_path = self.validate_autoinstall_snippet_file_path(file_path, new_snippet=True)

        file_full_path = "%s/%s" % (self.snippets_base_dir, file_path)
        try:
            utils.mkdir(os.path.dirname(file_full_path))
        except:
            utils.die(self.logger, "unable to create directory for automatic OS installation snippet at %s" % file_path)

        fileh = open(file_full_path, "w+")
        fileh.write(data)
        fileh.close()

    def remove_autoinstall_snippet(self, file_path):

        file_path = self.validate_autoinstall_snippet_file_path(file_path)
        os.remove(file_path)

        return True

    def is_autoinstall_in_use(self, name):

        for x in self.collection_mgr.profiles():
            if x.autoinstall is not None and x.autoinstall == name:
                return True
        for x in self.collection_mgr.systems():
            if x.autoinstall is not None and x.autoinstall == name:
                return True
        return False

    def generate_autoinstall(self, profile=None, system=None):

        if system is not None:
            return self.autoinstallgen.generate_autoinstall_for_system(system)
        elif profile is not None:
            return self.autoinstallgen.generate_autoinstall_for_profile(profile)

    def log_autoinstall_validation_errors(self, errors_type, errors):
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

    def validate_autoinstall_file(self, obj, is_profile):
        """
        Validate automatic installation file used by a system/profile

        @param Item obj system/profile
        @param bool is_profile if obj is a profile
        @return [bool, int, list] list with validation result, errors type and list of errors
        """

        last_errors = []
        blended = utils.blender(self.collection_mgr.api, False, obj)

        # get automatic installation template
        autoinstall = blended["autoinstall"]
        if autoinstall is None or autoinstall == "":
            self.logger.info("%s has no automatic installation template set, skipping" % obj.name)
            return [True, None, None]

        # generate automatic installation file
        os_version = blended["os_version"]
        self.logger.info("----------------------------")
        self.logger.debug("osversion: %s" % os_version)
        if is_profile:
            self.generate_autoinstall(profile=obj)
        else:
            self.generate_autoinstall(system=obj)
        last_errors = self.autoinstallgen.get_last_errors()
        if len(last_errors) > 0:
            return [False, TEMPLATING_ERROR, last_errors]

    def validate_autoinstall_files(self, logger=None):
        """
        Determine if Cobbler automatic OS installation files will be accepted by
        corresponding Linux distribution installers. The presence of an error
        does not imply that the automatic installation file is bad, only that
        the possibility exists. Automatic installation file validators are not
        available for all automatic installation file types and on all operating
        systems in which Cobbler may be installed.

        @param Logger logger logger
        @return bool if all automatic installation files are valid
        """

        for x in self.collection_mgr.profiles():
            (success, errors_type, errors) = self.validate_autoinstall_file(x, True)
            if not success:
                overall_success = True
            if len(errors) > 0:
                self.log_autoinstall_validation_errors(errors_type, errors)
        for x in self.collection_mgr.systems():
            (success, errors_type, errors) = self.validate_autoinstall_file(x, False)
            if not success:
                overall_success = False
            if len(errors) > 0:
                self.log_autoinstall_validation_errors(errors_type, errors)

        if not overall_success:
            self.logger.warning("*** potential errors detected in automatic installation files ***")
        else:
            self.logger.info("*** all automatic installation files seem to be ok ***")

        return overall_success
