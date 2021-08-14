"""
TODO
"""

import enum

VALUE_INHERITED = "<<inherit>>"
VALUE_NONE = "none"


class ResourceAction(enum.Enum):
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


class RepoBreeds(enum.Enum):
    """
    This enum describes all repository breeds Cobbler is able to manage.
    """
    NONE = VALUE_NONE
    RSYNC = "rsync"
    RHN = "rhn"
    YUM = "yum"
    APT = "apt"
    WGET = "wget"


class RepoArchs(enum.Enum):
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


class Archs(enum.Enum):
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


class VirtType(enum.Enum):
    """
    This enum represents all known types of virtualization Cobbler is able to handle via Koan.
    """
    INHERTIED = VALUE_INHERITED
    QEMU = "qemu"
    KVM = "kvm"
    XENPV = "xenpv"
    XENFV = "xenfv"
    VMWARE = "vmware"
    VMWAREW = "vmwarew"
    OPENVZ = "openvz"
    AUTO = "auto"


class VirtDiskDrivers(enum.Enum):
    """
    This enum represents all virtual disk driver Cobbler can handle.
    """
    INHERTIED = VALUE_INHERITED
    RAW = "raw"
    QCOW2 = "qcow2"
    QED = "qed"
    VDI = "vdi"
    VDMK = "vdmk"


class BaudRates(enum.Enum):
    """
    This enum describes all baud rates which are commonly used.
    """
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


class ImageTypes(enum.Enum):
    """
    This enum represents all image types which Cobbler can manage.
    """
    DIRECT = "direct"
    ISO = "iso"
    MEMDISK = "memdisk"
    VIRT_CLONE = "virt-clone"


class MirrorType(enum.Enum):
    """
    This enum represents all mirror types which Cobbler can manage.
    """
    METALINK = "metalink"
    MIRRORLIST = "mirrorlist"
    BASEURL = "baseurl"
