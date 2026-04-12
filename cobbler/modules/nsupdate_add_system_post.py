# -*- coding: utf-8 -*-
#
# Adrian Brzezinski <adrbxx@gmail.com>
# License: GPLv2+
#
# Replace (or remove) records in DNS zone for systems created (or removed) by Cobbler
#

# DNS toolkit for Python
#   - python-dnspython (Debian)
#   - python-dns (RH/CentOS)

import dns.message
import dns.name
import dns.query
import dns.rdataclass
import dns.rdatatype
import dns.tsigkeyring
import dns.update
import dns.resolver
import ipaddress
import time

from cobbler.cexceptions import CX

logf = None


def nslog(msg):
    """
    Log a message to the logger.

    :param msg: The message to log.
    """
    if logf is not None:
        logf.write(msg)


def register() -> str:
    """
    This method is the obligatory Cobbler registration hook.

    :return: The trigger name or an empty string.
    """
    if __name__ == "cobbler.modules.nsupdate_add_system_post":
        return "/var/lib/cobbler/triggers/add/system/post/*"
    elif __name__ == "cobbler.modules.nsupdate_delete_system_pre":
        return "/var/lib/cobbler/triggers/delete/system/pre/*"
    else:
        return ''

def findZoneApex(name):
    """
    This function will help locate the Zone Apex for a supplied name.

    :param name: The name to break down.
    :return: DNS name of the zone master nameserver, host and zone components of the domain name
    """

    r = dns.query.udp(dns.message.make_query(dns.name.from_text(name + '.'), dns.rdatatype.SOA),
                      dns.resolver.Resolver().nameservers[0])

    # nslog("===\n: %s\n===\n" % r)

    zone = r.authority[0].name
    lhost = ".".join(name.split(".")[0:len(name.split('.'))-len(zone.labels)+1])

    if zone == '' or zone == 'ip6.arpa' or zone == 'in-addr.arpa':
        nslog("lookup for '%s' zone apex failed!\n" % name)
        return None, lhost, zone

    nslog("lookup for lhost '%s'\n       and zone '%s'\n       master nameserver..." % (lhost, zone))

    try:
        rrset = r.find_rrset(r.authority, zone, dns.rdataclass.IN, dns.rdatatype.SOA)
    except:
        nslog(" failed1\n")
        return None, lhost, zone

    nslog(" %s\n" % rrset[0].mname)
    return dns.name.Name.to_text(rrset[0].mname), lhost, zone

