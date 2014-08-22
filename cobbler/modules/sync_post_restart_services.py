import distutils.sysconfig
import sys
import cobbler.module_loader as module_loader
import cobbler.utils as utils

plib = distutils.sysconfig.get_python_lib()
mod_path = "%s/cobbler" % plib
sys.path.insert(0, mod_path)


def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/sync/post/*"


def run(api, args, logger):

    settings = api.settings()

    manage_dhcp = str(settings.manage_dhcp).lower()
    manage_dns = str(settings.manage_dns).lower()
    restart_dhcp = str(settings.restart_dhcp).lower()
    restart_dns = str(settings.restart_dns).lower()

    which_dhcp_module = module_loader.get_module_name("dhcp", "module").strip()
    which_dns_module = module_loader.get_module_name("dns", "module").strip()

    # special handling as we don't want to restart it twice
    has_restarted_dnsmasq = False

    rc = 0
    if manage_dhcp != "0":
        if which_dhcp_module == "manage_isc":
            if restart_dhcp != "0":
                rc = utils.subprocess_call(logger, "dhcpd -t -q", shell=True)
                if rc != 0:
                    logger.error("dhcpd -t failed")
                    return 1
                dhcp_service_name = utils.dhcp_service_name(api)
                dhcp_restart_command = "service %s restart" % dhcp_service_name
                rc = utils.subprocess_call(logger, dhcp_restart_command, shell=True)
        elif which_dhcp_module == "manage_dnsmasq":
            if restart_dhcp != "0":
                rc = utils.subprocess_call(logger, "service dnsmasq restart")
                has_restarted_dnsmasq = True
        else:
            logger.error("unknown DHCP engine: %s" % which_dhcp_module)
            rc = 411

    if manage_dns != "0" and restart_dns != "0":
        if which_dns_module == "manage_bind":
            named_service_name = utils.named_service_name(api)
            dns_restart_command = "service %s restart" % named_service_name
            rc = utils.subprocess_call(logger, dns_restart_command, shell=True)
        elif which_dns_module == "manage_dnsmasq" and not has_restarted_dnsmasq:
            rc = utils.subprocess_call(logger, "service dnsmasq restart", shell=True)
        elif which_dns_module == "manage_dnsmasq" and has_restarted_dnsmasq:
            rc = 0
        elif which_dns_module == "manage_ndjbdns":
            # N-DJBDNS picks up configuration changes automatically and does not need to be restarted.
            pass
        else:
            logger.error("unknown DNS engine: %s" % which_dns_module)
            rc = 412

    return rc
