"""
Command line handling for Cobbler.

Copyright 2007, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import optparse
from cexceptions import *
from rhpl.translate import _, N_, textdomain, utf8
import sys

HELP_FORMAT = "%-20s%s"

#=============================================================

class FunctionLoader:

    """
    The F'n Loader controls processing of cobbler commands.
    """

    def __init__(self):
        """
        When constructed the loader has no functions.
        """
        self.functions = {}

    def add_func(self, obj):
        """
        Adds a CobblerFunction instance to the loader.
        """
        self.functions[obj.command_name()] = obj

    def run(self, args):
        """
        Runs a command line sequence through the loader.
        """

        args = self.old_school_remap(args)

        # if no args given, show all loaded fns
        if len(args) == 1:
            return self.show_options()
        called_name = args[1].lower()

        # also show avail options if command name is bogus
        if not called_name in self.functions.keys():
            return self.show_options()
        fn = self.functions[called_name]

        # some functions require args, if none given, show subcommands
        #if len(args) == 2:
        #    no_args_rc = fn.no_args_handler()
        #    if no_args_rc:
        #        return True

        # finally let the object parse its own args
        loaded_ok = fn.parse_args(args)
        if not loaded_ok:
            raise CX(_("Invalid arguments"))
        return fn.run()

    def old_school_remap(self,args): 
        """
        Replaces commands with common synonyms that should also work
     
        Also maps commands like:
             # cobbler system report foo to cobbler report --name=foo
        to:
             # cobblerr system report --name=foo

        for backwards compat and usability reasons
        """

        # to do:  handle synonyms
        for ct in range(0,len(args)):
           args[ct] = args[ct]
           if args[ct].startswith("-"):
               # stop synonym mapping after first option
               break
           # lowercase all args
           args[ct] = args[ct].lower()
           # delete means remove
           # are there any other common synonyms?
           if args[ct] == "delete":
               args[ct] = "remove" 

        # special handling for reports follows:
        if not "report" in args:
            return args
        ok = False
        for x in ["distro","profile","system","repo"]:
            if x in args:
                ok = True
        if not ok:
            return args
        idx = args.index("report")
        if idx + 1 < len(args):
           name = args[idx+1]
           if name.find("--name") == -1:
               args[idx+1] = "--name=%s" % name
        return args
       
    def show_options(self):
        """
        Prints out all loaded functions.
        """

        print "commands:"
        print "========="

        names = self.functions.keys()
        names.sort()

        for name in names:
            help = self.functions[name].help_me()
            if help != "":
                print help

#=============================================================

class CobblerFunction:

    def __init__(self,api):
        """
        Constructor requires a Cobbler API handle.
        """
        self.api = api

    def command_name(self):
        """
        The name of the command, as to be entered by users.
        """
        return "unspecified"

    def subcommands(self):
        """
        The names of any subcommands, such as "add", "edit", etc
        """
        return [ ]

    def run(self):
        """
        Called after arguments are parsed.  Return True for success.
        """
        return True

    def add_options(self, parser, args):
        """
        Used by subclasses to add options.  See subclasses for examples.
        """
        pass

    def parse_args(self,args):
        """
        Processes arguments, called prior to run ... do not override.
        """

        accum = ""
        for x in args[1:]:
            if not x.startswith("-"):
                accum = accum + "%s " % x
            else:
                break
        p = optparse.OptionParser(usage="cobbler %s [ARGS]" % accum)
        self.add_options(p, args)

        # if using subcommands, ensure one and only one is used
        subs = self.subcommands()
        if len(subs) > 0:
            count = 0
            for x in subs:
                if x in args:
                    count = count + 1               
            if count != 1:
                print "usage:"
                print "======"
                for x in subs: 
                    print "cobbler %s %s [ARGS|--help]" % (self.command_name(), x)
                sys.exit(1)    

        (self.options, self.args) = p.parse_args(args)
        return True

    def object_manipulator_start(self,new_fn,collect_fn,subobject=False):
        """
        Boilerplate for objects that offer add/edit/delete/remove/copy functionality.
        """

        if "remove" in self.args:
            if not self.options.name:
                raise CX(_("name is required"))
            collect_fn().remove(self.options.name,with_delete=True)
            return None # signal that we want no further processing on the object

        if "list" in self.args:
            self.list_list(collect_fn())
            return None

        if "report" in self.args:
            if self.options.name is None:
                self.reporting_print_sorted(collect_fn())
            else:
                self.reporting_list_names2(collect_fn(),self.options.name)
            return None

        if "add" in self.args:
            obj = new_fn(is_subobject=subobject)
        else:
            if not self.options.name:
                raise CX(_("name is required"))
            if "delete" in self.args:
                collect_fn().remove(self.options.name, with_delete=True)
                return None
            obj = collect_fn().find(self.options.name)
            if obj is None:
                raise CX(_("object named (%s) not found") % self.options.name)

        if not "copy" in self.args and not "rename" in self.args and self.options.name:
            obj.set_name(self.options.name)

        return obj

    def object_manipulator_finish(self,obj,collect_fn, options):
        """
        Boilerplate for objects that offer add/edit/delete/remove/copy functionality.
        """

        if "copy" in self.args or "rename" in self.args:
            if self.options.newname:
                obj = obj.make_clone()
                obj.set_name(self.options.newname)
            else:
                raise CX(_("--newname is required"))

        opt_sync     = not options.nosync
        opt_triggers = not options.notriggers

        rc = collect_fn().add(obj, save=True, with_sync=opt_sync, with_triggers=opt_triggers)

        if "rename" in self.args:
            return collect_fn().remove(self.options.name, with_delete=True)

        return rc

    def reporting_sorter(self, a, b):
        """
        Used for sorting cobbler objects for report commands
        """
        return cmp(a.name, b.name)

    def reporting_print_sorted(self, collection):
        """
        Prints all objects in a collection sorted by name
        """
        collection = [x for x in collection]
        collection.sort(self.reporting_sorter)
        for x in collection:
            print x.printable()
        return True

    def reporting_list_names2(self, collection, name):
        """
        Prints a specific object in a collection.
        """
        obj = collection.find(name=name)
        if obj is not None:
            print obj.printable()
        return True

    def list_tree(self,collection,level):
        """
        Print cobbler object tree as a, well, tree.
        """
        for item in collection:
            print _("%(indent)s%(type)s %(name)s") % {
                "indent" : "   " * level,
                "type"   : item.TYPE_NAME,
                "name"   : item.name
            }
            kids = item.get_children()
            if kids is not None and len(kids) > 0:
                self.list_tree(kids,level+1)

    def list_list(self, collection):
        """
        List all objects of a certain type.
        """
        names = [ x.name for x in collection]
        names.sort() # sorted() is 2.4 only
        for name in names:
           str = _("  %(name)s") % { "name" : name }
           print str
        return True

    def matches_args(self, args, list_of):
        """
        Used to simplify some code around which arguments to add when.
        """
        for x in args:
            if x in list_of:
                return True
        return False


