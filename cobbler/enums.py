"""
This module is responsible for containing all enums we use in Cobbler. It should not be dependent upon any other module
except the Python standard library.
"""

import enum
from typing import TypeVar, Union

VALUE_INHERITED = "<<inherit>>"
VALUE_NONE = "none"
CONVERTABLEENUM = TypeVar("CONVERTABLEENUM", bound="ConvertableEnum")


class ConvertableEnum(enum.Enum):
    """
    Abstract class to convert the enum via our convert method.
    """

    @classmethod
    def to_enum(cls, value: Union[str, CONVERTABLEENUM]) -> CONVERTABLEENUM:
        """
        This method converts the chosen str to the corresponding enum type.

        :param value: str which contains the to be converted value.
        :returns: The enum value.
        :raises TypeError: In case value was not of type str.
        :raises ValueError: In case value was not in the range of valid values.
        """
        # mypy cannot handle the MRO in case we make this a real abstract class
        # Thus since we use this like an abstract class we will just add the three ignores here since we
        # are sure that this will be okay.
        try:
            if isinstance(value, str):
                if value == VALUE_INHERITED:
                    try:
                        return cls["INHERITED"]  # type: ignore
                    except KeyError as key_error:
                        raise ValueError(
                            "The enum given does not support inheritance!"
                        ) from key_error
                return cls[value.upper()]  # type: ignore
            if isinstance(value, cls):
                return value  # type: ignore
            raise TypeError(f"{value} must be a str or Enum")
        except KeyError:
            raise ValueError(f"{value} must be one of {list(cls)}") from KeyError


class EventStatus(ConvertableEnum):
    """
    This enums describes the status an event can have. The cycle is the following:

        "Running" --> "Complete" or "Failed"
    """

    RUNNING = "running"
    """
    Shows that an event is currently being processed by the server
    """
    COMPLETE = "complete"
    """
    Shows that an event did complete as desired
    """
    FAILED = "failed"
    """
    Shows that an event did not complete as expected
    """
    INFO = "notification"
    """
    Default Event status
    """


class ItemTypes(ConvertableEnum):
    """
    This enum represents all valid item types in Cobbler. If a new item type is created it must be added into this enum.
    Abstract base item types don't have to be added here.
    """

    DISTRO = "distro"
    """
    See :func:`~cobbler.items.distro.Distro`
    """
    PROFILE = "profile"
    """
    See :func:`~cobbler.items.profile.Profile`
    """
    SYSTEM = "system"
    """
    See :func:`~cobbler.items.system.System`
    """
    REPO = "repo"
    """
    See :func:`~cobbler.items.repo.Repo`
    """
    IMAGE = "image"
    """
    See :func:`~cobbler.items.image.Image`
    """
    MENU = "menu"
    """
    See :func:`~cobbler.items.menu.Menu`
    """
    NETWORK_INTERFACE = "network_interface"
    """
    See :func:`~cobbler.items.network_interface.NetworkInterface`
    """
    TEMPLATE = "template"
    """
    See :func:`~cobbler.items.template.Template`
    """


class DHCP(enum.Enum):
    """
    This enum represents all DHCP versions that Cobbler supports.
    """

    V4 = 4
    V6 = 6


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

    NA = "na"
    BOND = "bond"
    BOND_SLAVE = "bond_slave"
    BRIDGE = "bridge"
    BRIDGE_SLAVE = "bridge_slave"
    BONDED_BRIDGE_SLAVE = "bonded_bridge_slave"
    BMC = "bmc"
    INFINIBAND = "infiniband"


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

    NONE = "none"
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


class BootLoader(ConvertableEnum):
    """
    This enum represents all supported boot loaders inside Cobbler.
    """

    INHERITED = VALUE_INHERITED
    GRUB = "grub"
    IPXE = "ipxe"
    PXE = "pxe"


class TemplateSchema(ConvertableEnum):
    """
    This enum represents all supported template sources that Cobbler can read.
    """

    FILE = "file"
    ENVIRONMENT = "environment"
    IMPORTLIB = "importlib"


class TemplateTag(ConvertableEnum):
    """
    This enum represents all the well-known tags that represent special templates that are needed so Cobbler can manage
    the target daemons.
    """

    ACTIVE = "active"
    DEFAULT = "default"
    DHCPV4 = "dhcpv4"
    DHCPV6 = "dhcpv6"
    DNSMASQ = "dnsmasq"
    GENDERS = "genders"
    NAMED_PRIMARY = "named_primary"
    NAMED_SECONDARY = "named_secondary"
    NAMED_ZONE_DEFAULT = "named_zone_default"
    NAMED_ZONE_SPECIFC = "named_zone_specifc"
    NDJBDNS = "ndjbdns"
    RSYNC = "rsync"
    BOOTCFG = "bootcfg"
    GRUB = "grub"
    GRUB_MENU = "grub_menu"
    GRUB_SUBMENU = "grub_submenu"
    IPXE = "ipxe"
    IPXE_MENU = "ipxe_menu"
    IPXE_SUBMENU = "ipxe_submenu"
    PXE = "pxe"
    PXE_MENU = "pxe_menu"
    PXE_SUBMENU = "pxe_submenu"
    ISO_BOOTINFO = "iso_bootinfo"
    ISO_BUILDISO = "iso_buildiso"
    ISO_GRUB_MENUENTRY = "iso_grub_menuentry"
    ISO_ISOLINUX_MENUENTRY = "iso_isolinux_menuentry"
    REPORTING_BUILD_EMAIL = "reporting_build_email"
    WINDOWS_ANSWERFILE = "windows_answerfile"
    WINDOWS_POST_INST_CMD = "windows_post_inst_cmd"
    WINDOWS_STARTNET = "windows_startnet"


class AutoinstallerType(ConvertableEnum):
    """
    This enum represents the currently allowed types that may request a file with the "autoinstallation" endpoints.
    """

    LEGACY = "legacy"
    PRESEED = "preseed"
    KICKSTART = "kickstart"
    AUTOYAST = "autoyast"
    # AGAMA = "agama"
    # CLOUDINIT = "cloud-init"
    WINDOWS = "windows"
    XEN = "xen"
    # IGNITION = "ignition"
    # COMBUSTION = "combustion"


class AutoinstallValidationError(ConvertableEnum):
    """
    This enum represents the template validation error codes that are well-known to Cobbler.
    """

    NONE = 0
    TEMPLATING = 1
    KICKSTART = 2
