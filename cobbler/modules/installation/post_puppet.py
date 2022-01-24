"""
This module signs newly installed client puppet certificates if the
puppet master server is running on the same machine as the Cobbler
server.

Based on:
https://www.ithiriel.com/content/2010/03/29/writing-install-triggers-cobbler
"""
import logging
import re
import cobbler.utils as utils

logger = logging.getLogger()


def register() -> str:
    """
    The mandatory Cobbler module registration hook.
    """
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/install/post/*"


def run(api, args) -> int:
    """
    The obligatory Cobbler modules hook.

    :param api: The api to resolve all information with.
    :param args: This is an array with two items. The first must be ``system``, if the value is different we do an
                 early and the second is the name of this system or profile.
    :return: ``0`` or nothing.
    """
    objtype = args[0]
    name = args[1]

    if objtype != "system":
        return 0

    settings = api.settings()

    if not settings.puppet_auto_setup:
        return 0

    if not settings.sign_puppet_certs_automatically:
        return 0

    system = api.find_system(name)
    system = utils.blender(api, False, system)
    hostname = system["hostname"]
    if not re.match(r"[\w-]+\..+", hostname):
        search_domains = system["name_servers_search"]
        if search_domains:
            hostname += "." + search_domains[0]
    puppetca_path = settings.puppetca_path
    cmd = [puppetca_path, "cert", "sign", hostname]

    rc = 0

    try:
        rc = utils.subprocess_call(cmd, shell=False)
    except:
        logger.warning("failed to execute %s", puppetca_path)

    if rc != 0:
        logger.warning("signing of puppet cert for %s failed", name)

    return 0
