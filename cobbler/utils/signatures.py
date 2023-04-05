"""
TODO
"""

import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from cobbler import utils

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro
    from cobbler.items.image import Image


signature_cache: Dict[str, Any] = {}


def get_supported_distro_boot_loaders(
    item: Union["Distro", "Image"], api_handle: Optional["CobblerAPI"] = None
) -> List[str]:
    """
    This is trying to return you the list of known bootloaders if all resorts fail. Otherwise this returns a list which
    contains only the subset of bootloaders which are available by the distro in the argument.

    :param distro: The distro to check for.
    :param api_handle: The api instance to resolve metadata and settings from.
    :return: The list of bootloaders or a dict of well known bootloaders.
    """
    try:
        # Try to read from the signature
        if api_handle is not None:
            return api_handle.get_signatures()["breeds"][item.breed][item.os_version][
                "boot_loaders"
            ][item.arch.value]
        raise Exception("Fall through to cache for signatures!")
    except Exception:
        try:
            # Try to read directly from the cache
            return signature_cache["breeds"][item.breed][item.os_version][
                "boot_loaders"
            ][item.arch.value]
        except Exception:
            try:
                well_known_defaults = {
                    "ppc": ["grub", "pxe"],
                    "ppc64": ["grub", "pxe"],
                    "ppc64le": ["grub", "pxe"],
                    "ppc64el": ["grub", "pxe"],
                    "aarch64": ["grub"],
                    "i386": ["grub", "pxe", "ipxe"],
                    "x86_64": ["grub", "pxe", "ipxe"],
                }
                # Else use some well-known defaults
                return well_known_defaults[item.arch.value]
            except Exception:
                # Else return the globally known list
                return utils.get_supported_system_boot_loaders()


def load_signatures(filename: str, cache: bool = True) -> None:
    """
    Loads the import signatures for distros.

    :param filename: Loads the file with the given name.
    :param cache: If the cache should be set with the newly read data.
    """
    # Signature cache is module wide and thus requires global
    global signature_cache  # pylint: disable=global-statement,invalid-name

    with open(filename, "r", encoding="UTF-8") as signature_file_fd:
        sigjson = signature_file_fd.read()
    sigdata = json.loads(sigjson)
    if cache:
        signature_cache = sigdata


def get_valid_breeds() -> List[str]:
    """
    Return a list of valid breeds found in the import signatures
    """
    if "breeds" in signature_cache:
        return list(signature_cache["breeds"].keys())
    return []


def get_valid_os_versions_for_breed(breed: str) -> List[str]:
    """
    Return a list of valid os-versions for the given breed

    :param breed: The operating system breed to check for.
    :return: All operating system version which are known to Cobbler according to the signature cache filtered by a
             os-breed.
    """
    os_versions = []
    if breed in get_valid_breeds():
        os_versions = list(signature_cache["breeds"][breed].keys())
    return os_versions


def get_valid_os_versions() -> List[str]:
    """
    Return a list of valid os-versions found in the import signatures

    :return: All operating system versions which are known to Cobbler according to the signature cache.
    """
    os_versions: List[str] = []
    try:
        for breed in get_valid_breeds():
            os_versions.extend(list(signature_cache["breeds"][breed].keys()))
    except Exception:
        pass
    return utils.uniquify(os_versions)


def get_valid_archs() -> List[str]:
    """
    Return a list of valid architectures found in the import signatures

    :return: All architectures which are known to Cobbler according to the signature cache.
    """
    archs: List[str] = []
    try:
        for breed in get_valid_breeds():
            for operating_system in list(signature_cache["breeds"][breed].keys()):
                archs += signature_cache["breeds"][breed][operating_system][
                    "supported_arches"
                ]
    except Exception:
        pass
    return utils.uniquify(archs)
