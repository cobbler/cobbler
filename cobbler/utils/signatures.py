"""
TODO
"""

import json

from cobbler import utils

SIGNATURE_CACHE = {}


def get_supported_distro_boot_loaders(distro, api_handle=None):
    """
    This is trying to return you the list of known bootloaders if all resorts fail. Otherwise this returns a list which
    contains only the subset of bootloaders which are available by the distro in the argument.

    :param distro: The distro to check for.
    :param api_handle: The api instance to resolve metadata and settings from.
    :return: The list of bootloaders or a dict of well known bootloaders.
    """
    try:
        # Try to read from the signature
        return api_handle.get_signatures()["breeds"][distro.breed][distro.os_version][
            "boot_loaders"
        ][distro.arch.value]
    except:
        try:
            # Try to read directly from the cache
            return SIGNATURE_CACHE["breeds"][distro.breed][distro.os_version][
                "boot_loaders"
            ][distro.arch.value]
        except:
            try:
                # Else use some well-known defaults
                return {
                    "ppc": ["grub", "pxe"],
                    "ppc64": ["grub", "pxe"],
                    "ppc64le": ["grub", "pxe"],
                    "ppc64el": ["grub", "pxe"],
                    "aarch64": ["grub"],
                    "i386": ["grub", "pxe", "ipxe"],
                    "x86_64": ["grub", "pxe", "ipxe"],
                }[distro.arch.value]
            except:
                # Else return the globally known list
                return utils.get_supported_system_boot_loaders()


def load_signatures(filename, cache: bool = True):
    """
    Loads the import signatures for distros.

    :param filename: Loads the file with the given name.
    :param cache: If the cache should be set with the newly read data.
    """
    global SIGNATURE_CACHE

    with open(filename, "r") as f:
        sigjson = f.read()
    sigdata = json.loads(sigjson)
    if cache:
        SIGNATURE_CACHE = sigdata


def get_valid_breeds() -> list:
    """
    Return a list of valid breeds found in the import signatures
    """
    if "breeds" in SIGNATURE_CACHE:
        return list(SIGNATURE_CACHE["breeds"].keys())
    else:
        return []


def get_valid_os_versions_for_breed(breed) -> list:
    """
    Return a list of valid os-versions for the given breed

    :param breed: The operating system breed to check for.
    :return: All operating system version which are known to Cobbler according to the signature cache filtered by a
             os-breed.
    """
    os_versions = []
    if breed in get_valid_breeds():
        os_versions = list(SIGNATURE_CACHE["breeds"][breed].keys())
    return os_versions


def get_valid_os_versions() -> list:
    """
    Return a list of valid os-versions found in the import signatures

    :return: All operating system versions which are known to Cobbler according to the signature cache.
    """
    os_versions = []
    try:
        for breed in get_valid_breeds():
            os_versions += list(SIGNATURE_CACHE["breeds"][breed].keys())
    except:
        pass
    return utils.uniquify(os_versions)


def get_valid_archs():
    """
    Return a list of valid architectures found in the import signatures

    :return: All architectures which are known to Cobbler according to the signature cache.
    """
    archs = []
    try:
        for breed in get_valid_breeds():
            for operating_system in list(SIGNATURE_CACHE["breeds"][breed].keys()):
                archs += SIGNATURE_CACHE["breeds"][breed][operating_system][
                    "supported_arches"
                ]
    except:
        pass
    return utils.uniquify(archs)
