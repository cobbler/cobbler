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

from builtins import object
from past.utils import old_div
import glob
import time
import gzip
import re

from cobbler import clogger

# ARRAY INDEXES
MOST_RECENT_START = 0
MOST_RECENT_STOP = 1
MOST_RECENT_TARGET = 2
SEEN_START = 3
SEEN_STOP = 4
STATE = 5


class CobblerStatusReport(object):

    def __init__(self, collection_mgr, mode, logger=None):
        """
        Constructor

        :param collection_mgr: The collection manager which holds all information.
        :param mode: This describes how Cobbler should report. Currently there only the option ``text`` can be set
                     explicitly.
        :param logger: The logger to audit all actions with.
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
        """
        Scan the install log-files - starting with the oldest file.
        """
        unsorted_files = glob.glob("/var/log/cobbler/install.log*")
        files_dict = dict()
        log_id_re = re.compile(r'install.log.(\d+)')
        for fname in unsorted_files:
            id_match = log_id_re.search(fname)
            if id_match:
                files_dict[int(id_match.group(1))] = fname

        files = list()
        sorted_ids = sorted(files_dict, key=files_dict.get, reverse=True)
        for file_id in sorted_ids:
            files.append(files_dict[file_id])
        if '/var/log/cobbler/install.log' in unsorted_files:
            files.append('/var/log/cobbler/install.log')

        for fname in files:
            if fname.endswith('.gz'):
                fd = gzip.open(fname)
            else:
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
        """
        Add a system to ``cobbler status``.

        :param profile_or_system: This can be ``system`` or ``profile``.
        :type profile_or_system: str
        :param name: The name of the object.
        :type name: str
        :param ip: The ip of the system to watch.
        :param start_or_stop: This parameter may be ``start`` or ``stop``
        :type start_or_stop: str
        :param ts: Don't know what this does.
        """
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
        """
        Look through all systems which were collected and update the status.

        :return: Return ``ip_data`` of the object.
        """
        # FIXME: this should update the times here
        tnow = int(time.time())
        for ip in list(self.ip_data.keys()):
            elem = self.ip_data[ip]
            start = int(elem[MOST_RECENT_START])
            stop = int(elem[MOST_RECENT_STOP])
            if (stop > start):
                elem[STATE] = "finished"
            else:
                delta = tnow - start
                min = old_div(delta, 60)
                sec = delta % 60
                if min > 100:
                    elem[STATE] = "unknown/stalled"
                else:
                    elem[STATE] = "installing (%sm %ss)" % (min, sec)

        return self.ip_data

    def get_printable_results(self):
        """
        Convert the status of Cobbler from a machine readable form to human readable.

        :return: A nice formatted representation of the results of ``cobbler status``.
        """
        format = "%-15s|%-20s|%-17s|%-17s"
        ip_data = self.ip_data
        ips = list(ip_data.keys())
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
