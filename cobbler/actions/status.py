"""
Reports on automatic installation activity by examining the logs in
/var/log/cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import glob
import gzip
import re
import time
from typing import List, Union

# ARRAY INDEXES
MOST_RECENT_START = 0
MOST_RECENT_STOP = 1
MOST_RECENT_TARGET = 2
SEEN_START = 3
SEEN_STOP = 4
STATE = 5


class CobblerStatusReport:
    def __init__(self, api, mode: str):
        """
        Constructor

        :param api: The API which holds all information.
        :param mode: This describes how Cobbler should report. Currently there only the option ``text`` can be set
                     explicitly.
        """
        self.settings = api.settings()
        self.ip_data = {}
        self.mode = mode

    @staticmethod
    def collect_logfiles() -> List[str]:
        """
        Collects all installation logfiles from ``/var/log/cobbler/``. This will also collect gzipped logfiles.

        :returns: List of absolute paths that are matching the filepattern ``install.log`` or ``install.log.x``, where
                  x is a number equal or greater than zero.
        """
        unsorted_files = glob.glob("/var/log/cobbler/install.log*")
        files_dict = {}
        log_id_re = re.compile(r"install.log.(\d+)")
        for fname in unsorted_files:
            id_match = log_id_re.search(fname)
            if id_match:
                files_dict[int(id_match.group(1))] = fname

        files = []
        sorted_ids = sorted(files_dict, key=files_dict.get, reverse=True)
        for file_id in sorted_ids:
            files.append(files_dict[file_id])
        if "/var/log/cobbler/install.log" in unsorted_files:
            files.append("/var/log/cobbler/install.log")

        return files

    def scan_logfiles(self):
        """
        Scan the installation log-files - starting with the oldest file.
        """
        for fname in self.collect_logfiles():
            if fname.endswith(".gz"):
                fd = gzip.open(fname, "rt")
            else:
                fd = open(fname, "rt")
            data = fd.read()
            for line in data.split("\n"):
                tokens = line.split()
                if len(tokens) == 0:
                    continue
                (profile_or_system, name, ip, start_or_stop, ts) = tokens
                self.catalog(profile_or_system, name, ip, start_or_stop, ts)
            fd.close()

    def catalog(
        self, profile_or_system: str, name: str, ip, start_or_stop: str, ts: float
    ):
        """
        Add a system to ``cobbler status``.

        :param profile_or_system: This can be ``system`` or ``profile``.
        :param name: The name of the object.
        :param ip: The ip of the system to watch.
        :param start_or_stop: This parameter may be ``start`` or ``stop``
        :param ts: Timestamp as returned by ``time.time()``
        """
        if ip not in self.ip_data:
            self.ip_data[ip] = [-1, -1, "?", 0, 0, "?"]
        elem = self.ip_data[ip]

        ts = float(ts)

        mrstart = elem[MOST_RECENT_START]
        mrstop = elem[MOST_RECENT_STOP]
        mrtarg = elem[MOST_RECENT_TARGET]

        if start_or_stop == "start":
            if mrstart < ts:
                mrstart = ts
                mrtarg = f"{profile_or_system}:{name}"
                elem[SEEN_START] += 1

        if start_or_stop == "stop":
            if mrstop < ts:
                mrstop = ts
                mrtarg = f"{profile_or_system}:{name}"
                elem[SEEN_STOP] += 1

        elem[MOST_RECENT_START] = mrstart
        elem[MOST_RECENT_STOP] = mrstop
        elem[MOST_RECENT_TARGET] = mrtarg

    def process_results(self) -> dict:
        """
        Look through all systems which were collected and update the status.

        :return: Return ``ip_data`` of the object.
        """
        # FIXME: this should update the times here
        tnow = int(time.time())
        for ip in self.ip_data.keys():
            elem = self.ip_data[ip]
            start = int(elem[MOST_RECENT_START])
            stop = int(elem[MOST_RECENT_STOP])
            if stop > start:
                elem[STATE] = "finished"
            else:
                delta = tnow - start
                minutes = delta // 60
                seconds = delta % 60
                if minutes > 100:
                    elem[STATE] = "unknown/stalled"
                else:
                    elem[STATE] = f"installing ({minutes}m {seconds}s)"

        return self.ip_data

    def get_printable_results(self) -> str:
        """
        Convert the status of Cobbler from a machine-readable form to human-readable.

        :return: A nice formatted representation of the results of ``cobbler status``.
        """
        printable_status_format = "%-15s|%-20s|%-17s|%-17s"
        ips = list(self.ip_data.keys())
        ips.sort()
        line = (
            "ip",
            "target",
            "start",
            "state",
        )
        buf = printable_status_format % line
        for ip in ips:
            elem = self.ip_data[ip]
            if elem[MOST_RECENT_START] > -1:
                start = time.ctime(elem[MOST_RECENT_START])
            else:
                start = "Unknown"
            line = (ip, elem[MOST_RECENT_TARGET], start, elem[STATE])
            buf += "\n" + printable_status_format % line
        return buf

    def run(self) -> Union[dict, str]:
        """
        Calculate and print a automatic installation status report.
        """
        self.scan_logfiles()
        results = self.process_results()
        if self.mode == "text":
            return self.get_printable_results()
        else:
            return results
