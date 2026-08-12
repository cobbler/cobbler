"""
Low-level OS/environment detection helpers for process-management backend selection. Contains no restart
logic -- see ``process_management.service.restart_service()`` and ``process_management.docker.restart_service()``.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import os
from xmlrpc.client import ServerProxy


def is_systemd() -> bool:
    """
    Return whether this system uses systemd.

    This method currently checks if the path ``/usr/lib/systemd/systemd`` exists.
    """
    return os.path.exists("/usr/lib/systemd/systemd")


def is_supervisord() -> bool:
    """
    Return whether this system uses supervisord.

    This method currently checks if there is a running supervisord instance on ``localhost``.
    """
    with ServerProxy("http://localhost:9001/RPC2") as server:
        try:
            server.supervisor.getState()
        except OSError:
            return False
        return True


def is_service() -> bool:
    """
    Return whether this system uses service.

    This method currently checks if the path ``/usr/sbin/service`` exists.
    """
    return os.path.exists("/usr/sbin/service")


def is_containerized() -> bool:
    """
    Return whether the current process is running inside a container.

    Checks, in order: the presence of ``/.dockerenv``, the ``container`` environment variable (set by
    systemd-nspawn and by ``docker/images/cobblerd/Dockerfile``'s own base image conventions), and
    "docker"/"containerd" substrings in ``/proc/1/cgroup`` as a last resort (covers older cgroup v1 hosts).
    Any one signal being true suffices.
    """
    if os.path.exists("/.dockerenv"):
        return True
    if os.environ.get("container"):
        return True
    try:
        with open("/proc/1/cgroup", encoding="utf-8") as cgroup_file:
            content = cgroup_file.read()
        return "docker" in content or "containerd" in content
    except OSError:
        return False
