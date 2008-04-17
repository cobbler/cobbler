"""
Reports on kickstart activity by examining the logs in
/var/log/cobbler.

Copyright 2007-2008, Red Hat, Inc
Michael DeHaan <mdehaan@redhat.com>

This software may be freely redistributed under the terms of the GNU
general public license.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
"""

import os
import os.path
import glob
import time
import api as cobbler_api

#from utils import _

# ARRAY INDEXES
MOST_RECENT_START  = 0
MOST_RECENT_STOP   = 1
MOST_RECENT_TARGET = 2
SEEN_START         = 3
SEEN_STOP          = 4
MAC                = 5
STATE              = 6

class BootStatusReport:

  
    def __init__(self,config,mode):
        """
        Constructor
        """
        self.config   = config
        self.settings = config.settings()
        self.ip_data  = {}
        self.mode     = mode

    # -------------------------------------------------------

    def scan_logfiles(self):

        #profile foosball        ?       127.0.0.1       start   1208294043.58
        #system  neo     ?       127.0.0.1       start   1208295122.86


        files = glob.glob("/var/log/cobbler/install.log*")
        for fname in files:
           fd = open(fname)
           data = fd.read()
           for line in data.split("\n"):
              tokens = line.split()
              if len(tokens) == 0:
                  continue
              (profile_or_system, name, mac, ip, start_or_stop, ts) = tokens
              self.catalog(profile_or_system,name,mac,ip,start_or_stop,ts)
           fd.close() 

    # ------------------------------------------------------

    def catalog(self,profile_or_system,name,mac,ip,start_or_stop,ts):    
        ip_data = self.ip_data

        if not ip_data.has_key(ip):
           ip_data[ip]  = [ -1, -1, "?", 0, 0, "?", "?" ]
        elem = ip_data[ip]

        ts = float(ts)

        mrstart = elem[MOST_RECENT_START]
        mrstop  = elem[MOST_RECENT_STOP]
        mrtarg  = elem[MOST_RECENT_TARGET]
        snstart = elem[SEEN_START]
        snstop  = elem[SEEN_STOP]
        snmac   = elem[MAC]


        if start_or_stop == "start":
           if mrstart < ts:
              mrstart = ts
              mrtarg  = "%s:%s" % (profile_or_system, name)
              snmac   = mac
              elem[SEEN_START] = elem[SEEN_START] + 1

        if start_or_stop == "stop":
           if mrstop < ts:
              mrstop = ts
              mrtarg = "%s:%s" % (profile_or_system, name)
              snmac  = mac
              elem[SEEN_STOP] = elem[SEEN_STOP] + 1

        elem[MOST_RECENT_START]  = mrstart
        elem[MOST_RECENT_STOP]   = mrstop
        elem[MOST_RECENT_TARGET] = mrtarg
        elem[MAC]                = mac

    # -------------------------------------------------------

    def process_results(self):
        # FIXME: this should update the times here

        tnow = int(time.time())
        for ip in self.ip_data.keys():
           elem = self.ip_data[ip]

           start = int(elem[MOST_RECENT_START])
           stop  = int(elem[MOST_RECENT_STOP])
           if (stop > start):
               elem[STATE] = "finished"
           else:
               delta = tnow - start
               min   = delta / 60
               sec   = delta % 60
               if min > 100:
                   elem[STATE] = "unknown/stalled"
               else:
                   elem[STATE] = "installing (%sm %ss)" % (min,sec)  

        return self.ip_data

    def get_printable_results(self):
        # ip | last mac | last target | start | stop | count
        format = "%-15s|%-17s|%-20s|%-17s|%-17s"
        ip_data = self.ip_data
        ips = ip_data.keys()
        ips.sort()
        line = (
               "ip",
               "mac",
               "target",
               "start",
               "state",
        )
        buf = format % line
        for ip in ips:
            elem = ip_data[ip]
            line = (
               ip,
               elem[MAC],
               elem[MOST_RECENT_TARGET],
               time.ctime(elem[MOST_RECENT_START]),
               elem[STATE]
            )
            buf = buf + "\n" + format % line
        return buf

    # -------------------------------------------------------

    def run(self):
        """
        Calculate and print a kickstart-status report.
        """

        self.scan_logfiles()
        self.process_results()
        print self.get_printable_results()
        return True

