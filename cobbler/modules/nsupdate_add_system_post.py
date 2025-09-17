"""
Replace (or remove) records in DNS zone for systems created (or removed) by Cobbler
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Adrian Brzezinski <adrbxx@gmail.com>

# DNS toolkit for Python
#   - python-dnspython (Debian)
#   - python-dns (RH/CentOS)

import time
from typing import IO, TYPE_CHECKING, Any, List, Optional

import dns.query
import dns.resolver
import dns.tsigkeyring
import dns.update

from cobbler.cexceptions import CX

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


LOGF: Optional[IO[str]] = None


def nslog(msg: str) -> None:
    """
    Log a message to the logger.

    :param msg: The message to log.
    """
    if LOGF is not None:
        LOGF.write(msg)


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


def run(api: "CobblerAPI", args: List[Any]):
    """
    This method executes the trigger, meaning in this case that it updates the dns configuration.

    :param api: The api to read metadata from.
    :param args: Metadata to log.
    :return: "0" on success or a skipped task. If the task failed or problems occurred then an exception is raised.
    """
    # Module level log file descriptor
    global LOGF  # pylint: disable=global-statement

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
    if str(settings.nsupdate_log) is not None:  # type: ignore[reportUnnecessaryComparison]
        LOGF = open(str(settings.nsupdate_log), "a", encoding="UTF-8")  # type: ignore
        nslog(f">> starting {__name__} {args}\n")

    if str(settings.nsupdate_tsig_key) is not None:  # type: ignore[reportUnnecessaryComparison]
        keyring = dns.tsigkeyring.from_text(
            {str(settings.nsupdate_tsig_key[0]): str(settings.nsupdate_tsig_key[1])}
        )
    else:
        keyring = None

    if str(settings.nsupdate_tsig_algorithm) is not None:  # type: ignore[reportUnnecessaryComparison]
        keyring_algo = str(settings.nsupdate_tsig_algorithm)
    else:
        keyring_algo = "HMAC-MD5.SIG-ALG.REG.INT"
    # nslog( " algo %s, key %s : %s \n" % (keyring_algo,str(settings.nsupdate_tsig_key[0]),
    #                                      str(settings.nsupdate_tsig_key[1])) )

    # get information about this system
    system = api.find_system(args[0])

    if system is None or isinstance(system, list):
        raise ValueError("Search result was ambiguous!")

    # process all interfaces and perform dynamic update for those with --dns-name
    for name, interface in system.interfaces.items():
        host = interface.dns.name
        host_ip = interface.ipv4.address

        if not system.is_management_supported(cidr_ok=False):
            continue
        if not host:
            continue
        if host.find(".") == -1:
            continue

        domain = ".".join(host.split(".")[1:])  # get domain from host name
        host = host.split(".")[0]  # strip domain

        nslog(f"processing interface {name} : {interface}\n")
        nslog(f"lookup for '{domain}' domain master nameserver... ")

        # get master nameserver ip address
        answers = dns.resolver.query(domain + ".", dns.rdatatype.SOA)  # type: ignore
        soa_mname = answers[0].mname  # type: ignore
        soa_mname_ip = None

        for rrset in answers.response.additional:  # type: ignore
            if rrset.name == soa_mname:  # type: ignore
                soa_mname_ip = str(rrset.items[0].address)  # type: ignore

        if soa_mname_ip is None:
            ip_address = dns.resolver.query(soa_mname, "A")  # type: ignore
            for answer in ip_address:  # type: ignore
                soa_mname_ip = answer.to_text()  # type: ignore

        nslog(f"{soa_mname} [{soa_mname_ip}]\n")
        nslog(f"{action} dns record for {host}.{domain} [{host_ip}] .. ")

        # try to update zone with new record
        update = dns.update.Update(
            domain + ".", keyring=keyring, keyalgorithm=keyring_algo  # type: ignore
        )

        if action == "replace":
            update.replace(host, 3600, dns.rdatatype.A, host_ip)  # type: ignore
            update.replace(  # type: ignore
                host,
                3600,
                dns.rdatatype.TXT,  # type: ignore
                f'"cobbler (date: {time.strftime("%c")})"',
            )
        else:
            update.delete(host, dns.rdatatype.A, host_ip)  # type: ignore
            update.delete(host, dns.rdatatype.TXT)  # type: ignore

        try:
            response = dns.query.tcp(update, soa_mname_ip)  # type: ignore
            rcode_txt = dns.rcode.to_text(response.rcode())  # type: ignore
        except dns.tsig.PeerBadKey as error:  # type: ignore
            nslog("failed (refused key)\n>> done\n")
            if LOGF is not None:
                LOGF.close()

            raise CX(
                f"nsupdate failed, server '{soa_mname}' refusing our key"
            ) from error

        nslog(f"response code: {rcode_txt}\n")

        # notice user about update failure
        if response.rcode() != dns.rcode.NOERROR:  # type: ignore
            nslog(">> done\n")
            if LOGF is not None:
                LOGF.close()

            raise CX(
                f"nsupdate failed (response: {rcode_txt}, name: {host}.{domain}, ip {host_ip}, name server {soa_mname})"
            )

    nslog(">> done\n")
    if LOGF is not None:
        LOGF.close()
    return 0
