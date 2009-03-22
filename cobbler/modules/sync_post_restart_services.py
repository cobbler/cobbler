import distutils.sysconfig
import sys
import os
from utils import _
import traceback
import cexceptions
import os
import sys
import xmlrpclib
import cobbler.module_loader as module_loader

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler" % plib
sys.path.insert(0, mod_path)

def register():
    # this pure python trigger acts as if it were a legacy shell-trigger, but is much faster.
    # the return of this method indicates the trigger type
    return "/var/lib/cobbler/triggers/sync/post/*"

def run(api,args):

    settings = api.settings()

    manage_dhcp        = str(settings.manage_dhcp).lower()
    manage_dns         = str(settings.manage_dns).lower()
    manage_ris_linuxd  = str(settings.manage_ris_linuxd).lower()
    manage_xinetd      = str(settings.manage_xinetd).lower()
    restart_dhcp       = str(settings.restart_dhcp).lower()
    restart_dns        = str(settings.restart_dns).lower()
    restart_ris_linuxd = str(settings.manage_ris_linuxd).lower()
    restart_xinetd     = str(settings.restart_xinetd).lower()
    omapi_enabled      = str(settings.omapi_enabled).lower()
    omapi_port         = str(settings.omapi_port).lower()

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
                   return 1
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
            rc = os.system("/sbin/service dnsmasq restart")
        else:
            print "- error: unknown DNS engine: %s" % which_dns_module
            rc = 412

    if manage_xinetd != "0" and restart_xinetd != "0":
        rc = os.system("/sbin/service xinetd restart")
        if rc != 0:
            print "- error: service xinetd restart failed"

    if manage_ris_linuxd != "0" and restart_ris_linuxd != "0":
        rc = os.system("/sbin/service ris-linuxd restart")
        if rc != 0:
            print "- error: service ris-linuxd restart failed"

    return rc

