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

import dns.query
import dns.tsigkeyring
import dns.update
import dns.resolver
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

    if str(settings.nsupdate_tsig_key) is not None:
        keyring = dns.tsigkeyring.from_text({
            str(settings.nsupdate_tsig_key[0]): str(settings.nsupdate_tsig_key[1])
        })
    else:
        keyring = None

    if str(settings.nsupdate_tsig_algorithm) is not None:
        keyring_algo = str(settings.nsupdate_tsig_algorithm)
    else:
        keyring_algo = "HMAC-MD5.SIG-ALG.REG.INT"
    # nslog( " algo %s, key %s : %s \n" % (keyring_algo,str(settings.nsupdate_tsig_key[0]),
    #                                      str(settings.nsupdate_tsig_key[1])) )

    # get information about this system
    system = api.find_system(args[0])

    # process all interfaces and perform dynamic update for those with --dns-name
    for (name, interface) in system.interfaces.items():
        host = interface.dns_name
        host_ip = interface.ip_address

        if not system.is_management_supported(cidr_ok=False):
            continue
        if not host:
            continue
        if host.find(".") == -1:
            continue

        domain = ".".join(host.split(".")[1:])    # get domain from host name
        host = host.split(".")[0]                   # strip domain

        nslog("processing interface %s : %s\n" % (name, interface))
        nslog("lookup for '%s' domain master nameserver... " % domain)

        # get master nameserver ip address
        answers = dns.resolver.query(domain + '.', dns.rdatatype.SOA)
        soa_mname = answers[0].mname
        soa_mname_ip = None

        for rrset in answers.response.additional:
            if rrset.name == soa_mname:
                soa_mname_ip = str(rrset.items[0].address)

        if soa_mname_ip is None:
            ip = dns.resolver.query(soa_mname, "A")
            for answer in ip:
                soa_mname_ip = answer.to_text()

        nslog("%s [%s]\n" % (soa_mname, soa_mname_ip))
        nslog("%s dns record for %s.%s [%s] .. " % (action, host, domain, host_ip))

        # try to update zone with new record
        update = dns.update.Update(domain + '.', keyring=keyring, keyalgorithm=keyring_algo)

        if action == "replace":
            update.replace(host, 3600, dns.rdatatype.A, host_ip)
            update.replace(host, 3600, dns.rdatatype.TXT, '"cobbler (date: %s)"' % (time.strftime("%c")))
        else:
            update.delete(host, dns.rdatatype.A, host_ip)
            update.delete(host, dns.rdatatype.TXT)

        try:
            response = dns.query.tcp(update, soa_mname_ip)
            rcode_txt = dns.rcode.to_text(response.rcode())
        except dns.tsig.PeerBadKey:
            nslog("failed (refused key)\n>> done\n")
            logf.close()

            raise CX("nsupdate failed, server '%s' refusing our key" % soa_mname)

        nslog('response code: %s\n' % rcode_txt)

        # notice user about update failure
        if response.rcode() != dns.rcode.NOERROR:
            nslog('>> done\n')
            logf.close()

            raise CX("nsupdate failed (response: %s, name: %s.%s, ip %s, name server %s)"
                     % (rcode_txt, host, domain, host_ip, soa_mname))

    nslog('>> done\n')
    logf.close()
    return 0
