"""
cobbler daemon for logging remote syslog traffic during kickstart
 
Copyright 2007-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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
import utils

import api as cobbler_api
import yaml # Howell Clark version
import utils
import remote


def main():
    core(logger=None)

def core(api):

    bootapi      = api
    settings     = bootapi.settings()
    xmlrpc_port  = settings.xmlrpc_port

    regen_ss_file()
    do_xmlrpc_tasks(bootapi, settings, xmlrpc_port)

def regen_ss_file():
    # this is only used for Kerberos auth at the moment.
    # it identifies XMLRPC requests from Apache that have already
    # been cleared by Kerberos.
    ssfile = "/var/lib/cobbler/web.ss"
    fd = open("/dev/urandom")
    data = fd.read(512)
    fd.close()
    if not os.path.isfile(ssfile):
        fd = os.open(ssfile,os.O_CREAT|os.O_RDWR,0600)
        os.write(fd,binascii.hexlify(data))
        os.close(fd)
        http_user = "apache"
        if utils.check_dist() in [ "debian", "ubuntu" ]:
            http_user = "www-data"
        utils.os_system("chown %s /var/lib/cobbler/web.ss"%http_user )
    else:
        fd = os.open(ssfile,os.O_CREAT|os.O_RDWR,0600)
        os.write(fd,binascii.hexlify(data))
        os.close(fd)

    return 1

def do_xmlrpc_tasks(bootapi, settings, xmlrpc_port):
    do_xmlrpc_rw(bootapi, settings, xmlrpc_port)

#def do_other_tasks(bootapi, settings, syslog_port, logger):
#
#    # FUTURE: this should also start the Web UI, if the dependencies
#    # are available.
# 
#    if os.path.exists("/usr/bin/avahi-publish-service"):
#        pid2 = os.fork()
#        if pid2 == 0:
#           do_syslog(bootapi, settings, syslog_port, logger)
#        else:
#           do_avahi(bootapi, settings, logger)
#           os.waitpid(pid2, 0)
#    else:
#        do_syslog(bootapi, settings, syslog_port, logger)


def log(logger,msg):
    if logger is not None:
        logger.info(msg)
    else:
        print >>sys.stderr, msg

#def do_avahi(bootapi, settings, logger):
#    # publish via zeroconf.  This command will not terminate
#    log(logger, "publishing avahi service")
#    cmd = [ "/usr/bin/avahi-publish-service",
#            "cobblerd",
#            "_http._tcp",
#            "%s" % settings.xmlrpc_port ]
#    proc = sub_process.Popen(cmd, shell=False, stderr=sub_process.PIPE, stdout=sub_process.PIPE, close_fds=True)
#    proc.communicate()[0]
#    log(logger, "avahi service terminated") 


def do_xmlrpc_rw(bootapi,settings,port):

    xinterface = remote.ProxiedXMLRPCInterface(bootapi,remote.CobblerXMLRPCInterface)
    server = remote.CobblerXMLRPCServer(('127.0.0.1', port))
    server.logRequests = 0  # don't print stuff
    xinterface.logger.debug("XMLRPC running on %s" % port)
    server.register_instance(xinterface)

    while True:
        try:
            print "SERVING!"
            server.serve_forever()
        except IOError:
            # interrupted? try to serve again
            time.sleep(0.5)

if __name__ == "__main__":

    bootapi  = cobbler_api.BootAPI()
    settings = bootapi.settings()

    regen_ss_file()

    do_xmlrpc_rw(bootapi, settings, 25151)

