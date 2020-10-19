"""
Copyright 2014-2015. Jorgen Maas <jorgen.maas@gmail.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import re
import shlex
from ipaddress import AddressValueError, NetmaskValueError
from typing import Union

import netaddr

from cobbler import enums, utils
from cobbler.utils import get_valid_breeds, input_string_or_list
RE_HOSTNAME = re.compile(r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]{0,61}[a-zA-Z0-9]))*$')

# blacklist invalid values to the repo statement in autoinsts
AUTOINSTALL_REPO_BLACKLIST = ['enabled', 'gpgcheck', 'gpgkey']


# FIXME: Allow the <<inherit>> magic string to be parsed correctly.


def hostname(dnsname: str) -> str:
    """
    Validate the DNS name.

    :param dnsname: Hostname or FQDN
    :returns: Hostname or FQDN
    :raises TypeError: If the Hostname/FQDN is not a string or in an invalid format.
    """
    if not isinstance(dnsname, str):
        raise TypeError("Invalid input, dnsname must be a string")
    else:
        dnsname = dnsname.strip()

    if dnsname == "":
        # hostname is not required
        return dnsname

    if not RE_HOSTNAME.match(dnsname):
        raise ValueError("Invalid hostname format (%s)" % dnsname)

    return dnsname


def mac_address(mac: str, for_item=True) -> str:
    """
    Validate as an Ethernet MAC address.

    :param mac: MAC address
    :param for_item: If the check should be performed for an item or not.
    :returns: MAC address
    :raises ValueError
    """
    if not isinstance(mac, str):
        raise TypeError("Invalid input, mac must be a string")
    else:
        mac = mac.lower().strip()

    if for_item is True:
        # this value has special meaning for items
        if mac == "random":
            return mac

        # copying system collection will set mac to ""
        # netaddr will fail to validate this mac and throws an exception
        if mac == "":
            return mac

    if not netaddr.valid_mac(mac):
        raise ValueError("Invalid mac address format (%s)" % mac)

    return mac


def ipv4_address(addr: str) -> str:
    """
    Validate an IPv4 address.

    :param addr: IPv4 address
    :returns: IPv4 address
    :raises TypeError, AddressValueError or NetmaskValueError
    """
    if not isinstance(addr, str):
        raise TypeError("Invalid input, addr must be a string")
    else:
        addr = addr.strip()

    if addr == "":
        return addr

    if not netaddr.valid_ipv4(addr):
        raise AddressValueError("Invalid IPv4 address format (%s)" % addr)

    if netaddr.IPAddress(addr).is_netmask():
        raise NetmaskValueError("Invalid IPv4 host address (%s)" % addr)

    return addr


def ipv4_netmask(addr: str) -> str:
    """
    Validate an IPv4 netmask.

    :param addr: IPv4 netmask
    :returns: IPv4 netmask
    :raises TypeError, AddressValueError or NetmaskValueError
    """
    if not isinstance(addr, str):
        raise TypeError("Invalid input, addr must be a string")
    else:
        addr = addr.strip()

    if addr == "":
        return addr

    if not netaddr.valid_ipv4(addr):
        raise AddressValueError("Invalid IPv4 address format (%s)" % addr)

    if not netaddr.IPAddress(addr).is_netmask():
        raise NetmaskValueError("Invalid IPv4 netmask (%s)" % addr)

    return addr


def ipv6_address(addr: str) -> str:
    """
    Validate an IPv6 address.

    :param addr: IPv6 address
    :returns: The IPv6 address.
    :raises TypeError or AddressValueError
    """
    if not isinstance(addr, str):
        raise TypeError("Invalid input, addr must be a string")
    else:
        addr = addr.strip()

    if addr == "":
        return addr

    if not netaddr.valid_ipv6(addr):
        raise AddressValueError("Invalid IPv6 address format (%s)" % addr)

    return addr


def name_servers(nameservers: Union[str, list], for_item: bool = True) -> Union[str, list]:
    """
    Validate nameservers IP addresses, works for IPv4 and IPv6

    :param nameservers: string or list of nameserver addresses
    :param for_item: enable/disable special handling for Item objects
    :return: The list of valid nameservers.
    :raises TypeError or AddressValueError
    """
    if isinstance(nameservers, str):
        nameservers = nameservers.strip()
        if for_item is True:
            # special handling for Items
            if nameservers in [enums.VALUE_INHERITED, ""]:
                return nameservers

        # convert string to a list; do the real validation in the isinstance(list) code block below
        nameservers = shlex.split(nameservers)

    if isinstance(nameservers, list):
        for ns in nameservers:
            ip_version = netaddr.IPAddress(ns).version
            if ip_version == 4:
                ipv4_address(ns)
            elif ip_version == 6:
                ipv6_address(ns)
            else:
                raise AddressValueError("Invalid IP address format")
    else:
        raise TypeError("Invalid input type %s, expected str or list" % type(nameservers))

    return nameservers


def name_servers_search(search: Union[str, list], for_item: bool = True) -> Union[str, list]:
    """
    Validate nameservers search domains.

    :param search: One or more search domains to validate.
    :param for_item: (enable/disable special handling for Item objects)
    :return: The list of valid nameservers.
    :raises TypeError
    """
    if isinstance(search, str):
        search = search.strip()
        if for_item is True:
            # special handling for Items
            if search in [enums.VALUE_INHERITED, ""]:
                return search

        # convert string to a list; do the real validation in the isinstance(list) code block below
        search = shlex.split(search)

    if isinstance(search, list):
        for sl in search:
            hostname(sl)
    else:
        raise TypeError("Invalid input type \"%s\", expected str or list" % type(search))

    return search


def validate_breed(breed: str) -> str:
    """
    This is a setter for the operating system breed.

    :param breed: The os-breed which shall be set.
    :raises TypeError: If breed is not a str.
    :raises ValueError: If breed is not a supported breed.
    """
    if not isinstance(breed, str):
        raise TypeError("breed must be of type str")
    if not breed:
        return ""
    # FIXME: The following line will fail if load_signatures() from utils.py was not called!
    valid_breeds = get_valid_breeds()
    breed = breed.lower()
    if breed and breed in valid_breeds:
        return breed
    nicer = ", ".join(valid_breeds)
    raise ValueError("Invalid value for breed (\"%s\"). Must be one of %s, different breeds have different levels of "
                     "support!" % (breed, nicer))


def validate_os_version(os_version: str, breed: str) -> str:
    """
    This is a setter for the operating system version of an object.

    :param os_version: The version which shall be set.
    :param breed: The breed to validate the os_version for.
    """
    # Type checks
    if not isinstance(os_version, str):
        raise TypeError("os_version needs to be of type str")
    if not isinstance(breed, str):
        raise TypeError("breed needs to be of type str")
    # Early bail out if we do a reset
    if not os_version or not breed:
        return ""
    # Check breed again, so access does not fail
    validated_breed = validate_breed(breed)
    if not validated_breed == breed:
        raise ValueError("The breed supplied to the validation function of os_version was not valid.")
    # Now check the os_version
    # FIXME: The following line will fail if load_signatures() from utils.py was not called!
    matched = utils.SIGNATURE_CACHE["breeds"][breed]
    os_version = os_version.lower()
    if os_version not in matched:
        nicer = ", ".join(matched)
        raise ValueError("os_version for breed \"%s\" must be one of %s, given was \"%s\"" % (breed, nicer, os_version))
    return os_version


def validate_arch(arch: Union[str, enums.Archs]) -> enums.Archs:
    """
    This is a validator for system architectures. If the arch is not valid then an exception is raised.

    :param arch: The desired architecture to set for the object.
    :raises TypeError: In case the any type other then str or enums.Archs was supplied.
    :raises ValueError: In case the supplied str could not be converted.
    """
    # Convert an arch which came in as a string
    if isinstance(arch, str):
        try:
            arch = enums.Archs[arch.upper()]
        except KeyError as e:
            raise ValueError("arch choices include: %s" % list(map(str, enums.Archs))) from e
    # Now the arch MUST be from the type for the enum.
    if not isinstance(arch, enums.Archs):
        raise TypeError("arch needs to be of type enums.Archs")
    return arch


def validate_repos(repos, api, bypass_check=False):
    """
    This is a setter for the repository.

    :param repos: The repositories to set for the object.
    :param api: The api to find the repos.
    :param bypass_check: If the newly set repos should be checked for existence.
    :type bypass_check: bool
    """
    # allow the magic inherit string to persist
    if repos == enums.VALUE_INHERITED:
        return enums.VALUE_INHERITED

    # store as an array regardless of input type
    if repos is None:
        repos = []
    else:
        # TODO: Don't store the names. Store the internal references.
        repos = input_string_or_list(repos)
    if not bypass_check:
        for r in repos:
            # FIXME: First check this and then set the repos if the bypass check is used.
            if api.repos().find(name=r) is None:
                raise ValueError("repo %s is not defined" % r)
    return repos


def validate_virt_file_size(num: Union[str, int, float]):
    """
    For Virt only: Specifies the size of the virt image in gigabytes. Older versions of koan (x<0.6.3) interpret 0 as
    "don't care". Newer versions (x>=0.6.4) interpret 0 as "no disks"

    :param num: is a non-negative integer (0 means default). Can also be a comma seperated list -- for usage with
                multiple disks
    """

    if num is None or num == "":
        return 0

    if num == enums.VALUE_INHERITED:
        return enums.VALUE_INHERITED

    if isinstance(num, str) and num.find(",") != -1:
        tokens = num.split(",")
        for t in tokens:
            # hack to run validation on each
            validate_virt_file_size(t)
        # if no exceptions raised, good enough
        return num

    try:
        inum = int(num)
        if inum != float(num):
            raise ValueError("invalid virt file size (%s)" % num)
        if inum >= 0:
            return inum
        raise ValueError("invalid virt file size (%s)" % num)
    except:
        raise ValueError("invalid virt file size (%s)" % num)


def validate_virt_disk_driver(driver: Union[enums.VirtDiskDrivers, str]):
    """
    For Virt only. Specifies the on-disk format for the virtualized disk

    :param driver: The virt driver to set.
    """
    if not isinstance(driver, (str, enums.VirtDiskDrivers)):
        raise TypeError("driver needs to be of type str or enums.VirtDiskDrivers")
    # Convert an driver which came in as a string
    if isinstance(driver, str):
        if driver == enums.VALUE_INHERITED:
            return enums.VirtDiskDrivers.INHERTIED
        try:
            driver = enums.VirtDiskDrivers[driver.upper()]
        except KeyError as e:
            raise ValueError("driver choices include: %s" % list(map(str, enums.VirtDiskDrivers))) from e
    # Now the arch MUST be from the type for the enum.
    if driver not in enums.VirtDiskDrivers:
        raise ValueError("invalid virt disk driver type (%s)" % driver)
    return driver


def validate_virt_auto_boot(value: bool) -> bool:
    """
    For Virt only.
    Specifies whether the VM should automatically boot upon host reboot 0 tells Koan not to auto_boot virtuals.

    :param value: May be True or False.
    """
    if not isinstance(value, bool):
        raise TypeError("virt_auto_boot needs to be of type bool.")
    return value


def validate_virt_pxe_boot(value: bool) -> bool:
    """
    For Virt only.
    Specifies whether the VM should use PXE for booting 0 tells Koan not to PXE boot virtuals

    :param value: May be True or False.
    :return: True or False
    """
    if not isinstance(value, bool):
        raise TypeError("virt_pxe_boot needs to be of type bool.")
    return value


def validate_virt_ram(value: Union[int, float]) -> Union[str, int]:
    """
    For Virt only.
    Specifies the size of the Virt RAM in MB.

    :param value: 0 tells Koan to just choose a reasonable default.
    :returns: An integer in all cases, except when ``value`` is the magic inherit string.
    """
    if not isinstance(value, (str, int, float)):
        raise TypeError("virt_ram must be of type int, float or the str '<<inherti>>'!")

    if isinstance(value, str):
        if value != enums.VALUE_INHERITED:
            raise ValueError("str numbers are not allowed for virt_ram")
        return enums.VALUE_INHERITED

    # value is a non-negative integer (0 means default)
    interger_number = int(value)
    if interger_number != float(value):
        raise ValueError("The virt_ram needs to be an integer. The float conversion changed its value and is thus "
                         "invalid. Value was: \"%s\"" % value)
    if interger_number < 0:
        raise ValueError("The virt_ram needs to have a value greater or equal to zero. Zero means default raM" % value)
    return interger_number


def validate_virt_type(vtype: Union[enums.VirtType, str]):
    """
    Virtualization preference, can be overridden by koan.

    :param vtype: May be one of "qemu", "kvm", "xenpv", "xenfv", "vmware", "vmwarew", "openvz" or "auto"
    """
    if not isinstance(vtype, (str, enums.VirtType)):
        raise TypeError("driver needs to be of type str or enums.VirtDiskDrivers")
    # Convert an arch which came in as a string
    if isinstance(vtype, str):
        if vtype == enums.VALUE_INHERITED:
            return enums.VALUE_INHERITED
        try:
            vtype = enums.VirtType[vtype.upper()]
        except KeyError as e:
            raise ValueError("vtype choices include: %s" % list(map(str, enums.VirtType))) from e
    # Now it must be of the enum Type
    if vtype not in enums.VirtType:
        raise ValueError("invalid virt type (%s)" % vtype)
    return vtype


def validate_virt_bridge(vbridge: str) -> str:
    """
    The default bridge for all virtual interfaces under this profile.

    :param vbridge: The bridgename to set for the object.
    :raises TypeError: In case vbridge was not of type str.
    """
    if not isinstance(vbridge, str):
        raise TypeError("vbridge must be of type str.")
    # FIXME: Settings are not available here
    if not vbridge:
        return ""
    return vbridge


def validate_virt_path(path: str, for_system: bool = False):
    """
    Virtual storage location suggestion, can be overriden by koan.

    :param path: The path to the storage.
    :param for_system: If this is set to True then the value is inherited from a profile.
    """
    if path is None:
        path = ""
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
    if not isinstance(num, int):
        raise TypeError("virt_cpus needs to be an integer")
    if num < 0:
        raise ValueError("virt_cpus needs to be 0 or greater")
    return int(num)


def validate_serial_device(device_number: int) -> int:
    """
    Set the serial device for an object.

    :param device_number: The number of the serial device.
    :return: The validated device number
    """
    if device_number == "" or device_number is None:
        device_number = None
    else:
        try:
            device_number = int(str(device_number))
        except:
            raise ValueError("invalid value for serial device (%s)" % device_number)

    return device_number


def validate_serial_baud_rate(baud_rate: Union[int, enums.BaudRates]) -> enums.BaudRates:
    """
    The baud rate is very import that the communication between the two devices can be established correctly. This is
    the setter for this parameter. This effectively is the speed of the connection.

    :param baud_rate: The baud rate to set.
    :return: The validated baud rate.
    """
    if not isinstance(baud_rate, (int, enums.BaudRates)):
        raise TypeError("serial baud rate needs to be of type int or enums.BaudRates")
    # Convert the baud rate which came in as an int
    if isinstance(baud_rate, int):
        try:
            baud_rate = enums.BaudRates["B" + str(baud_rate)]
        except KeyError as key_error:
            raise ValueError("vtype choices include: %s" % list(map(str, enums.BaudRates))) from key_error
    # Now it must be of the enum Type
    if baud_rate not in enums.BaudRates:
        raise ValueError("invalid value for serial baud Rate (%s)" % baud_rate)
    return baud_rate
