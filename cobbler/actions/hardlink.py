"""
Hard links Cobbler content together to save space.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import logging
import os
from typing import TYPE_CHECKING

from cobbler import utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class HardLinker:
    """
    HardLinker is responsible for managing hardlinking of Cobbler-managed directories to save disk space.

    This class locates the system's 'hardlink' executable and uses it to deduplicate files in specified directories,
    typically those used for distribution and repository mirrors. The arguments passed to the 'hardlink' command
    are determined by the detected Linux distribution family.
    """

    def __init__(self, api: "CobblerAPI") -> None:
        """
        Constructor

        :param api: The API to resolve information with.
        """
        self.api = api
        self.hardlink = ""
        self.logger = logging.getLogger()
        self.family = utils.get_family()
        self.webdir = self.api.settings().webdir

        # Getting the path to hardlink
        for possible_location in ["/usr/bin/hardlink", "/usr/sbin/hardlink"]:
            if os.path.exists(possible_location):
                self.hardlink = possible_location
        if not self.hardlink:
            utils.die("please install 'hardlink' to use this feature")

    def run(self) -> int:
        """
        Simply hardlinks directories that are Cobbler managed.
        """
        self.logger.info("now hardlinking to save space, this may take some time.")

        # Setting the args for hardlink according to the distribution. Must end with a space!
        if self.family == "debian":
            hardlink_args = ["-f", "-p", "-o", "-t", "-v"]
        elif self.family == "suse":
            hardlink_args = ["-f", "-v"]
        else:
            hardlink_args = ["-c", "-v"]
        hardlink_cmd = (
            [self.hardlink]
            + hardlink_args
            + [f"{self.webdir}/distro_mirror", f"{self.webdir}/repo_mirror"]
        )
        utils.subprocess_call(hardlink_cmd.copy(), shell=False)

        hardlink_cmd = [
            self.hardlink,
            "-c",
            "-v",
            f"{self.webdir}/distro_mirror",
            f"{self.webdir}/repo_mirror",
        ]
        return utils.subprocess_call(hardlink_cmd.copy(), shell=False)
