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

import cobbler_msg
import cexceptions

LOCKING_ENABLED = False
LOCKFILE="/var/lib/cobbler/lock"

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
        }
        self.commands['profile'] = {
            'add'     :  self.profile_edit,
            'edit'    :  self.profile_edit,
            'delete'  :  self.profile_remove,
            'remove'  :  self.profile_remove,
        }
        self.commands['system'] = {
            'add'     :  self.system_edit,
            'edit'    :  self.system_edit,
            'delete'  :  self.system_remove,
            'remove'  :  self.system_remove,
            'enchant' :  self.system_enchant,
        }
        self.commands['toplevel'] = {
            'check'    : self.check,
            'list'     : self.list,
            'distros'  : self.distro,
            'distro'   : self.distro,
            'profiles' : self.profile,
            'profile'  : self.profile,
            'systems'  : self.system,
            'system'   : self.system,
            'sync'     : self.sync,
            'import'   : self.import_tree,
            'help'     : self.usage,
            '/?'       : self.usage
        }

    def run(self):
        """
        Run the command line and return system exit code
        """
        self.api.deserialize()
        self.curry_args(self.args[1:], self.commands['toplevel'])

    def usage(self,args):
        """
        Print out abbreviated help if user gives bad syntax
        """
        raise cexceptions.CobblerException("usage")

    def list(self,args):
        all = [ self.api.settings(), self.api.distros(),
                self.api.profiles(), self.api.systems() ]
        for item in all:
            print item.printable()

    def system_remove(self,args):
        """
        Delete a system:  'cobbler system remove --name=foo'
        """
        commands = {
           '--name'       : lambda(a):  self.api.systems().remove(a),
           '--system'     : lambda(a):  self.api.systems().remove(a),
        }
        on_ok = lambda: True
        return self.apply_args(args,commands,on_ok)

    def profile_remove(self,args):
        """
        Delete a profile:   'cobbler profile remove --name=foo'
        """
        commands = {
           '--name'       : lambda(a):  self.api.profiles().remove(a),
           '--profile'    : lambda(a):  self.api.profiles().remove(a)
        }
        on_ok = lambda: True
        return self.apply_args(args,commands,on_ok)


    def distro_remove(self,args):
        """
        Delete a distro:  'cobbler distro remove --name='foo'
        """
        commands = {
           '--name'     : lambda(a):  self.api.distros().remove(a),
           '--distro'   : lambda(a):  self.api.distros().remove(a)
        }
        on_ok = lambda: True
        return self.apply_args(args,commands,on_ok)


    def system_enchant(self,args):
        """
        Reinstall a system:
        'cobbler system enchant --name='foo' [--password='foo']
        """
        self.temp_password = ''
        self.temp_name = ''
        def set_password(a):
           self.temp_password = a
           return True
        def set_name(a):
           self.temp_name = a
           return True
        def go_enchant():
           return self.api.enchant(self.temp_name,self.temp_password)
        commands = {
           '--name'     :  lambda(a): set_name(a),
           '--password' :  lambda(a): set_password(a),
        }
        on_ok = lambda: go_enchant()
        return self.apply_args(args,commands,on_ok)

    def import_tree(self,args):
        """
        Import a directory tree and auto-create distros & profiles.
        'cobbler
        """
        self.temp_path = None
        self.temp_mirror = None
        self.temp_mirror_name = None
        def set_mirror_name(a):
            self.temp_mirror_name = a
        def set_mirror(a):
            self.temp_mirror = a
        def set_path(a):
            if os.path.isdir(a):
                self.temp_path = a
                return True
            return False
        def go_import():
            return self.api.import_tree(self.temp_path,
                self.temp_mirror,
                self.temp_mirror_name)
        commands = {
            '--path'    : lambda(a): set_path(a),
            '--mirror'  : lambda(a): set_mirror(a)
        }
        on_ok = lambda: go_import()
        return self.apply_args(args,commands,on_ok)

    def system_edit(self,args):
        """
        Create/Edit a system:  'cobbler system edit --name='foo' ...
        """
        sys = self.api.new_system()
        commands = {
           '--name'     :  lambda(a) : sys.set_name(a),
           '--system'   :  lambda(a) : sys.set_name(a),
           '--profile'  :  lambda(a) : sys.set_profile(a),
           '--kopts'    :  lambda(a) : sys.set_kernel_options(a),
           '--ksmeta'   :  lambda(a) : sys.set_ksmeta(a)
        }
        on_ok = lambda: self.api.systems().add(sys)
        return self.apply_args(args,commands,on_ok)


    def profile_edit(self,args):
        """
        Create/Edit a profile:  'cobbler profile edit --name='foo' ...
        """
        profile = self.api.new_profile()
        commands = {
            '--name'            :  lambda(a) : profile.set_name(a),
            '--profile'         :  lambda(a) : profile.set_name(a),
            '--distro'          :  lambda(a) : profile.set_distro(a),
            '--kickstart'       :  lambda(a) : profile.set_kickstart(a),
            '--kick-start'      :  lambda(a) : profile.set_kickstart(a),
            '--kopts'           :  lambda(a) : profile.set_kernel_options(a),
            '--xen-name'        :  lambda(a) : profile.set_xen_name(a),
            '--xen-file-size'   :  lambda(a) : profile.set_xen_file_size(a),
            '--xen-ram'         :  lambda(a) : profile.set_xen_ram(a),
            '--ksmeta'          :  lambda(a) : profile.set_ksmeta(a)
        # the following options are most likely not useful for profiles (yet)
        #    '--xen-paravirt'    :  lambda(a) : profile.set_xen_paravirt(a),
        }
        on_ok = lambda: self.api.profiles().add(profile)
        return self.apply_args(args,commands,on_ok)


    def distro_edit(self,args):
        """
        Create/Edit a distro:  'cobbler distro edit --name='foo' ...
        """
        distro = self.api.new_distro()
        commands = {
            '--name'      :  lambda(a) : distro.set_name(a),
            '--distro'    :  lambda(a) : distro.set_name(a),
            '--kernel'    :  lambda(a) : distro.set_kernel(a),
            '--initrd'    :  lambda(a) : distro.set_initrd(a),
            '--kopts'     :  lambda(a) : distro.set_kernel_options(a),
            '--arch'      :  lambda(a) : distro.set_arch(a),
            '--ksmeta'    :  lambda(a) : distro.set_ksmeta(a)
        }
        on_ok = lambda: self.api.distros().add(distro)
        return self.apply_args(args,commands,on_ok)


    def apply_args(self,args,input_routines,on_ok):
        """
        Custom CLI handling, instead of getopt/optparse.
        Parses arguments of the form --foo=bar.
        'on_ok' is a callable that is run if all arguments are parsed
        successfully.  'input_routines' is a dispatch table of routines
        that parse the arguments.  See distro_edit for an example.
        """
        if len(args) == 0:
            raise cexceptions.CobblerException("no_args")
        for x in args:
            try:
                key, value = x.split("=",1)
                value = value.replace('"','').replace("'",'')
            except:
                raise cexceptions.CobblerException("bad_arg",x)
            if input_routines.has_key(key):
                input_routines[key](value)
            else:
                raise cexceptions.CobblerException("weird_arg", key)
        on_ok()
        self.api.serialize()

    def curry_args(self, args, commands):
        """
        Lookup command args[0] in the dispatch table and
        feed it the remaining args[1:-1] as arguments.
        """
        if args is None or len(args) == 0:
            raise cexceptions.CobblerException("help")
        if args[0] in commands:
            commands[args[0]](args[1:])
        else:
            raise cexceptions.CobblerException("unknown_cmd", args[0])
        return True


    def sync(self, args):
        """
        Sync the config file with the system config: 'cobbler sync [--dryrun]'
        """
        status = None
        if args is not None and "--dryrun" in args:
            status = self.api.sync(dryrun=True)
        else:
            status = self.api.sync(dryrun=False)
        return status


    def check(self,args):
        """
        Check system for network boot decency/prereqs: 'cobbler check'
        """
        status = self.api.check()
        if len(status) == 0:
            print cobbler_msg.lookup("check_ok")
            return True
        else:
            print cobbler_msg.lookup("need_to_fix")
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
    exitcode = 0
    try:
        if LOCKING_ENABLED:
            if os.path.exists(LOCKFILE):
                raise cexceptions.CobblerException("lock")
            try:
                lockfile = open(LOCKFILE,"w+")
            except:
                raise cexceptions.CobblerException("no_create",LOCKFILE)
            lockfile.close()
        BootCLI(sys.argv).run()
    except cexceptions.CobblerException, exc:
        print str(exc)[1:-1]  # remove framing air quotes
        exitcode = 1
    if LOCKING_ENABLED:
        try:
            os.remove(LOCKFILE)
        except:
            pass
    return exitcode

if __name__ == "__main__":
    sys.exit(main())
