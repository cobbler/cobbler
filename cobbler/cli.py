"""
Command line interface for cobbler.

Copyright 2006-2009, Red Hat, Inc
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

import sys
import xmlrpclib
import traceback
import optparse
import exceptions
import time
import os

import utils
import module_loader
import item_distro
import item_profile
import item_system
import item_repo
import item_image

OBJECT_ACTIONS   = {
   "distro"  : "add copy edit find list remove rename report".split(" "),
   "profile" : "add copy dumpvars edit find getks list remove rename report".split(" "),
   "system"  : "add copy dumpvars edit find getks list remove rename report".split(" "),
   "image"   : "add copy edit find list remove rename report".split(" "),
   "repo"    : "add copy edit find list remove rename report".split(" ")
} 
OBJECT_TYPES = OBJECT_ACTIONS.keys()
DIRECT_ACTIONS = "aclsetup buildiso deploy import list report reposync sync validateks version".split()

####################################################

def report_items(remote, otype):
   items = remote.get_items(otype)
   for x in items:
      report_item(remote,otype,item=x)

def report_item(remote,otype,item=None,name=None):
   if item is None:
      item = remote.get_item(otype, name)
   if otype == "distro":
      data = utils.printable_from_fields(item, item_distro.FIELDS)
   elif otype == "profile":
      data = utils.printable_from_fields(item, item_profile.FIELDS)
   elif otype == "system":
      data = utils.printable_from_fields(item, item_system.FIELDS)
   elif otype == "repo":
      data = utils.printable_from_fields(item, item_repo.FIELDS)
   elif otype == "image":
      data = utils.printable_from_fields(item, item_image.FIELDS)
   print data

def list_items(remote,otype):
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

def opt(options, k):
   """
   Returns an option from an Optparse values instance
   """
   try:
      data = getattr(options, k) 
   except:
      # FIXME: debug only
      traceback.print_exc()
      return ""
   return n2s(data)

class BootCLI:

    def __init__(self,endpoint="http://127.0.0.1/cobbler_api"):
        # FIXME: allow specifying other endpoints, and user+pass
        self.parser        = optparse.OptionParser()
        self.remote        = xmlrpclib.Server(endpoint)
        self.shared_secret = utils.get_shared_secret()
        self.token         = self.remote.login("", self.shared_secret)

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
        if args[2] in OBJECT_ACTIONS[object_type]:
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

    def run(self, args):
        """
        Process the command line and do what the user asks.
        """
        object_type   = self.get_object_type(args)
        object_action = self.get_object_action(object_type, args)
        direct_action = self.get_direct_action(object_type, args) 

        if object_type is not None:
            if object_action is not None:
               self.object_command(object_type, object_action)
            else:
               self.print_object_help(object_type)   

        elif direct_action is not None:
            self.direct_command(direct_action)

        else:
            self.print_help()

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
            return item_repo.FIELDS

    def object_command(self, object_type, object_action):
        """
        Process object-based commands such as "distro add" or "profile rename"
        """
        fields = self.get_fields(object_type)
        if object_action not in [ "report", "getks", "dumpvars", "remove" ]:
            utils.add_options_from_fields(object_type, self.parser, fields, object_action)
        elif object_action in [ "list" ]:
            pass
        else:
            self.parser.add_option("--name", dest="name", help="name of object")
        (options, args) = self.parser.parse_args()

        if object_action in [ "add", "edit", "copy", "rename", "remove" ]:
            if opt(options, "name") == "":
                print "--name is required"
                sys.exit(1)
            self.remote.xapi_object_edit(object_type, options.name, object_action, utils.strip_none(vars(options), omit_none=True), self.token)
        elif object_action == "getks":
            if object_type == "profile":
                data = self.remote.generate_kickstart(options.name,"")
            elif object_type == "system":
                data = self.remote.generate_kickstart("",options.name)
            print data
        elif object_action == "dumpvars":
            if object_type == "profile":
                data = self.remote.get_blended_data(options.name,"")
            elif object_type == "system":
                data = self.remote.get_blended_data("",options.name)
            # FIXME: pretty-printing and sorting here
            print data
        elif object_action == "report":
            if options.name is not None:
                report_item(self.remote,object_type,None,options.name)
            else:
                report_items(self.remote,object_type)
        elif object_action == "list":
            list_items(self.remote, object_type)
        elif object_action == "find":
            items = self.remote.find_items(object_type, utils.strip_none(vars(options), omit_none=True), "name", False)
            for item in items:
                print item
        else:
            raise exceptions.NotImplementedError() 
        

    # BOOKMARK
    def direct_command(self, action_name):
        """
        Process non-object based commands like "sync" and "hardlink"
        """
        task_id = -1 # if assigned, we must tail the logfile

        if action_name == "buildiso":

            defaultiso = os.path.join(os.getcwd(), "generated.iso")
            self.parser.add_option("--iso",      dest="iso",  default=defaultiso, help="(OPTIONAL) output ISO to this path")
            self.parser.add_option("--profiles", dest="profiles", help="(OPTIONAL) use these profiles only")
            self.parser.add_option("--systems",  dest="systems",  help="(OPTIONAL) use these systems only")
            self.parser.add_option("--tempdir",  dest="tempdir",  help="(OPTIONAL) working directory")
            self.parser.add_option("--distro",   dest="distro",   help="(OPTIONAL) used with --standalone to create a distro-based ISO including all associated profiles/systems")
            self.parser.add_option("--standalone", dest="standalone", action="store_true", help="(OPTIONAL) creates a standalone ISO with all required distro files on it")
            self.parser.add_option("--source",   dest="source",   help="(OPTIONAL) used with --standalone to specify a source for the distribution files")
            self.parser.add_option("--exclude-dns", dest="exclude_dns", action="store_true", help="(OPTIONAL) prevents addition of name server addresses to the kernel boot options")

            (options, args) = self.parser.parse_args()
            task_id = self.start_task("buildiso",options)

        elif action_name == "replicate":
            self.parser.add_option("--master",               dest="master",           help="Cobbler server to replicate from.")
            self.parser.add_option("--include-systems",      dest="systems",          action="store_true", help="include systems in addition to distros, profiles, and repos")
            self.parser.add_option("--full-data-sync",       dest="all",              action="store_true", help="rsync everything")
            self.parser.add_option("--sync-kickstarts",      dest="kickstarts",       action="store_true", help="rsync kickstart templates")
            self.parser.add_option("--sync-trees",           dest="trees",            action="store_true", help="rsync imported trees")
            self.parser.add_option("--sync-triggers",        dest="triggers",         action="store_true", help="rsync trigger scripts")
            self.parser.add_option("--sync-repos",           dest="repos",            action="store_true", help="rsync mirrored repo data")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("replicate",options)

        elif action_name == "deploy":
            self.parser.add_option("--system", dest="system", help="name of cobbler guest system")
            self.parser.add_option("--virt-group", dest="virt_group", help="for create operations, the group name of cobbler systems to use instead of --virt-host")
            self.parser.add_option("--virt-host", dest="virt_host", help="for create operations, the name of the system that will host the instance")
            self.parser.add_option("--method", dest="method", help="communication mechanism, ssh or func")
            self.parser.add_option("--operation", dest="operation", help="install, uninstall, start, reboot, shutdown, or unplug")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("deploy",options)

        elif action_name == "aclsetup":
            self.parser.add_option("--adduser",            dest="adduser",            help="give acls to this user")
            self.parser.add_option("--addgroup",           dest="addgroup",           help="give acls to this group")
            self.parser.add_option("--removeuser",         dest="removeuser",         help="remove acls from this user")
            self.parser.add_option("--removegroup",        dest="removegroup",        help="remove acls from this group")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("deploy",options)

        elif action_name == "version":
            version = self.remote.extended_version()
            print "Cobbler %s" % version["version"]
            print "  source: %s, %s" % (version["gitstamp"], version["gitdate"])
            print "  build time: %s" % version["builddate"]

        elif action_name == "hardlink":
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("hardlink",options)
        elif action_name == "reserialize":
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("reserialize",options)
        elif action_name == "status":
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("status",options)
        elif action_name == "validateks":
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("validateks",options)
        elif action_name == "get-loaders":
            self.parser.add_option("--force", dest="force", action="store_true", help="overwrite any existing content in /var/lib/cobbler/loaders")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("dlcontent",options)
        elif action_name == "import":
            self.parser.add_option("--arch",         dest="arch",           help="OS architecture being imported")
            self.parser.add_option("--breed",        dest="breed",          help="the breed being imported")
            self.parser.add_option("--os-version",   dest="os_version",     help="the version being imported")
            self.parser.add_option("--path",         dest="path",         help="local path or rsync location")
            self.parser.add_option("--name",         dest="name",           help="name, ex 'RHEL-5'")
            self.parser.add_option("--available-as", dest="available_as",   help="tree is here, don't mirror")
            self.parser.add_option("--kickstart",    dest="kickstart_file", help="assign this kickstart file")
            self.parser.add_option("--rsync-flags",  dest="rsync_flags",    help="pass additional flags to rsync")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("import",options)
        elif action_name == "reposync":
            print "reposync"
            self.parser.add_option("--only",           dest="only",             help="update only this repository name")
            self.parser.add_option("--tries",          dest="tries",            help="try each repo this many times", default=1)
            self.parser.add_option("--no-fail",        dest="nofail",           help="don't stop reposyncing if a failure occurs", action="store_true")
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("reposync",options)
        elif action_name == "aclsetup":
            (options, args) = self.parser.parse_args()
            # FIXME: missing options, add them here
            task_id = self.start_task("aclsetup",options)
        elif action_name == "check":
            (options, args) = self.parser.parse_args()
            task_id = self.start_task("check",options)
        elif action_name == "sync":
            print "parse_args"
            (options, args) = self.parser.parse_args()
            self.parser.add_option("--verbose", dest="verbose", action="store_true", help="run sync with more output")
            task_id = self.start_task("sync",options)
        elif action_name == "report":
            (options, args) = self.parser.parse_args()
            print "distros:\n=========="
            report_items(self.remote,"distro")
            print "\nprofiles:\n=========="
            report_items(self.remote,"profile")
            print "\nsystems:\n=========="
            report_items(self.remote,"system")
            print "\nrepos:\n=========="
            report_items(self.remote,"repo")
            print "\nimages:\n=========="
            report_items(self.remote,"image")
        elif action_name == "list":
            # no tree view like 1.6?  This is more efficient remotely
            # for large configs and prevents xfering the whole config
            # though we could consider that...
            (options, args) = self.parser.parse_args()
            print "distros:"
            list_items(self.remote,"distro")
            print "\nprofiles:"
            list_items(self.remote,"profile")
            print "\nsystems:"
            list_items(self.remote,"system")
            print "\nrepos:"
            list_items(self.remote,"repo")
            print "\nimages:"
            list_items(self.remote,"image")
        else:
            print "No such command: %s" % action_name
            sys.exit(1)
            # FIXME: run here

        # FIXME: add tail/polling code here
        if task_id != -1:
            print "task started: %s" % task_id
            events = self.remote.get_events()
            (etime, name, status, who_viewed) = events[task_id]
            atime = time.asctime(time.localtime(etime))
            print "task started (id=%s, time=%s)" % (name, atime)
            self.follow_task(task_id) 

        return True


    def follow_task(self, task_id):
        logfile = "/var/log/cobbler/tasks/%s.log" % task_id
        # adapted from:  http://code.activestate.com/recipes/157035/        
        file = open(logfile,'r')
        #Find the size of the file and move to the end
        #st_results = os.stat(filename)
        #st_size = st_results[6]
        #file.seek(st_size)

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
                print line, # already has newline


    def print_object_help(self, object_type):
        """
        Prints the subcommands for a given object, e.g. "cobbler distro --help"
        """
        commands = OBJECT_ACTIONS[object_type]
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
        print "cobbler <distro|profile|system|repo|image> ... "
        print "        [add|edit|copy|getks*|list|remove|rename|report] [options|--help]"
        print "cobbler <%s> [options|--help]" % "|".join(DIRECT_ACTIONS)
        sys.exit(2)

def main():
    """
    CLI entry point
    """
    rc = BootCLI().run(sys.argv)
    if rc == True or rc is None:
        sys.exit(0)
    elif rc == False:
        sys.exit(1)
    return sys.exit(rc)

if __name__ == "__main__":
    main()


