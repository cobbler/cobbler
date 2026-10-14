"""
This module represents all Cobbler methods of authorization. All present modules may be used through the configuration
file ``modules.conf`` normally found at ``/etc/cobbler/``.

Every authorization module must implement :class:`AuthorizationModule` below:

#. The module must define a module-level ``register()`` function returning ``"authz"``.
#. The module must define a module-level ``get_authorization_handler(api)`` factory function returning an instance
   of its :class:`AuthorizationModule` subclass.
#. The subclass must implement :meth:`AuthorizationModule.authorize`.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2007-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class AuthorizationModule(ABC):
    """
    Abstract base class that every Cobbler authorization module must implement.
    """

    def __init__(self, api: "CobblerAPI") -> None:
        """
        Constructor.

        :param api: The API which is used for resolving information.
        """
        self.api = api

    @abstractmethod
    def authorize(
        self, user: str, resource: str, arg1: Any = None, arg2: Any = None
    ) -> int:
        """
        Validate a user against a resource.

        :param user: The user to authorize to the resource.
        :param resource: The resource the user is asking for access. This is something abstract like a remove
                          operation.
        :param arg1: Reserved for the individual use of the implementing authorization module.
        :param arg2: Reserved for the individual use of the implementing authorization module.
        :return: An integer; by convention ``1`` for success and ``0`` for an authorization failure.
        """
