"""
Command line interface for cobbler, a network provisioning configuration
library.  Consult 'man cobbler' for general info.  This class serves
as a good reference on how to drive the API (api.py).

Michael DeHaan <mdehaan@redhat.com>
"""

import os
import sys
import api
import syck
import traceback
from msg import *

class BootCLI:


    def __init__(self,args):
        """
        Build the command line parser and API instances, etc.
        """
        self.args = args
        self.api = api.BootAPI()
        self.commands = {}
        self.commands['distro'] = {
            'add'     :  self.distro_edit,
            'edit'    :  self.distro_edit,
            'delete'  :  self.distro_remove,
            'remove'  :  self.distro_remove,
            'list'    :  self.distro_list
        }
        self.commands['profile'] = {
            'add'     :  self.profile_edit,
            'edit'    :  self.profile_edit,
            'delete'  :  self.profile_remove,
            'remove'  :  self.profile_remove,
            'list'    :  self.profile_list
        }
        self.commands['system'] = {
            'add'     :  self.system_edit,
            'edit'    :  self.system_edit,
            'delete'  :  self.system_remove,
            'remove'  :  self.system_remove,
            'list'    :  self.system_list
        }
        self.commands['toplevel'] = {
            'check'    : self.check,
            'distros'  : self.distro,
            'distro'   : self.distro,
            'profiles' : self.profile,
            'profile'  : self.profile,
            'systems'  : self.system,
            'system'   : self.system,
            'sync'     : self.sync,
            '--help'   : self.usage,
            '/?'       : self.usage
        }


    def run(self):
        """
        Run the command line and return system exit code
        """
        rc = self.curry_args(self.args[1:], self.commands['toplevel'])
        if not rc:
            print self.api.last_error
            return 1
        return 0

    def usage(self,args):
        """
        Print out abbreviated help if user gives bad syntax
        """
        print m("usage")
        return False


    def system_list(self,args):
        """
        Print out the list of systems:  'cobbler system list'
        """
        print self.api.systems().printable()
        return True

    def profile_list(self,args):
        """
        Print out the list of profiles: 'cobbler profile list'
        """
        print self.api.profiles().printable()
        return True

    def distro_list(self,args):
        """
        Print out the list of distros: 'cobbler distro list'
        """
        print self.api.distros().printable()
        return True

    def system_remove(self,args):
        """
        Delete a system:  'cobbler system remove --name=foo'
        """
        commands = {
           '--name'       : lambda(a):  self.api.systems().remove(a)
        }
        on_ok = lambda: True
        return self.apply_args(args,commands,on_ok,True)


    def profile_remove(self,args):
        """
        Delete a profile:   'cobbler profile remove --name=foo'
        """
        commands = {
           '--name'       : lambda(a):  self.api.profiles().remove(a)
        }
        on_ok = lambda: True
        return self.apply_args(args,commands,on_ok,True)


    def distro_remove(self,args):
        """
        Delete a distro:  'cobbler distro remove --name='foo'
        """
        commands = {
           '--name'     : lambda(a):  self.api.distros().remove(a)
        }
        on_ok = lambda: True
        return self.apply_args(args,commands,on_ok,True)


    def system_edit(self,args):
        """
        Create/Edit a system:  'cobbler system edit --name='foo' ...
        """
        sys = self.api.new_system()
        commands = {
           '--name'     :  lambda(a) : sys.set_name(a),
           '--profile'  :  lambda(a) : sys.set_profile(a),
           '--kopts'    :  lambda(a) : sys.set_kernel_options(a)
        }
        on_ok = lambda: self.api.systems().add(sys)
        return self.apply_args(args,commands,on_ok,True)


    def profile_edit(self,args):
        """
        Create/Edit a profile:  'cobbler profile edit --name='foo' ...
        """
        profile = self.api.new_profile()
        commands = {
            '--name'            :  lambda(a) : profile.set_name(a),
            '--distro'          :  lambda(a) : profile.set_distro(a),
            '--kickstart'       :  lambda(a) : profile.set_kickstart(a),
            '--kopts'           :  lambda(a) : profile.set_kernel_options(a),
            '--xen-name'        :  lambda(a) : profile.set_xen_name(a),
            '--xen-file-size'   :  lambda(a) : profile.set_xen_file_size(a),
            '--xen-ram'         :  lambda(a) : profile.set_xen_ram(a)
        # the following options are most likely not useful for profiles (yet)
        # primarily due to not being implemented in koan.
        #    '--xen-mac'         :  lambda(a) : profile.set_xen_mac(a),
        #    '--xen-paravirt'    :  lambda(a) : profile.set_xen_paravirt(a),
        }
        on_ok = lambda: self.api.profiles().add(profile)
        return self.apply_args(args,commands,on_ok,True)


    def distro_edit(self,args):
        """
        Create/Edit a distro:  'cobbler distro edit --name='foo' ...
        """
        distro = self.api.new_distro()
        commands = {
            '--name'      :  lambda(a) : distro.set_name(a),
            '--kernel'    :  lambda(a) : distro.set_kernel(a),
            '--initrd'    :  lambda(a) : distro.set_initrd(a),
            '--kopts'     :  lambda(a) : distro.set_kernel_options(a)
        }
        on_ok = lambda: self.api.distros().add(distro)
        return self.apply_args(args,commands,on_ok,True)


    def apply_args(self,args,input_routines,on_ok,serialize):
        """
        Custom CLI handling, instead of getopt/optparse
        Parses arguments of the form --foo=bar, see profile_edit for example
        """
        if len(args) == 0:
            print m("no_args")
            return False
        for x in args:
            try:
                # all arguments must be of the form --key=value
                key, value = x.split("=",1)
                value = value.replace('"','').replace("'",'')
            except:
                print m("bad_arg") % x
                return False
            if key in input_routines:
                # --argument is recognized, so run the loader
                # attached to it in the dispatch table
                if not input_routines[key](value):
                   # loader does not like passed value
                   print m("reject_arg") % key
                   return False
            else:
                # --argument is not recognized
                print m("weird_arg") % key
                return False
        # success thus far, so run the success routine for the set of
        # arguments.  Configuration will only be written to file if the
        # final routine succeeds.
        rc = on_ok()
        if rc and serialize:
            self.api.serialize()
        return rc


    def curry_args(self, args, commands):
        """
        Helper function to make subcommands a bit more friendly.
        See profiles(), system(), or distro() for examples
        """
        if args is None or len(args) == 0:
            print m("help")
            return False
        if args[0] in commands:
            # if the subargument is in the dispatch table, run
            # the selected command routine with the rest of the
            # arguments
            rc = commands[args[0]](args[1:])
            if not rc:
               return False
        else:
            print m("unknown_cmd") % args[0]
            return False
        return True


    def sync(self, args):
        """
        Sync the config file with the system config: 'cobbler sync [--dryrun]'
        """
        status = None
        if args is not None and "--dryrun" in args:
            status = self.api.sync(dry_run=True)
        else:
            status = self.api.sync(dry_run=False)
        return status


    def check(self,args):
        """
        Check system for network boot decency/prereqs: 'cobbler check'
        """
        status = self.api.check()
        if status is None:
            return False
        elif len(status) == 0:
            print m("check_ok")
            return True
        else:
            print m("need_to_fix")
            for i,x in enumerate(status):
               print "#%d: %s" % (i,x)
            return False


    def distro(self,args):
        """
        Handles any of the 'cobbler distro' subcommands
        """
        return self.curry_args(args, self.commands['distro'])


    def profile(self,args):
        """
        Handles any of the 'cobbler profile' subcommands
        """
        return self.curry_args(args, self.commands['profile'])


    def system(self,args):
        """
        Handles any of the 'cobbler system' subcommands
        """
        return self.curry_args(args, self.commands['system'])

def main():
    """
    CLI entry point
    """

    # verify syck isn't busted (old syck bindings were)
    if not hasattr(syck,"dump"):
        raise Exception("needs a more-recent PySyck module")

    if os.getuid() != 0:
        # FIXME: don't require root
        print m("need_root")
        sys.exit(1)
    try:
        cli = BootCLI(sys.argv)
    except Exception, e:
        traceback.print_exc()
        sys.exit(1)
    sys.exit(cli.run())