def run(api, args):
    """
    This method executes the trigger, meaning in this case that it updates the dns configuration.

    :param api: The api to read metadata from.
    :param args: Metadata to log.
    :return: "0" on success or a skipped task. If the task failed or problems occurred then an exception is raised.
    """
    global logf

    action = None
    if __name__ == "cobbler.modules.nsupdate_add_system_post":
        action = "replace"
    elif __name__ == "cobbler.modules.nsupdate_delete_system_pre":
        action = "delete"
    else:
        return 0

    settings = api.settings()

    if not settings.nsupdate_enabled:
        return 0

    # read our settings
    if str(settings.nsupdate_log) is not None:
        logf = open(str(settings.nsupdate_log), "a+")
        nslog(">> starting %s %s\n" % (__name__, args))

    nsupdate_tsig = settings.nsupdate_tsig
    nsupdate_mgm_txt = settings.nsupdate_mgm_txt

    # get information about this system
    system = api.find_system(args[0])

    # process all interfaces and perform dynamic update for those with --dns-name
    for (name, interface) in system.interfaces.items():
        host = interface.dns_name
        cnames = interface.cnames
        host_ip = interface.ip_address
        host_ipv6 = interface.ipv6_address
        host_ipv6_sec_addrs = interface.ipv6_secondaries

        if not system.is_management_supported(cidr_ok=False):
            continue
        if not host or ((not host_ip) and (not host_ipv6)):
            # gotta have some dns_name and ip or else!
            continue
        if host.find(".") == -1:
            continue

        nslog("%s processing interface %s: %s\n" % (action.capitalize(), name, interface))
        nslog("Trying HOST %s\n" % host)
        soa_mname, lhost, zone = findZoneApex(host)

        # This is to be used for the CNAME handling below
        if len(lhost.split('.', 1)[1:]) != 0:
            rhost = '.' + '.'.join(lhost.split('.', 1)[1:])
        else:
            rhost = ''

        if soa_mname != None:
            nslog("%s dns record for %s.%s [%s] .. " % (action.capitalize(), lhost, zone, host_ip))

            # Check to see if we have a TSIG key for the NS
            try:
                keyring_algo = nsupdate_tsig[soa_mname]['algorithm']
                keyring = dns.tsigkeyring.from_text({str(settings.nsupdate_tsig[soa_mname]['key'][0]):
                                                     str(settings.nsupdate_tsig[soa_mname]['key'][1])})
            except (IndexError, KeyError) as e:
                nslog("TSIG not found (%s)\n" % e)
            else:
                # Setup the Query packet
                update = dns.update.Update(zone, keyring=keyring, keyalgorithm=keyring_algo)

                if action == "replace":
                    if host_ip:
                        update.replace(lhost, 3600, dns.rdatatype.A, host_ip)
                    if host_ipv6 or host_ipv6_sec_addrs:
                        ip6s = []
                        if host_ipv6:
                            ip6s.append(host_ipv6)
                        for each_ipv6 in ip6s + host_ipv6_sec_addrs:
                            update.replace(lhost, 3600, dns.rdatatype.AAAA, each_ipv6)
                    if nsupdate_mgm_txt == True:
                        update.replace(lhost, 3600, dns.rdatatype.TXT, '"cobbler (date: %s)"' % (time.strftime("%c")))
                    for cname in cnames:
                        update.replace(cname.split('.')[0] + rhost, 3600, dns.rdatatype.CNAME, lhost)
                else:
                    update.delete(lhost, dns.rdatatype.A)
                    update.delete(lhost, dns.rdatatype.AAAA)
                    if nsupdate_mgm_txt == True:
                        update.delete(lhost, dns.rdatatype.TXT)
                    for cname in cnames:
                        update.delete(cname.split('.')[0] + rhost, dns.rdatatype.CNAME)

                # Find the IP of the NS
                try:
                    ip = dns.resolver.query(soa_mname, "A")
                    for answer in ip:
                        soa_mname_ip = answer.to_text()
                except Exception as e:
                    nslog("No IP found for %s due to %s\n" % (soa_mname, e))
                else:
                    # Send the update packet
                    try:
                        response = dns.query.tcp(update, soa_mname_ip)
                        rcode_txt = dns.rcode.to_text(response.rcode())
                    except dns.tsig.PeerBadKey:
                        nslog("failed (refused key)\n>> done\n")
                    else:
                        nslog('response code: %s\n' % rcode_txt)

                        if response.rcode() != dns.rcode.NOERROR:
                            nslog('>> done\n')
        else:
            nslog('No soa_mname found for %s\n' % host)
        # Done updating A, AAAA, CNAME and TXT for fwd zone

        rrset = []
        if host_ip:
            rrset.append(host_ip)
        if host_ipv6:
            rrset.append(host_ipv6)

        # Now iterate and update all PTR records in relevant zone(s)
        for each_rr in rrset + host_ipv6_sec_addrs:
            reverse = ipaddress.ip_address(each_rr).reverse_pointer
            nslog("Trying PTR %s\n" % reverse)
            soa_mname, lhost, zone = findZoneApex(reverse)
            if soa_mname != None:
                nslog("%s dns record for %s.%s [%s] .. " % (action.capitalize(), lhost, zone, host))

                # Check to see if we have a TSIG key for the NS
                try:
                    keyring_algo = nsupdate_tsig[soa_mname]['algorithm']
                    keyring = dns.tsigkeyring.from_text({str(settings.nsupdate_tsig[soa_mname]['key'][0]):
                                                        str(settings.nsupdate_tsig[soa_mname]['key'][1])})
                except (IndexError, KeyError) as e:
                    nslog("TSIG not found (%s)\n" % e)
                else:
                    # Setup the Query packet
                    update = dns.update.Update(zone, keyring=keyring, keyalgorithm=keyring_algo)

                    if action == "replace":
                        update.replace(lhost, 3600, dns.rdatatype.PTR, host + '.')
                        if nsupdate_mgm_txt == True:
                            update.replace(lhost, 3600, dns.rdatatype.TXT, '"cobbler (date: %s)"' % (time.strftime("%c")))
                    else:
                        update.delete(lhost, dns.rdatatype.PTR)
                        if nsupdate_mgm_txt == True:
                            update.delete(lhost, dns.rdatatype.TXT)

                    # Find the IP of the NS
                    try:
                        ip = dns.resolver.query(soa_mname, "A")
                        for answer in ip:
                            soa_mname_ip = answer.to_text()
                    except Exception as e:
                        nslog("No IP found for %s due to %s\n" % (soa_mname, e))
                    else:
                        # Send the update packet
                        try:
                            response = dns.query.tcp(update, soa_mname_ip)
                            rcode_txt = dns.rcode.to_text(response.rcode())
                        except dns.tsig.PeerBadKey:
                            nslog("failed (refused key)\n>> done\n")
                        else:
                            nslog('response code: %s\n' % rcode_txt)

                            if response.rcode() != dns.rcode.NOERROR:
                                nslog('>> done\n')
            else:
                nslog('No soa_mname found for %s\n' % reverse)
        # end for each_rr
    # end for (name, interface)

    nslog('>> done\n')
    logf.close()
    return 0
