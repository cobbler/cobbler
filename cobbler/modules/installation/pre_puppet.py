"""
This module removes puppet certs from the puppet master prior to
reinstalling a machine if the puppet master is running on the Cobbler
server.

Based on:
https://www.ithiriel.com/content/2010/03/29/writing-install-triggers-cobbler
"""
import logging
import re
from typing import TYPE_CHECKING, List

from cobbler import utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


logger = logging.getLogger()


def register() -> str:
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type.

    :return: Always `/var/lib/cobbler/triggers/install/pre/*`
    """

    return "/var/lib/cobbler/triggers/install/pre/*"


def run(api: "CobblerAPI", args: List[str]) -> int:
    """
    This method runs the trigger, meaning in this case that old puppet certs are automatically removed via puppetca.

    The list of args should have two elements:
        - 0: system or profile
        - 1: the name of the system or profile

    :param api: The api to resolve external information with.
    :param args: Already described above.
    :return: "0" on success. If unsuccessful this raises an exception.
    """
    objtype = args[0]
    name = args[1]

    if objtype != "system":
        return 0

    settings = api.settings()

    if not settings.puppet_auto_setup:
        return 0

    if not settings.remove_old_puppet_certs_automatically:
        return 0

    system = api.find_system(name)
    if system is None or isinstance(system, list):
        raise ValueError("Ambigous search match detected!")
    blended_system = utils.blender(api, False, system)
    hostname = blended_system["hostname"]
    if not re.match(r"[\w-]+\..+", hostname):
        search_domains = blended_system["name_servers_search"]
        if search_domains:
            hostname += "." + search_domains[0]
    if not re.match(r"[\w-]+\..+", hostname):
        default_search_domains = blended_system["default_name_servers_search"]
        if default_search_domains:
            hostname += "." + default_search_domains[0]
    puppetca_path = settings.puppetca_path
    cmd = [puppetca_path, "cert", "clean", hostname]

    return_code = 0

    try:
        return_code = utils.subprocess_call(cmd, shell=False)
    except Exception:
        logger.warning("failed to execute %s", puppetca_path)

    if return_code != 0:
        logger.warning("puppet cert removal for %s failed", name)

    return 0
