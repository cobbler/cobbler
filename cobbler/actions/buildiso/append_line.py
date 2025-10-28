"""
Module to centralize the generation of kernel options for custom built ISOs.
"""

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from cobbler.enums import NetworkInterfaceType
from cobbler.utils import kernel_command_line

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI
    from cobbler.items.distro import Distro
    from cobbler.items.profile import Profile
    from cobbler.items.system import System


class AppendLineBuilder:
    """
    This class is meant to be initiated for a single append line. Afterwards the object should be disposed.
    """

    def __init__(self, api: "CobblerAPI", distro_name: str, data: Dict[str, Any]):
        self.append_line = kernel_command_line.KernelCommandLine(api)
        self.data = data
        self.distro_name = distro_name
        self.dist: Optional["Distro"] = None
        self.system: Optional["System"] = None
        self.system_interface: Optional[str] = None
        self.system_ip = None
        self.system_netmask = None
        self.system_gw = None
        self.system_dns: Optional[Union[str, List[str]]] = None

    def _system_int_append_line(self) -> None:
        """
        This generates the interface configuration for the system to boot for the append line.
        """
        if self.dist is None:
            return
        if self.system_interface is not None:
            intmac = "mac_address_" + self.system_interface
            if self.dist.breed == "suse":
                if self.data.get(intmac, "") != "":
                    self.append_line.append_key_value(
                        "netdevice",
                        self.data["mac_address_" + self.system_interface].lower(),
                    )
                else:
                    self.append_line.append_key_value(
                        "netdevice", self.system_interface
                    )
            elif self.dist.breed == "redhat":
                if self.data.get(intmac, "") != "":
                    self.append_line.append_key_value(
                        "ksdevice", self.data["mac_address_" + self.system_interface]
                    )
                else:
                    self.append_line.append_key_value("ksdevice", self.system_interface)
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line.append_key_value(
                    "netcfg/choose_interface", self.system_interface
                )

    def _system_ip_append_line(self) -> None:
        """
        This generates the IP configuration for the system to boot for the append line.
        """
        if self.dist is None:
            return
        if self.system_ip is not None:
            if self.dist.breed == "suse":
                self.append_line.append_key_value("hostip", self.system_ip)
            elif self.dist.breed == "redhat":
                self.append_line.append_key_value("ip", self.system_ip)
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line.append_key_value(
                    "netcfg/get_ipaddress", self.system_ip
                )

    def _system_mask_append_line(self) -> None:
        """
        This generates the netmask configuration for the system to boot for the append line.
        """
        if self.dist is None:
            return
        if self.system_netmask is not None:
            if self.dist.breed in ["suse", "redhat"]:
                self.append_line.append_key_value("netmask", self.system_netmask)
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line.append_key_value(
                    "netcfg/get_netmask", self.system_netmask
                )

    def _system_gw_append_line(self) -> None:
        """
        This generates the gateway configuration for the system to boot for the append line.
        """
        if self.dist is None:
            return
        if self.system_gw is not None:
            if self.dist.breed in ["suse", "redhat"]:
                self.append_line.append_key_value("gateway", self.system_gw)
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line.append_key_value("netcfg/get_gateway", self.system_gw)

    def _system_dns_append_line(self, exclude_dns: bool) -> None:
        """
        This generates the DNS configuration for the system to boot for the append line.
        :param exclude_dns: If this flag is set to True, the DNS configuration is skipped.
        """
        if self.dist is None:
            return
        if not exclude_dns and self.system_dns is not None:
            if self.dist.breed == "suse":
                nameserver_key = "nameserver"
            elif self.dist.breed == "redhat":
                nameserver_key = "dns"
            elif self.dist.breed in ["ubuntu", "debian"]:
                nameserver_key = "netcfg/get_nameservers"
            else:
                return

            if isinstance(self.system_dns, list):
                joined_nameservers = ",".join(self.system_dns)
                if joined_nameservers != "":
                    self.append_line.append_key_value(
                        nameserver_key, joined_nameservers
                    )
            else:
                self.append_line.append_key_value(nameserver_key, self.system_dns)

    def _generate_static_ip_boot_interface(self) -> None:
        """
        The interface to use when the system boots.
        """
        if self.dist is None:
            return
        if self.dist.breed == "redhat":
            if self.data["kernel_options"].get("ksdevice", "") != "":
                self.system_interface = self.data["kernel_options"]["ksdevice"]
                if self.system_interface == "bootif":
                    self.system_interface = None
                del self.data["kernel_options"]["ksdevice"]
        elif self.dist.breed == "suse":
            if self.data["kernel_options"].get("netdevice", "") != "":
                self.system_interface = self.data["kernel_options"]["netdevice"]
                del self.data["kernel_options"]["netdevice"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/choose_interface", "") != "":
                self.system_interface = self.data["kernel_options"][
                    "netcfg/choose_interface"
                ]
                del self.data["kernel_options"]["netcfg/choose_interface"]

    def _generate_static_ip_boot_ip(self) -> None:
        """
        Generate the IP which is used during the installation process. This respects overrides.
        """
        if self.dist is None:
            return
        if self.dist.breed == "redhat":
            if self.data["kernel_options"].get("ip", "") != "":
                self.system_ip = self.data["kernel_options"]["ip"]
                del self.data["kernel_options"]["ip"]
        elif self.dist.breed == "suse":
            if self.data["kernel_options"].get("hostip", "") != "":
                self.system_ip = self.data["kernel_options"]["hostip"]
                del self.data["kernel_options"]["hostip"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_ipaddress", "") != "":
                self.system_ip = self.data["kernel_options"]["netcfg/get_ipaddress"]
                del self.data["kernel_options"]["netcfg/get_ipaddress"]

    def _generate_static_ip_boot_mask(self) -> None:
        """
        Generate the Netmask which is used during the installation process. This respects overrides.
        """
        if self.dist is None:
            return
        if self.dist.breed in ["suse", "redhat"]:
            if self.data["kernel_options"].get("netmask", "") != "":
                self.system_netmask = self.data["kernel_options"]["netmask"]
                del self.data["kernel_options"]["netmask"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_netmask", "") != "":
                self.system_netmask = self.data["kernel_options"]["netcfg/get_netmask"]
                del self.data["kernel_options"]["netcfg/get_netmask"]

    def _generate_static_ip_boot_gateway(self) -> None:
        """
        Generate the Gateway which is used during the installation process. This respects overrides.
        """
        if self.dist is None:
            return
        if self.dist.breed in ["suse", "redhat"]:
            if self.data["kernel_options"].get("gateway", "") != "":
                self.system_gw = self.data["kernel_options"]["gateway"]
                del self.data["kernel_options"]["gateway"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_gateway", "") != "":
                self.system_gw = self.data["kernel_options"]["netcfg/get_gateway"]
                del self.data["kernel_options"]["netcfg/get_gateway"]

    def _generate_static_ip_boot_dns(self) -> None:
        """
        Generates the static Boot DNS Server which is used for resolving Domains.
        """
        if self.dist is None:
            return
        if self.dist.breed == "redhat":
            if self.data["kernel_options"].get("dns", "") != "":
                self.system_dns = self.data["kernel_options"]["dns"]
                del self.data["kernel_options"]["dns"]
        elif self.dist.breed == "suse":
            if self.data["kernel_options"].get("nameserver", "") != "":
                self.system_dns = self.data["kernel_options"]["nameserver"]
                del self.data["kernel_options"]["nameserver"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_nameservers", "") != "":
                self.system_dns = self.data["kernel_options"]["netcfg/get_nameservers"]
                del self.data["kernel_options"]["netcfg/get_nameservers"]

    def _generate_static_ip_boot_options(self) -> None:
        """
        Try to add static ip boot options to avoid DHCP (interface/ip/netmask/gw/dns)
        Check for overrides first and clear them from kernel_options
        """
        self._generate_static_ip_boot_interface()
        self._generate_static_ip_boot_ip()
        self._generate_static_ip_boot_mask()
        self._generate_static_ip_boot_gateway()
        self._generate_static_ip_boot_dns()

    def _generate_append_redhat(self) -> None:
        """
        Generate additional content for the append line in case that dist is a RedHat based one.
        """
        if self.data.get("proxy", "") != "":
            self.append_line.append_key_value("proxy", self.data["proxy"])
            self.append_line.append_key_value("http_proxy", self.data["proxy"])
        if self.dist and self.dist.os_version in [
            "rhel4",
            "rhel5",
            "rhel6",
            "fedora16",
        ]:
            self.append_line.append_key_value("ks", self.data["autoinstall"])
            if self.data["autoinstall_meta"].get("tree"):
                self.append_line.append_key_value(
                    "repo", self.data["autoinstall_meta"]["tree"]
                )
        else:
            self.append_line.append_key_value("inst.ks", self.data["autoinstall"])
            if self.data["autoinstall_meta"].get("tree"):
                self.append_line.append_key_value(
                    "inst.repo", self.data["autoinstall_meta"]["tree"]
                )

    def _generate_append_debian(self, system: "System") -> None:
        """
        Generate additional content for the append line in case that dist is Ubuntu or Debian.
        :param system: The system which the append line should be generated for.
        """
        if self.dist is None:
            return
        self.append_line.append_key_value("auto-install/enable", "true")
        self.append_line.append_key_value("url", self.data["autoinstall"])
        self.append_line.append_key_value("netcfg/disable_autoconfig", "true")
        if self.data.get("proxy", "") != "":
            self.append_line.append_key_value("mirror/http/proxy", self.data["proxy"])
        # hostname is required as a parameter, the one in the preseed is not respected
        my_domain = "local.lan"
        if system.hostname != "":
            # if this is a FQDN, grab the first bit
            my_hostname = system.hostname.split(".")[0]
            _domain = system.hostname.split(".")[1:]
            if _domain:
                my_domain = ".".join(_domain)
        else:
            my_hostname = system.name.split(".")[0]
            _domain = system.name.split(".")[1:]
            if _domain:
                my_domain = ".".join(_domain)
        # At least for debian deployments configured for DHCP networking this values are not used, but
        # specifying here avoids questions
        self.append_line.append_key_value("hostname", my_hostname)
        self.append_line.append_key_value("domain", my_domain)
        # A similar issue exists with suite name, as installer requires the existence of "stable" in the dists
        # directory
        self.append_line.append_key_value("suite", self.dist.os_version)

    def _generate_append_suse(self, scheme: str = "http") -> None:
        """
        Special adjustments for generating the append line for suse.

        :param scheme: This can be either ``http`` or ``https``.
        :return: The updated append line. If the distribution is not SUSE, then nothing is changed.
        """
        if self.dist is None:
            return
        if self.data.get("proxy", "") != "":
            self.append_line.append_key_value("proxy", self.data["proxy"])
        if self.data["kernel_options"].get("install", "") != "":
            self.append_line.append_key_value(
                "install", self.data["kernel_options"]["install"]
            )
            del self.data["kernel_options"]["install"]
        else:
            self.append_line.append_key_value(
                "install",
                f"{scheme}://{self.data['server']}:{self.data['http_port']}/cblr/links/{self.dist.name}",
            )
        if self.data["kernel_options"].get("autoyast", "") != "":
            self.append_line.append_key_value(
                "autoyast", self.data["kernel_options"]["autoyast"]
            )
            del self.data["kernel_options"]["autoyast"]
        else:
            self.append_line.append_key_value("autoyast", self.data["autoinstall"])

    def _adjust_interface_config(self) -> None:
        """
        If no kernel_options overrides are present find the management interface do nothing when zero or multiple
        management interfaces are found.
        """
        if self.system_interface is None:
            mgmt_ints: List[str] = []
            mgmt_ints_multi: List[str] = []
            slave_ints: List[str] = []
            if self.system is None:
                raise ValueError(
                    "Please give system to AppendLineBuilder.generate_system()!"
                )
            for iname, idata in self.system.interfaces.items():
                if idata.management and idata.interface_type in [
                    NetworkInterfaceType.BOND,
                    NetworkInterfaceType.BRIDGE,
                ]:
                    # bonded/bridged management interface
                    mgmt_ints_multi.append(iname)
                if idata.management and idata.interface_type not in [
                    NetworkInterfaceType.BOND,
                    NetworkInterfaceType.BRIDGE,
                    NetworkInterfaceType.BOND_SLAVE,
                    NetworkInterfaceType.BRIDGE_SLAVE,
                    NetworkInterfaceType.BONDED_BRIDGE_SLAVE,
                ]:
                    # single management interface
                    mgmt_ints.append(iname)

            if len(mgmt_ints_multi) == 1 and len(mgmt_ints) == 0:
                # Bonded/bridged management interface, find a slave interface if eth0 is a slave use that (it's what
                # people expect)
                for iname, idata in self.data["interfaces"].items():
                    if (
                        idata.interface_type
                        in [
                            NetworkInterfaceType.BOND_SLAVE,
                            NetworkInterfaceType.BRIDGE_SLAVE,
                            NetworkInterfaceType.BONDED_BRIDGE_SLAVE,
                        ]
                        and idata.interface_master == mgmt_ints_multi[0]
                    ):
                        slave_ints.append(iname)

                if "eth0" in slave_ints:
                    self.system_interface = "eth0"
                else:
                    self.system_interface = slave_ints[0]
                # Set self.system_ip from the bonded/bridged interface here
                self.system_ip = self.data[
                    "ip_address_"
                    + self.data["interface_master_" + self.system_interface]
                ]
                self.system_netmask = self.data[
                    "netmask_" + self.data["interface_master_" + self.system_interface]
                ]

            if len(mgmt_ints) == 1 and len(mgmt_ints_multi) == 0:
                # Single management interface
                self.system_interface = mgmt_ints[0]

    def _get_tcp_ip_config(self) -> None:
        """
        Lookup tcp/ip configuration data. If not present already present this adds it from the previously blenderd data.
        """
        if self.system_ip is None and self.system_interface is not None:
            intip = "ip_address_" + self.system_interface
            if self.data.get(intip, "") != "":
                self.system_ip = self.data["ip_address_" + self.system_interface]
        if self.system_netmask is None and self.system_interface is not None:
            intmask = "netmask_" + self.system_interface
            if self.data.get(intmask, "") != "":
                self.system_netmask = self.data["netmask_" + self.system_interface]
        if self.system_gw is None:
            if self.data.get("gateway", "") != "":
                self.system_gw = self.data["gateway"]
        if self.system_dns is None:
            if self.data.get("dns", {}).get("name_servers") != "":
                self.system_dns = self.data.get("dns", {})["name_servers"]

    def add_remaining_kopts(self, kopts: Dict[str, Union[str, List[str]]]) -> None:
        """
        Add remaining kernel_options to append_line
        :param kopts: The kernel options which are not present in append_line.
        :return: A single line with all kernel options from the dictionary in the string. Starts with a space.
        """
        for option, args in kopts.items():
            if args is None:  # type: ignore
                self.append_line.append_key(option)
                continue

            if not isinstance(args, list):
                args = [args]

            for arg in args:
                arg_str = format(arg)
                if " " in arg_str:
                    arg_str = f'"{arg_str}"'
                self.append_line.append_key_value(option, arg_str)

    def generate_standalone(
        self,
        data: Dict[Any, Any],
        distro: "Distro",
        descendant: Union["Profile", "System"],
    ) -> str:
        """
        Generates the append line for the kernel so the installation can be done unattended.
        :param data: The values for the append line. The key "kernel_options" must be present.
        :param distro: The distro object to generate the append line from.
        :param descendant: The profile or system which is underneath the distro.
        :return: The base append_line which we need for booting the built ISO. Contains initrd and autoinstall parameter.
        """
        self.append_line.append_raw("  APPEND")
        self.append_line.append_key_value(
            "initrd", f"/{os.path.basename(distro.initrd)}"
        )
        if distro.breed == "redhat":
            if distro.os_version in ["rhel4", "rhel5", "rhel6", "fedora16"]:
                self.append_line.append_key_value(
                    "ks", f"cdrom:/autoinstall/{descendant.name}.cfg"
                )
                self.append_line.append_key_value("repo", "cdrom")
            else:
                self.append_line.append_key_value(
                    "inst.ks", f"cdrom:/autoinstall/{descendant.name}.cfg"
                )
                self.append_line.append_key_value("inst.repo", "cdrom")
        elif distro.breed == "suse":
            self.append_line.append_key_value(
                "autoyast",
                f"file:///autoinstall/{descendant.name}.cfg install=cdrom:///",
            )
            if "install" in data["kernel_options"]:
                del data["kernel_options"]["install"]
        elif distro.breed in ["ubuntu", "debian"]:
            self.append_line.append_key_value("auto-install/enable", "true")
            self.append_line.append_key_value(
                "preseed/file", f"/cdrom/autoinstall/{descendant.name}.cfg"
            )

        # add remaining kernel_options to append_line
        self.add_remaining_kopts(data["kernel_options"])
        return self.append_line.render({})

    def generate_system(
        self, dist: "Distro", system: "System", exclude_dns: bool, scheme: str = "http"
    ) -> str:
        """
        Generate the append-line for a net-booting system.

        :param dist: The distribution associated with the system.
        :param system: The system itself
        :param exclude_dns: Whether to include the DNS config or not.
        :param scheme: The scheme that is used to read the autoyast file from the server
        """
        self.dist = dist
        self.system = system

        self.append_line.append_raw("  APPEND")
        self.append_line.append_key_value("initrd", f"/{self.distro_name}.img")
        if self.dist.breed == "suse":
            self._generate_append_suse(scheme=scheme)
        elif self.dist.breed == "redhat":
            self._generate_append_redhat()
        elif dist.breed in ["ubuntu", "debian"]:
            self._generate_append_debian(system)

        self._generate_static_ip_boot_options()
        self._adjust_interface_config()
        self._get_tcp_ip_config()

        # Add information to the append_line
        self._system_int_append_line()
        self._system_ip_append_line()
        self._system_mask_append_line()
        self._system_gw_append_line()
        self._system_dns_append_line(exclude_dns)

        # Add remaining kernel_options to append_line
        self.add_remaining_kopts(self.data["kernel_options"])
        return self.append_line.render({})

    def generate_profile(
        self, distro_breed: str, os_version: str, protocol: str = "http"
    ) -> str:
        """
        Generate the append line for the kernel for a network installation.
        :param distro_breed: The name of the distribution breed.
        :param os_version: The OS version of the distribution.
        :param protocol: The scheme that is used to read the autoyast file from the server
        :return: The generated append line.
        """
        self.append_line.append_raw(" append")
        self.append_line.append_key_value("initrd", f"/{self.distro_name}.img")
        if distro_breed == "suse":
            if self.data.get("proxy", "") != "":
                self.append_line.append_key_value("proxy", self.data["proxy"])
            if self.data["kernel_options"].get("install", "") != "":
                install_options: Union[str, List[str]] = self.data["kernel_options"][
                    "install"
                ]
                if isinstance(install_options, list):
                    install_options = install_options[0]
                self.append_line.append_key_value("install", install_options)
                del self.data["kernel_options"]["install"]
            else:
                self.append_line.append_key_value(
                    "install",
                    f"{protocol}://{self.data['server']}:{self.data['http_port']}/cblr/links/{self.distro_name}",
                )
            if self.data["kernel_options"].get("autoyast", "") != "":
                self.append_line.append_key_value(
                    "autoyast", self.data["kernel_options"]["autoyast"]
                )
                del self.data["kernel_options"]["autoyast"]
            else:
                self.append_line.append_key_value("autoyast", self.data["autoinstall"])
        elif distro_breed == "redhat":
            if self.data.get("proxy", "") != "":
                self.append_line.append_key_value("proxy", self.data["proxy"])
                self.append_line.append_key_value("http_proxy", self.data["proxy"])
            if os_version in ["rhel4", "rhel5", "rhel6", "fedora16"]:
                self.append_line.append_key_value("ks", self.data["autoinstall"])
                if self.data["autoinstall_meta"].get("tree"):
                    self.append_line.append_key_value(
                        "repo", self.data["autoinstall_meta"]["tree"]
                    )
            else:
                self.append_line.append_key_value("inst.ks", self.data["autoinstall"])
                if self.data["autoinstall_meta"].get("tree"):
                    self.append_line.append_key_value(
                        "inst.repo", self.data["autoinstall_meta"]["tree"]
                    )
        elif distro_breed in ["ubuntu", "debian"]:
            self.append_line.append_key_value("auto-install/enable", "true")
            self.append_line.append_key_value("url", self.data["autoinstall"])
            if self.data.get("proxy", "") != "":
                self.append_line.append_key_value(
                    "mirror/http/proxy", self.data["proxy"]
                )
        self.add_remaining_kopts(self.data["kernel_options"])
        return self.append_line.render({})
