"""
Reports on automatic installation activity by examining the logs in
/var/log/cobbler.

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

import glob
import time

import clogger

# ARRAY INDEXES
MOST_RECENT_START = 0
MOST_RECENT_STOP = 1
MOST_RECENT_TARGET = 2
SEEN_START = 3
SEEN_STOP = 4
STATE = 5


class CobblerStatusReport:

    def __init__(self, collection_mgr, mode, logger=None):
        """
        Constructor
        """
        self.collection_mgr = collection_mgr
        self.settings = collection_mgr.settings()
        self.ip_data = {}
        self.mode = mode
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger

    # -------------------------------------------------------

    def scan_logfiles(self):
        files = glob.glob("/var/log/cobbler/install.log*")
        for fname in files:
            fd = open(fname)
            data = fd.read()
            for line in data.split("\n"):
                tokens = line.split()
                if len(tokens) == 0:
                    continue
                (profile_or_system, name, ip, start_or_stop, ts) = tokens
                self.catalog(profile_or_system, name, ip, start_or_stop, ts)
            fd.close()

    # ------------------------------------------------------

    def catalog(self, profile_or_system, name, ip, start_or_stop, ts):
        ip_data = self.ip_data

        if ip not in ip_data:
            ip_data[ip] = [-1, -1, "?", 0, 0, "?"]
        elem = ip_data[ip]

        ts = float(ts)

        mrstart = elem[MOST_RECENT_START]
        mrstop = elem[MOST_RECENT_STOP]
        mrtarg = elem[MOST_RECENT_TARGET]

        if start_or_stop == "start":
            if mrstart < ts:
                mrstart = ts
                mrtarg = "%s:%s" % (profile_or_system, name)
                elem[SEEN_START] += 1

        if start_or_stop == "stop":
            if mrstop < ts:
                mrstop = ts
                mrtarg = "%s:%s" % (profile_or_system, name)
                elem[SEEN_STOP] += 1

        elem[MOST_RECENT_START] = mrstart
        elem[MOST_RECENT_STOP] = mrstop
        elem[MOST_RECENT_TARGET] = mrtarg

    # -------------------------------------------------------

    def process_results(self):
        # FIXME: this should update the times here
        tnow = int(time.time())
        for ip in self.ip_data.keys():
            elem = self.ip_data[ip]
            start = int(elem[MOST_RECENT_START])
            stop = int(elem[MOST_RECENT_STOP])
            if (stop > start):
                elem[STATE] = "finished"
            else:
                delta = tnow - start
                min = delta / 60
                sec = delta % 60
                if min > 100:
                    elem[STATE] = "unknown/stalled"
                else:
                    elem[STATE] = "installing (%sm %ss)" % (min, sec)

        return self.ip_data

    def get_printable_results(self):
        format = "%-15s|%-20s|%-17s|%-17s"
        ip_data = self.ip_data
        ips = ip_data.keys()
        ips.sort()
        line = (
            "ip",
            "target",
            "start",
            "state",
        )
        buf = format % line
        for ip in ips:
            elem = ip_data[ip]
            if elem[MOST_RECENT_START] > -1:
                start = time.ctime(elem[MOST_RECENT_START])
            else:
                start = "Unknown"
            line = (
                ip,
                elem[MOST_RECENT_TARGET],
                start,
                elem[STATE]
            )
            buf += "\n" + format % line
        return buf

    # -------------------------------------------------------

    def run(self):
        """
        Calculate and print a automatic installation status report.
        """
        self.scan_logfiles()
        results = self.process_results()
        if self.mode == "text":
            return self.get_printable_results()
        else:
            return results
