"""
TODO
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2008-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import time

from cobbler import validate


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/post/*"


def run(api, args) -> int:
    """
    The method runs the trigger, meaning this logs that an installation has ended.

    The list of args should have three elements:
        - 0: system or profile
        - 1: the name of the system or profile
        - 2: the ip or a "?"

    :param api: This parameter is unused currently.
    :param args: An array of three elements. Type (system/profile), name and ip. If no ip is present use a ``?``.
    :return: Always 0
    """
    objtype = args[0]
    name = args[1]
    ip = args[2]

    if not validate.validate_obj_type(objtype):
        return 1

    if not api.find_items(objtype, name=name, return_list=False):
        return 1

    if not (ip == "?" or validate.ipv4_address(ip) or validate.ipv6_address(ip)):
        return 1

    # FIXME: use the logger

    with open("/var/log/cobbler/install.log", "a+") as fd:
        fd.write("%s\t%s\t%s\tstop\t%s\n" % (objtype, name, ip, time.time()))

    return 0
