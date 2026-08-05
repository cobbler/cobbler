"""
This is some of the code behind 'cobbler sync' for the default HTTP-serving mode, where the distro source tree is
copied into the webroot (e.g. ``/var/www/cobbler/distro_mirror``) so it can be served by the system HTTP server.
"""

# SPDX-License-Identifier: GPL-2.0-or-later

from typing import TYPE_CHECKING

from cobbler.modules.managers import HttpdManagerModule

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


MANAGER = None


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    return "manage"


class _InHttpdManager(HttpdManagerModule):
    @staticmethod
    def what() -> str:
        """
        Static method to identify the manager.

        :return: Always "in_httpd".
        """
        return "in_httpd"

    def __init__(self, api: "CobblerAPI"):
        super().__init__(api)


def get_manager(api: "CobblerAPI") -> _InHttpdManager:
    """
    Creates a manager object to manage an in_httpd server.

    :param api: The API which holds all information in the current Cobbler instance.
    :return: The object to manage the server with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _InHttpdManager(api)  # type: ignore
    return MANAGER
