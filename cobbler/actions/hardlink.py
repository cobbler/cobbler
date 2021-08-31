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

from cobbler import utils


class HardLinker:

    def __init__(self, api=None):
        """
        Constructor

        :param api: The API to resolve information with.
        """
        if api is None:
            raise ValueError("cobbler hardlink requires the Cobbler-API for resolving the root folders.")
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

        # Setting the args for hardlink according to the distribution. Must end with a space!
        if self.family == "debian":
            hardlink_args = "-f -p -o -t -v "
        elif self.family == "suse":
            hardlink_args = "-f -v "
        else:
            hardlink_args = "-c -v "
        self.hardlink_cmd = "%s %s %s/distro_mirror %s/repo_mirror" \
                            % (self.hardlink, hardlink_args, self.webdir, self.webdir)

    def run(self):
        """
        Simply hardlinks directories that are Cobbler managed.
        """
        self.logger.info("now hardlinking to save space, this may take some time.")

        utils.subprocess_call(self.hardlink_cmd, shell=True)
        hardlink_cmd = "%s -c -v %s/distro_mirror %s/repo_mirror" % (self.hardlink, self.webdir, self.webdir)

        return utils.subprocess_call(hardlink_cmd, shell=True)
