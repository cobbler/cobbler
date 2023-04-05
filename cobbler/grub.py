"""
Module that contains GRUB related helper functionality.
"""

import logging
from typing import Optional

import netaddr  # type: ignore


def parse_grub_remote_file(file_location: str) -> Optional[str]:
    """
    Parses a URI which grub would try to load from the network.

    :param file_location: The location which grub would try to load from the network.
    :return: In case the URL could be parsed it is returned in the converted format. Otherwise None is returned.
    :raises TypeError: In case file_location is not of type ``str``.
    :raises ValueError: In case the file location does not contain a valid IPv4 or IPv6 address
    """
    if not isinstance(file_location, str):  # type: ignore
        raise TypeError('"file_location" should be of type "str"')
    if file_location.startswith("ftp://"):
        logging.warning(
            "FTP protocol not supported by GRUB. Only HTTP and TFTP [%s]", file_location
        )
        return None
    if file_location.startswith("http://"):
        (server, _, path) = file_location[7:].partition("/")
        prot = "http"
    elif file_location.startswith("tftp://"):
        (server, _, path) = file_location[7:].partition("/")
        prot = "tftp"
    else:
        logging.warning(
            "Unknown or unsupported protocol set for GRUB [%s]", file_location
        )
        return None

    if not (server.startswith("@@") and server.endswith("server@@")):
        if not (netaddr.valid_ipv4(server) or netaddr.valid_ipv6(server)):
            raise ValueError(
                f"Invalid remote file format {file_location}\n{server} is not a valid IP address"
            )

    res = f"({prot},{server})/{path}"
    # logging.info("Found remote grub file. Converted [%s] to [%s]", file_location, res)
    return res
