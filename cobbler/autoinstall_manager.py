from builtins import object
from builtins import str
import os

from cobbler import autoinstallgen
from cobbler import clogger
from cobbler import utils
from cobbler.cexceptions import CX

TEMPLATING_ERROR = 1
KICKSTART_ERROR = 2


class AutoInstallationManager(object):
    """
    Manage automatic installation templates, snippets and final files
    """

    def __init__(self, collection_mgr, logger=None):
        """
        Constructor for the autoinstall manager.

        :param collection_mgr: The collection manager which has all objects.
        :param logger: The logger object which logs to the desired target. If this argument is None then a default
                       Cobbler logger is created.
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

        :param autoinstall: automatic installation template relative file path
        :type autoinstall: str
        :param for_item: enable/disable special handling for Item objects
        :type for_item: bool
        :param new_autoinstall: when set to true new filenames are allowed
        :type new_autoinstall: bool
        :returns: automatic installation template relative file path
        :rtype: str
        """

        if not isinstance(autoinstall, str):
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

        :returns: A list of automatic installation templates
        :rtype: list
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

        :param file_path: automatic installation template relative file path
        :type file_path: str
        :returns: automatic installation template content
        :rtype: str
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

        :param file_path: automatic installation template relative file path
        :type file_path: str
        :param data: automatic installation template content
        :type data: str
        :rtype: bool
        """

        file_path = self.validate_autoinstall_template_file_path(file_path, for_item=False, new_autoinstall=True)

        file_full_path = "%s/%s" % (self.templates_base_dir, file_path)
        try:
            utils.mkdir(os.path.dirname(file_full_path))
        except:
            utils.die(self.logger, "unable to create directory for automatic OS installation template at %s"
                      % file_path)

        fileh = open(file_full_path, "w+")
        fileh.write(data)
        fileh.close()

        return True

    def remove_autoinstall_template(self, file_path):
        """
        Remove an automatic OS installation template

        :param file_path: automatic installation template relative file path
        :type file_path: str
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

        :param snippet: automatic installation snippet relative file path
        :type snippet: str
        :param new_snippet: when set to true new filenames are allowed
        :type new_snippet: bool
        :returns: Snippet if successful otherwise raises an exception.
        :raises CX: Raised when the arguments are invalid or the action performed raised an internal error.
        :rtype: str
        """

        if not isinstance(snippet, str):
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
        """
        Get a list of all autoinstallation snippets.

        :return: The list of snippets
        :rtype: list
        """
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
        """
        Reads a autoinstall snippet from underneath the configured snippet base dir.

        :param file_path: The relative file path under the configured snippets base dir.
        :type file_path: str
        :return: The read snippet.
        :rtype: str
        """
        file_path = self.validate_autoinstall_snippet_file_path(file_path)

        file_full_path = "%s/%s" % (self.snippets_base_dir, file_path)
        fileh = open(file_full_path, "r")
        data = fileh.read()
        fileh.close()

        return data

    def write_autoinstall_snippet(self, file_path, data):
        """
        Writes a snippet with the given content to the relative path under the snippet root directory.

        :param file_path: The relative path under the configured snippet base dir.
        :type file_path: str
        :param data: The snippet code.
        :type data: str
        """
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
        """
        Remove the autoinstall snippet with the given path.

        :param file_path: The path relative to the configured snippet root.
        :type file_path: str
        :return: A boolean indicating the success of the task.
        :rtype: bool
        """
        file_path = self.validate_autoinstall_snippet_file_path(file_path)

        file_full_path = "%s/%s" % (self.snippets_base_dir, file_path)
        os.remove(file_full_path)

        return True

    def is_autoinstall_in_use(self, name):
        """
        Reports the status if a given system is currently being provisioned.

        :param name: The name of the system.
        :type name: str
        :return: Whether the system is in install mode or not.
        :rtype: bool
        """
        for x in self.collection_mgr.profiles():
            if x.autoinstall is not None and x.autoinstall == name:
                return True
        for x in self.collection_mgr.systems():
            if x.autoinstall is not None and x.autoinstall == name:
                return True
        return False

    def generate_autoinstall(self, profile=None, system=None):
        """
        Generates the autoinstallation for a system or a profile. You may only specifify one parameter. If you specify
        both, the system is generated and the profile argument is ignored.

        :param profile: The Cobbler profile you want an autoinstallation generated for.
        :param system: The Cobbler system you want an autoinstallation generated for.
        :return: The rendered template for the system or profile.
        :rtype: str
        """
        if system is not None:
            return self.autoinstallgen.generate_autoinstall_for_system(system)
        elif profile is not None:
            return self.autoinstallgen.generate_autoinstall_for_profile(profile)

    def log_autoinstall_validation_errors(self, errors_type, errors):
        """
        Log automatic installation file errors

        :param errors_type: validation errors type
        :type errors_type: int
        :param errors: A list with all the errors which occurred.
        :type errors: list
        """

        if errors_type == TEMPLATING_ERROR:
            self.logger.warning("Potential templating errors:")
            for error in errors:
                (line, col) = error["lineCol"]
                line -= 1   # we add some lines to the template data, so numbering is off
                self.logger.warning("Unknown variable found at line %d, column %d: '%s'"
                                    % (line, col, error["rawCode"]))
        elif errors_type == KICKSTART_ERROR:
            self.logger.warning("Kickstart validation errors: %s" % errors[0])

    def validate_autoinstall_file(self, obj, is_profile):
        """
        Validate automatic installation file used by a system/profile.

        :param obj: system/profile
        :param is_profile: if obj is a profile
        :type is_profile: bool
        :returns: [bool, int, list] list with validation result, errors type and list of errors
        :rtype: list
        """

        last_errors = []
        blended = utils.blender(self.collection_mgr.api, False, obj)

        # get automatic installation template
        autoinstall = blended["autoinstall"]
        if autoinstall is None or autoinstall == "":
            self.logger.info("%s has no automatic installation template set, skipping" % obj.name)
            return [True, 0, ()]

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
        else:
            return [True, 0, ()]

    def validate_autoinstall_files(self, logger=None):
        """
        Determine if Cobbler automatic OS installation files will be accepted by corresponding Linux distribution
        installers. The presence of an error does not imply that the automatic installation file is bad, only that the
        possibility exists. Automatic installation file validators are not available for all automatic installation file
        types and on all operating systems in which Cobbler may be installed.

        :param logger: The logger which watches the validation
        :return: True if all automatic installation files are valid, otherwise false.
        :rtype: bool
        """
        overall_success = True

        for x in self.collection_mgr.profiles():
            (success, errors_type, errors) = self.validate_autoinstall_file(x, True)
            if not success:
                overall_success = False
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
