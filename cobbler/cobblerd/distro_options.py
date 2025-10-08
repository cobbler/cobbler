"""
Module to provide reasonable defaults to the cobblerd setup utility.
"""

import pathlib
import shutil
from dataclasses import dataclass
from typing import Dict

from cobbler.utils import get_family


@dataclass
class DistroOptions:
    """
    This class sets up configuration options based on the detected Linux distribution.
    """

    datapath: pathlib.Path = pathlib.Path("/usr/share/cobbler")
    docpath: pathlib.Path = pathlib.Path("/usr/share/man")
    etcpath: pathlib.Path = pathlib.Path("/etc/cobbler")
    libpath: pathlib.Path = pathlib.Path("/var/lib/cobbler")
    logpath: pathlib.Path = pathlib.Path("/var/log")
    systemd_dir: pathlib.Path = pathlib.Path("/etc/systemd/system")
    completion_path: pathlib.Path = pathlib.Path(
        "/usr/share/bash-completion/completions"
    )
    httpd_user: str = "apache"
    """
    User which is used to execute apache2.
    """
    httpd_group: str = "apache"

    """
    Group which is used to execute apache2.
    """

    httpd_service: str = "apache2.service"

    webroot: pathlib.Path = pathlib.Path("/srv/www")
    """
    Directory where Cobbler can create the directory which the webserver can serve.
    """

    webconfig: pathlib.Path = pathlib.Path("/etc/apache2/vhosts.d")
    webrootconfig: pathlib.Path = pathlib.Path("/etc/apache2")

    tftproot: pathlib.Path = pathlib.Path("/srv/tftpboot")
    """
    Directory which the TFTP server is offering.
    """

    bind_zonefiles: pathlib.Path = pathlib.Path("/var/lib/named")
    defaultpath: pathlib.Path = pathlib.Path("etc/sysconfig")
    shim_folder: str = r"/usr/share/efi/*/"
    shim_file: str = r"shim\.efi"
    secure_grub_folder: str = r"/usr/share/efi/*/"
    secure_grub_file: str = r"grub\.efi"
    ipxe_folder: pathlib.Path = pathlib.Path("/usr/share/ipxe/")
    pxelinux_folder: pathlib.Path = pathlib.Path("/usr/share/syslinux")
    memdisk_folder: pathlib.Path = pathlib.Path("/usr/share/syslinux")
    syslinux_dir: pathlib.Path = pathlib.Path("/usr/share/syslinux")
    grub_mod_folder: pathlib.Path = pathlib.Path("/usr/share/grub2")

    def to_context(self) -> Dict[str, str]:
        """
        This creates a context dictionary that can be used to template a given file.
        """
        result: Dict[str, str] = {}
        for key, value in vars(self).items():
            result[key] = str(value)
        cobblerd_location = shutil.which("cobblerd")
        if cobblerd_location is None:
            cobblerd_location = "/usr/bin/cobblerd"
        result["cobblerd_location"] = cobblerd_location
        return result


def get_distro_options() -> DistroOptions:
    """
    Detects the Linux distribution and sets up environment variables accordingly.
    Returns an instance of DistroOptions with the appropriate settings.
    """
    distro_options = DistroOptions()
    distro = get_family()

    # Set environment variables based on the detected distribution
    if distro == "debian":
        distro_options.httpd_user = "www-data"
        distro_options.httpd_group = "www-data"
        distro_options.webroot = pathlib.Path("/var/www")
        distro_options.webconfig = pathlib.Path("/etc/apache2/conf-available")
        distro_options.tftproot = pathlib.Path("/srv/tftp")
        distro_options.bind_zonefiles = pathlib.Path("/etc/bind/db.")
        distro_options.defaultpath = pathlib.Path("etc/default")
        distro_options.shim_folder = r"/usr/lib/shim/"
        distro_options.shim_file = r"shim.*\.efi\.signed"
        distro_options.secure_grub_folder = r"/usr/lib/shim/"
        distro_options.secure_grub_file = r"grub[a-zA-Z0-9]*\.efi"
        distro_options.ipxe_folder = pathlib.Path("/usr/lib/ipxe/")
        distro_options.pxelinux_folder = pathlib.Path("/usr/lib/PXELINUX/")
        distro_options.memdisk_folder = pathlib.Path("/usr/lib/syslinux/")
        distro_options.syslinux_dir = pathlib.Path("/usr/lib/syslinux/modules/bios/")
        distro_options.grub_mod_folder = pathlib.Path("/usr/lib/grub")
    elif distro == "redhat":
        distro_options.httpd_user = "apache"
        distro_options.httpd_group = "apache"
        distro_options.httpd_service = "httpd.service"
        distro_options.webroot = pathlib.Path("/var/www")
        distro_options.webconfig = pathlib.Path("/etc/httpd/conf.d")
        distro_options.webrootconfig = pathlib.Path("/etc/httpd")
        distro_options.tftproot = pathlib.Path("/var/lib/tftpboot")
        distro_options.bind_zonefiles = pathlib.Path("/var/named")
        distro_options.shim_folder = r"/boot/efi/EFI/*/"
        distro_options.shim_file = r"shim[a-zA-Z0-9]*\.efi"
        distro_options.secure_grub_folder = r"/boot/efi/EFI/*/"
        distro_options.secure_grub_file = r"grub\.efi"
        distro_options.grub_mod_folder = pathlib.Path("/usr/lib/grub")
    elif distro == "suse":
        distro_options.httpd_user = "wwwrun"
        distro_options.httpd_group = "www"
    else:
        raise ValueError(f"Unsupported distribution: {distro}")

    return distro_options
