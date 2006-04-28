# Abstracts out the config file format/access and holds
# reasonable default settings.
#
# Michael DeHaan <mdehaan@redhat.com>

import api 
import util
from msg import *

import os
import yaml
#import syck -- we *want* to use syck, but the FC syck currently does not 
#            -- contain the dump function, i.e. not gonna work
import traceback

class BootConfig:

    """
    Constructor.  This class maintains both the logical
    configuration for Boot and the file representation thereof.
    Creating the config object only loads the default values,
    users of this class need to call deserialize() to load config
    file values.
    """
    def __init__(self,api):
        self.api = api
        self.settings_file    = "/etc/cobbler.conf"
        self.state_file       = "/var/cobbler/cobbler.conf"
        self.set_defaults()
        self.clear()

    def files_exist(self):
        return os.path.exists(self.settings_file) and os.path.exists(self.state_file)

    """
    Establish an empty list of profiles distros, and systems.
    """
    def clear(self):
        self.profiles       = api.Profiles(self.api,None)
        self.distros        = api.Distros(self.api,None)
        self.systems        = api.Systems(self.api,None)

    """
    Set some reasonable defaults in case no values are available
    """
    def set_defaults(self):
        self.server         = "localhost"
        self.tftpboot       = "/tftpboot"
        self.dhcpd_conf     = "/etc/dhcpd.conf"
        self.tftpd_conf     = "/etc/xinetd.d/tftp"
        self.pxelinux       = "/usr/lib/syslinux/pxelinux.0"    
        self.tftpd_bin      = "/usr/sbin/in.tftpd"
        self.dhcpd_bin      = "/usr/sbin/dhcpd"
        self.httpd_bin      = "/usr/sbin/httpd"
        self.kernel_options = "append devfs=nomount ramdisk_size=16438 lang= vga=788 ksdevice=eth0" #initrd and ks added programmatically

    """
    Access the current profiles list
    """
    def get_profiles(self):
        return self.profiles

    """
    Access the current distros list
    """
    def get_distros(self):
        return self.distros

    """
    Access the current systems list
    """
    def get_systems(self):
        return self.systems

    """
    Save all global config options in hash form (for serialization)
    """
    def config_to_hash(self):
        data = {}
        data['server']         = self.server
        data['tftpboot']       = self.tftpboot
        data['dhcpd_conf']     = self.dhcpd_conf
        data['tftpd_conf']     = self.tftpd_conf
        data['pxelinux']       = self.pxelinux
        data['tftpd_bin']      = self.tftpd_bin
        data['dhcpd_bin']      = self.dhcpd_bin
        data['httpd_bin']      = self.httpd_bin
        data['kernel_options'] = self.kernel_options
        return data
    
    """
    Load all global config options from hash form (for deserialization)
    """
    def config_from_hash(self,hash):
        try:
            self.server          = hash['server']
            self.tftpboot        = hash['tftpboot']
            self.dhcpd_conf      = hash['dhcpd_conf']
            self.tftpd_conf      = hash['tftpd_conf']
            self.pxelinux        = hash['pxelinux']
            self.tftpd_bin       = hash['tftpd_bin']
            self.dhcpd_bin       = hash['dhcpd_bin']
            self.httpd_bin       = hash['httpd_bin']
            self.kernel_options  = hash['kernel_options']
        except:
            print "WARNING: config file error: %s" % (self.settings_file)
            self.set_defaults()
    """
    Convert all items cobbler knows about to a nested hash.
    There are seperate hashes for the /etc and /var portions.
    """
    def to_hash(self,is_etc):
        world = {} 
        if is_etc:
            world['config']      = self.config_to_hash()
        else:
            world['distros']     = self.get_distros().to_datastruct()
            world['profiles']    = self.get_profiles().to_datastruct()
            world['systems']     = self.get_systems().to_datastruct()
        #print "DEBUG: %s" % (world)
        return world  


    """
    Convert a hash representation of a cobbler to 'reality'
    There are seperate hashes for the /etc and /var portions.
    """
    def from_hash(self,hash,is_etc):
        #print "DEBUG: %s" % hash
        if is_etc:
            self.config_from_hash(hash['config'])
        else:
            self.distros   = api.Distros(self.api, hash['distros'])
            self.profiles  = api.Profiles(self.api,  hash['profiles'])
            self.systems   = api.Systems(self.api, hash['systems'])

    # ------------------------------------------------------
    # we don't care about file formats until below this line

    """
    Save everything to the config file.
    This goes through an intermediate data format so we
    could use YAML later if we wanted.
    """
    def serialize(self):

        settings = None
        state = None
        
        # ------
        # dump global config (pathing, urls, etc)...
        try:
            settings = open(self.settings_file,"w+")
        except IOError:
            self.api.last_error = m("cant_create: %s" % self.settings_file)
            return False
        data = self.to_hash(True)
        settings.write(yaml.dump(data))
 
        # ------
        # dump internal state (distros, profiles, systems...)
        if not os.path.isdir(os.path.dirname(self.state_file)):
            os.mkdir(os.path.dirname(self.state_file))
        try:
            state = open(self.state_file,"w+")
        except:
            self.api.last_error = m("cant_create: %s" % self.state_file)
        data = self.to_hash(False)
        state.write(yaml.dump(data))

        # all good
        return True

    """
    Load everything from the config file.
    This goes through an intermediate data structure format so we
    could use YAML later if we wanted.
    """
    def deserialize(self):
        #print "DEBUG: deserialize"

        # -----
        # load global config (pathing, urls, etc)...
        try:
            settings = yaml.loadFile(self.settings_file)
            raw_data = settings.next()
            if raw_data is not None:
                self.from_hash(raw_data,True)
            else:
                print "WARNING: no %s data?" % self.settings_file
        except:
            self.api.last_error = m("parse_error")
            return False

        # -----
        # load internal state(distros, systems, profiles...)
        try:
            state = yaml.loadFile(self.state_file)
            raw_data = state.next()
            if raw_data is not None:
                self.from_hash(raw_data,False)
            else:
                print "WARNING: no %s data?" % self.state_file
        except:
            traceback.print_exc()
            self.api.last_error = m("parse_error2")
            return False
        
        # all good
        return True

