"""
Configures acls for various users/groups so they can access the Cobbler command
line as non-root.  Now that CLI is largely remoted (XMLRPC) this is largely just
useful for not having to log in (access to shared-secret) file but also grants
access to hand-edit various cobbler_collections files and other useful things.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from typing import TYPE_CHECKING, Optional

from cobbler import utils
from cobbler.cexceptions import CX

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class AclConfig:
    """
    TODO
    """

    def __init__(self, api: "CobblerAPI") -> None:
        """
        Constructor

        :param api: The API which holds all information about Cobbler.
        """
        self.api = api
        self.settings = api.settings()

    def run(
        self,
        adduser: Optional[str] = None,
        addgroup: Optional[str] = None,
        removeuser: Optional[str] = None,
        removegroup: Optional[str] = None,
    ) -> None:
        """
        Automate setfacl commands. Only one of the four may be specified but one option also must be specified.

        :param adduser: Add a user to be able to manage Cobbler.
        :param addgroup: Add a group to be able to manage Cobbler.
        :param removeuser: Remove a user to be able to manage Cobbler.
        :param removegroup: Remove a group to be able to manage Cobbler.
        :raises CX: Raised in case not enough arguments are specified.
        """

        args_ok = False
        if adduser:
            args_ok = True
            self.modacl(True, True, adduser)
        if addgroup:
            args_ok = True
            self.modacl(True, False, addgroup)
        if removeuser:
            args_ok = True
            self.modacl(False, True, removeuser)
        if removegroup:
            args_ok = True
            self.modacl(False, False, removegroup)
        if not args_ok:
            raise CX("no arguments specified, nothing to do")

    def modacl(self, isadd: bool, isuser: bool, who: str) -> None:
        """
        Modify the acls for Cobbler on the filesystem.

        :param isadd: If true then the ``who`` will be added. If false then ``who`` will be removed.
        :param isuser: If true then the ``who`` may be a user. If false then ``who`` may be a group.
        :param who: The user or group to be added or removed.
        """
        snipdir = self.settings.autoinstall_snippets_dir
        tftpboot = self.settings.tftpboot_location

        process_dirs = {
            "/var/log/cobbler": "rwx",
            "/var/log/cobbler/tasks": "rwx",
            "/var/lib/cobbler": "rwx",
            "/etc/cobbler": "rwx",
            tftpboot: "rwx",
            "/var/lib/cobbler/triggers": "rwx",
        }
        if not snipdir.startswith("/var/lib/cobbler/"):
            process_dirs[snipdir] = "r"

        for (directory, how) in process_dirs.items():
            cmd = [
                "setfacl",
                "-d",
                "-R",
                "-m" if isadd else "-x",
                f"u:{who}" if isuser else f"g:{who}",
                directory,
            ]
            if isadd:
                cmd[4] = f"{cmd[4]}:{how}"

            # We must pass in a copy of list because in case the call is async we
            # would modify the call that maybe has not been done. We don't do this
            # yet but let's be sure. Also, the tests would break if we don't pass a copy.
            setfacl_reset_return_code = utils.subprocess_call(cmd.copy(), shell=False)
            if setfacl_reset_return_code != 0:
                utils.die(f'"setfacl" command failed for "{directory}"')
            cmd.pop(1)
            setfacl_return_code = utils.subprocess_call(cmd.copy(), shell=False)
            if setfacl_return_code != 0:
                utils.die(f'"setfacl" command failed for "{directory}"')
