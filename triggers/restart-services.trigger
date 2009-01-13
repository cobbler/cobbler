#!/usr/bin/python

import cobbler.api as capi
import os
import sys

bootapi = capi.BootAPI()
settings = bootapi.settings()
manage_dhcp = str(settings.manage_dhcp).lower()
manage_dns = str(settings.manage_dns).lower()
manage_xinetd = str(settings.manage_xinetd).lower()
restart_dhcp = str(settings.restart_dhcp).lower()
restart_dns = str(settings.restart_dns).lower()
restart_xinetd = str(settings.restart_xinetd).lower()
omapi_enabled = settings.omapi_enabled
omapi_port = settings.omapi_port

# load up our DHCP and DNS modules
bootapi.get_sync(verbose=False)
# bootapi.dhcp and bootapi.dns are now module references

# special handling as we don't want to restart it twice
has_restarted_dnsmasq = False

rc = 0
if manage_dhcp != "0":
    if bootapi.dhcp.what() == "isc":
        if not omapi_enabled and restart_dhcp:
            rc = os.system("/usr/sbin/dhcpd -t")
            if rc != 0:
               print "/usr/sbin/dhcpd -t failed"
               sys.exit(rc)
            rc = os.system("/sbin/service dhcpd restart")
    elif bootapi.dhcp.what() == "dnsmasq":
        if restart_dhcp:
            rc = os.system("/sbin/service dnsmasq restart")
            has_restarted_dnsmasq = True
    else:
        print "- error: unknown DHCP engine: %s" % bootapi.dhcp.what()
        rc = 411

if manage_dns != "0" and restart_dns != "0":
    if bootapi.dns.what() == "bind":
        rc = os.system("/sbin/service named restart")
    elif bootapi.dns.what() == "dnsmasq" and not has_restarted_dnsmasq:
        rc = os.ssytem("/sbin/service dnsmasq restart")

if manage_xinetd != "0" and restart_xinetd != "0":
    rc = os.system("/sbin/service xinetd restart")

sys.exit(rc)

