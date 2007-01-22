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

import api as cobbler_api

def main():

    bootapi  = cobbler_api.BootAPI()
    settings = bootapi.settings()
    port     = settings.syslog_port

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((socket.gethostname(), port))

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

