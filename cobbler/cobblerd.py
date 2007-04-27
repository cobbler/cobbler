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

import socket
import time
import os
import SimpleXMLRPCServer
import yaml # Howell Clark version

import api as cobbler_api

# hack to make xmlrpclib tolerate None:
# http://www.thescripts.com/forum/thread499321.html
import xmlrpclib
# WARNING: Dirty hack below.
# Replace the dumps() function in xmlrpclib with one that by default
# handles None, so SimpleXMLRPCServer can return None.
class _xmldumps(object):
    def __init__(self, dumps):
        self.__dumps = (dumps,)
    def __call__(self, *args, **kwargs):
        kwargs.setdefault('allow_none', 1)
        return self.__dumps[0](*args, **kwargs)
xmlrpclib.dumps = _xmldumps(xmlrpclib.dumps)

def main():

    bootapi     = cobbler_api.BootAPI()
    settings    = bootapi.settings()
    syslog_port = settings.syslog_port
    xmlrpc_port = settings.xmlrpc_port

    pid = os.fork()

    if pid == 0:
        do_xmlrpc(bootapi, settings, xmlrpc_port)
    else:
        do_syslog(bootapi, settings, syslog_port)

def do_xmlrpc(bootapi, settings, port):

    xinterface = CobblerXMLRPCInterface(bootapi)
    server = CobblerXMLRPCServer(('', port))
    server.register_instance(xinterface)
    server.serve_forever()

def do_syslog(bootapi, settings, port):

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", port))

    buf = 1024

    while 1:
        data, addr = s.recvfrom(buf)
        (ip, port) = addr
        if not data:
            break
        else:
            logfile = open("/var/log/cobbler/syslog/%s" % ip, "a+")
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

class CobblerXMLRPCInterface:

    def __init__(self,api):
        self.api = api

    def __sorter(self,a,b):
        return cmp(a["name"],b["name"])

    def __get_all(self,collection):
        data = collection.to_datastruct()
        data.sort(self.__sorter)
        return data

    def get_distros(self):
        return self.__get_all(self.api.distros())

    def get_profiles(self):
        return self.__get_all(self.api.profiles())

    def get_systems(self):
        return self.__get_all(self.api.systems())

    def __get_specific(self,collection,name):
        item = collection.find(name)
        if item is None:
            return {}
        return item.to_datastruct()

    def get_distro(self,name):
        return self.__get_specific(self.api.distros(),name)

    def get_profile(self,name):
        return self.__get_specific(self.api.profiles(),name)

    def get_system(self,name):
        return self.__get_specific(self.api.systems(),name)

    def get_repo(self,name):
        return self.__get_specific(self.api.repos(),name)

    def __get_for_koan(self,dir,name):
        path = os.path.join(settings.webdir, dir, name)
        if not os.path.exists(path):
            return {}
        fd = open(path)
        data = fd.read()
        datastruct = yaml.load(data).next()
        fd.close()
        return datastruct

    def get_distro_for_koan(self,name):
        return self.__get_for_koan("distros",name)

    def get_profile_for_koan(self,name):
        return self.__get_for_koan("profiles",name)

    def get_system_for_koan(self,name):
        return self.__get_for_koan("systems",name)

class CobblerXMLRPCServer(SimpleXMLRPCServer.SimpleXMLRPCServer):

    def __init__(self, args):
        self.allow_reuse_address = True
        SimpleXMLRPCServer.SimpleXMLRPCServer.__init__(self,args)


if __name__ == "__main__":

    main()

