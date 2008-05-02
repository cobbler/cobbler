#!/usr/bin/python

import cobbler.api as capi
import os
import sys

bootapi = capi.BootAPI()
settings = bootapi.settings()
manage_dhcp = str(settings.manage_dhcp).lower()
manage_dhcp_mode = str(settings.manage_dhcp_mode).lower()
manage_dns = str(settings.manage_dns).lower()
omapi_enabled = settings.omapi_enabled
omapi_port = settings.omapi_port



# We're just going to restart DHCPD if using ISC and if not using OMAPI at all
rc = 0
if manage_dhcp != "0":
    if manage_dhcp_mode == "isc":
        if not omapi_enabled:
          if not omapi_port:
            rc = os.system("/sbin/service dhcpd restart")
    elif manage_dhcp_mode == "dnsmasq":
        rc = os.system("/sbin/service dnsmasq restart")
    else:
        print "- error: unknown DHCP engine: %s" % manage_dhcp_mode
        rc = 411

if rc != 0: 
    sys.exit(rc)

if manage_dns != "0":
    rc = os.system("/sbin/service named restart")

sys.exit(rc)

