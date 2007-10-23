#!/usr/bin/python

import cobbler.api as capi
import os
import sys

bootapi = capi.BootAPI()
settings = bootapi.settings()
manage_dhcp = str(settings.manage_dhcp).lower()
manage_dhcp_mode = str(settings.manage_dhcp_mode).lower()

rc = 0
if manage_dhcp != "0":
    if manage_dhcp_mode == "isc":
        rc = os.system("/sbin/service dhcpd restart")
    elif manage_dhcp_mode == "dnsmasq":
        rc = os.system("/sbin/service dnsmasq restart")
    else:
        print "- error: unknown DHCP engine: %s" % manage_dhcp_mode
        rc = 411

sys.exit(rc)
