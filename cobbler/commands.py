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
from utils import _
import sys

HELP_FORMAT = "%-20s%s"

#=============================================================

class FunctionLoader:

    """
    The F'n Loader controls processing of cobbler commands.
    """

    def __init__(self, api):
        """
        When constructed the loader has no functions.
        """
        self.api = api
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
            if "--helpbash" in args:
                return self.show_options_bashcompletion()
            else:
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
        for x in ["distro","profile","system","repo","image"]:
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

    def show_options_bashcompletion(self):
        """
        Prints out all loaded functions in an easily parseable form for
        bash-completion
        """
        names = self.functions.keys()
        names.sort()
        print ' '.join(names)

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

    def helpbash(self, parser, args):
        """
        Print out the arguments in an easily parseable format
        """
        # We only want to print either the subcommands available or the
        # options, but not both
        option_list = []
        for sub in self.subcommands():
            if sub.__str__() in args:
                # Subcommand has already been entered so lets show the options
                option_list = []
                break
            option_list.append(sub.__str__())
        if not option_list:
            for opt in parser.option_list:
                option_list.extend(opt.__str__().split('/'))
        print ' '.join(option_list)


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
        if "--helpbash" in args:
            self.helpbash(p, args)
            sys.exit(0)
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

        if "dumpvars" in self.args:
            if not self.options.name:
                raise CX(_("name is required"))
            obj = collect_fn().find(self.options.name)
            if obj is None:
                raise CX(_("object not found")) 
            return obj

        if "remove" in self.args:
            recursive = False
            # only applies to distros/profiles and is not supported elsewhere
            if hasattr(self.options, "recursive"):
                recursive = self.options.recursive
            if not self.options.name:
                raise CX(_("name is required"))
            if not recursive:
                collect_fn().remove(self.options.name,with_delete=True)
            else:
                collect_fn().remove(self.options.name,with_delete=True,recursive=True)
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

        if not self.options.name:
            raise CX(_("name is required"))

        if "add" in self.args:
            obj = new_fn(is_subobject=subobject)
        else:
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

        if "dumpvars" in self.args:
            print obj.dump_vars(True)
            return True

        clobber = False
        if "add" in self.args:
            clobber = options.clobber

        if "copy" in self.args:
            if self.options.newname:
                obj = obj.make_clone()
                obj.set_name(self.options.newname)
            else:
                raise CX(_("--newname is required"))

        opt_sync     = not options.nosync
        opt_triggers = not options.notriggers

        # ** WARNING: COMPLICATED **
        # what operation we call depends on what type of object we are editing
        # and what the operation is.  The details behind this is that the
        # add operation has special semantics around adding objects that might
        # clobber other objects, and we don't want that to happen.  Edit
        # does not have to check for named clobbering but still needs
        # to check for IP/MAC clobbering in some scenarios (FIXME).
        # this is all enforced by collections.py though we need to make
        # the apppropriate call to add to invoke the safety code in the right
        # places -- and not in places where the safety code will generate
        # errors under legit circumstances.

        if not ("rename" in self.args):
            if "add" in self.args:
               if obj.COLLECTION_TYPE == "system":
                   # duplicate names and netinfo are both bad.
                   if not clobber:
                       rc = collect_fn().add(obj, save=True, with_sync=opt_sync, with_triggers=opt_triggers, check_for_duplicate_names=True, check_for_duplicate_netinfo=True)
                   else:
                       rc = collect_fn().add(obj, save=True, with_sync=opt_sync, with_triggers=opt_triggers, check_for_duplicate_names=False, check_for_duplicate_netinfo=True)
               else:
                   # duplicate names are bad
                   if not clobber:
                       rc = collect_fn().add(obj, save=True, with_sync=opt_sync, with_triggers=opt_triggers, check_for_duplicate_names=True, check_for_duplicate_netinfo=False)
                   else:
                       rc = collect_fn().add(obj, save=True, with_sync=opt_sync, with_triggers=opt_triggers, check_for_duplicate_names=False, check_for_duplicate_netinfo=False)
            else:
               check_dup = False
               if not "copy" in self.args:
                   check_dup = True 
               rc = collect_fn().add(obj, save=True, with_sync=opt_sync, with_triggers=opt_triggers, check_for_duplicate_netinfo=check_dup)

        else:
            # we are renaming here, so duplicate netinfo checks also
            # need to be made.(FIXME)
            rc = collect_fn().rename(obj, self.options.newname, with_triggers=opt_triggers)

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

        def sorter(a,b):
            return cmp(a.name,b.name)

        collection2 = []
        for c in collection:
            collection2.append(c)
        collection2.sort(sorter)

        for item in collection2:
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


