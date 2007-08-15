# cobbler daemon for logging remote syslog traffic during kickstart
# 
# Copyright 2007, Red Hat, Inc
# Michael DeHaan <mdehaan@redhat.com>
# 
# This software may be freely redistributed under the terms of the GNU
# general public license.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sys
import socket
import time
import os
import SimpleXMLRPCServer
import yaml # Howell Clark version
import glob
import api as cobbler_api
import utils
from rhpl.translate import _, N_, textdomain, utf8
import xmlrpclib

def main():
   core(logger=None)

def core(logger=None):

    bootapi     = cobbler_api.BootAPI()
    settings    = bootapi.settings()
    syslog_port = settings.syslog_port
    xmlrpc_port = settings.xmlrpc_port

    pid = os.fork()

    if pid == 0:
        do_xmlrpc(bootapi, settings, xmlrpc_port, logger)
    else:
        do_syslog(bootapi, settings, syslog_port, logger)

def log(logger,msg):
    if logger is not None:
        logger.info(msg)
    else:
        print >>sys.stderr, msg

def do_xmlrpc(bootapi, settings, port, logger):

    xinterface = CobblerXMLRPCInterface(bootapi,logger)
    server = CobblerXMLRPCServer(('', port))
    log(logger, "XMLRPC running on %s" % port)
    server.register_instance(xinterface)

    while True:
        try:
            server.serve_forever()
        except IOError:
            # interrupted? try to serve again
            time.sleep(0.5)
             

def do_syslog(bootapi, settings, port, logger):

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", port))
    log(logger, "syslog running on %s" % port)

    buf = 1024

    while 1:
        data, addr = s.recvfrom(buf)
        (ip, port) = addr
        system = bootapi.systems().find(ip_address = ip)
        if not data and system:
            break
        else:
            logfile = open("/var/log/cobbler/syslog/%s" % system.name, "a+")
            t = time.localtime()
            # write numeric time
            seconds = str(time.mktime(t))
            logfile.write(seconds)
            logfile.write("\t")
            # write string time
            timestr = str(time.asctime(t))
            logfile.write(timestr)
            logfile.write("\t")
            # write the IP address of the client
            logfile.write(ip)
            logfile.write("\t")
            # write the data
            logfile.write(data)
            logfile.write("\n")
            logfile.close()

# FIXME: somewhat inefficient as it reloads the configs each time
# better to watch files for changes?

class CobblerXMLRPCInterface:

    def __init__(self,api,logger):
        self.api = api
        self.logger = logger

    def __sorter(self,a,b):
        return cmp(a["name"],b["name"])

    def get_settings(self):
        self.api.clear()
        self.api.deserialize()
        data = self.api.settings().to_datastruct()
        return self.fix_none(data)
 
    def disable_netboot(self,name):
        # used by nopxe.cgi
        self.api.clear()
        self.api.deserialize()
        if not self.api.settings().pxe_just_once:
            # feature disabled!
            return False
        systems = self.api.systems()
        obj = systems.find(name=name)
        if obj == None:
            # system not found!
            return False
        obj.set_netboot_enabled(0)
        systems.add(obj,with_copy=True)
        return True

    def __get_all(self,collection):
        self.api.clear() 
        self.api.deserialize()
        data = collection.to_datastruct()
        data.sort(self.__sorter)
        return self.fix_none(data)

    def version(self):
        return self.api.version()

    def get_distros(self):
        return self.__get_all(self.api.distros())

    def get_profiles(self):
        return self.__get_all(self.api.profiles())

    def get_systems(self):
        return self.__get_all(self.api.systems())

    def __get_specific(self,collection,name):
        self.api.clear() 
        self.api.deserialize()
        item = collection.find(name=name)
        if item is None:
            return self.fix_none({})
        return self.fix_none(item.to_datastruct())

    def get_distro(self,name):
        return self.__get_specific(self.api.distros(),name)

    def get_profile(self,name):
        return self.__get_specific(self.api.profiles(),name)

    def get_system(self,name):
        name = self.fix_system_name(name)
        return self.__get_specific(self.api.systems(),name)

    def get_repo(self,name):
        return self.__get_specific(self.api.repos(),name)

    def get_distro_for_koan(self,name):
        self.api.clear() 
        self.api.deserialize()
        obj = self.api.distros().find(name=name)
        if obj is not None:
            return self.fix_none(utils.blender(True, obj))
        return self.fix_none({})

    def get_profile_for_koan(self,name):
        self.api.clear() 
        self.api.deserialize()
        obj = self.api.profiles().find(name=name)
        if obj is not None:
            return self.fix_none(utils.blender(True, obj))
        return self.fix_none({})

    def get_system_for_koan(self,name):
        self.api.clear() 
        self.api.deserialize()
        obj = self.api.systems().find(name=name)
        if obj is not None:
           return self.fix_none(utils.blender(True, obj))
        return self.fix_none({})

    def get_repo_for_koan(self,name):
        self.api.clear() 
        self.api.deserialize()
        obj = self.api.repos().find(name=name)
        if obj is not None:
            return self.fix_none(utils.blender(True, obj))
        return self.fix_none({})

    def fix_none(self,data,recurse=False):
        """
        Convert None in XMLRPC to just '~'.  Above hack should
        do this, but let's make extra sure.
        """

        if data is None:
            data = '~'

        elif type(data) == list:
            data = [ self.fix_none(x,recurse=True) for x in data ]

        elif type(data) == dict:
            for key in data.keys():
               data[key] = self.fix_none(data[key],recurse=True)

        return data



class CobblerXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):

    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)


if __name__ == "__main__":

    main()

