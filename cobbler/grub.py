import logging
import netaddr


def parse_grub_remote_file(file_location):
    prot = ""
    if file_location.startswith("ftp://"):
        logging.warning("ftp protocol not supported by grub. Only http and tftp [%s]" % file_location)
        return None
    elif file_location.startswith("http://"):
        (server, delim, path) = file_location[7:].partition('/')
        prot = "http"
    elif file_location.startswith("tftp://"):
        (server, delim, path) = file_location[7:].partition('/')
        prot = "tftp"
    if not prot:
        return None

    if not netaddr.valid_ipv4(server):
        if not netaddr.valid_ipv6(server):
            raise ValueError("Invalid remote file format %s\n%s is not a valid IP address" % (file_location, server))

    res = '(%s,%s)/%s' % (prot, server, path)
    logging.info("Found remote grub file. Converted [%s] to [%s]", file_location, res)
    return res
