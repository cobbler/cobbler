# Abstracts out the config file format/access and holds
# reasonable default settings.
#
# Michael DeHaan <mdehaan@redhat.com>

import api 
import util
from msg import *

import os
import yaml
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
        self.config_file    = "/etc/bootconf.conf"
        self.set_defaults()
        self.clear()

    """
    Establish an empty list of groups, distros, and systems.
    """
    def clear(self):
        self.groups         = api.Groups(self.api,None)
        self.distros        = api.Distros(self.api,None)
        self.systems        = api.Systems(self.api,None)

    """
    Set some reasonable defaults in case no values are available
    """
    def set_defaults(self):
        self.servername     = "your_server_ip"
        self.kickstart_root = "/var/www/bootconf"
        self.kickstart_url  = "http://%s/kickstart" % (self.servername)
        self.kernel_root    = "/var/www/bootconf"
        self.tftpboot       = "/tftpboot"
        self.dhcpd_conf     = "/etc/dhcpd.conf"
        self.tftpd_conf     = "/etc/xinetd.d/tftp"
        self.pxelinux       = "/usr/lib/syslinux/pxelinux.0"    
        self.tftpd_bin      = "/usr/sbin/in.tftpd"
        self.dhcpd_bin      = "/usr/sbin/dhcpd"

    """
    Access the current groups list
    """
    def get_groups(self):
        return self.groups

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
        # FIXME: this duplication NEEDS to go away.
        # idea: add list of properties to self.properties
        # and use method_missing to write accessors???
        data = {}
        data['servername']     = self.servername
        data['kickstart_root'] = self.kickstart_root
        data['kickstart_url']  = self.kickstart_url
        data['kernel_root']    = self.kernel_root
        data['tftpboot']       = self.tftpboot
        data['dhcpd_conf']     = self.dhcpd_conf
        data['tftpd_conf']     = self.tftpd_conf
        data['pxelinux']       = self.pxelinux
        data['tftpd_bin']      = self.tftpd_bin
        data['dhcpd_bin']      = self.dhcpd_bin
        return data
    
    """
    Load all global config options from hash form (for deserialization)
    """
    def config_from_hash(self,hash):
        try:
            self.servername      = hash['servername']
            self.kickstart_root  = hash['kickstart_root']
            self.kickstart_url   = hash['kickstart_url']
            self.kernel_root     = hash['kernel_root']
            self.tftpboot        = hash['tftpboot']
            self.dhcpd_conf      = hash['dhcpd_conf']
            self.tftpd_conf      = hash['tftpd_conf']
            self.pxelinux        = hash['pxelinux']
            self.tftpd_bin       = hash['tftpd_bin']
            self.dhcpd_bin       = hash['dhcpd_bin']
        except:
            self.set_defaults()
    """
    Convert *everything* Boot knows about to a nested hash
    """
    def to_hash(self):
        world = {} 
        world['config']  = self.config_to_hash()
        world['distros'] = self.get_distros().to_datastruct()
        world['groups']  = self.get_groups().to_datastruct()
        world['systems'] = self.get_systems().to_datastruct()
        return world  


    """
    Convert a hash representation of a Boot config to 'reality'
    """
    def from_hash(self,hash):
        self.config_from_hash(hash['config'])
        self.distros = api.Distros(self.api, hash['distros'])
        self.groups  = api.Groups(self.api,  hash['groups'])
        self.systems = api.Systems(self.api, hash['systems'])

    # ------------------------------------------------------
    # we don't care about file formats until below this line

    """
    Save everything to the config file.
    This goes through an intermediate data format so we
    could use YAML later if we wanted.
    """
    def serialize(self):
        try:
            conf = open(self.config_file,"w+")
        except IOError:
            self.api.last_error = m("cant_create: %s" % self.config_file)
            return False
        data = self.to_hash()
        conf.write(yaml.dump(data))
        return True

    """
    Load everything from the config file.
    This goes through an intermediate data structure format so we
    could use YAML later if we wanted.
    """
    def deserialize(self):
        try:
            conf = yaml.loadFile(self.config_file)
            raw_data = conf.next()
            if raw_data is not None:
                self.from_hash(raw_data)
            return True
        except:
            self.api.last_error = m("parse_error")
            return False

 
