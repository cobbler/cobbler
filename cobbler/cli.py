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

import utils
import module_loader
import item_distro
import item_profile
import item_system
import item_repo
import item_image

OBJECT_ACTIONS   = {
   "distro"  : "add copy edit list remove report".split(" "),
   "profile" : "add copy dumpvars edit getks list remove report".split(" "),
   "system"  : "add copy dumpvars edit getks list remove report".split(" "),
   "image"   : "add copy edit list remove report".split(" "),
   "repo"    : "add copy edit list remove report".split(" ")
} 
OBJECT_TYPES = OBJECT_ACTIONS.keys()
DIRECT_ACTIONS = [ "buildiso", "reposync", "sync", "validateks", "import", "aclsetup", "list", "report" ]

####################################################

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
      return ""
   return n2s(data)

class BootCLI:

    def __init__(self,endpoint="http://127.0.0.1/cobbler_api"):
        # FIXME: allow specifying other endpoints, and user+pass
        self.parser        = optparse.OptionParser()
        self.remote        = xmlrpclib.Server(endpoint)
        self.shared_secret = utils.get_shared_secret()
        self.token         = self.remote.login("", self.shared_secret)

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
        if args[1] in DIRECT_ACTIONS:
            return args[1]
        return None

    def run(self, args):
        """
        Process the command line and do what the user asks.
        """
        object_type   = self.get_object_type(args)
        object_action = self.get_object_action(object_type, args)
        direct_action = self.get_direct_action(object_type, args) 
 
        print "DEBUG: CLI (%s,%s,%s)" % (object_type, object_action, direct_action)

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
        utils.add_options_from_fields(self.parser, fields, object_action)

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
            # FIXME: implement this!
            raise exceptions.NotImplementedError()
        else:
            raise exceptions.NotImplementedError() 

    def direct_command(self, action_name):
        """
        Process non-object based commands like "sync" and "hardlink"
        """
        # FIXME: copy in all the options from the old cli_misc.py

        print "DEBUG: direct_command: %s" % action_name
        task_id = -1  # if assigned, we must tail the logfile

        if action_name == "buildiso":
            print "buildiso"
            (options, args) = self.parser.parse_args()
            # FIXME: run here
        elif action_name == "hardlink":
            print "hardlink"
            (options, args) = self.parser.parse_args()
            # FIXME: run here
        elif action_name == "import":
            self.parser.add_option("--arch",         dest="arch",           help="OS architecture being imported")
            self.parser.add_option("--breed",        dest="breed",          help="the breed being imported")
            self.parser.add_option("--os-version",   dest="os_version",     help="the version being imported")
            self.parser.add_option("--path",         dest="mirror",         help="local path or rsync location")
            self.parser.add_option("--name",         dest="name",           help="name, ex 'RHEL-5'")
            self.parser.add_option("--available-as", dest="available_as",   help="tree is here, don't mirror")
            self.parser.add_option("--kickstart",    dest="kickstart_file", help="assign this kickstart file")
            self.parser.add_option("--rsync-flags",  dest="rsync_flags",    help="pass additional flags to rsync")
            (options, args) = self.parser.parse_args()
            task_id = self.remote.background_import(
                opt(options,"name"), 
                opt(options,"path"), 
                opt(options,"arch"), 
                opt(options,"breed"), 
                opt(options,"available_as"), 
                opt(options,"kickstart"), 
                opt(options,"rsync_flags"), 
                opt(options,"os_version"), 
                self.token
            )
            # FIXME: run here
        elif action_name == "reposync":
            print "reposync"
            (options, args) = self.parser.parse_args()
            # FIXME: run here
        elif action_name == "aclsetup":
            print "aclsetup"
            (options, args) = self.parser.parse_args()
            # FIXME: run here
        elif action_name == "check":
            print "check"
            (options, args) = self.parser.parse_args()
            # FIXME: run here
        elif action_name == "sync":
            print "parse_args"
            (options, args) = self.parser.parse_args()
            # FIXME: run here
        elif action_name == "list":
            # no tree view like 1.6?  This is more efficient remotely
            # for large configs and prevents xfering the whole config
            # though we could consider that...
            print "distros:"
            distros  = self.remote.get_item_names("distro")
            distros.sort()
            for d in distros:
               print "  %s" % d

            print "\nprofiles:"
            profiles = self.remote.get_item_names("profile")
            profiles.sort()
            for p in profiles:
               print "  %s" % p 

            print "\nsystems:"
            systems = self.remote.get_item_names("system")
            systems.sort()
            for s in systems:
               print "  %s" % s

            print "\nrepos:"
            repos    = self.remote.get_item_names("repo")
            repos.sort()
            for r in repos:
               print "  %s" % r

            print "\nimages:"
            images   = self.remote.get_item_names("image")
            images.sort()
            for i in images:
               print "  %s" % i
        else:
            raise Exception("internal error, no such action: %s" % action_name)
            # FIXME: run here

        # FIXME: add tail/polling code here
        if task_id != -1:
            print "task started: %s" % task_id
            events = self.remote.get_events()
            (etime, name, status, who_viewed) = events[task_id]
            atime = time.asctime(time.localtime(etime))
            print "task started (id=%s, time=%s)" % (name, atime)
            # FIXME: add log tailing code here?

        return True

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
        print "cobbler <distro|profile|system|repo|image> --help"
        print "cobbler <distro|profile|system|repo|image> <subcommand> [options|--help]"
        print "cobbler <aclsetup|check|buildiso|hardlink> [options|--help]"
        print "cobbler <import|reposync|sync|validateks> [options|--help]"
        sys.exit(2)

####################################################

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


