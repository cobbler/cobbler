"""
Cobbler module that is related to validating data for other internal Cobbler modules.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2014-2015. Jorgen Maas <jorgen.maas@gmail.com>

import re
import shlex
from ipaddress import AddressValueError, NetmaskValueError
from typing import TYPE_CHECKING, List, Union
from urllib.parse import urlparse
from uuid import UUID

import netaddr

from cobbler import enums, utils
from cobbler.items.abstract import base_item
from cobbler.utils import input_converters, signatures

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


RE_HOSTNAME = re.compile(
    r"^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])"
    r"(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$"
)
RE_URL_GRUB = re.compile(r"^\((?P<protocol>http|tftp),(?P<server>.*)\)/(?P<path>.*)$")
RE_URL = re.compile(
    r"^[a-zA-Z\d-]{,63}(\.[a-zA-Z\d-]{,63})*$"
)  # https://stackoverflow.com/a/2894918
RE_SCRIPT_NAME = re.compile(r"[a-zA-Z0-9_\-.]+")

# blacklist invalid values to the repo statement in autoinsts
AUTOINSTALL_REPO_BLACKLIST = ["enabled", "gpgcheck", "gpgkey"]


# FIXME: Allow the <<inherit>> magic string to be parsed correctly.


def hostname(dnsname: str) -> str:
    """
    Validate the DNS name.

    :param dnsname: Hostname or FQDN
    :returns: Hostname or FQDN
    :raises TypeError: If the Hostname/FQDN is not a string or in an invalid format.
    """
    if not isinstance(dnsname, str):  # type: ignore
        raise TypeError("Invalid input, dnsname must be a string")
    dnsname = dnsname.strip()

    if dnsname == "":
        # hostname is not required
        return dnsname

    if not RE_HOSTNAME.match(dnsname):
        raise ValueError(f"Invalid hostname format ({dnsname})")

    return dnsname


def mac_address(mac: str, for_item: bool = True) -> str:
    """
    Validate as an Ethernet MAC address.

    :param mac: MAC address
    :param for_item: If the check should be performed for an item or not.
    :returns: MAC address
    :raises ValueError: Raised in case ``mac`` has an invalid format.
    :raises TypeError: Raised in case ``mac`` is not a string.
    """
    if not isinstance(mac, str):  # type: ignore
        raise TypeError("Invalid input, mac must be a string")
    mac = mac.lower().strip()

    if for_item is True:
        # this value has special meaning for items
        if mac == "random":
            return mac

        # copying system collection will set mac to ""
        # netaddr will fail to validate this mac and throws an exception
        if mac == "":
            return mac

    if not netaddr.valid_mac(mac):  # type: ignore
        raise ValueError(f"Invalid mac address format ({mac})")

    return mac


def ipv4_address(addr: str) -> str:
    """
    Validate an IPv4 address.

    :param addr: IPv4 address
    :returns: IPv4 address
    :raises TypeError: Raised if ``addr`` is not a string.
    :raises AddressValueError: Raised in case ``addr`` is not a valid IPv4 address.
    :raises NetmaskValueError: Raised in case ``addr`` is not a valid IPv4 netmask.
    """
    if not isinstance(addr, str):  # type: ignore
        raise TypeError("Invalid input, addr must be a string")
    addr = addr.strip()

    if addr == "":
        return addr

    if not netaddr.valid_ipv4(addr):  # type: ignore
        raise AddressValueError(f"Invalid IPv4 address format ({addr})")

    if netaddr.IPAddress(addr).is_netmask():
        raise NetmaskValueError(f"Invalid IPv4 host address ({addr})")

    return addr


def ipv4_netmask(addr: str) -> str:
    """
    Validate an IPv4 netmask.

    :param addr: IPv4 netmask
    :returns: IPv4 netmask
    :raises TypeError: Raised if ``addr`` is not a string.
    :raises AddressValueError: Raised in case ``addr`` is not a valid IPv4 address.
    :raises NetmaskValueError: Raised in case ``addr`` is not a valid IPv4 netmask.
    """
    if not isinstance(addr, str):  # type: ignore
        raise TypeError("Invalid input, addr must be a string")
    addr = addr.strip()

    if addr == "":
        return addr

    if not netaddr.valid_ipv4(addr):  # type: ignore
        raise AddressValueError(f"Invalid IPv4 address format ({addr})")

    if not netaddr.IPAddress(addr).is_netmask():
        raise NetmaskValueError(f"Invalid IPv4 netmask ({addr})")

    return addr


def ipv6_address(addr: str) -> str:
    """
    Validate an IPv6 address.

    :param addr: IPv6 address
    :returns: The IPv6 address.
    :raises TypeError: Raised if ``addr`` is not a string.
    :raises AddressValueError: Raised in case ``addr`` is not a valid IPv6 address.
    """
    if not isinstance(addr, str):  # type: ignore
        raise TypeError("Invalid input, addr must be a string")
    addr = addr.strip()

    if addr == "":
        return addr

    if not netaddr.valid_ipv6(addr):  # type: ignore
        raise AddressValueError(f"Invalid IPv6 address format ({addr})")

    return addr


def name_servers(
    nameservers: Union[str, List[str]], for_item: bool = True
) -> Union[str, List[str]]:
    """
    Validate nameservers IP addresses, works for IPv4 and IPv6

    :param nameservers: string or list of nameserver addresses
    :param for_item: enable/disable special handling for Item objects
    :return: The list of valid nameservers.
    :raises TypeError: Raised if ``nameservers`` is not a string or list.
    :raises AddressValueError: Raised in case ``nameservers`` is not a valid address.
    """
    if isinstance(nameservers, str):
        nameservers = nameservers.strip()
        if for_item is True:
            # special handling for Items
            if nameservers in [enums.VALUE_INHERITED, ""]:
                return nameservers

        # convert string to a list; do the real validation in the isinstance(list) code block below
        nameservers = shlex.split(nameservers)

    if isinstance(nameservers, list):  # type: ignore
        for name_server in nameservers:
            ip_version = netaddr.IPAddress(name_server).version
            if ip_version == 4:
                ipv4_address(name_server)
            elif ip_version == 6:
                ipv6_address(name_server)
            else:
                raise AddressValueError("Invalid IP address format")
    else:
        raise TypeError(f"Invalid input type {type(nameservers)}, expected str or list")

    return nameservers


def name_servers_search(
    search: Union[str, List[str]], for_item: bool = True
) -> Union[str, List[str]]:
    """
    Validate nameservers search domains.

    :param search: One or more search domains to validate.
    :param for_item: enable/disable special handling for Item objects
    :return: The list of valid nameservers.
    :raises TypeError: Raised if ``search`` is not a string or list.
    """
    if isinstance(search, str):
        search = search.strip()
        if for_item is True:
            # special handling for Items
            if search in [enums.VALUE_INHERITED, ""]:
                return search

        # convert string to a list; do the real validation in the isinstance(list) code block below
        search = shlex.split(search)

    if isinstance(search, list):  # type: ignore
        for nameserver in search:
            hostname(nameserver)
    else:
        raise TypeError(f'Invalid input type "{type(search)}", expected str or list')

    return search


def validate_breed(breed: str) -> str:
    """
    This is a setter for the operating system breed.

    :param breed: The os-breed which shall be set.
    :raises TypeError: If breed is not a str.
    :raises ValueError: If breed is not a supported breed.
    """
    if not isinstance(breed, str):  # type: ignore
        raise TypeError("breed must be of type str")
    if not breed:
        return ""
    # FIXME: The following line will fail if load_signatures() from utils/signatures.py was not called!
    valid_breeds = signatures.get_valid_breeds()
    breed = breed.lower()
    if breed and breed in valid_breeds:
        return breed
    nicer = ", ".join(valid_breeds)
    raise ValueError(
        f'Invalid value for breed ("{breed}"). Must be one of {nicer}, different breeds have different levels of '
        "support!"
    )


def validate_os_version(os_version: str, breed: str) -> str:
    """
    This is a setter for the operating system version of an object.

    :param os_version: The version which shall be set.
    :param breed: The breed to validate the os_version for.
    """
    # Type checks
    if not isinstance(os_version, str):  # type: ignore
        raise TypeError("os_version needs to be of type str")
    if not isinstance(breed, str):  # type: ignore
        raise TypeError("breed needs to be of type str")
    # Early bail out if we do a reset
    if not os_version or not breed:
        return ""
    # Check breed again, so access does not fail
    validated_breed = validate_breed(breed)
    if not validated_breed == breed:
        raise ValueError(
            "The breed supplied to the validation function of os_version was not valid."
        )
    # Now check the os_version
    # FIXME: The following line will fail if load_signatures() from utils/signatures.py was not called!
    matched = signatures.signature_cache["breeds"][breed]
    os_version = os_version.lower()
    if os_version not in matched:
        nicer = ", ".join(matched)
        raise ValueError(
            f'os_version for breed "{breed}" must be one of {nicer}, given was "{os_version}"'
        )
    return os_version


def validate_repos(
    repos: Union[List[str], str], api: "CobblerAPI", bypass_check: bool = False
) -> Union[List[str], str]:
    """
    This is a setter for the repository.

    :param repos: The repositories to set for the object.
    :param api: The api to find the repos.
    :param bypass_check: If the newly set repos should be checked for existence.
    """
    # allow the magic inherit string to persist
    if repos == enums.VALUE_INHERITED:
        return enums.VALUE_INHERITED

    # store as an array regardless of input type
    if repos is None:  # pyright: ignore [reportUnnecessaryComparison]
        repos = []
    else:
        # TODO: Don't store the names. Store the internal references.
        # repos are not allowed to be inherited atm
        repos = api.input_string_or_list_no_inherit(repos)
    if not bypass_check:
        for repo in repos:
            # FIXME: First check this and then set the repos if the bypass check is used.
            if api.repos().find(name=repo) is None:
                raise ValueError(f"repo {repo} is not defined")
    return repos


def validate_virt_file_size(num: Union[str, int, float]) -> Union[str, float]:
    """
    For Virt only: Specifies the size of the virt image in gigabytes. Older versions of koan (x<0.6.3) interpret 0 as
    "don't care". Newer versions (x>=0.6.4) interpret 0 as "no disks"

    :param num: is a non-negative integer (0 means default). Can also be a comma seperated list -- for usage with
                multiple disks (not working at the moment)
    """

    # FIXME: Data structure does not allow this (yet)
    # if isinstance(num, str) and num.find(",") != -1:
    #    tokens = num.split(",")
    #    for token in tokens:
    #        # hack to run validation on each
    #        validate_virt_file_size(token)
    #    # if no exceptions raised, good enough
    #    return num

    if isinstance(num, str):
        if num == enums.VALUE_INHERITED:
            return enums.VALUE_INHERITED
        if num == "":
            return 0.0
        if not utils.is_str_float(num):
            raise TypeError("virt_file_size needs to be a float")
        num = float(num)
    if isinstance(num, int):
        num = float(num)
    if not isinstance(num, float):  # type: ignore
        raise TypeError("virt_file_size needs to be a float")
    if num < 0:
        raise ValueError(f"invalid virt_file_size ({num})")
    return num


def validate_virt_auto_boot(value: Union[str, bool, int]) -> Union[bool, str]:
    """
    For Virt only.
    Specifies whether the VM should automatically boot upon host reboot 0 tells Koan not to auto_boot virtuals.

    :param value: May be True or False.
    """
    if value == enums.VALUE_INHERITED:
        return enums.VALUE_INHERITED
    value = input_converters.input_boolean(value)
    if not isinstance(value, bool):  # type: ignore
        raise TypeError("virt_auto_boot needs to be of type bool.")
    return value


def validate_virt_pxe_boot(value: bool) -> bool:
    """
    For Virt only.
    Specifies whether the VM should use PXE for booting 0 tells Koan not to PXE boot virtuals

    :param value: May be True or False.
    :return: True or False
    """
    value = input_converters.input_boolean(value)
    if not isinstance(value, bool):  # type: ignore
        raise TypeError("virt_pxe_boot needs to be of type bool.")
    return value


def validate_virt_ram(value: Union[int, str]) -> Union[str, int]:
    """
    For Virt only.
    Specifies the size of the Virt RAM in MB.

    :param value: 0 tells Koan to just choose a reasonable default.
    :returns: An integer in all cases, except when ``value`` is the magic inherit string.
    """
    if not isinstance(value, (str, int)):  # type: ignore
        raise TypeError("virt_ram must be of type int or the str '<<inherit>>'!")

    if isinstance(value, str):
        if value == enums.VALUE_INHERITED:
            return enums.VALUE_INHERITED
        if value == "":
            return 0
        if not utils.is_str_int(value):
            raise TypeError("virt_ram needs to be an integer")
        value = int(value)

    # value is a non-negative integer (0 means default)
    interger_number = int(value)
    if interger_number < 0:
        raise ValueError(
            "The virt_ram needs to have a value greater or equal to zero. Zero means default RAM."
        )
    return interger_number


def validate_virt_bridge(vbridge: str) -> str:
    """
    The default bridge for all virtual interfaces under this profile.

    :param vbridge: The bridgename to set for the object.
    :raises TypeError: In case vbridge was not of type str.
    """
    if not isinstance(vbridge, str):  # type: ignore
        raise TypeError("vbridge must be of type str.")
    if not vbridge:
        return enums.VALUE_INHERITED
    return vbridge


def validate_virt_path(path: str, for_system: bool = False) -> str:
    """
    Virtual storage location suggestion, can be overriden by koan.

    :param path: The path to the storage.
    :param for_system: If this is set to True then the value is inherited from a profile.
    """
    if not isinstance(path, str):  # type: ignore
        raise TypeError("Field virt_path needs to be of type str!")
    if for_system:
        if path == "":
            path = enums.VALUE_INHERITED
    return path


def validate_virt_cpus(num: Union[str, int]) -> int:
    """
    For Virt only. Set the number of virtual CPUs to give to the virtual machine. This is fed to virtinst RAW, so
    Cobbler will not yelp if you try to feed it 9999 CPUs. No formatting like 9,999 please :)

    Zero means that the number of cores is inherited. Negative numbers are forbidden

    :param num: The number of cpu cores. If you pass the magic inherit string it will be converted to 0.
    """
    if isinstance(num, str):
        if num == enums.VALUE_INHERITED:
            return 0
        if num == "":
            return 0
        if not utils.is_str_int(num):
            raise TypeError("virt_cpus needs to be an integer")
        num = int(num)
    if not isinstance(num, int):  # type: ignore
        raise TypeError("virt_cpus needs to be an integer")
    if num < 0:
        raise ValueError("virt_cpus needs to be 0 or greater")
    return int(num)


def validate_serial_device(value: Union[str, int]) -> int:
    """
    Set the serial device for an object.

    :param value: The number of the serial device.
    :return: The validated device number
    """
    if isinstance(value, str):
        if not utils.is_str_int(value):
            raise TypeError("serial_device needs to be an integer")
        value = int(value)
    if not isinstance(value, int):  # type: ignore
        raise TypeError("serial_device needs to be an integer")
    if value < -1:
        raise ValueError("serial_device needs to be -1 or greater")
    return int(value)


def validate_serial_baud_rate(
    baud_rate: Union[int, str, enums.BaudRates]
) -> enums.BaudRates:
    """
    The baud rate is very import that the communication between the two devices can be established correctly. This is
    the setter for this parameter. This effectively is the speed of the connection.

    :param baud_rate: The baud rate to set.
    :return: The validated baud rate.
    """
    if not isinstance(baud_rate, (int, str, enums.BaudRates)):  # type: ignore
        raise TypeError("serial baud rate needs to be of type int or enums.BaudRates")
    # Convert the baud rate which came in as an int or str
    if isinstance(baud_rate, (int, str)):
        try:
            if str(baud_rate).upper() == "DISABLED" or baud_rate == -1:
                baud_rate = enums.BaudRates.DISABLED
            else:
                baud_rate = enums.BaudRates["B" + str(baud_rate)]
        except KeyError as key_error:
            raise ValueError(
                f"vtype choices include: {list(map(str, enums.BaudRates))}"
            ) from key_error
    # Now it must be of the enum Type
    if baud_rate not in enums.BaudRates:
        raise ValueError(f"invalid value for serial baud Rate ({baud_rate})")
    return baud_rate


def validate_boot_remote_file(value: str) -> bool:
    """
    This validates if the passed value is a valid value for ``remote_boot_{kernel,initrd}``.

    :param value: Must be a valid URI starting with http or tftp. ftp is not supported and thus invalid.
    :return: False in any case. If value is valid, ``True`` is returned.
    """
    if not isinstance(value, str):  # type: ignore
        return False
    parsed_url = urlparse(value)
    # Check that it starts with http / tftp
    if parsed_url.scheme not in ("http", "tftp"):
        return False
    # Check the port
    # FIXME: Allow ports behind the hostname and check if they are allowed
    # Check we have magic @@server@@
    if parsed_url.netloc.startswith("@@") and parsed_url.netloc.endswith("server@@"):
        return True
    # If not magic @@server@@ then assume IPv4/v6
    if netaddr.valid_ipv4(parsed_url.netloc) or netaddr.valid_ipv6(parsed_url.netloc):
        return True
    # If not magic or IPv4/v6 then it must be a valid hostname
    # To check that we remove the protocol and get then everything to the first slash
    host = value[7:].split("/", 1)[0]
    if RE_URL.match(host):
        return True
    return False


def validate_grub_remote_file(value: str) -> bool:
    """
    This validates if the passed value is a valid value for ``remote_grub_{kernel,initrd}``.

    :param value: Must be a valid grub formatted URI starting with http or tftp. ftp is not supported and thus invalid.
    :return: False in any case. If value is valid, ``True`` is returned.
    """
    if not isinstance(value, str):  # type: ignore
        return False
    # Format: "(%s,%s)/%s" % (prot, server, path)
    grub_match_result = RE_URL_GRUB.match(value)
    success = False
    if grub_match_result:
        # grub_match_result.group("protocol") -> No further processing needing if the match is there.
        server = grub_match_result.group("server")
        # FIXME: Disallow invalid port specifications in the URL
        success_server_ip = netaddr.valid_ipv4(server) or netaddr.valid_ipv6(server)
        # FIXME: Disallow invalid URLs (e.g.: underscore in URL)
        success_server_name = urlparse(f"https://{server}").netloc == server
        path = grub_match_result.group("path")
        success_path = urlparse(f"https://fake.local/{path}").path[1:] == path
        success = (success_server_ip or success_server_name) and success_path
    return success


def validate_autoinstall_script_name(name: str) -> bool:
    """
    This validates if the name given for the script is valid in the context of the API call made. It will be handed to
    tftpgen.py#generate_script in the end.

    :param name: The name of the script. Will end up being a filename. May have an extension but should never be a path.
    :return: If this is a valid script name or not.
    """
    if not isinstance(name, str):  # type: ignore
        return False
    if re.fullmatch(RE_SCRIPT_NAME, name):
        return True
    return False


def validate_uuid(possible_uuid: str) -> bool:
    """
    Validate if the handed string is a valid UUIDv4 hex representation.

    :param possible_uuid: The str with the UUID.
    :return: True in case it is one, False otherwise.
    """
    if not isinstance(possible_uuid, str):  # type: ignore
        return False
    # Taken from: https://stackoverflow.com/a/33245493/4730773
    try:
        uuid_obj = UUID(possible_uuid, version=4)
    except ValueError:
        return False
    return uuid_obj.hex == possible_uuid


def validate_obj_type(object_type: str) -> bool:
    """
    This validates the given object type against the available object types in Cobbler.

    :param object_type: The str with the object type to validate.
    :return: True in case it is one, False in all other cases.
    """
    if not isinstance(object_type, str):  # type: ignore
        return False
    return object_type in [
        "distro",
        "profile",
        "system",
        "repo",
        "image",
        "menu",
    ]


def validate_obj_name(object_name: str) -> bool:
    """
    This validates the name of an object against the Cobbler specific object name schema.

    :param object_name: The object name candidate.
    :return: True in case it matches the RE_OBJECT_NAME regex, False in all other cases.
    """
    if not isinstance(object_name, str):  # type: ignore
        return False
    return bool(re.fullmatch(base_item.RE_OBJECT_NAME, object_name))
