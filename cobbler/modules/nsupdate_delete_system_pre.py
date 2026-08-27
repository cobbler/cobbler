"""
Replace (or remove) records in DNS zone for systems created (or removed) by Cobbler
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Adrian Brzezinski <adrbxx@gmail.com>
# SPDX-FileCopyrightText: 2024 Joakim Fallsjo <Joakim.Fallsjo@derivco.se>

# DNS toolkit for Python
#   - python-dnspython (Debian)
#   - python-dns (RH/CentOS)

import ipaddress
import logging
import time
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

import dns.message
import dns.name
import dns.query
import dns.rdataclass
import dns.resolver
import dns.tsigkeyring
import dns.update

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


logger = logging.getLogger("nsupdate")


def register() -> str:
    """
    This method is the obligatory Cobbler registration hook.

    :return: The trigger name or an empty string.
    """
    if __name__ == "cobbler.modules.nsupdate_add_system_post":
        return "/var/lib/cobbler/triggers/add/system/post/*"
    if __name__ == "cobbler.modules.nsupdate_delete_system_pre":
        return "/var/lib/cobbler/triggers/delete/system/pre/*"
    return ""


def find_zone_apex(name: str) -> Tuple[Optional[str], str, str]:
    """
    Helper to locate the Zone Apex for a supplied name.

    :param name: The name to break down.
    :return: A tuple of the DNS name of the zone's SOA master nameserver (or ``None`` if it could not be
             determined), the host part and the zone part of the domain name.
    """
    response = dns.query.udp(  # type: ignore
        dns.message.make_query(dns.name.from_text(name + "."), dns.rdatatype.SOA),  # type: ignore
        dns.resolver.Resolver().nameservers[0],  # type: ignore
    )

    zone = response.authority[0].name  # type: ignore
    lhost = ".".join(name.split(".")[0 : len(name.split(".")) - len(zone.labels) + 1])  # type: ignore

    if zone == dns.name.root or zone.to_text(omit_final_dot=True) in (  # type: ignore
        "ip6.arpa",
        "in-addr.arpa",
    ):
        logger.warning(
            "nsupdate: zone apex lookup for '%s' hit an unsupported zone '%s', skipping",
            name,
            zone,  # type: ignore
        )
        return None, lhost, zone  # type: ignore

    logger.debug(
        "nsupdate: resolving master nameserver for lhost '%s' in zone '%s'", lhost, zone
    )

    try:
        rrset = response.find_rrset(response.authority, zone, dns.rdataclass.IN, dns.rdatatype.SOA)  # type: ignore
    except KeyError:
        logger.warning("nsupdate: no SOA rrset found for zone '%s', skipping", zone)
        return None, lhost, zone  # type: ignore

    logger.debug(
        "nsupdate: master nameserver for zone '%s' is %s", zone, rrset[0].mname  # type: ignore
    )
    return dns.name.Name.to_text(rrset[0].mname), lhost, zone  # type: ignore


def run(api: "CobblerAPI", args: List[Any]) -> int:
    """
    This method executes the trigger, meaning in this case that it updates the dns configuration.

    :param api: The api to read metadata from.
    :param args: Metadata to log.
    :return: "0" on success or a skipped task. Individual records that could not be updated (unknown nameserver,
             refused key, ...) are logged and skipped rather than raising.
    """
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

    logger.debug("nsupdate: starting for %s", args)

    nsupdate_tsig = settings.nsupdate_tsig
    nsupdate_mgm_txt = settings.nsupdate_mgm_txt

    # get information about this system
    system = api.find_system(args[0])

    if system is None or isinstance(system, list):
        raise ValueError("Search result was ambiguous!")

    # process all interfaces and perform dynamic update for those with --dns-name
    # Use list() to avoid "dictionary changed size during iteration" when is_management_supported() accesses interfaces
    for name, interface in list(system.interfaces.items()):
        host = interface.dns.name
        cnames = interface.dns.common_names
        host_ip = interface.ipv4.address
        host_ipv6 = interface.ipv6.address
        host_ipv6_sec_addrs = interface.ipv6.secondaries

        if not system.is_management_supported(cidr_ok=False):
            continue
        if not host or ((not host_ip) and (not host_ipv6)):
            # gotta have some dns name and ip or else!
            continue
        if host.find(".") == -1:
            continue

        logger.debug(
            "nsupdate: %s processing interface %s: %s", action, name, interface
        )
        logger.debug("nsupdate: trying host %s", host)
        soa_mname, lhost, zone = find_zone_apex(host)

        # This is to be used for the CNAME handling below
        if len(lhost.split(".", 1)[1:]) != 0:
            rhost = "." + ".".join(lhost.split(".", 1)[1:])
        else:
            rhost = ""

        if soa_mname is not None:
            logger.info(
                "nsupdate: %s dns record for %s.%s [%s]", action, lhost, zone, host_ip
            )

            # Check to see if we have a TSIG key for the NS
            try:
                keyring_algo = nsupdate_tsig[soa_mname]["algorithm"]
                keyring = dns.tsigkeyring.from_text(  # type: ignore
                    {
                        str(nsupdate_tsig[soa_mname]["key"][0]): str(
                            nsupdate_tsig[soa_mname]["key"][1]
                        )
                    }
                )
            except (IndexError, KeyError) as error:
                logger.warning(
                    "nsupdate: no TSIG key configured for nameserver %s, skipping (%s)",
                    soa_mname,
                    error,
                )
            else:
                # Setup the Query packet
                update = dns.update.Update(zone, keyring=keyring, keyalgorithm=keyring_algo)  # type: ignore

                if action == "replace":
                    if host_ip:
                        update.replace(lhost, 3600, dns.rdatatype.A, host_ip)  # type: ignore
                    if host_ipv6 or host_ipv6_sec_addrs:
                        ip6s = [host_ipv6] if host_ipv6 else []
                        for each_ipv6 in ip6s + host_ipv6_sec_addrs:
                            update.replace(lhost, 3600, dns.rdatatype.AAAA, each_ipv6)  # type: ignore
                    if nsupdate_mgm_txt:
                        update.replace(  # type: ignore
                            lhost,
                            3600,
                            dns.rdatatype.TXT,  # type: ignore
                            f'"cobbler (date: {time.strftime("%c")})"',
                        )
                    for cname in cnames:
                        update.replace(cname.split(".")[0] + rhost, 3600, dns.rdatatype.CNAME, lhost)  # type: ignore
                else:
                    update.delete(lhost, dns.rdatatype.A)  # type: ignore
                    update.delete(lhost, dns.rdatatype.AAAA)  # type: ignore
                    if nsupdate_mgm_txt:
                        update.delete(lhost, dns.rdatatype.TXT)  # type: ignore
                    for cname in cnames:
                        update.delete(cname.split(".")[0] + rhost, dns.rdatatype.CNAME)  # type: ignore

                # Find the IP of the NS
                try:
                    ns_ips = dns.resolver.query(soa_mname, "A")  # type: ignore
                    for answer in ns_ips:  # type: ignore
                        soa_mname_ip = answer.to_text()  # type: ignore
                except Exception as error:  # pylint: disable=broad-except
                    logger.warning(
                        "nsupdate: no IP found for nameserver %s: %s", soa_mname, error
                    )
                else:
                    # Send the update packet
                    try:
                        response = dns.query.tcp(update, soa_mname_ip)  # type: ignore
                        rcode_txt = str(dns.rcode.to_text(response.rcode()))  # type: ignore
                    except dns.tsig.PeerBadKey:  # type: ignore
                        logger.warning(
                            "nsupdate: update to %s failed, nameserver refused our TSIG key",
                            soa_mname,
                        )
                    else:
                        if response.rcode() != dns.rcode.NOERROR:  # type: ignore
                            logger.warning(
                                "nsupdate: update to %s failed with response code %s",
                                soa_mname,
                                rcode_txt,
                            )
                        else:
                            logger.debug(
                                "nsupdate: update to %s succeeded (%s)",
                                soa_mname,
                                rcode_txt,
                            )
        else:
            logger.warning(
                "nsupdate: could not determine master nameserver for %s, skipping", host
            )
        # Done updating A, AAAA, CNAME and TXT for fwd zone

        rrset: List[str] = []
        if host_ip:
            rrset.append(host_ip)
        if host_ipv6:
            rrset.append(host_ipv6)

        # Now iterate and update all PTR records in relevant zone(s)
        for each_rr in rrset + host_ipv6_sec_addrs:
            reverse = ipaddress.ip_address(each_rr).reverse_pointer
            logger.debug("nsupdate: trying PTR %s", reverse)
            soa_mname, lhost, zone = find_zone_apex(reverse)
            if soa_mname is not None:
                logger.info(
                    "nsupdate: %s dns record for %s.%s [%s]", action, lhost, zone, host
                )

                # Check to see if we have a TSIG key for the NS
                try:
                    keyring_algo = nsupdate_tsig[soa_mname]["algorithm"]
                    keyring = dns.tsigkeyring.from_text(  # type: ignore
                        {
                            str(nsupdate_tsig[soa_mname]["key"][0]): str(
                                nsupdate_tsig[soa_mname]["key"][1]
                            )
                        }
                    )
                except (IndexError, KeyError) as error:
                    logger.warning(
                        "nsupdate: no TSIG key configured for nameserver %s, skipping (%s)",
                        soa_mname,
                        error,
                    )
                else:
                    # Setup the Query packet
                    update = dns.update.Update(zone, keyring=keyring, keyalgorithm=keyring_algo)  # type: ignore

                    if action == "replace":
                        update.replace(lhost, 3600, dns.rdatatype.PTR, host + ".")  # type: ignore
                        if nsupdate_mgm_txt:
                            update.replace(  # type: ignore
                                lhost,
                                3600,
                                dns.rdatatype.TXT,  # type: ignore
                                f'"cobbler (date: {time.strftime("%c")})"',
                            )
                    else:
                        update.delete(lhost, dns.rdatatype.PTR)  # type: ignore
                        if nsupdate_mgm_txt:
                            update.delete(lhost, dns.rdatatype.TXT)  # type: ignore

                    # Find the IP of the NS
                    try:
                        ns_ips = dns.resolver.query(soa_mname, "A")  # type: ignore
                        for answer in ns_ips:  # type: ignore
                            soa_mname_ip = answer.to_text()  # type: ignore
                    except Exception as error:  # pylint: disable=broad-except
                        logger.warning(
                            "nsupdate: no IP found for nameserver %s: %s",
                            soa_mname,
                            error,
                        )
                    else:
                        # Send the update packet
                        try:
                            response = dns.query.tcp(update, soa_mname_ip)  # type: ignore
                            rcode_txt = str(dns.rcode.to_text(response.rcode()))  # type: ignore
                        except dns.tsig.PeerBadKey:  # type: ignore
                            logger.warning(
                                "nsupdate: update to %s failed, nameserver refused our TSIG key",
                                soa_mname,
                            )
                        else:
                            if response.rcode() != dns.rcode.NOERROR:  # type: ignore
                                logger.warning(
                                    "nsupdate: update to %s failed with response code %s",
                                    soa_mname,
                                    rcode_txt,
                                )
                            else:
                                logger.debug(
                                    "nsupdate: update to %s succeeded (%s)",
                                    soa_mname,
                                    rcode_txt,
                                )
            else:
                logger.warning(
                    "nsupdate: could not determine master nameserver for %s, skipping",
                    reverse,
                )
        # end for each_rr
    # end for name, interface

    logger.debug("nsupdate: finished processing %s", args)
    return 0
