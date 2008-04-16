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
           ip_data[ip] = {}
        elem = ip_data[ip]

        ts = float(ts)
         
        if not elem.has_key("most_recent_start"):
           elem["most_recent_start"] = -1
        if not elem.has_key("most_recent_stop"):
           elem["most_recent_stop"] = -1
        if not elem.has_key("most_recent_target"):
           elem["most_recent_target"] = "?"
        if not elem.has_key("seen_start"):
           elem["seen_start"] = 0
        if not elem.has_key("seen_stop"):
           elem["seen_stop"] = 0
        if not elem.has_key("mac"):
           elem["mac"] = "?"

        mrstart = elem["most_recent_start"]
        mrstop  = elem["most_recent_stop"]
        mrtarg  = elem["most_recent_target"]
        snstart = elem["seen_start"]
        snstop  = elem["seen_stop"]
        snmac   = elem["mac"]


        if start_or_stop == "start":
           if mrstart < ts:
              mrstart = ts
              mrtarg  = "%s:%s" % (profile_or_system, name)
              snmac   = mac
              elem["seen_start"] = elem["seen_start"] + 1

        if start_or_stop == "stop":
           if mrstop < ts:
              mrstop = ts
              mrtarg = "%s:%s" % (profile_or_system, name)
              snmac  = mac
              elem["seen_stop"] = elem["seen_stop"] + 1

        elem["most_recent_start"]  = mrstart
        elem["most_recent_stop"]   = mrstop
        elem["most_recent_target"] = mrtarg
        elem["mac"]                = mac

    # -------------------------------------------------------

    def process_results(self):
        # FIXME: this should update the times here
        print "DEBUG: %s" % self.ip_data
        return self.ip_data

    def get_printable_results(self):
        # ip | last mac | last target | start | stop | count
        format = "%-15s %-17s %-20s %-17s %-17s %5s"
        ip_data = self.ip_data
        ips = ip_data.keys()
        ips.sort()
        line = (
               "ip",
               "mac",
               "target",
               "start",
               "stop",
               "count",
        )
        print "DEBUG:", line
        buf = format % line
        for ip in ips:
            elem = ip_data[ip]
            line = (
               ip,
               elem["mac"],
               elem["most_recent_target"],
               elem["most_recent_start"], # clean up
               elem["most_recent_stop"], # clean up
               elem["seen_stop"]
            )
            print "DEBUG: ", line
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

