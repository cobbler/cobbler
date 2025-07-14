"""
Cobbler daemon for logging remote syslog traffic during automatic installation
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
import logging.config
import os
import sys
import traceback

from cobbler.api import CobblerAPI
from cobbler.cobblerd.cli import cli_generate_main_parser
from cobbler.cobblerd.daemon import core, daemonize_self
from cobbler.cobblerd.distro_options import get_distro_options
from cobbler.cobblerd.setup import setup_cobblerd

if os.geteuid() == 0 and os.path.exists("/etc/cobbler/logging_config.conf"):
    logging.config.fileConfig("/etc/cobbler/logging_config.conf")


logger = logging.getLogger()


def main() -> int:
    """
    Main entrypoint for the Cobbler daemon.
    """
    op = cli_generate_main_parser()
    options = op.parse_args()

    if options.subparser_name == "setup":
        distro_options = get_distro_options()
        distro_options.systemd_dir = options.systemd_directory
        setup_cobblerd(options.base_dir, distro_options, options.mode)
    else:
        # load the API now rather than later, to ensure cobblerd startup time is done before the service returns
        # Disable broad exception caught as this is desired on a top-level entrypoint
        # pylint: disable=broad-exception-caught
        api = None
        try:
            api = CobblerAPI(
                is_cobblerd=True,
                settingsfile_location=options.config,
                execute_settings_automigration=options.automigration,
            )
        except Exception as exc:
            if sys.exc_info()[0] == SystemExit:
                # pylint: disable-next=no-member
                return exc.code  # type: ignore
            else:
                # FIXME: log this too
                traceback.print_exc()
                return 1

        if options.daemonize:
            daemonize_self()

        try:
            core(api)
        except Exception as e:
            logger.error(e)
            traceback.print_exc()

    return 0


if __name__ == "__main__":
    sys.exit(main())
