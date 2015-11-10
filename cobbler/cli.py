"""
Command line interface for cobbler.

Copyright 2006-2009, Red Hat, Inc and Others
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

import exceptions
import optparse
import os
import sys
import time
import traceback
import xmlrpclib

from cobbler import field_info
from cobbler import item_distro
from cobbler import item_profile
from cobbler import item_system
from cobbler import item_repo
from cobbler import item_image
from cobbler import item_mgmtclass
from cobbler import item_package
from cobbler import item_file
from cobbler import settings
from cobbler import utils


OBJECT_ACTIONS_MAP = {
    "distro": "add copy edit find list remove rename report".split(" "),
    "profile": "add copy dumpvars edit find get-autoinstall list remove rename report".split(" "),
    "system": "add copy dumpvars edit find get-autoinstall list remove rename report poweron poweroff powerstatus reboot".split(" "),
    "image": "add copy edit find list remove rename report".split(" "),
    "repo": "add copy edit find list remove rename report".split(" "),
    "mgmtclass": "add copy edit find list remove rename report".split(" "),
    "package": "add copy edit find list remove rename report".split(" "),
    "file": "add copy edit find list remove rename report".split(" "),
    "setting": "edit report".split(" "),
    "signature": "reload report update".split(" ")
}

OBJECT_TYPES = OBJECT_ACTIONS_MAP.keys()
# would like to use from_iterable here, but have to support python 2.4
OBJECT_ACTIONS = []
for actions in OBJECT_ACTIONS_MAP.values():
    OBJECT_ACTIONS += actions
DIRECT_ACTIONS = "aclsetup buildiso import list replicate report reposync sync validate-autoinstalls version signature get-loaders hardlink".split()

####################################################


def report_items(remote, otype):
    if otype == "setting":
        items = remote.get_settings()
        keys = items.keys()
        keys.sort()
        for key in keys:
            item = {'name': key, 'value': items[key]}
            report_item(remote, otype, item=item)
    elif otype == "signature":
        items = remote.get_signatures()
        total_breeds = 0
        total_sigs = 0
        if "breeds" in items:
            print "Currently loaded signatures:"
            bkeys = items["breeds"].keys()
            bkeys.sort()
            total_breeds = len(bkeys)
            for breed in bkeys:
                print "%s:" % breed
                oskeys = items["breeds"][breed].keys()
                oskeys.sort()
                if len(oskeys) > 0:
                    total_sigs += len(oskeys)
                    for osversion in oskeys:
                        print "\t%s" % osversion
                else:
                    print "\t(none)"
            print "\n%d breeds with %d total signatures loaded" % (total_breeds, total_sigs)
        else:
            print "No breeds found in the signature, a signature update is recommended"
            sys.exit(1)
    else:
        items = remote.get_items(otype)
        for x in items:
            report_item(remote, otype, item=x)


def report_item(remote, otype, item=None, name=None):
    if item is None:
        if otype == "setting":
            cur_settings = remote.get_settings()
            try:
                item = {'name': name, 'value': cur_settings[name]}
            except:
                print "Setting not found: %s" % name
                sys.exit(1)
        elif otype == "signature":
            items = remote.get_signatures()
            total_sigs = 0
            if "breeds" in items:
                print "Currently loaded signatures:"
                if name in items["breeds"]:
                    print "%s:" % name
                    oskeys = items["breeds"][name].keys()
                    oskeys.sort()
                    if len(oskeys) > 0:
                        total_sigs += len(oskeys)
                        for osversion in oskeys:
                            print "\t%s" % osversion
                    else:
                        print "\t(none)"
                    print "\nBreed '%s' has %d total signatures" % (name, total_sigs)
                else:
                    print "No breed named '%s' found" % name
                    sys.exit(1)
            else:
                print "No breeds found in the signature, a signature update is recommended"
                sys.exit(1)
            return
        else:
            item = remote.get_item(otype, name)
            if item == "~":
                print "No %s found: %s" % (otype, name)
                sys.exit(1)

    if otype == "distro":
        data = utils.to_string_from_fields(item, item_distro.FIELDS)
    elif otype == "profile":
        data = utils.to_string_from_fields(item, item_profile.FIELDS)
    elif otype == "system":
        data = utils.to_string_from_fields(item, item_system.FIELDS,
                                           item_system.NETWORK_INTERFACE_FIELDS)
    elif otype == "repo":
        data = utils.to_string_from_fields(item, item_repo.FIELDS)
    elif otype == "image":
        data = utils.to_string_from_fields(item, item_image.FIELDS)
    elif otype == "mgmtclass":
        data = utils.to_string_from_fields(item, item_mgmtclass.FIELDS)
    elif otype == "package":
        data = utils.to_string_from_fields(item, item_package.FIELDS)
    elif otype == "file":
        data = utils.to_string_from_fields(item, item_file.FIELDS)
    elif otype == "setting":
        data = "%-40s: %s" % (item['name'], item['value'])
    print data


def list_items(remote, otype):
    items = remote.get_item_names(otype)
    items.sort()
    for x in items:
        print "   %s" % x


def n2s(data):
    """
    Return spaces for None
    """
    if data is None:
        return ""
    return data


def opt(options, k, defval=""):
    """
    Returns an option from an Optparse values instance
    """
    try:
        data = getattr(options, k)
    except:
        # FIXME: debug only
        # traceback.print_exc()
        return defval
    return n2s(data)


def _add_parser_option_from_field(parser, field, settings):

    # extract data from field dictionary
    name = field[0]
    default = field[1]
    if isinstance(default, basestring) and default.startswith("SETTINGS:"):
        setting_name = default.replace("SETTINGS:", "", 1)
        default = settings[setting_name]
    description = field[3]
    tooltip = field[5]
    choices = field[6]
    if choices and default not in choices:
        raise Exception("field %s default value (%s) is not listed in choices (%s)" % (name, default, str(choices)))
    if tooltip != "":
        description += " (%s)" % tooltip

    # generate option string
    option_string = "--%s" % name.replace("_", "-")

    # generate option aliases
    aliases = []
    for deprecated_field in field_info.DEPRECATED_FIELDS.keys():
        if field_info.DEPRECATED_FIELDS[deprecated_field] == name:
            aliases.append("--%s" % deprecated_field)

    # add option to parser
    if isinstance(choices, list) and len(choices) != 0:
        description += " (valid options: %s)" % ",".join(choices)
        parser.add_option(option_string, dest=name, help=description, choices=choices)
        for alias in aliases:
            parser.add_option(alias, dest=name, help=description, choices=choices)
    else:
        parser.add_option(option_string, dest=name, help=description)
        for alias in aliases:
            parser.add_option(alias, dest=name, help=description)


def add_options_from_fields(object_type, parser, fields, network_interface_fields, settings, object_action):

    if object_action in ["add", "edit", "find", "copy", "rename"]:
        for field in fields:
            _add_parser_option_from_field(parser, field, settings)

        # system object
        if object_type == "system":
            for field in network_interface_fields:
                _add_parser_option_from_field(parser, field, settings)

            parser.add_option("--interface", dest="interface", help="the interface to operate on (can only be specified once per command line)")
            if object_action in ["add", "edit"]:
                parser.add_option("--delete-interface", dest="delete_interface", action="store_true")
                parser.add_option("--rename-interface", dest="rename_interface")

        if object_action in ["copy", "rename"]:
            parser.add_option("--newname", help="new object name")

        if object_action not in ["find"] and object_type != "setting":
            parser.add_option("--in-place", action="store_true", default=False, dest="in_place", help="edit items in kopts or autoinstall without clearing the other items")

    elif object_action == "remove":
        parser.add_option("--name", help="%s name to remove" % object_type)
        parser.add_option("--recursive", action="store_true", dest="recursive", help="also delete child objects")

    # FIXME: not supported in 2.0 ?
    # if not object_action in ["dumpvars","find","remove","report","list"]:
    #    parser.add_option("--no-sync",     action="store_true", dest="nosync", help="suppress sync for speed")


class CobblerCLI:

    def __init__(self):
        # Load server ip and ports from local config
        self.url_cobbler_api = utils.local_get_cobbler_api_url()
        self.url_cobbler_xmlrpc = utils.local_get_cobbler_xmlrpc_url()

        # FIXME: allow specifying other endpoints, and user+pass
        self.parser = optparse.OptionParser()
        self.remote = xmlrpclib.Server(self.url_cobbler_api)
        self.shared_secret = utils.get_shared_secret()

    def start_task(self, name, options):
        options = utils.strip_none(vars(options), omit_none=True)
        fn = getattr(self.remote, "background_%s" % name)
        return fn(options, self.token)

    def get_object_type(self, args):
        """
        If this is a CLI command about an object type, e.g. "cobbler distro add", return the type, like "distro"
        """
        if len(args) < 2:
            return None
        elif args[1] in OBJECT_TYPES:
            return args[1]
        return None

    def get_object_action(self, object_type, args):
        """
        If this is a CLI command about an object type, e.g. "cobbler distro add", return the action, like "add"
        """
        if object_type is None or len(args) < 3:
            return None
        if args[2] in OBJECT_ACTIONS_MAP[object_type]:
            return args[2]
        return None

    def get_direct_action(self, object_type, args):
        """
        If this is a general command, e.g. "cobbler hardlink", return the action, like "hardlink"
        """
        if object_type is not None:
            return None
        elif len(args) < 2:
            return None
        elif args[1] == "--help":
            return None
        elif args[1] == "--version":
            return "version"
        else:
            return args[1]

    def check_setup(self):
        """
        Detect permissions and service accessibility problems and provide
        nicer error messages for them.
        """

        s = xmlrpclib.Server(self.url_cobbler_xmlrpc)
        try:
            s.ping()
        except Exception, e:
            print >> sys.stderr, "cobblerd does not appear to be running/accessible: %s" % repr(e)
            sys.exit(411)

        s = xmlrpclib.Server(self.url_cobbler_api)
        try:
            s.ping()
        except:
            print >> sys.stderr, "httpd does not appear to be running and proxying cobbler, or SELinux is in the way. Original traceback:"
            traceback.print_exc()
            sys.exit(411)

        if not os.path.exists("/var/lib/cobbler/web.ss"):
            print >> sys.stderr, "Missing login credentials file.  Has cobblerd failed to start?"
            sys.exit(411)

        if not os.access("/var/lib/cobbler/web.ss", os.R_OK):
            print >> sys.stderr, "User cannot run command line, need read access to /var/lib/cobbler/web.ss"
            sys.exit(411)

    def run(self, args):
        """
        Process the command line and do what the user asks.
        """
        self.token = self.remote.login("", self.shared_secret)
        object_type = self.get_object_type(args)
        object_action = self.get_object_action(object_type, args)
        direct_action = self.get_direct_action(object_type, args)

        try:
            if object_type is not None:
                if object_action is not None:
                    self.object_command(object_type, object_action)
                else:
                    self.print_object_help(object_type)

            elif direct_action is not None:
                self.direct_command(direct_action)

            else:
                self.print_help()
        except xmlrpclib.Fault, err:
            if err.faultString.find("cobbler.cexceptions.CX") != -1:
                print self.cleanup_fault_string(err.faultString)
            else:
                print "### ERROR ###"
                print "Unexpected remote error, check the server side logs for further info"
                print err.faultString
                sys.exit(1)

    def cleanup_fault_string(self, str):
        """
        Make a remote exception nicely readable by humans so it's not evident that is a remote
        fault.  Users should not have to understand tracebacks.
        """
        if str.find(">:") != -1:
            (first, rest) = str.split(">:", 1)
            if rest.startswith("\"") or rest.startswith("\'"):
                rest = rest[1:]
            if rest.endswith("\"") or rest.endswith("\'"):
                rest = rest[:-1]
            return rest
        else:
            return str

    def get_fields(self, object_type):
        """
        For a given name of an object type, return the FIELDS data structure.
        """
        # FIXME: this should be in utils, or is it already?
        if object_type == "distro":
            return item_distro.FIELDS
        elif object_type == "profile":
            return item_profile.FIELDS
        elif object_type == "system":
            return item_system.FIELDS
        elif object_type == "repo":
            return item_repo.FIELDS
        elif object_type == "image":
            return item_image.FIELDS
        elif object_type == "mgmtclass":
            return item_mgmtclass.FIELDS
        elif object_type == "package":
            return item_package.FIELDS
        elif object_type == "file":
            return item_file.FIELDS
        elif object_type == "setting":
            return settings.FIELDS

    def object_command(self, object_type, object_action):
        """
        Process object-based commands such as "distro add" or "profile rename"
        """
        task_id = -1        # if assigned, we must tail the logfile
        settings = self.remote.get_settings()

        fields = self.get_fields(object_type)
        network_interface_fields = None
        if object_type == "system":
            network_interface_fields = item_system.NETWORK_INTERFACE_FIELDS
        if object_action in ["add", "edit", "copy", "rename", "find", "remove"]:
            add_options_from_fields(object_type, self.parser, fields,
                                    network_interface_fields, settings, object_action)
        elif object_action in ["list"]:
            pass
        elif object_action not in ("reload", "update"):
            self.parser.add_option("--name", dest="name", help="name of object")
        elif object_action == "reload":
            self.parser.add_option("--filename", dest="filename", help="filename to load data from")
        (options, args) = self.parser.parse_args()

        # the first three don't require a name
        if object_action == "report":
            if options.name is not None:
                report_item(self.remote, object_type, None, options.name)
            else:
                report_items(self.remote, object_type)
        elif object_action == "list":
            list_items(self.remote, object_type)
        elif object_action == "find":
            items = self.remote.find_items(object_type, utils.strip_none(vars(options), omit_none=True), "name", False)
            for item in items:
                print item
        elif object_action in OBJECT_ACTIONS:
            if opt(options, "name") == "" and object_action not in ("reload", "update"):
                print "--name is required"
                sys.exit(1)
            if object_action in ["add", "edit", "copy", "rename", "remove"]:
                try:
                    if object_type == "setting":
                        settings = self.remote.get_settings()
                        if options.value is None:
                            raise RuntimeError("You must specify a --value when editing a setting")
                        elif not settings.get('allow_dynamic_settings', False):
                            raise RuntimeError("Dynamic settings changes are not enabled. Change the allow_dynamic_settings to 1 and restart cobblerd to enable dynamic settings changes")
                        elif options.name == 'allow_dynamic_settings':
                            raise RuntimeError("Cannot modify that setting live")
                        elif self.remote.modify_setting(options.name, options.value, self.token):
                            raise RuntimeError("Changing the setting failed")
                    else:
                        self.remote.xapi_object_edit(object_type, options.name, object_action, utils.strip_none(vars(options), omit_none=True), self.token)
                except xmlrpclib.Fault, (err):
                    (etype, emsg) = err.faultString.split(":", 1)
                    print "exception on server: %s" % emsg
                    sys.exit(1)
                except RuntimeError, (err):
                    print err.args[0]
                    sys.exit(1)
            elif object_action == "get-autoinstall":
                if object_type == "profile":
                    data = self.remote.generate_profile_autoinstall(options.name)
                elif object_type == "system":
                    data = self.remote.generate_system_autoinstall(options.name)
                print data
            elif object_action == "dumpvars":
                if object_type == "profile":
                    data = self.remote.get_blended_data(options.name, "")
                elif object_type == "system":
                    data = self.remote.get_blended_data("", options.name)
                # FIXME: pretty-printing and sorting here
                keys = data.keys()
                keys.sort()
                for x in keys:
                    print "%s: %s" % (x, data[x])
            elif object_action in ["poweron", "poweroff", "powerstatus", "reboot"]:
                power = {}
                power["power"] = object_action.replace("power", "")
                power["systems"] = [options.name]
                task_id = self.remote.background_power_system(power, self.token)
            elif object_action == "update":
                task_id = self.remote.background_signature_update(utils.strip_none(vars(options), omit_none=True), self.token)
            elif object_action == "reload":
                filename = opt(options, "filename", "/var/lib/cobbler/distro_signatures.json")
                try:
                    utils.load_signatures(filename, cache=True)
                except:
                    print "There was an error loading the signature data in %s." % filename
                    print "Please check the JSON file or run 'cobbler signature update'."
                    return
                else:
                    print "Signatures were successfully loaded"
            else:
                raise exceptions.NotImplementedError()
        else:
            raise exceptions.NotImplementedError()

        # FIXME: add tail/polling code here
        if task_id != -1:
            self.print_task(task_id)
            self.follow_task(task_id)

    # BOOKMARK
    def direct_command(self, action_name):
        """
        Process non-object based commands like "sync" and "hardlink"
        """
        task_id = -1        # if assigned, we must tail the logfile

        if action_name == "buildiso":

            defaultiso = os.path.join(os.getcwd(), "generated.iso")
            self.parser.add_option("--iso", dest="iso", default=defaultiso, help="(OPTIONAL) output ISO to this file")
            self.parser.add_option("--profiles", dest="profiles", help="(OPTIONAL) use these profiles only")
            self.parser.add_option("--systems", dest="systems", help="(OPTIONAL) use these systems only")
            self.parser.add_option("--tempdir", dest="buildisodir", help="(OPTIONAL) working directory")
            self.parser.add_option("--distro", dest="distro", help="(OPTIONAL) used with --standalone and --airgapped to create a distro-based ISO including all associated profiles/systems")
            self.parser.add_option("--standalone", dest="standalone", action="store_true", help="(OPTIONAL) creates a standalone ISO with all required distro files, but without any added repos")
            self.parser.add_option("--airgapped", dest="airgapped", action="store_true", help="(OPTIONAL) creates a standalone ISO with all distro and repo files for disconnected system installation")
            self.parser.add_option("--source", dest="source", help="(OPTIONAL) used with --standalone to specify a source for the distribution files")
            self.parser.add_option("--exclude-dns", dest="exclude_dns", action="store_true", help="(OPTIONAL) prevents addition of name server addresses to the kernel boot options")
            self.parser.add_option("--mkisofs-opts", dest="mkisofs_opts", help="(OPTIONAL) extra options for mkisofs")

            (options, args) = self.parser.parse_args()
            task_id = self.start_task("buildiso", options)

        elif action_name == "replicate":
            self.parser.add_option("--master", dest="master", help="Cobbler server to replicate from.")
            self.parser.add_option("--distros", dest="distro_patterns", help="patterns of distros to replicate")
            self.parser.add_option("--profiles", dest="profile_patterns", help="patterns of profiles to replicate")
            self.parser.add_option("--systems", dest="system_patterns", help="patterns of systems to replicate")
            self.parser.add_option("--repos", dest="repo_patterns", help="patterns of repos to replicate")
            self.parser.add_option("--image", dest="image_patterns", help="patterns of images to replicate")
            self.parser.add_option("--mgmtclasses", dest="mgmtclass_patterns", help="patterns of mgmtclasses to replicate")
            self.parser.add_option("--packages", dest="package_patterns", help="patterns of packages to replicate")
            self.parser.add_option("--files", dest="file_patterns", help="patterns of files to replicate")
            self.parser.add_option("--omit-data", dest="omit_data", action="store_true", help="do not rsync data")
            self.parser.add_option("--sync-all", dest="sync_all", action="store_true", help="sync all data")
            self.parser.add_option("--prune", dest="prune", action="store_true", help="remove objects (of all types) not found on the master")
            self.parser.add_option("--use-ssl", dest="use_ssl", action="store_true", help="use ssl to access the Cobbler master server api")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("replicate", options)

        elif action_name == "aclsetup":
            self.parser.add_option("--adduser", dest="adduser", help="give acls to this user")
            self.parser.add_option("--addgroup", dest="addgroup", help="give acls to this group")
            self.parser.add_option("--removeuser", dest="removeuser", help="remove acls from this user")
            self.parser.add_option("--removegroup", dest="removegroup", help="remove acls from this group")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("aclsetup", options)

        elif action_name == "version":
            version = self.remote.extended_version()
            print "Cobbler %s" % version["version"]
            print "  source: %s, %s" % (version["gitstamp"], version["gitdate"])
            print "  build time: %s" % version["builddate"]

        elif action_name == "hardlink":
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("hardlink", options)
        elif action_name == "reserialize":
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("reserialize", options)
        elif action_name == "status":
            (options, args) = self.parser.parse_args()
            print self.remote.get_status("text", self.token)
        elif action_name == "validate-autoinstalls":
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("validate_autoinstall_files", options)
        elif action_name == "get-loaders":
            self.parser.add_option("--force", dest="force", action="store_true", help="overwrite any existing content in /var/lib/cobbler/loaders")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("dlcontent", options)
        elif action_name == "import":
            self.parser.add_option("--arch", dest="arch", help="OS architecture being imported")
            self.parser.add_option("--breed", dest="breed", help="the breed being imported")
            self.parser.add_option("--os-version", dest="os_version", help="the version being imported")
            self.parser.add_option("--path", dest="path", help="local path or rsync location")
            self.parser.add_option("--name", dest="name", help="name, ex 'RHEL-5'")
            self.parser.add_option("--available-as", dest="available_as", help="tree is here, don't mirror")
            self.parser.add_option("--autoinstall", dest="autoinstall_file", help="assign this autoinstall file")
            self.parser.add_option("--rsync-flags", dest="rsync_flags", help="pass additional flags to rsync")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("import", options)
        elif action_name == "reposync":
            self.parser.add_option("--only", dest="only", help="update only this repository name")
            self.parser.add_option("--tries", dest="tries", help="try each repo this many times", default=1)
            self.parser.add_option("--no-fail", dest="nofail", help="don't stop reposyncing if a failure occurs", action="store_true")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("reposync", options)
        elif action_name == "aclsetup":
            (options, args) = self.parser.parse_args()
            # FIXME: missing options, add them here
            task_id = self.start_task("aclsetup", options)
        elif action_name == "check":
            results = self.remote.check(self.token)
            ct = 0
            if len(results) > 0:
                print "The following are potential configuration items that you may want to fix:\n"
                for r in results:
                    ct += 1
                    print "%s: %s" % (ct, r)
                print "\nRestart cobblerd and then run 'cobbler sync' to apply changes."
            else:
                print "No configuration problems found.  All systems go."

        elif action_name == "sync":
            (options, args) = self.parser.parse_args()
            self.parser.add_option("--verbose", dest="verbose", action="store_true", help="run sync with more output")
            task_id = self.start_task("sync", options)
        elif action_name == "report":
            (options, args) = self.parser.parse_args()
            print "distros:\n=========="
            report_items(self.remote, "distro")
            print "\nprofiles:\n=========="
            report_items(self.remote, "profile")
            print "\nsystems:\n=========="
            report_items(self.remote, "system")
            print "\nrepos:\n=========="
            report_items(self.remote, "repo")
            print "\nimages:\n=========="
            report_items(self.remote, "image")
            print "\nmgmtclasses:\n=========="
            report_items(self.remote, "mgmtclass")
            print "\npackages:\n=========="
            report_items(self.remote, "package")
            print "\nfiles:\n=========="
            report_items(self.remote, "file")
        elif action_name == "list":
            # no tree view like 1.6?  This is more efficient remotely
            # for large configs and prevents xfering the whole config
            # though we could consider that...
            (options, args) = self.parser.parse_args()
            print "distros:"
            list_items(self.remote, "distro")
            print "\nprofiles:"
            list_items(self.remote, "profile")
            print "\nsystems:"
            list_items(self.remote, "system")
            print "\nrepos:"
            list_items(self.remote, "repo")
            print "\nimages:"
            list_items(self.remote, "image")
            print "\nmgmtclasses:"
            list_items(self.remote, "mgmtclass")
            print "\npackages:"
            list_items(self.remote, "package")
            print "\nfiles:"
            list_items(self.remote, "file")
        else:
            print "No such command: %s" % action_name
            sys.exit(1)
            # FIXME: run here

        # FIXME: add tail/polling code here
        if task_id != -1:
            self.print_task(task_id)
            self.follow_task(task_id)

        return True

    def print_task(self, task_id):
        print "task started: %s" % task_id
        events = self.remote.get_events()
        (etime, name, status, who_viewed) = events[task_id]
        atime = time.asctime(time.localtime(etime))
        print "task started (id=%s, time=%s)" % (name, atime)

    def follow_task(self, task_id):
        logfile = "/var/log/cobbler/tasks/%s.log" % task_id
        # adapted from:  http://code.activestate.com/recipes/157035/
        file = open(logfile, 'r')
        # Find the size of the file and move to the end
        # st_results = os.stat(filename)
        # st_size = st_results[6]
        # file.seek(st_size)

        while 1:
            where = file.tell()
            line = file.readline()
            if line.find("### TASK COMPLETE ###") != -1:
                print "*** TASK COMPLETE ***"
                sys.exit(0)
            if line.find("### TASK FAILED ###") != -1:
                print "!!! TASK FAILED !!!"
                sys.exit(1)
            if not line:
                time.sleep(1)
                file.seek(where)
            else:
                if line.find(" | "):
                    line = line.split(" | ")[-1]
                print line,         # already has newline

    def print_object_help(self, object_type):
        """
        Prints the subcommands for a given object, e.g. "cobbler distro --help"
        """
        commands = OBJECT_ACTIONS_MAP[object_type]
        commands.sort()
        print "usage\n====="
        for c in commands:
            print "cobbler %s %s" % (object_type, c)
        sys.exit(2)

    def print_help(self):
        """
        Prints general-top level help, e.g. "cobbler --help" or "cobbler" or "cobbler command-does-not-exist"
        """
        print "usage\n====="
        print "cobbler <distro|profile|system|repo|image|mgmtclass|package|file> ... "
        print "        [add|edit|copy|get-autoinstall*|list|remove|rename|report] [options|--help]"
        print "cobbler <%s> [options|--help]" % "|".join(DIRECT_ACTIONS)
        sys.exit(2)


def main():
    """
    CLI entry point
    """
    cli = CobblerCLI()
    cli.check_setup()
    rc = cli.run(sys.argv)
    if rc or rc is None:
        sys.exit(0)
    elif not rc:
        sys.exit(1)
    return sys.exit(rc)

if __name__ == "__main__":
    main()
