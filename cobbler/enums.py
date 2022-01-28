"""
This module is responsible for containing all enums we use in Cobbler. It should not be dependent upon any other module
except the Python standard library.
"""

import enum
from typing import Union

VALUE_INHERITED = "<<inherit>>"
VALUE_NONE = "none"


class ConvertableEnum(enum.Enum):
    """
    Abstract class to convert the enum via our convert method.
    """

    @classmethod
    def to_enum(cls, value: Union[str, "ConvertableEnum"]) -> "ConvertableEnum":
        """
        This method converts the chosen str to the corresponding enum type.

        :param value: str which contains the to be converted value.
        :returns: The enum value.
        :raises TypeError: In case value was not of type str.
        :raises ValueError: In case value was not in the range of valid values.
        """
        try:
            if isinstance(value, str):
                if value == VALUE_INHERITED:
                    try:
                        return cls["INHERITED"]
                    except KeyError as key_error:
                        raise ValueError("The enum given does not support inheritance!") from key_error
                return cls[value.upper()]
            elif isinstance(value, cls):
                return value
            else:
                raise TypeError(f"{value} must be a str or Enum")
        except KeyError:
            raise ValueError(f"{value} must be one of {list(cls)}")


class ResourceAction(ConvertableEnum):
    """
    This enum represents all actions a resource may execute.
    """

    CREATE = "create"
    REMOVE = "remove"


class NetworkInterfaceType(enum.Enum):
    """
    This enum represents all interface types Cobbler is able to set up on a target host.
    """

    NA = 0
    BOND = 1
    BOND_SLAVE = 2
    BRIDGE = 3
    BRIDGE_SLAVE = 4
    BONDED_BRIDGE_SLAVE = 5
    BMC = 6
    INFINIBAND = 7


class RepoBreeds(ConvertableEnum):
    """
    This enum describes all repository breeds Cobbler is able to manage.
    """

    NONE = VALUE_NONE
    RSYNC = "rsync"
    RHN = "rhn"
    YUM = "yum"
    APT = "apt"
    WGET = "wget"


class RepoArchs(ConvertableEnum):
    """
    This enum describes all repository architectures Cobbler is able to serve in case the content of the repository is
    serving the same architecture.
    """

    NONE = VALUE_NONE
    I386 = "i386"
    X86_64 = "x86_64"
    IA64 = "ia64"
    PPC = "ppc"
    PPC64 = "ppc64"
    PPC64LE = "ppc64le"
    PPC64EL = "ppc64el"
    S390 = "s390"
    ARM = "arm"
    AARCH64 = "aarch64"
    NOARCH = "noarch"
    SRC = "src"


class Archs(ConvertableEnum):
    """
    This enum describes all system architectures which Cobbler is able to provision.
    """

    I386 = "i386"
    X86_64 = "x86_64"
    IA64 = "ia64"
    PPC = "ppc"
    PPC64 = "ppc64"
    PPC64LE = "ppc64le"
    PPC64EL = "ppc64el"
    S390 = "s390"
    S390X = "s390x"
    ARM = "arm"
    AARCH64 = "aarch64"


class VirtType(ConvertableEnum):
    """
    This enum represents all known types of virtualization Cobbler is able to handle via Koan.
    """

    INHERITED = VALUE_INHERITED
    QEMU = "qemu"
    KVM = "kvm"
    XENPV = "xenpv"
    XENFV = "xenfv"
    VMWARE = "vmware"
    VMWAREW = "vmwarew"
    OPENVZ = "openvz"
    AUTO = "auto"


class VirtDiskDrivers(ConvertableEnum):
    """
    This enum represents all virtual disk driver Cobbler can handle.
    """

    INHERITED = VALUE_INHERITED
    RAW = "raw"
    QCOW2 = "qcow2"
    QED = "qed"
    VDI = "vdi"
    VDMK = "vdmk"


class BaudRates(enum.Enum):
    """
    This enum describes all baud rates which are commonly used.
    """

    DISABLED = -1
    B0 = 0
    B110 = 110
    B300 = 300
    B600 = 600
    B1200 = 1200
    B2400 = 2400
    B4800 = 4800
    B9600 = 9600
    B14400 = 14400
    B19200 = 19200
    B38400 = 38400
    B57600 = 57600
    B115200 = 115200
    B128000 = 128000
    B256000 = 256000


class ImageTypes(ConvertableEnum):
    """
    This enum represents all image types which Cobbler can manage.
    """

    DIRECT = "direct"
    ISO = "iso"
    MEMDISK = "memdisk"
    VIRT_CLONE = "virt-clone"


class MirrorType(ConvertableEnum):
    """
    This enum represents all mirror types which Cobbler can manage.
    """

    METALINK = "metalink"
    MIRRORLIST = "mirrorlist"
    BASEURL = "baseurl"


class TlsRequireCert(ConvertableEnum):
    """
    This enum represents all TLS validation server cert types which Cobbler can manage.
    """

    NEVER = "never"
    ALLOW = "allow"
    DEMAND = "demand"
    HARD = "hard"
