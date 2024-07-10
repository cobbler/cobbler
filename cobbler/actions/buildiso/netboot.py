"""
This module contains the specific code to generate a network bootable ISO.
"""

# SPDX-License-Identifier: GPL-2.0-or-later

import pathlib
import re
from typing import List, Optional, Tuple

from cobbler import utils
from cobbler.actions import buildiso
from cobbler.actions.buildiso import BootFilesCopyset, LoaderCfgsParts


class AppendLineBuilder:
    """
    This class is meant to be initiated for a single append line. Afterwards the object should be disposed.
    """

    def __init__(self, distro_name: str, data: dict):
        self.append_line = ""
        self.data = data
        self.distro_name = distro_name
        self.dist = None
        self.system_interface = None
        self.system_ip = None
        self.system_netmask = None
        self.system_gw = None
        self.system_dns = None

    def _system_int_append_line(self):
        """
        This generates the interface configuration for the system to boot for the append line.
        """
        if self.system_interface is not None:
            intmac = "mac_address_" + self.system_interface
            if self.dist.breed == "suse":
                if self.data.get(intmac, "") != "":
                    self.append_line += (
                        " netdevice=%s"
                        % self.data["mac_address_" + self.system_interface].lower()
                    )
                else:
                    self.append_line += " netdevice=%s" % self.system_interface
            elif self.dist.breed == "redhat":
                if self.data.get(intmac, "") != "":
                    self.append_line += (
                        " ksdevice=%s"
                        % self.data["mac_address_" + self.system_interface]
                    )
                else:
                    self.append_line += " ksdevice=%s" % self.system_interface
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line += (
                    " netcfg/choose_interface=%s" % self.system_interface
                )

    def _system_ip_append_line(self):
        """
        This generates the IP configuration for the system to boot for the append line.
        """
        if self.system_ip is not None:
            if self.dist.breed == "suse":
                self.append_line += " hostip=%s" % self.system_ip
            elif self.dist.breed == "redhat":
                self.append_line += " ip=%s" % self.system_ip
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line += " netcfg/get_ipaddress=%s" % self.system_ip

    def _system_mask_append_line(self):
        """
        This generates the netmask configuration for the system to boot for the append line.
        """
        if self.system_netmask is not None:
            if self.dist.breed in ["suse", "redhat"]:
                self.append_line += " netmask=%s" % self.system_netmask
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line += " netcfg/get_netmask=%s" % self.system_netmask

    def _system_gw_append_line(self):
        """
        This generates the gateway configuration for the system to boot for the append line.
        """
        if self.system_gw is not None:
            if self.dist.breed in ["suse", "redhat"]:
                self.append_line += " gateway=%s" % self.system_gw
            elif self.dist.breed in ["ubuntu", "debian"]:
                self.append_line += " netcfg/get_gateway=%s" % self.system_gw

    def _system_dns_append_line(self, exclude_dns: bool):
        """
        This generates the DNS configuration for the system to boot for the append line.
        :param exclude_dns: If this flag is set to True, the DNS configuration is skipped.
        """
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
                    self.append_line += " %s=%s" % (nameserver_key, joined_nameservers)
            else:
                self.append_line += " %s=%s" % (nameserver_key, self.system_dns)

    def _generate_static_ip_boot_interface(self):
        """
        The interface to use when the system boots.
        """
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

    def _generate_static_ip_boot_ip(self):
        """
        Generate the IP which is used during the installation process. This respects overrides.
        """
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

    def _generate_static_ip_boot_mask(self):
        """
        Generate the Netmask which is used during the installation process. This respects overrides.
        """
        if self.dist.breed in ["suse", "redhat"]:
            if self.data["kernel_options"].get("netmask", "") != "":
                self.system_netmask = self.data["kernel_options"]["netmask"]
                del self.data["kernel_options"]["netmask"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_netmask", "") != "":
                self.system_netmask = self.data["kernel_options"]["netcfg/get_netmask"]
                del self.data["kernel_options"]["netcfg/get_netmask"]

    def _generate_static_ip_boot_gateway(self):
        """
        Generate the Gateway which is used during the installation process. This respects overrides.
        """
        if self.dist.breed in ["suse", "redhat"]:
            if self.data["kernel_options"].get("gateway", "") != "":
                self.system_gw = self.data["kernel_options"]["gateway"]
                del self.data["kernel_options"]["gateway"]
        elif self.dist.breed in ["debian", "ubuntu"]:
            if self.data["kernel_options"].get("netcfg/get_gateway", "") != "":
                self.system_gw = self.data["kernel_options"]["netcfg/get_gateway"]
                del self.data["kernel_options"]["netcfg/get_gateway"]

    def _generate_static_ip_boot_dns(self):
        """
        Generates the static Boot DNS Server which is used for resolving Domains.
        """
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

    def _generate_static_ip_boot_options(self):
        """
        Try to add static ip boot options to avoid DHCP (interface/ip/netmask/gw/dns)
        Check for overrides first and clear them from kernel_options
        """
        self._generate_static_ip_boot_interface()
        self._generate_static_ip_boot_ip()
        self._generate_static_ip_boot_mask()
        self._generate_static_ip_boot_gateway()
        self._generate_static_ip_boot_dns()

    def _generate_append_redhat(self):
        """
        Generate additional content for the append line in case that dist is a RedHat based one.
        """
        if self.data.get("proxy", "") != "":
            self.append_line += " proxy=%s http_proxy=%s" % (
                self.data["proxy"],
                self.data["proxy"],
            )
        if self.dist and self.dist.os_version in [
            "rhel4",
            "rhel5",
            "rhel6",
            "fedora16",
        ]:
            self.append_line += f" ks={self.data['autoinstall']}"
            if self.data["autoinstall_meta"].get("tree"):
                self.append_line += f" repo={self.data['autoinstall_meta']['tree']}"
        else:
            self.append_line += f" inst.ks={self.data['autoinstall']}"
            if self.data["autoinstall_meta"].get("tree"):
                self.append_line += (
                    f" inst.repo={self.data['autoinstall_meta']['tree']}"
                )

    def _generate_append_debian(self, system):
        """
        Generate additional content for the append line in case that dist is Ubuntu or Debian.
        :param system: The system which the append line should be generated for.
        """
        self.append_line += (
            " auto-install/enable=true url=%s netcfg/disable_autoconfig=true"
            % self.data["autoinstall"]
        )
        if self.data.get("proxy", "") != "":
            self.append_line += " mirror/http/proxy=%s" % self.data["proxy"]
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
        self.append_line += " hostname=%s domain=%s" % (my_hostname, my_domain)
        # A similar issue exists with suite name, as installer requires the existence of "stable" in the dists
        # directory
        self.append_line += " suite=%s" % self.dist.os_version

    def _generate_append_suse(self):
        """
        Special adjustments for generating the append line for suse.
        :return: The updated append line. If the distribution is not SUSE, then nothing is changed.
        """
        if self.data.get("proxy", "") != "":
            self.append_line += " proxy=%s" % self.data["proxy"]
        if self.data["kernel_options"].get("install", "") != "":
            self.append_line += " install=%s" % self.data["kernel_options"]["install"]
            del self.data["kernel_options"]["install"]
        else:
            self.append_line += " install=http://%s:%s/cblr/links/%s" % (
                self.data["server"],
                self.data["http_port"],
                self.dist.name,
            )
        if self.data["kernel_options"].get("autoyast", "") != "":
            self.append_line += " autoyast=%s" % self.data["kernel_options"]["autoyast"]
            del self.data["kernel_options"]["autoyast"]
        else:
            self.append_line += " autoyast=%s" % self.data["autoinstall"]

    def _adjust_interface_config(self):
        """
        If no kernel_options overrides are present find the management interface do nothing when zero or multiple
        management interfaces are found.
        """
        if self.system_interface is None:
            mgmt_ints = []
            mgmt_ints_multi = []
            slave_ints = []
            for iname, idata in self.data["interfaces"].items():
                if idata["management"] and idata["interface_type"] in [
                    "bond",
                    "bridge",
                ]:
                    # bonded/bridged management interface
                    mgmt_ints_multi.append(iname)
                if idata["management"] and idata["interface_type"] not in [
                    "bond",
                    "bridge",
                    "bond_slave",
                    "bridge_slave",
                    "bonded_bridge_slave",
                ]:
                    # single management interface
                    mgmt_ints.append(iname)

            if len(mgmt_ints_multi) == 1 and len(mgmt_ints) == 0:
                # Bonded/bridged management interface, find a slave interface if eth0 is a slave use that (it's what
                # people expect)
                for iname, idata in self.data["interfaces"].items():
                    if (
                        idata["interface_type"]
                        in ["bond_slave", "bridge_slave", "bonded_bridge_slave"]
                        and idata["interface_master"] == mgmt_ints_multi[0]
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

    def _get_tcp_ip_config(self):
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
            if self.data.get("name_servers") != "":
                self.system_dns = self.data["name_servers"]

    def generate_system(self, dist, system, exclude_dns: bool) -> str:
        """
        Generate the append line for a netbooting system.
        :param dist: The distribution associated with the system.
        :param system: The system itself
        :param exclude_dns: Whether to include the DNS config or not.
        """
        self.dist = dist

        self.append_line = f"  APPEND initrd=/{self.distro_name}.img"
        if self.dist.breed == "suse":
            self._generate_append_suse()
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
        self.append_line += buildiso.add_remaining_kopts(self.data["kernel_options"])
        return self.append_line

    def generate_profile(self, distro_breed: str) -> str:
        """
        Generate the append line for the kernel for a network installation.
        :param distro_breed: The name of the distribution breed.
        :return: The generated append line.
        """
        self.append_line = f"  APPEND initrd=/{self.distro_name}.img"
        if distro_breed == "suse":
            if self.data.get("proxy", "") != "":
                self.append_line += " proxy=%s" % self.data["proxy"]
            if self.data["kernel_options"].get("install", "") != "":
                install_options = self.data["kernel_options"]["install"]
                if isinstance(install_options, list):
                    install_options = install_options[0]
                    self.append_line += " install=%s" % install_options
                del self.data["kernel_options"]["install"]
            else:
                self.append_line += " install=http://%s:%s/cblr/links/%s" % (
                    self.data["server"],
                    self.data["http_port"],
                    self.distro_name,
                )
            if self.data["kernel_options"].get("autoyast", "") != "":
                self.append_line += (
                    " autoyast=%s" % self.data["kernel_options"]["autoyast"]
                )
                del self.data["kernel_options"]["autoyast"]
            else:
                self.append_line += " autoyast=%s" % self.data["autoinstall"]
        elif distro_breed == "redhat":
            if self.data.get("proxy", "") != "":
                self.append_line += " proxy=%s http_proxy=%s" % (
                    self.data["proxy"],
                    self.data["proxy"],
                )
            if self.dist.os_version in ["rhel4", "rhel5", "rhel6", "fedora16"]:
                self.append_line += f" ks={self.data['autoinstall']}"
                if self.data["autoinstall_meta"].get("tree"):
                    self.append_line += f" repo={self.data['autoinstall_meta']['tree']}"
            else:
                self.append_line += f" inst.ks={self.data['autoinstall']}"
                if self.data["autoinstall_meta"].get("tree"):
                    self.append_line += (
                        f" inst.repo={self.data['autoinstall_meta']['tree']}"
                    )
        elif distro_breed in ["ubuntu", "debian"]:
            self.append_line += (
                " auto-install/enable=true url=%s" % self.data["autoinstall"]
            )
            if self.data.get("proxy", "") != "":
                self.append_line += " mirror/http/proxy=%s" % self.data["proxy"]
        self.append_line += buildiso.add_remaining_kopts(self.data["kernel_options"])
        return self.append_line


class NetbootBuildiso(buildiso.BuildIso):
    """
    This class contains all functionality related to building network installation images.
    """

    def filter_systems(self, selected_items: List[str] = None) -> list:
        """
        Return a list of valid system objects selected from all systems by name, or everything if ``selected_items`` is
        empty.

        :param selected_items: A list of names to include in the returned list.
        :return: A list of valid systems. If an error occurred this is logged and an empty list is returned.
        """
        if selected_items is None:
            selected_items = []
        found_systems = self.filter_items(self.api.systems(), selected_items)
        # Now filter all systems out that are image based as we don't know about their kernel and initrds
        return_systems = []
        for system in found_systems:
            # All systems not underneath a profile should be skipped
            if system.get_conceptual_parent().TYPE_NAME == "profile":
                return_systems.append(system)
        # Now finally return
        return return_systems

    def make_shorter(self, distname: str) -> str:
        """
        Return a short distro identifier which is basically an internal counter which is mapped via the real distro
        name.

        :param distname: The distro name to return an identifier for.
        :return: A short distro identifier
        """
        if distname in self.distmap:
            return self.distmap[distname]

        self.distctr += 1
        self.distmap[distname] = str(self.distctr)
        return str(self.distctr)

    def _generate_boot_loader_configs(
        self, profile_names: List[str], system_names: List[str], exclude_dns: bool
    ) -> LoaderCfgsParts:
        """Generate boot loader configuration.

        The configuration is placed as parts into a list. The elements expect to
        be joined by newlines for writing.

        :param profile_names: Profile filter, can be an empty list for "all profiles".
        :param system_names: System filter, can be an empty list for "all systems".
        :param exclude_dns: Used for system kernel cmdline.
        """
        loader_config_parts = LoaderCfgsParts([self.iso_template], [], [])
        loader_config_parts.isolinux.append("MENU SEPARATOR")
        self._generate_profiles_loader_configs(profile_names, loader_config_parts)
        self._generate_systems_loader_configs(
            system_names, exclude_dns, loader_config_parts
        )
        return loader_config_parts

    def _generate_profiles_loader_configs(
        self, profiles: List[str], loader_cfg_parts: LoaderCfgsParts
    ) -> None:
        """Generate isolinux configuration for profiles.

        The passed in isolinux_cfg_parts list is changed in-place.

        :param profiles: Profile filter, can be empty for "all profiles".
        :param isolinux_cfg_parts: Output parameter for isolinux configuration.
        :param bootfiles_copyset: Output parameter for bootfiles copyset.
        """
        for profile in self.filter_profiles(profiles):
            isolinux, grub, to_copy = self._generate_profile_config(profile)
            loader_cfg_parts.isolinux.append(isolinux)
            loader_cfg_parts.grub.append(grub)
            loader_cfg_parts.bootfiles_copysets.append(to_copy)

    def _generate_profile_config(self, profile) -> Tuple[str, str, BootFilesCopyset]:
        """Generate isolinux configuration for a single profile.

        :param profile: Profile object to generate the configuration for.
        """
        distro = profile.get_conceptual_parent()
        distroname = self.make_shorter(distro.name)
        data = utils.blender(self.api, False, distro)
        if distro is not None:  # SUSE uses 'textmode' instead of 'text'
            utils.kopts_overwrite(
                data["kernel_options"], self.api.settings().server, distro.breed
            )

        if not re.match(r"[a-z]+://.*", data["autoinstall"]):
            data["autoinstall"] = "http://%s:%s/cblr/svc/op/autoinstall/profile/%s" % (
                data["server"],
                data["http_port"],
                profile.name,
            )

        append_line = AppendLineBuilder(
            distro_name=distroname, data=data
        ).generate_profile(distro.breed)
        kernel_path = f"/{distroname}.krn"
        initrd_path = f"/{distroname}.img"

        isolinux_cfg = self._render_isolinux_entry(
            append_line, menu_name=profile.name, kernel_path=kernel_path
        )
        grub_cfg = self._render_grub_entry(
            append_line,
            menu_name=profile.name,
            kernel_path=kernel_path,
            initrd_path=initrd_path,
        )
        return (
            isolinux_cfg,
            grub_cfg,
            BootFilesCopyset(distro.kernel, distro.initrd, distroname),
        )

    def _generate_systems_loader_configs(
        self,
        system_names: List[str],
        exclude_dns: bool,
        loader_cfg_parts: LoaderCfgsParts,
    ) -> None:
        """Generate isolinux configuration for systems.

        The passed in isolinux_cfg_parts list is changed in-place.

        :param systems: System filter, can be empty for "all profiles".
        :param isolinux_cfg_parts: Output parameter for isolinux configuration.
        :param bootfiles_copyset: Output parameter for bootfiles copyset.
        """
        for system in self.filter_systems(system_names):
            isolinux, grub, to_copy = self._generate_system_config(
                system, exclude_dns=exclude_dns
            )
            loader_cfg_parts.isolinux.append(isolinux)
            loader_cfg_parts.grub.append(grub)
            loader_cfg_parts.bootfiles_copysets.append(to_copy)

    def _generate_system_config(
        self, system, exclude_dns
    ) -> Tuple[str, str, BootFilesCopyset]:
        """Generate isolinux configuration for a single system.

        :param system: System object to generate the configuration for.
        :exclude_dns: Control if DNS configuration is part of the kernel cmdline.
        """
        profile = system.get_conceptual_parent()
        distro = (
            profile.get_conceptual_parent()
        )  # FIXME: pass distro, it's known from CLI
        distroname = self.make_shorter(distro.name)

        data = utils.blender(self.api, False, system)
        if not re.match(r"[a-z]+://.*", data["autoinstall"]):
            data["autoinstall"] = (
                f"http://{data['server']}:{data['http_port']}/cblr/svc/op/autoinstall/"
                f"system/{system.name}"
            )

        append_line = AppendLineBuilder(
            distro_name=distroname, data=data
        ).generate_system(distro, system, exclude_dns)
        kernel_path = f"/{distroname}.krn"
        initrd_path = f"/{distroname}.img"

        isolinux_cfg = self._render_isolinux_entry(
            append_line, menu_name=system.name, kernel_path=kernel_path
        )
        grub_cfg = self._render_grub_entry(
            append_line,
            menu_name=system.name,
            kernel_path=kernel_path,
            initrd_path=initrd_path,
        )

        return (
            isolinux_cfg,
            grub_cfg,
            BootFilesCopyset(distro.kernel, distro.initrd, distroname),
        )

    def _copy_esp(self, esp_source: str, buildisodir: str):
        """Copy existing EFI System Partition into the buildisodir."""
        utils.copyfile(esp_source, buildisodir + "/efi")


    def run(
        self,
        iso: str = "autoinst.iso",
        buildisodir: str = "",
        profiles: List[str] = None,
        xorrisofs_opts: str = "",
        distro_name: str = "",
        systems: List[str] = None,
        exclude_dns: bool = False,
        **kwargs,
    ):
        """
        Generate a net-installer for a distribution.

        By default, the ISO includes all available systems and profiles. Specify
        ``profiles`` and ``systems`` to only include the selected systems and
        profiles. Both parameters can be provided at the same time.

        :param iso: The name of the iso. Defaults to "autoinst.iso".
        :param buildisodir: This overwrites the directory from the settings in which the iso is built in.
        :param profiles: The filter to generate the ISO only for selected profiles.
        :param xorrisofs_opts: ``xorrisofs`` options to include additionally.
        :param distro_name: For detecting the architecture of the ISO.
        :param systems: Don't use that when building standalone ISOs. The filter to generate the ISO only for selected
                        systems.
        :param exclude_dns: Whether the repositories have to be locally available or the internet is reachable.
        """
        del kwargs  # just accepted for polymorphism

        distro_obj = self.parse_distro(distro_name)
        system_names = utils.input_string_or_list_no_inherit(systems)
        profile_names = utils.input_string_or_list_no_inherit(profiles)
        loader_config_parts = self._generate_boot_loader_configs(
            system_names, profile_names, exclude_dns
        )

        buildisodir = self._prepare_buildisodir(buildisodir)
        buildiso_dirs = self.create_buildiso_dirs(buildisodir)
        distro_mirrordir = pathlib.Path(self.api.settings().webdir) / "distro_mirror"

        # fill temporary directory with binaries
        self._copy_isolinux_files()
        for copyset in loader_config_parts.bootfiles_copysets:
            self._copy_boot_files(
                copyset.src_kernel,
                copyset.src_initrd,
                str(buildiso_dirs.root),
                copyset.new_filename,
            )

        try:
            filesource = self._find_distro_source(
                distro_obj.kernel, str(distro_mirrordir)
            )
            self.logger.info("filesource=%s", filesource)
            distro_esp = self._find_esp(pathlib.Path(filesource))
            self.logger.info("esp=%s", distro_esp)
        except ValueError:
            distro_esp = None

        if distro_esp is not None:
            self._copy_esp(distro_esp, buildisodir)
        else:
            esp_location = self._create_esp_image_file(buildisodir)
            self._copy_grub_into_esp(esp_location, distro_obj.arch)

        self._write_isolinux_cfg(loader_config_parts.isolinux, buildiso_dirs.isolinux)
        self._write_grub_cfg(loader_config_parts.grub, buildiso_dirs.grub)
        self._generate_iso(xorrisofs_opts, iso, buildisodir, buildisodir + "/efi")
