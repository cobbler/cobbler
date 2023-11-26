"""
TODO
"""

import time
from typing import TYPE_CHECKING, List

from cobbler import validate

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


def register() -> str:
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type.

    :return: Always `/var/lib/cobbler/triggers/install/pre/*`
    """
    return "/var/lib/cobbler/triggers/install/pre/*"


def run(api: "CobblerAPI", args: List[str]) -> int:
    """
    The method runs the trigger, meaning this logs that an installation has started.

    The list of args should have three elements:
        - 0: system or profile
        - 1: the name of the system or profile
        - 2: the ip or a "?"

    :param api: This parameter is currently unused.
    :param args: Already described above.
    :return: A "0" on success.
    """
    objtype = args[0]
    name = args[1]
    ip_address = args[2]

    if not validate.validate_obj_type(objtype):
        return 1

    if not api.find_items(objtype, name=name, return_list=False):
        return 1

    if not (
        ip_address == "?"
        or validate.ipv4_address(ip_address)
        or validate.ipv6_address(ip_address)
    ):
        return 1

    # FIXME: use the logger

    with open("/var/log/cobbler/install.log", "a", encoding="UTF-8") as install_log_fd:
        install_log_fd.write(f"{objtype}\t{name}\t{ip_address}\tstart\t{time.time()}\n")

    return 0
