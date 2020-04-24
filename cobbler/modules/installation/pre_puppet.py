"""
This module removes puppet certs from the puppet master prior to
reinstalling a machine if the puppet master is running on the Cobbler
server.

Based on:
http://www.ithiriel.com/content/2010/03/29/writing-install-triggers-cobbler
"""
from builtins import str
import re

import cobbler.utils as utils


def register():
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type.

    :return: Always: "/var/lib/cobbler/triggers/install/pre/\*"
    :rtype: str
    """

    return "/var/lib/cobbler/triggers/install/pre/*"


def run(api, args, logger):
    """
    This method runs the trigger, meaning in this case that old puppet certs are automatically removed via puppetca.

    The list of args should have two elements:
        - 0: system or profile
        - 1: the name of the system or profile

    :param api: The api to resolve external information with.
    :param args: Already described above.
    :param logger: The logger to audit the action with.
    :return: "0" on success. If unsuccessful this raises an exception.
    """
    objtype = args[0]
    name = args[1]

    if objtype != "system":
        return 0

    settings = api.settings()

    if not str(settings.puppet_auto_setup).lower() in ["1", "yes", "y", "true"]:
        return 0

    if not str(settings.remove_old_puppet_certs_automatically).lower() in ["1", "yes", "y", "true"]:
        return 0

    system = api.find_system(name)
    system = utils.blender(api, False, system)
    hostname = system["hostname"]
    if not re.match(r'[\w-]+\..+', hostname):
        search_domains = system['name_servers_search']
        if search_domains:
            hostname += '.' + search_domains[0]
    if not re.match(r'[\w-]+\..+', hostname):
        default_search_domains = system['default_name_servers_search']
        if default_search_domains:
            hostname += '.' + default_search_domains[0]
    puppetca_path = settings.puppetca_path
    cmd = [puppetca_path, 'cert', 'clean', hostname]

    rc = 0

    try:
        rc = utils.subprocess_call(logger, cmd, shell=False)
    except:
        if logger is not None:
            logger.warning("failed to execute %s" % puppetca_path)

    if rc != 0:
        if logger is not None:
            logger.warning("puppet cert removal for %s failed" % name)

    return 0
