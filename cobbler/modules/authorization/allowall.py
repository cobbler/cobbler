"""
Authorization module that allows everything, which is the default for new Cobbler installs.
"""

from typing import TYPE_CHECKING, Any

from cobbler.modules.authorization import AuthorizationModule

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: Always "authz"
    """
    return "authz"


class AllowAllAuthorizationModule(AuthorizationModule):
    """
    Authorization module that allows everything, which is the default for new Cobbler installs.
    """

    def authorize(
        self, user: str, resource: str, arg1: Any = None, arg2: Any = None
    ) -> int:
        """
        Validate a user against a resource.
        NOTE: acls are not enforced as there is no group support in this module

        :param user: This parameter is not used currently.
        :param resource: This parameter is not used currently.
        :param arg1: This parameter is not used currently.
        :param arg2: This parameter is not used currently.
        :return: Always ``1``
        """
        return 1


def get_authorization_handler(api: "CobblerAPI") -> AllowAllAuthorizationModule:
    """
    Factory consumed by :class:`cobbler.api.CobblerAPI` to obtain the authorization handler instance.

    :param api: The API which is used for resolving information.
    :return: The handler instance.
    """
    return AllowAllAuthorizationModule(api)
