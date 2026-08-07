"""
This is some of the code behind 'cobbler sync' for the dynamic HTTP-serving mode, where the distro source tree is
served on demand (e.g. straight from its original location) instead of being copied into the webroot.

Unlike ``dynamic_tftp.py``, which changes behavior itself by turning all its methods into no-ops, this module does
**not** change any sync-time behavior on its own. It is inert; it only exists to be *selectable*, so a later task's
``cobbler import`` logic can check
``api.get_module_name_from_file("httpd", "module", "managers.in_httpd") == "managers.dynamic_httpd"`` and decide to
skip copying the distro tree, and so ``cobbler check`` can warn about stale source paths.
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


class _DynamicHttpdManager(HttpdManagerModule):
    """
    Marker manager for the dynamic (non-copying) HTTP-serving mode.

    This class does not change any sync-time behavior on its own; it only exists so it can be selected via
    ``modules.httpd.module`` and detected through its :meth:`what` return value.
    """

    @staticmethod
    def what() -> str:
        """
        Static method to identify the manager.

        :return: Always "dynamic_httpd".
        """
        return "dynamic_httpd"

    def __init__(self, api: "CobblerAPI"):
        super().__init__(api)


def get_manager(api: "CobblerAPI") -> _DynamicHttpdManager:
    """
    Creates a manager object to manage HTTP content that is served dynamically instead of being copied into the
    webroot.

    :param api: The API which holds all information in the current Cobbler instance.
    :return: The object to manage the server with.
    """
    # Singleton used, therefore ignoring 'global'
    global MANAGER  # pylint: disable=global-statement

    if not MANAGER:
        MANAGER = _DynamicHttpdManager(api)  # type: ignore
    return MANAGER
