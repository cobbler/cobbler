"""
Utility module to provide methods for working with the distro signatures JSON database file.
"""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from libcobblersignatures import Signatures
from libcobblersignatures.enums import ImportTypes
from libcobblersignatures.models.osbreed import OsBreed

from cobbler import enums, utils

if TYPE_CHECKING:
    from cobbler.items.distro import Distro
    from cobbler.items.image import Image


_signatures: Optional[Signatures] = None


def get_breeds() -> List[OsBreed]:
    """
    Return the list of OS breeds known from the currently loaded signatures.

    :return: The list of breeds, or an empty list if no signatures have been loaded yet.
    """
    if _signatures is None:
        return []
    return _signatures.osbreeds


def get_raw_signatures() -> Dict[str, Any]:
    """
    Return the signatures as originally parsed from JSON. This is used where the exact on-disk shape is required
    (e.g. the XML-RPC API), as opposed to the typed model returned by :func:`get_breeds`.

    :return: The dict containing all signatures, or an empty dict if none have been loaded yet.
    """
    if _signatures is None:
        return {}
    return _signatures.signaturesjson


def get_supported_distro_boot_loaders(
    item: Union["Distro", "Image"], api_handle: Optional[Any] = None
) -> List[enums.BootLoader]:
    """
    This is trying to return you the list of known bootloaders if all resorts fail. Otherwise this returns a list which
    contains only the subset of bootloaders which are available by the distro in the argument.

    :param item: The distro to check for.
    :param api_handle: Unused, kept for backward compatibility of the call signature.
    :return: The list of bootloaders or a dict of well known bootloaders.
    """
    try:
        for breed in get_breeds():
            if breed.name != item.breed:
                continue
            osversion = breed.osversions.get(item.os_version)
            if osversion is None:
                continue
            loaders = osversion.boot_loaders.get(item.arch.value)
            if loaders:
                return [enums.BootLoader.to_enum(loader) for loader in loaders]
        raise Exception("Fall through to well-known defaults for signatures!")
    except Exception:
        try:
            well_known_defaults = {
                enums.Archs.PPC: [enums.BootLoader.GRUB, enums.BootLoader.PXE],
                enums.Archs.PPC64: [enums.BootLoader.GRUB, enums.BootLoader.PXE],
                enums.Archs.PPC64LE: [enums.BootLoader.GRUB, enums.BootLoader.PXE],
                enums.Archs.PPC64EL: [enums.BootLoader.GRUB, enums.BootLoader.PXE],
                enums.Archs.AARCH64: [enums.BootLoader.GRUB],
                enums.Archs.I386: [
                    enums.BootLoader.GRUB,
                    enums.BootLoader.PXE,
                    enums.BootLoader.IPXE,
                ],
                enums.Archs.X86_64: [
                    enums.BootLoader.GRUB,
                    enums.BootLoader.PXE,
                    enums.BootLoader.IPXE,
                ],
            }
            # Else use some well-known defaults
            return well_known_defaults[item.arch]
        except Exception:
            # Else return the globally known list
            return utils.get_supported_system_boot_loaders()


def load_signatures(filename: str, cache: bool = True) -> Signatures:
    """
    Loads the import signatures for distros.

    :param filename: Loads the file with the given name.
    :param cache: If the cache should be set with the newly read data.
    :return: The loaded signatures.
    """
    # Signature cache is module wide and thus requires global
    global _signatures  # pylint: disable=global-statement,invalid-name

    new_signatures = Signatures()
    new_signatures.importsignatures(ImportTypes.FILE, filename)
    new_signatures.jsontomodels()
    if cache:
        _signatures = new_signatures
    return new_signatures


def get_valid_breeds() -> List[str]:
    """
    Return a list of valid breeds found in the import signatures
    """
    return [breed.name for breed in get_breeds()]


def get_valid_os_versions_for_breed(breed: str) -> List[str]:
    """
    Return a list of valid os-versions for the given breed

    :param breed: The operating system breed to check for.
    :return: All operating system version which are known to Cobbler according to the signature cache filtered by a
             os-breed.
    """
    for os_breed in get_breeds():
        if os_breed.name == breed:
            return list(os_breed.osversions.keys())
    return []


def get_valid_os_versions() -> List[str]:
    """
    Return a list of valid os-versions found in the import signatures

    :return: All operating system versions which are known to Cobbler according to the signature cache.
    """
    os_versions: List[str] = []
    for breed in get_breeds():
        os_versions.extend(breed.osversions.keys())
    return utils.uniquify(os_versions)


def get_valid_archs() -> List[str]:
    """
    Return a list of valid architectures found in the import signatures

    :return: All architectures which are known to Cobbler according to the signature cache.
    """
    archs: List[str] = []
    for breed in get_breeds():
        for osversion in breed.osversions.values():
            archs.extend(osversion.supported_arches)
    return utils.uniquify(archs)
