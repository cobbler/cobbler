#!/usr/bin/python

import os
import sys
import xmlrpclib
import cobbler.module_loader as module_loader

server = xmlrpclib.Server("http://127.0.0.1/cobbler_api")
settings = server.get_settings()

manage_dhcp    = str(settings.get("manage_dhcp",0)).lower()
manage_dns     = str(settings.get("manage_dns",0)).lower()
manage_xinetd  = str(settings.get("manage_xinetd",0)).lower()
restart_dhcp   = str(settings.get("restart_dhcp",0)).lower()
restart_dns    = str(settings.get("restart_dns",0)).lower()
restart_xinetd = str(settings.get("restart_xinetd",0)).lower()
omapi_enabled  = str(settings.get("omapi_enabled",0)).lower()
omapi_port     = str(settings.get("omapi_port",0)).lower()

which_dhcp_module = module_loader.get_module_from_file("dhcp","module",just_name=True).strip()
which_dns_module  = module_loader.get_module_from_file("dns","module",just_name=True).strip()

# special handling as we don't want to restart it twice
has_restarted_dnsmasq = False

rc = 0
if manage_dhcp != "0":
    if which_dhcp_module == "manage_isc":
        if not omapi_enabled in [ "1", "true", "yes", "y" ] and restart_dhcp:
            rc = os.system("/usr/sbin/dhcpd -t")
            if rc != 0:
               print "/usr/sbin/dhcpd -t failed"
               sys.exit(rc)
            rc = os.system("/sbin/service dhcpd restart")
    elif which_dhcp_module == "manage_dnsmasq":
        if restart_dhcp:
            rc = os.system("/sbin/service dnsmasq restart")
            has_restarted_dnsmasq = True
    else:
        print "- error: unknown DHCP engine: %s" % which_dhcp_module
        rc = 411

if manage_dns != "0" and restart_dns != "0":
    if which_dns_module == "manage_bind":
        rc = os.system("/sbin/service named restart")
    elif which_dns_module == "manage_dnsmasq" and not has_restarted_dnsmasq:
        rc = os.ssytem("/sbin/service dnsmasq restart")
    else:
        print "- error: unknown DNS engine: %s" % which_dns_module
        rc = 412

if manage_xinetd != "0" and restart_xinetd != "0":
    rc = os.system("/sbin/service xinetd restart")

sys.exit(rc)

