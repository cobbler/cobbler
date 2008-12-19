"""
cobbler daemon for logging remote syslog traffic during kickstart
 
Copyright 2007, Red Hat, Inc
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
import socket
import time
import os
import SimpleXMLRPCServer
import glob
from utils import _
import xmlrpclib
import binascii

from server import xmlrpclib2
import api as cobbler_api
import yaml # Howell Clark version
import utils
import sub_process
import remote


def main():
   core(logger=None)

def core(logger=None):

    bootapi      = cobbler_api.BootAPI()
    settings     = bootapi.settings()
    syslog_port  = settings.syslog_port
    xmlrpc_port  = settings.xmlrpc_port
    xmlrpc_port2 = settings.xmlrpc_rw_port

    pid = os.fork()

    regen_ss_file()

    if pid == 0:
        # part one: XMLRPC -- which may be just read-only or both read-only and read-write
        do_xmlrpc_tasks(bootapi, settings, xmlrpc_port, xmlrpc_port2, logger)
    else:
        # part two: syslog, or syslog+avahi if avahi is installed
        do_other_tasks(bootapi, settings, syslog_port, logger)
        os.waitpid(pid, 0)

def regen_ss_file():
    # this is only used for Kerberos auth at the moment.
    # it identifies XMLRPC requests from Apache that have already
    # been cleared by Kerberos.

    fd = open("/dev/urandom")
    data = fd.read(512)
    fd.close()
    fd = open("/var/lib/cobbler/web.ss","w+")
    fd.write(binascii.hexlify(data))
    fd.close()
    os.system("chmod 700 /var/lib/cobbler/web.ss")
    os.system("chown apache /var/lib/cobbler/web.ss")
    return 1

def do_xmlrpc_tasks(bootapi, settings, xmlrpc_port, xmlrpc_port2, logger):
    if str(settings.xmlrpc_rw_enabled) != "0":
        pid2 = os.fork()
        if pid2 == 0:
            do_mandatory_xmlrpc_tasks(bootapi, settings, xmlrpc_port, logger)
        else:
            do_xmlrpc_rw(bootapi, settings, xmlrpc_port2, logger)
            os.waitpid(pid2, 0)
    else:
        logger.debug("xmlrpc_rw is disabled in the settings file")
        do_mandatory_xmlrpc_tasks(bootapi, settings, xmlrpc_port, logger)

def do_mandatory_xmlrpc_tasks(bootapi,settings,xmlrpc_port,logger):
    #pid3 = os.fork()
    #if pid3 == 0:
    #    do_xmlrpc(bootapi, settings, xmlrpc_port, logger)
    #else:
    #    # NOTE: this shouldn't be enabled unless we decide
    #    # to use it for something.
    #    # do_xmlrpc_unix(bootapi, settings, logger)
    #    pass
    do_xmlrpc(bootapi, settings, xmlrpc_port, logger)


def do_other_tasks(bootapi, settings, syslog_port, logger):

    # FUTURE: this should also start the Web UI, if the dependencies
    # are available.
 
    if os.path.exists("/usr/bin/avahi-publish-service"):
        pid2 = os.fork()
        if pid2 == 0:
           do_syslog(bootapi, settings, syslog_port, logger)
        else:
           do_avahi(bootapi, settings, logger)
           os.waitpid(pid2, 0)
    else:
        do_syslog(bootapi, settings, syslog_port, logger)


def log(logger,msg):
    if logger is not None:
        logger.info(msg)
    else:
        print >>sys.stderr, msg

def do_avahi(bootapi, settings, logger):
    # publish via zeroconf.  This command will not terminate
    log(logger, "publishing avahi service")
    cmd = [ "/usr/bin/avahi-publish-service",
            "cobblerd",
            "_http._tcp",
            "%s" % settings.xmlrpc_port ]
    proc = sub_process.Popen(cmd, shell=False, stderr=sub_process.PIPE, stdout=sub_process.PIPE, close_fds=True)
    proc.communicate()[0]
    log(logger, "avahi service terminated") 


def do_xmlrpc(bootapi, settings, port, logger):

    # This is the simple XMLRPC API we provide to koan and other
    # apps that do not need to manage Cobbler's config

    xinterface = remote.ProxiedXMLRPCInterface(bootapi,logger,remote.CobblerXMLRPCInterface,False)
    
    server = remote.CobblerXMLRPCServer(('', port))
    server.logRequests = 0  # don't print stuff
    log(logger, "XMLRPC running on %s" % port)
    server.register_instance(xinterface)

    while True:
        try:
            server.serve_forever()
        except IOError:
            # interrupted? try to serve again
            time.sleep(0.5)

def do_xmlrpc_rw(bootapi,settings,port,logger):

    xinterface = remote.ProxiedXMLRPCInterface(bootapi,logger,remote.CobblerReadWriteXMLRPCInterface,True)
    server = remote.CobblerReadWriteXMLRPCServer(('127.0.0.1', port))
    server.logRequests = 0  # don't print stuff
    logger.debug("XMLRPC (read-write variant) running on %s" % port)
    server.register_instance(xinterface)

    while True:
        try:
            server.serve_forever()
        except IOError:
            # interrupted? try to serve again
            time.sleep(0.5)

def do_xmlrpc_unix(bootapi,settings,logger):

    xinterface = remote.ProxiedXMLRPCInterface(bootapi,logger,remote.CobblerReadWriteXMLRPCInterface,True)
    SOCKT = "/var/lib/cobbler/sock"
    server = xmlrpclib2.UnixXMLRPCServer(SOCKT)
    server.logRequests = 0  # don't print stuff
    logger.debug("XMLRPC (socket variant) available on %s" % SOCKT)
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
        if not system:
            usename = ip
        else:
            usename = system.name

        if not data:
            break
        else:
            logfile = open("/var/log/cobbler/syslog/%s" % usename, "a+")
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

if __name__ == "__main__":

    #main()

    #bootapi      = cobbler_api.BootAPI()
    #settings     = bootapi.settings()
    #syslog_port  = settings.syslog_port
    #xmlrpc_port  = settings.xmlrpc_port
    #xmlrpc_port2 = settings.xmlrpc_rw_port
    #logger       = bootapi.logger_remote
    #do_xmlrpc_unix(bootapi, settings, logger)
   
    regen_ss_file()


