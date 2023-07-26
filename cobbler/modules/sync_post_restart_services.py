"""
Restarts the DHCP and/or DNS after a Cobbler sync to apply changes to the configuration files.
"""

import logging
from typing import TYPE_CHECKING, List

from cobbler import utils
from cobbler.utils import process_management

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI

logger = logging.getLogger()


def register() -> str:
    """
    This pure python trigger acts as if it were a legacy shell-trigger, but is much faster. The return of this method
    indicates the trigger type

    :return: Always ``/var/lib/cobbler/triggers/sync/post/*``
    """

    return "/var/lib/cobbler/triggers/sync/post/*"


def run(api: "CobblerAPI", args: List[str]) -> int:
    """
    Run the trigger via this method, meaning in this case that depending on the settings dns and/or dhcp services are
    restarted.

    :param api: The api to resolve settings.
    :param args: This parameter is not used currently.
    :return: The return code of the service restarts.
    """
    settings = api.settings()

    which_dhcp_module = api.get_module_name_from_file("dhcp", "module")
    which_dns_module = api.get_module_name_from_file("dns", "module")

    # special handling as we don't want to restart it twice
    has_restarted_dnsmasq = False

    ret_code = 0
    if settings.manage_dhcp and settings.restart_dhcp:
        if which_dhcp_module in ("managers.isc", "managers.dnsmasq"):
            dhcp_module = api.get_module_from_file("dhcp", "module")
            ret_code = dhcp_module.get_manager(api).restart_service()
            if which_dhcp_module == "managers.dnsmasq":
                has_restarted_dnsmasq = True
        else:
            logger.error("unknown DHCP engine: %s", which_dhcp_module)
            ret_code = 411

    if settings.manage_dns and settings.restart_dns:
        if which_dns_module == "managers.bind":
            named_service_name = utils.named_service_name()
            ret_code = process_management.service_restart(named_service_name)
        elif which_dns_module == "managers.dnsmasq" and not has_restarted_dnsmasq:
            ret_code = process_management.service_restart("dnsmasq")
        elif which_dns_module == "managers.dnsmasq" and has_restarted_dnsmasq:
            ret_code = 0
        elif which_dns_module == "managers.ndjbdns":
            # N-DJBDNS picks up configuration changes automatically and does not need to be restarted.
            pass
        else:
            logger.error("unknown DNS engine: %s", which_dns_module)
            ret_code = 412

    return ret_code
