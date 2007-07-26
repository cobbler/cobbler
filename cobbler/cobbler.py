"""
Command line interface for cobbler, a network provisioning configuration
library.  Consult 'man cobbler' for general info.  This class serves
as a good reference on how to drive the API (api.py).

Copyright 2006, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import sys
import api
import os
import os.path
import traceback

from cexceptions import *

from rhpl.translate import _, N_, textdomain, utf8
I18N_DOMAIN = "cobbler"

LOCKING_ENABLED = True 
LOCKFILE="/var/lib/cobbler/lock"

USAGE = _("see 'man cobbler' for instructions")

class BootCLI:


    def __init__(self,args):
        """
        Build the command line parser and API instances, etc.
        """
        textdomain(I18N_DOMAIN)
        self.args = args
        self.api = api.BootAPI()
        self.commands = {}
        self.commands['distro'] = {
            'add'     :  self.distro_add,
            'edit'    :  self.distro_edit,
            'copy'    :  self.distro_copy,
            'rename'  :  self.distro_rename,
            'delete'  :  self.distro_remove,
            'remove'  :  self.distro_remove,
            'list'    :  self.distro_list,
            'report'  :  self.distro_report
        }
        self.commands['profile'] = {
            'add'     :  self.profile_add,
            'edit'    :  self.profile_edit,
            'copy'    :  self.profile_copy,
            'rename'  :  self.profile_rename,
            'delete'  :  self.profile_remove,
            'remove'  :  self.profile_remove,
            'list'    :  self.profile_list,
            'report'  :  self.profile_report
        }
        self.commands['system'] = {
            'add'     :  self.system_add,
            'edit'    :  self.system_edit,
            'rename'  :  self.system_rename,
            'copy'    :  self.system_copy,
            'delete'  :  self.system_remove,
            'remove'  :  self.system_remove,
            'list'    :  self.system_list,
            'report'  :  self.system_report
        }
        self.commands['repo'] = {
            'add'     :  self.repo_add,
            'edit'    :  self.repo_edit,
            'rename'  :  self.repo_rename,
            'copy'    :  self.repo_copy,
            'delete'  :  self.repo_remove,
            'remove'  :  self.repo_remove,
            'list'    :  self.repo_list,
            'report'  :  self.repo_report,
            'sync'    :  self.reposync
        }
        self.commands['toplevel'] = {
            '-v'           : self.version,
            '--version'    : self.version,
            'check'        : self.check,
            'validateks'   : self.validateks,  
            'list'         : self.list,
            'report'       : self.report,
            'distros'      : self.distro,
            'distro'       : self.distro,
            'profiles'     : self.profile,
            'profile'      : self.profile,
            'systems'      : self.system,
            'system'       : self.system,
            'repos'        : self.repo,
            'repo'         : self.repo,
            'sync'         : self.sync,
            'reposync'     : self.reposync,
            'import'       : self.import_tree,
            'enchant'      : self.enchant,
            'clobber'      : self.enchant,
            'transmogrify' : self.enchant,
            'status'       : self.status,
            'reserialize'  : self.reserialize,
            'help'         : self.usage,
            '--help'       : self.usage,
            '/?'           : self.usage
        }

    def run(self):
        """
        Run the command line and return system exit code
        """
        self.api.deserialize()
        self.relay_args(self.args[1:], self.commands['toplevel'])

    def usage(self,args):
        """
        Print out abbreviated help if user gives bad syntax
        """
        print USAGE


    ###########################################################
    # REPORTING FUNCTIONS

    def distro_report(self,args):
        if len(args) > 0:
           return self.__list_names2(self.api.distros(), args)
        else:
           return self.__print_sorted(self.api.distros())

    def system_report(self,args):
        if len(args) > 0:
           return self.__list_names2(self.api.systems(), args)
        else:
           return self.__print_sorted(self.api.systems())

    def profile_report(self,args):
        if len(args) > 0:
           return self.__list_names2(self.api.profiles(), args)
        else:
           return self.__print_sorted(self.api.profiles())

    def repo_report(self,args):
        if len(args) > 0:
           return self.__list_names2(self.api.repos(), args)
        else:
           return self.__print_sorted(self.api.repos())

    def report(self,args):

        args.append("") # filler
        match = False
        for a in args:
            if a == '--distros' or len(args) == 1:
                self.distro_report([])
                match = True
            if a == '--repos' or len(args) == 1:
                self.repo_report([])
                match = True
            if a == '--profiles' or len(args) == 1:
                self.profile_report([])
                match = True
            if a == '--systems' or len(args) == 1:
                self.system_report([])
                match = True
            if not match and a is not None and a != "":
                raise CX(_("cobbler does not understand '%(command)s'") % { "command" : a })
            match = False

    #############################################
    # LISTING FUNCTIONS

    def list(self,args):
        self.__tree(self.api.distros(),0)
        self.__tree(self.api.repos(),0)

    def __tree(self,collection,level):
        for item in collection:
            print _("%(indent)s%(type)s %(name)s") % { 
                "indent" : "   " * level,
                "type"   : item.TYPE_NAME,
                "name"   : item.name 
            }
            kids = item.get_children()
            if kids is not None and len(kids) > 0:
               self.__tree(kids,level+1)

    def __list_names(self, collection):
        names = [ x.name for x in collection]
        names.sort() # sorted() is 2.4 only
        for name in names:
           str = _("  %(name)s") % { "name" : name }
           print str
        return True

    def __list_names2(self, collection, args):
        for p in args:
            obj = collection.find(p)
            if obj is not None:
                print obj.printable()
        return True

    def system_list(self, args):
        if len(args) > 0:
           self.__list_names2(self.api.systems(), args)
        else:
           return self.__list_names(self.api.systems())
    
    def distro_list(self, args):
        if len(args) > 0:
           return self.__list_names2(self.api.distros(),args)
        else:
           return self.__list_names(self.api.distros())
    
    def profile_list(self, args):
        if len(args) > 0:
           return self.__list_names2(self.api.profiles(),args)
        else:
           return self.__list_names(self.api.profiles())
    
    def repo_list(self, args):
        if len(args) > 0:
           return self.__list_names2(self.api.repos(),args)
        else:
           return self.__list_names(self.api.repos())

    ###############################################################
    # UTILITY FUNCTIONS
 
    def find_arg(self,haystack,needle):
        for arg in haystack:
           arg2 = arg.replace('"','')
           if arg2.startswith(needle):
               tokens = arg2.split("=")
               if len(tokens) >= 1:
                   return "".join(tokens[1:])
        return None

    def replace_names(self,haystack,newname):
        args2 = []
        for arg in haystack:
            if arg.startswith("--name"):
                args2.append("--name=%s" % newname) 
            else:
                args2.append(arg)
        return args2


    def __sorter(self, a, b):
        return cmp(a.name, b.name)

    def __print_sorted(self, collection):
        collection = [x for x in collection]
        collection.sort(self.__sorter)
        for x in collection:
            print x.printable()
        return True

    ######################################################################
    # BASIC FRAMEWORK

    def __generic_add(self,args,new_fn,control_fn,does_inherit):
        obj = new_fn(is_subobject=does_inherit)
        control_fn(args,obj)

    def __generic_edit(self,args,collection_fn,control_fn,exc_msg):
        obj = collection_fn().find(self.find_arg(args,"--name"))
        name2 = self.find_arg(args,"--newname")
        if name2 is not None:
            raise CX("objects cannot be renamed with the edit command, use 'rename'")
        if obj is None:
            raise CX(exc_msg)
        control_fn(args,obj)

    def __generic_copy(self,args,collection_fn,control_fn,exc_msg):
        obj = collection_fn().find(self.find_arg(args,"--name"))
        obj2 = self.find_arg(args,"--newname")
        if obj is None:
            raise CX(exc_msg)
        args = self.replace_names(args, obj2)
        obj3 = obj.make_clone()
        obj3.set_name(obj2)
        control_fn(args,obj3)

    def __generic_rename(self,args,collection_fn,control_fn,exc_msg):
        objname = self.find_arg(args,"--name")
        if objname is None:
            raise CX(_("at least one required parameter is missing.  See 'man cobbler'."))
        objname2 = self.find_arg(args,"--newname")
        if objname2 is None:
            raise CX(_("at least one required parameter is missing.  See 'man cobbler'."))
        self.__generic_copy(args,collection_fn,control_fn,exc_msg)
        if objname != objname2:
            collection_fn().remove(objname, with_delete=self.api.sync_flag)
        self.api.serialize()

    def __generic_remove(self,args,alias1,alias2,collection_fn):
        commands = {
            "--%s" % alias1 : lambda(a):  collection_fn().remove(a, with_delete=self.api.sync_flag),
            "--%s" % alias2 : lambda(a):  collection_fn().remove(a, with_delete=self.api.sync_flag)
        }
        on_ok = lambda: True
        return self.apply_args(args,commands,on_ok)

    ####################################################################
    # REMOVAL FUNCTIONS
  
    def distro_remove(self,args):
        return self.__generic_remove(args,"distro","name",self.api.distros)
    
    def profile_remove(self,args):
        return self.__generic_remove(args,"profile","name",self.api.profiles)

    def system_remove(self,args):
        return self.__generic_remove(args,"system","name",self.api.systems)
    
    def repo_remove(self,args):
        return self.__generic_remove(args,"repo","name",self.api.repos)
 
    ####################################################################
    # COPY FUNCTIONS
 
    def distro_copy(self,args):
        exc = _("distribution does not exist")
        self.__generic_copy(args,self.api.distros,self.__distro_control,exc)
    
    def profile_copy(self,args):
        exc = _("profile does not exist")
        self.__generic_copy(args,self.api.profiles,self.__profile_control,exc)
    
    def system_copy(self,args):
        exc = _("system does not exist")
        self.__generic_copy(args,self.api.systems,self.__system_control,exc)
        
    def repo_copy(self,args):
        exc = _("repository does not exist")
        self.__generic_copy(args,self.api.repos,self.__repo_control,exc)

    #####################################################################
    # RENAME FUNCTIONS

    def distro_rename(self,args):
        exc = _("distribution does not exist")
        self.__generic_rename(args,self.api.distros,self.__distro_control,exc)

    def profile_rename(self,args):
        exc = _("profile does not exist")
        self.__generic_rename(args,self.api.profiles,self.__profile_control,exc)

    def system_rename(self,args):
        exc = _("system does not exist")
        self.__generic_rename(args,self.api.systems,self.__system_control,exc)

    def repo_rename(self,args):
        exc = _("repository does not exist")
        self.__generic_rename(args,self.api.repos,self.__repo_control,exc)

    #####################################################################
    # EDIT FUNCTIONS

    def distro_edit(self,args):
        exc = _("distribution does not exist")
        self.__generic_edit(args,self.api.distros,self.__distro_control,exc)
    
    def profile_edit(self,args):
        exc = _("profile does not exist")
        self.__generic_edit(args,self.api.profiles,self.__profile_control,exc)
    
    def system_edit(self,args):
        exc = _("system does not exist")
        self.__generic_edit(args,self.api.systems,self.__system_control,exc)
    
    def repo_edit(self,args):
        exc = _("repository does not exist")
        self.__generic_edit(args,self.api.repos,self.__repo_control,exc)
   
    #####################################################################
    # ADD FUNCTIONS

    def __prescan_for_inheritance_args(self,args):
        """
        Normally we just feed all the arguments through to the functions
        in question, but here, we need to send a special flag to the foo_add
        functions if we are creating a subobject, because that needs to affect
        what function calls we make.  So, this checks to see if the user
        is creating a subobject by looking for --inherit in the arguments list,
        before we actually parse the --inherit arg.  Complicated :)
        """
        for x in args:
            try:
                key, value = x.split("=",1)
                value = value.replace('"','').replace("'",'')
                if key == "--inherit":
                   return True
            except:
                traceback.print_exc() # FIXME: remove
                pass
        return False

    def distro_add(self,args):
        does_inherit = self.__prescan_for_inheritance_args(args)
        self.__generic_add(args,self.api.new_distro,self.__distro_control,does_inherit)

    def profile_add(self,args):
        does_inherit = self.__prescan_for_inheritance_args(args)
        self.__generic_add(args,self.api.new_profile,self.__profile_control,does_inherit)    

    def system_add(self,args):
        does_inherit = self.__prescan_for_inheritance_args(args)
        self.__generic_add(args,self.api.new_system,self.__system_control,does_inherit)

    def repo_add(self,args):
        does_inherit = self.__prescan_for_inheritance_args(args)
        self.__generic_add(args,self.api.new_repo,self.__repo_control,does_inherit)


    ###############################################################
    # CONTROL IMPLEMENTATIONS

    def __profile_control(self,args,profile,newname=None):
        """
        Create/Edit a profile:  'cobbler profile edit --name='foo' ...
        """
        commands = {
            '--name'            :  lambda(a) : profile.set_name(a),
            '--inherit'         :  lambda(a) : profile.set_parent(a),
            '--newname'         :  lambda(a) : True,
            '--profile'         :  lambda(a) : profile.set_name(a),
            '--distro'          :  lambda(a) : profile.set_distro(a),
            '--kickstart'       :  lambda(a) : profile.set_kickstart(a),
            '--kick-start'      :  lambda(a) : profile.set_kickstart(a),
            '--answers'         :  lambda(a) : profile.set_kickstart(a),
            '--kopts'           :  lambda(a) : profile.set_kernel_options(a),
            '--virt-file-size'  :  lambda(a) : profile.set_virt_file_size(a),
            '--virt-ram'        :  lambda(a) : profile.set_virt_ram(a),
            '--ksmeta'          :  lambda(a) : profile.set_ksmeta(a),
            '--repos'           :  lambda(a) : profile.set_repos(a),
            '--virt-path'       :  lambda(a) : profile.set_virt_path(a),
            '--virt-type'       :  lambda(a) : profile.set_virt_type(a)
        }
        def on_ok():
            if newname is not None:
                profile.set_name(newname)
            self.api.profiles().add(profile, with_copy=self.api.sync_flag)
        return self.apply_args(args,commands,on_ok)

    def __repo_control(self,args,repo,newname=None):
        """
        Create/edit a repo:  'cobbler repo add --name='foo' ...
        """
        commands = {
           '--name'             :  lambda(a): repo.set_name(a),
           '--newname'          :  lambda(a): True,
           '--mirror-name'      :  lambda(a): repo.set_name(a),
           '--mirror'           :  lambda(a): repo.set_mirror(a),
           '--keep-updated'     :  lambda(a): repo.set_keep_updated(a),
           '--local-filename'   :  lambda(a): repo.set_local_filename(a),
           '--rpm-list'         :  lambda(a): repo.set_rpm_list(a),
           '--createrepo-flags' :  lambda(a): repo.set_createrepo_flags(a)
        }
        def on_ok():
            if newname is not None:
                repo.set_name(newname)
            self.api.repos().add(repo)
        return self.apply_args(args,commands,on_ok)

    def __distro_control(self,args,distro):
        """
        Create/Edit a distro:  'cobbler distro edit --name='foo' ...
        """
        commands = {
            '--name'      :  lambda(a) : distro.set_name(a),
            '--newname'   :  lambda(a) : True,
            '--distro'    :  lambda(a) : distro.set_name(a),
            '--kernel'    :  lambda(a) : distro.set_kernel(a),
            '--initrd'    :  lambda(a) : distro.set_initrd(a),
            '--kopts'     :  lambda(a) : distro.set_kernel_options(a),
            '--arch'      :  lambda(a) : distro.set_arch(a),
            '--ksmeta'    :  lambda(a) : distro.set_ksmeta(a),
            '--breed'     :  lambda(a) : distro.set_breed(a)
        }
        def on_ok():
            self.api.distros().add(distro, with_copy=self.api.sync_flag)
        return self.apply_args(args,commands,on_ok)

    def __system_control(self,args,sys):
        """
        Create/Edit a system:  'cobbler system edit --name='foo' ...
        """
        commands = {
           '--name'        :  lambda(a) : sys.set_name(a),
           '--newname'     :  lambda(a) : True,
           '--system'      :  lambda(a) : sys.set_name(a),
           '--profile'     :  lambda(a) : sys.set_profile(a),
           '--kopts'       :  lambda(a) : sys.set_kernel_options(a),
           '--ksmeta'      :  lambda(a) : sys.set_ksmeta(a),
           '--hostname'    :  lambda(a) : sys.set_hostname(a),
           '--pxe-address' :  lambda(a) : sys.set_ip_address(a),  # deprecated
           '--ip-address'  :  lambda(a) : sys.set_ip_address(a),
           '--ip'          :  lambda(a) : sys.set_ip_address(a),  # alias
           '--mac-address' :  lambda(a) : sys.set_mac_address(a),
           '--mac'         :  lambda(a) : sys.set_mac_address(a), # alias
           '--kickstart'   :  lambda(a) : sys.set_kickstart(a),
           '--kick-start'  :  lambda(a) : sys.set_kickstart(a),
           '--netboot-enabled' : lambda(a) : sys.set_netboot_enabled(a),
           '--virt-path'   :  lambda(a) : sys.set_virt_path(a),
           '--virt-type'   :  lambda(a) : sys.set_virt_type(a)
        }
        def on_ok():
            self.api.systems().add(sys, with_copy=self.api.sync_flag)
        return self.apply_args(args,commands,on_ok)

    ###################################################################################
    # PARSING FUNCTIONS

    def apply_args(self,args,input_routines,on_ok):
        """
        Custom CLI handling, instead of getopt/optparse.
        Parses arguments of the form --foo=bar.
        'on_ok' is a callable that is run if all arguments are parsed
        successfully.  'input_routines' is a dispatch table of routines
        that parse the arguments.  See distro_edit for an example.
        """
        if len(args) == 0:
            raise CX(_("this command requires arguments"))
        for x in args:
            try:
                key, value = x.split("=",1)
                value = value.replace('"','').replace("'",'')
            except:
                raise CX(_("Cobbler was expecting an equal sign in argument '%(argument)s'") % { "argument" : x })
            if input_routines.has_key(key):
                input_routines[key](value)
            else:
                raise CX(_("this command doesn't take an option called '%(argument)s'") % { "argument" : key })
        on_ok()
        self.api.serialize()

    def relay_args(self, args, commands):
        """
        Lookup command args[0] in the dispatch table and
        feed it the remaining args[1:-1] as arguments.
        """
        if args is None or len(args) == 0:
            print USAGE
            return True
        if args[0] in commands:
            commands[args[0]](args[1:])
        else:
            raise CX(_("Cobbler does not understand '%(command)s'") % { "command" : args[0] })
        return True

    ################################################
    # GENERAL FUNCTIONS

    def reserialize(self, args):
        """
        This command is intentionally not documented in the manpage.
        Basically it loads the cobbler config and then reserialize's it's internal state.
        It can be used for testing config format upgrades and other development related things.
        It has very little purpose in the real world.
        """
        self.api.serialize()
        return True

    def sync(self, args):
        """
        Sync the config file with the system config: 'cobbler sync'
        """
        self.api.sync()
        return True

    def reposync(self, args):
        """
        Sync the repo-specific portions of the config with the filesystem.
        'cobbler reposync'.  Intended to be run on cron.
        """
        self.api.reposync()
        return True

    def validateks(self,args):
        """
        Scan rendered kickstarts for potential errors, before actual install
        """
        return self.api.validateks()

    def version(self,args):
        print self.api.version()
        return True

    def check(self,args):
        """
        Check system for network boot decency/prereqs: 'cobbler check'
        """
        status = self.api.check()
        if len(status) == 0:
            print _("No setup problems found")
            print _("Manual review and editing of /var/lib/cobbler/settings is recommended to tailor cobbler to your particular configuration.") 
            print _("Good luck.")

            return True
        else:
            print _("The following potential problems were detected:")
            for i,x in enumerate(status):
               print _("#%(number)d: %(problem)s") % { "number" : i, "problem" : x }
            return False

    def status(self,args):
        """
        Show the kickstart status for logged kickstart activity.
        'cobbler status [--mode=text|somethingelse]'
        """
        self.mode = "text"
        if args is None or len(args) == 0:
            return self.api.status(self.mode)
        def set_mode(a):
            if a.lower in [ "text" ]:
                self.mode = a
                return True
            else: 
                return False
        commands = {
            '--mode' : set_mode
        }
        def go_status():
            return self.api.status(self.mode)
        return self.apply_args(args, commands, go_status)

    def enchant(self,args):
        """
        Reinstall a system:
        'cobbler system enchant --name='foo' [--password='foo']
        """
        self.temp_profile = None
        self.temp_system = None
        self.temp_address = None
        self.is_virt = False
        def set_is_virt(a):
           if a.lower() in [ "0", "false", "no", "n", "off" ]:
               self.is_virt = False
           elif a.lower() in [ "1", "true", "yes", "y", "on" ]:
               self.is_virt = True
           else:
               raise CX("reject_arg","virt")
        def set_profile(a):
           self.temp_profile = a
        def set_system(a):
           self.temp_system = a
        def set_address(a):
           self.temp_address = a
        def go_enchant():
           return self.api.enchant(self.temp_address,self.temp_profile,self.temp_system,self.is_virt)
        commands = {
           '--address'  :  lambda(a): set_address(a),
           '--profile'  :  lambda(a): set_profile(a),
           '--system'   :  lambda(a): set_system(a),
           '--virt'     :  lambda(a): set_is_virt(a)
        }
        on_ok = lambda: go_enchant()
        return self.apply_args(args,commands,on_ok)

    def import_tree(self,args):
        """
        Import a directory tree and auto-create distros & profiles.
        'cobbler
        """
        self.temp_mirror = None
        self.temp_mirror_name = None
        def set_mirror_name(a):
            self.temp_mirror_name = a
        def set_mirror(a):
            self.temp_mirror = a
        def go_import():
            return self.api.import_tree(
                self.temp_mirror,
                self.temp_mirror_name)
        commands = {
            '--path'         : lambda(a): set_mirror(a),
            '--mirror'       : lambda(a): set_mirror(a),
            '--mirror-name'  : lambda(a): set_mirror_name(a),
            '--name'         : lambda(a): set_mirror_name(a)
        }
        on_ok = lambda: go_import()
        return self.apply_args(args,commands,on_ok)


    #########################################################
    # TOPLEVEL MAPPINGS

    def distro(self,args):
        """
        Handles any of the 'cobbler distro' subcommands
        """
        return self.relay_args(args, self.commands['distro'])

    def profile(self,args):
        """
        Handles any of the 'cobbler profile' subcommands
        """
        return self.relay_args(args, self.commands['profile'])

    def system(self,args):
        """
        Handles any of the 'cobbler system' subcommands
        """
        return self.relay_args(args, self.commands['system'])

    def repo(self,args):
        """
        Handles any of the 'cobbler repo' subcommands
        """
        return self.relay_args(args, self.commands['repo'])

####################################################

def main():
    """
    CLI entry point
    """
    exitcode = 0
    lock_hit = False
    try:
        if LOCKING_ENABLED:
            if os.path.exists(LOCKFILE):
                lock_hit = True
                raise CX(_("Locked.  If cobbler is currently running, wait for termination, otherwise remove /var/lib/cobbler/lock"))
            try:
                lockfile = open(LOCKFILE,"w+")
            except:
                raise CX(_("Cobbler could not create the lockfile %(lockfile)s. Are you root?") % { "lockfile" : LOCKFILE })
            lockfile.close()
        BootCLI(sys.argv).run()
    except CobblerException, exc:
        print str(exc)[1:-1]  # remove framing air quotes
        exitcode = 1
    except KeyboardInterrupt:
        print _("interrupted.")
        exitcode = 1
    except Exception, other:
        traceback.print_exc()
        exitcode = 1
    if LOCKING_ENABLED and not lock_hit:
        try:
            os.remove(LOCKFILE)
        except:
            pass
    return exitcode

if __name__ == "__main__":
    sys.exit(main())
