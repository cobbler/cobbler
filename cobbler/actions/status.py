"""
Reports on automatic installation activity by examining the logs in
/var/log/cobbler.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import bz2
import glob
import gzip
import logging
import lzma
import os
import re
import time
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, Union

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


LOGGER = logging.getLogger(__name__)


class InstallStatus:
    """
    Helper class that represents the current state of the installation of a system or profile.
    """

    def __init__(self) -> None:
        """
        Default constructor.
        """
        self.most_recent_start = -1.0
        self.most_recent_stop = -1.0
        self.most_recent_target = ""
        self.seen_start = -1.0
        self.seen_stop = -1.0
        self.state = "?"

    def __eq__(self, other: Any) -> bool:
        """
        Equality function that overrides the default behavior.

        :param other: Other object.
        :returns: True in case object is of the same type and all attributes are identical. False otherwise.
        """
        if isinstance(other, InstallStatus):
            return (
                self.most_recent_start == other.most_recent_start
                and self.most_recent_stop == other.most_recent_stop
                and self.most_recent_target == other.most_recent_target
                and self.seen_start == other.seen_start
                and self.seen_stop == other.seen_stop
                and self.state == other.state
            )
        return False


class CobblerStatusReport:
    """
    The class provides functionality to collect, process, and report the status of Cobbler automatic installations.

    It scans installation log files, catalogs installation events, and generates status reports for systems based on
    their IP addresses. It supports both machine-readable and human-readable output formats.
    """

    def __init__(self, api: "CobblerAPI", mode: str) -> None:
        """
        Constructor

        :param api: The API which holds all information.
        :param mode: This describes how Cobbler should report. Currently, there only the option ``text`` can be set
                     explicitly.
        """
        self.settings = api.settings()
        self.ip_data: Dict[str, InstallStatus] = {}
        self.mode = mode

    @staticmethod
    def _safe_getmtime(filename: str) -> float:
        """
        Retrieve the modification time of a log file while tolerating missing files.

        :param filename: Path to the log file.
        :return: Modification time as returned by ``os.path.getmtime`` or ``0.0`` if unavailable.
        """
        try:
            return os.path.getmtime(filename)
        except OSError:
            return 0.0

    @staticmethod
    def collect_logfiles() -> List[str]:
        """
        Collects all installation logfiles from ``/var/log/cobbler/``.

        :returns: Paths sorted from oldest to newest, with ``install.log`` last.
        """
        base_log = os.path.join("/var/log/cobbler", "install.log")
        unsorted_files = glob.glob(f"{base_log}*")
        files_with_keys: List[Tuple[float, str]] = []
        log_id_re = re.compile(r"install\.log\.(\d+)")

        for fname in unsorted_files:
            if fname == base_log:
                continue
            base_name = os.path.basename(fname)
            if not (
                base_name.startswith("install.log.")
                or base_name.startswith("install.log-")
            ):
                continue
            id_match = log_id_re.search(fname)
            if id_match:
                sort_key = float(-int(id_match.group(1)))
            else:
                sort_key = CobblerStatusReport._safe_getmtime(fname)
            files_with_keys.append((sort_key, fname))

        files_with_keys.sort()
        files: List[str] = [fname for _, fname in files_with_keys]
        if "/var/log/cobbler/install.log" in unsorted_files:
            files.append(base_log)

        return files

    @staticmethod
    def _open_logfile(filename: str):
        """
        Open a Cobbler installation log file with the appropriate decompressor.

        :param filename: Path to the log file.
        :return: File object opened in text mode.
        """
        text_kwargs = {"encoding": "utf-8", "errors": "replace"}
        if filename.endswith(".gz"):
            return gzip.open(filename, "rt", **text_kwargs)
        if filename.endswith(".bz2"):
            return bz2.open(filename, "rt", **text_kwargs)
        if filename.endswith(".xz") or filename.endswith(".lzma"):
            return lzma.open(filename, "rt", **text_kwargs)
        return open(filename, "r", **text_kwargs)

    def scan_logfiles(self) -> None:
        """
        Scan the installation log-files - starting with the oldest file.
        """
        for fname in self.collect_logfiles():
            try:
                with self._open_logfile(fname) as logfile_fd:
                    for line in logfile_fd:
                        tokens = line.split()
                        if len(tokens) == 0:
                            continue
                        (
                            profile_or_system,
                            name,
                            ip_address,
                            start_or_stop,
                            timestamp,
                        ) = tokens
                        self.catalog(
                            profile_or_system,
                            name,
                            ip_address,
                            start_or_stop,
                            float(timestamp),
                        )
            except (OSError, UnicodeError, lzma.LZMAError) as error:
                LOGGER.warning(
                    "Skipping unreadable Cobbler log %s: %s",
                    fname,
                    error,
                )

    def catalog(
        self,
        profile_or_system: str,
        name: str,
        ip_address: str,
        start_or_stop: str,
        timestamp: float,
    ) -> None:
        """
        Add a system to ``cobbler status``.

        :param profile_or_system: This can be ``system`` or ``profile``.
        :param name: The name of the object.
        :param ip_address: The ip of the system to watch.
        :param start_or_stop: This parameter may be ``start`` or ``stop``
        :param timestamp: Timestamp as returned by ``time.time()``
        """
        if ip_address not in self.ip_data:
            self.ip_data[ip_address] = InstallStatus()
        elem = self.ip_data[ip_address]

        timestamp = float(timestamp)

        mrstart = elem.most_recent_start
        mrstop = elem.most_recent_stop
        mrtarg = elem.most_recent_target

        if start_or_stop == "start":
            if mrstart < timestamp:
                mrstart = timestamp
                mrtarg = f"{profile_or_system}:{name}"
                elem.seen_start += 1

        if start_or_stop == "stop":
            if mrstop < timestamp:
                mrstop = timestamp
                mrtarg = f"{profile_or_system}:{name}"
                elem.seen_stop += 1

        elem.most_recent_start = mrstart
        elem.most_recent_stop = mrstop
        elem.most_recent_target = mrtarg

    def process_results(self) -> Dict[Any, Any]:
        """
        Look through all systems which were collected and update the status.

        :return: Return ``ip_data`` of the object.
        """
        # FIXME: this should update the times here
        tnow = int(time.time())
        for _, elem in self.ip_data.items():
            start = int(elem.most_recent_start)
            stop = int(elem.most_recent_stop)
            if stop > start:
                elem.state = "finished"
            else:
                delta = tnow - start
                minutes = delta // 60
                seconds = delta % 60
                if minutes > 100:
                    elem.state = "unknown/stalled"
                else:
                    elem.state = f"installing ({minutes}m {seconds}s)"

        return self.ip_data

    def get_printable_results(self) -> str:
        """
        Convert the status of Cobbler from a machine-readable form to human-readable.

        :return: A nice formatted representation of the results of ``cobbler status``.
        """
        printable_status_format = "%-15s|%-20s|%-17s|%-17s"
        ip_addresses = list(self.ip_data.keys())
        ip_addresses.sort()
        line = (
            "ip",
            "target",
            "start",
            "state",
        )
        buf = printable_status_format % line
        for ip_address in ip_addresses:
            elem = self.ip_data[ip_address]
            if elem.most_recent_start > -1:
                start = time.ctime(elem.most_recent_start)
            else:
                start = "Unknown"
            line = (ip_address, elem.most_recent_target, start, elem.state)
            buf += "\n" + printable_status_format % line
        return buf

    def run(self) -> Union[Dict[Any, Any], str]:
        """
        Calculate and print a automatic installation status report.
        """
        self.scan_logfiles()
        results = self.process_results()
        if self.mode == "text":
            return self.get_printable_results()
        return results
