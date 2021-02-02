"""
Builds bootable CD images that have PXE-equivalent behavior
for all Cobbler distros/profiles/systems currently in memory.

Copyright 2006-2009, Red Hat, Inc and Others
Michael DeHaan <michael.dehaan AT gmail>

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


import os
import os.path
import re
import shutil
from typing import Optional

from cobbler import clogger
from cobbler import utils


class BuildIso:
    """
    Handles conversion of internal state to the isolinux tree layout
    """
    def __init__(self, collection_mgr, verbose: bool = False, logger=None):
        """
        Constructor
        """
        self.verbose = verbose
        self.collection_mgr = collection_mgr
        self.settings = collection_mgr.settings()
        self.api = collection_mgr.api
        self.distros = collection_mgr.distros()
        self.profiles = collection_mgr.profiles()
        self.systems = collection_mgr.systems()
        self.distros = collection_mgr.distros()
        self.distmap = {}
        self.distctr = 0
        self.source = ""
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger
        # grab the header from buildiso.header file
        header_src = open(os.path.join(self.settings.iso_template_dir, "buildiso.template"))
        self.iso_template = header_src.read()
        header_src.close()

    def add_remaining_kopts(self, koptdict: dict) -> str:
        """
        Add remaining kernel_options to append_line

        :param koptdict: The kernel options which are not present in append_line.
        :return: A single line with all kernel options
        """
        append_line = ""
        for (k, v) in list(koptdict.items()):
            if v is None:
                append_line += " %s" % k
            else:
                if isinstance(v, list):
                    for i in v:
                        _i = str(i).strip()
                        if ' ' in _i:
                            append_line += " %s='%s'" % (k, _i)
                        else:
                            append_line += " %s=%s" % (k, _i)
                else:
                    _v = str(v).strip()
                    if ' ' in _v:
                        append_line += " %s='%s'" % (k, _v)
                    else:
                        append_line += " %s=%s" % (k, _v)
        append_line += "\n"
        return append_line

    def make_shorter(self, distname: str) -> str:
        """
        Return A short distro identifier.

        :param distname: The distro name to return a identifier for.
        :return: A short distro identifier
        """
        if distname in self.distmap:
            return self.distmap[distname]
        else:
            self.distctr += 1
            self.distmap[distname] = str(self.distctr)
            return str(self.distctr)

    def copy_boot_files(self, distro, destdir, prefix: Optional[str] = None):
        """
        Copy kernel/initrd to destdir with (optional) newfile prefix

        :param distro: Distro object to return the boot files for.
        :param destdir: The destionation direcotry.
        :param prefix: The file prefix.
        """
        if not os.path.exists(distro.kernel):
            utils.die(self.logger, "path does not exist: %s" % distro.kernel)
        if not os.path.exists(distro.initrd):
            utils.die(self.logger, "path does not exist: %s" % distro.initrd)
        if prefix is None:
            shutil.copyfile(distro.kernel, os.path.join(destdir, "%s" % os.path.basename(distro.kernel)))
            shutil.copyfile(distro.initrd, os.path.join(destdir, "%s" % os.path.basename(distro.initrd)))
        else:
            shutil.copyfile(distro.kernel, os.path.join(destdir, "%s.krn" % prefix))
            shutil.copyfile(distro.initrd, os.path.join(destdir, "%s.img" % prefix))

    def filter_systems_or_profiles(self, selected_items, list_type: str) -> list:
        """
        Return a list of valid profile or system objects selected from all profiles or systems by name, or everything if
        selected_items is empty.

        :param selected_items: The filter to match certain objects with. The filter will be applied to the object name.
        :param list_type: Must be "profile" or "system".
        :return: A list of valid profiles OR systems.
        """
        if list_type == 'profile':
            all_objs = [profile for profile in self.api.profiles()]
        elif list_type == 'system':
            all_objs = [system for system in self.api.systems()]
        else:
            utils.die(self.logger, "Invalid list_type argument: " + list_type)

        all_objs.sort(key=lambda profile: profile.name)

        # no profiles/systems selection is made, let's process everything
        if not selected_items:
            return all_objs

        which_objs = []
        selected_list = utils.input_string_or_list(selected_items)
        for obj in all_objs:
            if obj.name in selected_list:
                which_objs.append(obj)
                selected_list.remove(obj.name)

        for bad_name in selected_list:
            self.logger.warning("WARNING: %s is not a valid %s" % (bad_name, list_type))

        if not which_objs:
            utils.die(self.logger, "No valid systems or profiles were specified.")

        return which_objs

    def generate_netboot_iso(self, imagesdir, isolinuxdir, profiles=None, systems=None,
                             exclude_dns: Optional[bool] = None):
        """
        Create bootable CD image to be used for network installations

        :param imagesdir: Currently unused parameter.
        :param isolinuxdir: The parent directory where the isolinux.cfg is located.
        :param profiles: The filter to generate a netboot iso for. You may specify multiple profiles on the CLI space
                        separated.
        :param systems: The filter to generate a netboot iso for. You may specify multiple systems on the CLI space
                        separated.
        :param exclude_dns: If this is True then the dns server is skipped. None or False will set it.
        """
        which_profiles = self.filter_systems_or_profiles(profiles, 'profile')
        which_systems = self.filter_systems_or_profiles(systems, 'system')

        # setup isolinux.cfg
        isolinuxcfg = os.path.join(isolinuxdir, "isolinux.cfg")
        cfg = open(isolinuxcfg, "w+")
        cfg.write(self.iso_template)

        # iterate through selected profiles
        for profile in which_profiles:
            self.logger.info("processing profile: %s" % profile.name)
            dist = profile.get_conceptual_parent()
            distname = self.make_shorter(dist.name)
            self.copy_boot_files(dist, isolinuxdir, distname)

            cfg.write("\n")
            cfg.write("LABEL %s\n" % profile.name)
            cfg.write("  MENU LABEL %s\n" % profile.name)
            cfg.write("  kernel %s.krn\n" % distname)

            data = utils.blender(self.api, False, profile)

            # SUSE is not using 'text'. Instead 'textmode' is used as kernel option.
            utils.kopts_overwrite(None, dist, data['kernel_options'], self.api.settings())

            if not re.match(r"[a-z]+://.*", data["autoinstall"]):
                data["autoinstall"] = "http://%s:%s/cblr/svc/op/autoinstall/profile/%s" % (
                    data["server"], self.api.settings().http_port, profile.name
                )

            append_line = " append initrd=%s.img" % distname
            if dist.breed == "suse":
                if "proxy" in data and data["proxy"] != "":
                    append_line += " proxy=%s" % data["proxy"]
                if "install" in data["kernel_options"] and data["kernel_options"]["install"] != "":
                    v = data["kernel_options"]["install"]
                    if isinstance(v, list):
                        v = v[0]
                        append_line += " install=%s" % v
                    del data["kernel_options"]["install"]
                else:
                    append_line += " install=http://%s:%s/cblr/links/%s" % (
                        data["server"], self.api.settings().http_port, dist.name
                    )
                if "autoyast" in data["kernel_options"] and data["kernel_options"]["autoyast"] != "":
                    append_line += " autoyast=%s" % data["kernel_options"]["autoyast"]
                    del data["kernel_options"]["autoyast"]
                else:
                    append_line += " autoyast=%s" % data["autoinstall"]

            if dist.breed == "redhat":
                if "proxy" in data and data["proxy"] != "":
                    append_line += " proxy=%s http_proxy=%s" % (data["proxy"], data["proxy"])
                append_line += " inst.ks=%s" % data["autoinstall"]

            if dist.breed in ["ubuntu", "debian"]:
                append_line += " auto-install/enable=true url=%s" % data["autoinstall"]
                if "proxy" in data and data["proxy"] != "":
                    append_line += " mirror/http/proxy=%s" % data["proxy"]
            append_line += self.add_remaining_kopts(data["kernel_options"])
            cfg.write(append_line)

        cfg.write("\nMENU SEPARATOR\n")

        # iterate through all selected systems
        for system in which_systems:
            self.logger.info("processing system: %s" % system.name)
            profile = system.get_conceptual_parent()
            dist = profile.get_conceptual_parent()
            distname = self.make_shorter(dist.name)
            self.copy_boot_files(dist, isolinuxdir, distname)

            cfg.write("\n")
            cfg.write("LABEL %s\n" % system.name)
            cfg.write("  MENU LABEL %s\n" % system.name)
            cfg.write("  kernel %s.krn\n" % distname)

            data = utils.blender(self.api, False, system)
            if not re.match(r"[a-z]+://.*", data["autoinstall"]):
                data["autoinstall"] = "http://%s:%s/cblr/svc/op/autoinstall/system/%s" % (
                    data["server"], self.api.settings().http_port, system.name
                )

            append_line = " append initrd=%s.img" % distname
            if dist.breed == "suse":
                if "proxy" in data and data["proxy"] != "":
                    append_line += " proxy=%s" % data["proxy"]
                if "install" in data["kernel_options"] and data["kernel_options"]["install"] != "":
                    append_line += " install=%s" % data["kernel_options"]["install"]
                    del data["kernel_options"]["install"]
                else:
                    append_line += " install=http://%s:%s/cblr/links/%s" % (
                        data["server"], self.api.settings().http_port, dist.name
                    )
                if "autoyast" in data["kernel_options"] and data["kernel_options"]["autoyast"] != "":
                    append_line += " autoyast=%s" % data["kernel_options"]["autoyast"]
                    del data["kernel_options"]["autoyast"]
                else:
                    append_line += " autoyast=%s" % data["autoinstall"]

            if dist.breed == "redhat":
                if "proxy" in data and data["proxy"] != "":
                    append_line += " proxy=%s http_proxy=%s" % (data["proxy"], data["proxy"])
                append_line += " inst.ks=%s" % data["autoinstall"]

            if dist.breed in ["ubuntu", "debian"]:
                append_line += " auto-install/enable=true url=%s netcfg/disable_autoconfig=true" % data["autoinstall"]
                if "proxy" in data and data["proxy"] != "":
                    append_line += " mirror/http/proxy=%s" % data["proxy"]
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
                append_line += " hostname=%s domain=%s" % (my_hostname, my_domain)
                # A similar issue exists with suite name, as installer requires the existence of "stable" in the dists
                # directory
                append_line += " suite=%s" % dist.os_version

            # Try to add static ip boot options to avoid DHCP (interface/ip/netmask/gw/dns)
            # Check for overrides first and clear them from kernel_options
            my_int = None
            my_ip = None
            my_mask = None
            my_gw = None
            my_dns = None
            if dist.breed in ["suse", "redhat"]:
                if "netmask" in data["kernel_options"] and data["kernel_options"]["netmask"] != "":
                    my_mask = data["kernel_options"]["netmask"]
                    del data["kernel_options"]["netmask"]
                if "gateway" in data["kernel_options"] and data["kernel_options"]["gateway"] != "":
                    my_gw = data["kernel_options"]["gateway"]
                    del data["kernel_options"]["gateway"]

            if dist.breed == "redhat":
                if "ksdevice" in data["kernel_options"] and data["kernel_options"]["ksdevice"] != "":
                    my_int = data["kernel_options"]["ksdevice"]
                    if my_int == "bootif":
                        my_int = None
                    del data["kernel_options"]["ksdevice"]
                if "ip" in data["kernel_options"] and data["kernel_options"]["ip"] != "":
                    my_ip = data["kernel_options"]["ip"]
                    del data["kernel_options"]["ip"]
                if "dns" in data["kernel_options"] and data["kernel_options"]["dns"] != "":
                    my_dns = data["kernel_options"]["dns"]
                    del data["kernel_options"]["dns"]

            if dist.breed == "suse":
                if "netdevice" in data["kernel_options"] and data["kernel_options"]["netdevice"] != "":
                    my_int = data["kernel_options"]["netdevice"]
                    del data["kernel_options"]["netdevice"]
                if "hostip" in data["kernel_options"] and data["kernel_options"]["hostip"] != "":
                    my_ip = data["kernel_options"]["hostip"]
                    del data["kernel_options"]["hostip"]
                if "nameserver" in data["kernel_options"] and data["kernel_options"]["nameserver"] != "":
                    my_dns = data["kernel_options"]["nameserver"]
                    del data["kernel_options"]["nameserver"]

            if dist.breed in ["ubuntu", "debian"]:
                if "netcfg/choose_interface" in data["kernel_options"] and data["kernel_options"]["netcfg/choose_interface"] != "":
                    my_int = data["kernel_options"]["netcfg/choose_interface"]
                    del data["kernel_options"]["netcfg/choose_interface"]
                if "netcfg/get_ipaddress" in data["kernel_options"] and data["kernel_options"]["netcfg/get_ipaddress"] != "":
                    my_ip = data["kernel_options"]["netcfg/get_ipaddress"]
                    del data["kernel_options"]["netcfg/get_ipaddress"]
                if "netcfg/get_netmask" in data["kernel_options"] and data["kernel_options"]["netcfg/get_netmask"] != "":
                    my_mask = data["kernel_options"]["netcfg/get_netmask"]
                    del data["kernel_options"]["netcfg/get_netmask"]
                if "netcfg/get_gateway" in data["kernel_options"] and data["kernel_options"]["netcfg/get_gateway"] != "":
                    my_gw = data["kernel_options"]["netcfg/get_gateway"]
                    del data["kernel_options"]["netcfg/get_gateway"]
                if "netcfg/get_nameservers" in data["kernel_options"] and data["kernel_options"]["netcfg/get_nameservers"] != "":
                    my_dns = data["kernel_options"]["netcfg/get_nameservers"]
                    del data["kernel_options"]["netcfg/get_nameservers"]

            # If no kernel_options overrides are present find the management interface do nothing when zero or multiple
            # management interfaces are found
            if my_int is None:
                mgmt_ints = []
                mgmt_ints_multi = []
                slave_ints = []
                if len(list(data["interfaces"].keys())) >= 1:
                    for (iname, idata) in list(data["interfaces"].items()):
                        if idata["management"] and idata["interface_type"] in ["bond", "bridge"]:
                            # bonded/bridged management interface
                            mgmt_ints_multi.append(iname)
                        if idata["management"] and idata["interface_type"] not in ["bond", "bridge", "bond_slave", "bridge_slave", "bonded_bridge_slave"]:
                            # single management interface
                            mgmt_ints.append(iname)

                if len(mgmt_ints_multi) == 1 and len(mgmt_ints) == 0:
                    # Bonded/bridged management interface, find a slave interface if eth0 is a slave use that (it's what
                    # people expect)
                    for (iname, idata) in list(data["interfaces"].items()):
                        if idata["interface_type"] in ["bond_slave", "bridge_slave", "bonded_bridge_slave"] and idata["interface_master"] == mgmt_ints_multi[0]:
                            slave_ints.append(iname)

                    if "eth0" in slave_ints:
                        my_int = "eth0"
                    else:
                        my_int = slave_ints[0]
                    # Set my_ip from the bonded/bridged interface here
                    my_ip = data["ip_address_" + data["interface_master_" + my_int]]
                    my_mask = data["netmask_" + data["interface_master_" + my_int]]

                if len(mgmt_ints) == 1 and len(mgmt_ints_multi) == 0:
                    # Single management interface
                    my_int = mgmt_ints[0]

            # Lookup tcp/ip configuration data
            if my_ip is None and my_int is not None:
                intip = "ip_address_" + my_int
                if intip in data and data[intip] != "":
                    my_ip = data["ip_address_" + my_int]

            if my_mask is None and my_int is not None:
                intmask = "netmask_" + my_int
                if intmask in data and data[intmask] != "":
                    my_mask = data["netmask_" + my_int]

            if my_gw is None:
                if "gateway" in data and data["gateway"] != "":
                    my_gw = data["gateway"]

            if my_dns is None:
                if "name_servers" in data and data["name_servers"] != "":
                    my_dns = data["name_servers"]

            # Add information to the append_line
            if my_int is not None:
                intmac = "mac_address_" + my_int
                if dist.breed == "suse":
                    if intmac in data and data[intmac] != "":
                        append_line += " netdevice=%s" % data["mac_address_" + my_int].lower()
                    else:
                        append_line += " netdevice=%s" % my_int
                if dist.breed == "redhat":
                    if intmac in data and data[intmac] != "":
                        append_line += " ksdevice=%s" % data["mac_address_" + my_int]
                    else:
                        append_line += " ksdevice=%s" % my_int
                if dist.breed in ["ubuntu", "debian"]:
                    append_line += " netcfg/choose_interface=%s" % my_int

            if my_ip is not None:
                if dist.breed == "suse":
                    append_line += " hostip=%s" % my_ip
                if dist.breed == "redhat":
                    append_line += " ip=%s" % my_ip
                if dist.breed in ["ubuntu", "debian"]:
                    append_line += " netcfg/get_ipaddress=%s" % my_ip

            if my_mask is not None:
                if dist.breed in ["suse", "redhat"]:
                    append_line += " netmask=%s" % my_mask
                if dist.breed in ["ubuntu", "debian"]:
                    append_line += " netcfg/get_netmask=%s" % my_mask

            if my_gw is not None:
                if dist.breed in ["suse", "redhat"]:
                    append_line += " gateway=%s" % my_gw
                if dist.breed in ["ubuntu", "debian"]:
                    append_line += " netcfg/get_gateway=%s" % my_gw

            if exclude_dns is None or my_dns is not None:
                if dist.breed == "suse":
                    if type(my_dns) == list:
                        append_line += " nameserver=%s" % ",".join(my_dns)
                    else:
                        append_line += " nameserver=%s" % my_dns
                if dist.breed == "redhat":
                    if type(my_dns) == list:
                        append_line += " dns=%s" % ",".join(my_dns)
                    else:
                        append_line += " dns=%s" % my_dns
                if dist.breed in ["ubuntu", "debian"]:
                    if type(my_dns) == list:
                        append_line += " netcfg/get_nameservers=%s" % ",".join(my_dns)
                    else:
                        append_line += " netcfg/get_nameservers=%s" % my_dns

            # Add remaining kernel_options to append_line
            append_line += self.add_remaining_kopts(data["kernel_options"])
            cfg.write(append_line)

        cfg.write("\n")
        cfg.write("MENU END\n")
        cfg.close()

    def generate_standalone_iso(self, imagesdir, isolinuxdir, distname, filesource, airgapped: bool, profiles):
        """
        Create bootable CD image to be used for handsoff CD installtions

        :param imagesdir: Unused Parameter.
        :param isolinuxdir: The parent directory where the file isolinux.cfg is located at.
        :param distname: The name of the Cobbler distribution.
        :param filesource: Not clear what this exactly does
        :param airgapped: Whether the repositories have to be locally available or the internet is reachable.
        :param profiles: The list of profiles to include.
        """
        # Get the distro object for the requested distro and then get all of its descendants (profiles/sub-profiles/
        # systems) with sort=True for profile/system heirarchy to allow menu indenting
        distro = self.api.find_distro(distname)
        if distro is None:
            utils.die(self.logger, "distro %s was not found, aborting" % distname)
        descendants = distro.get_descendants(sort=True)
        profiles = utils.input_string_or_list(profiles)

        if filesource is None:
            # Try to determine the source from the distro kernel path
            self.logger.debug("trying to locate source for distro")
            found_source = False
            (source_head, source_tail) = os.path.split(distro.kernel)
            while source_tail != '':
                if source_head == os.path.join(self.api.settings().webdir, "distro_mirror"):
                    filesource = os.path.join(source_head, source_tail)
                    found_source = True
                    self.logger.debug("found source in %s" % filesource)
                    break
                (source_head, source_tail) = os.path.split(source_head)
            # Can't find the source, raise an error
            if not found_source:
                utils.die(self.logger, "Error, no installation source found. When building a standalone ISO, you must "
                                       "specify a --source if the distro install tree is not hosted locally")

        self.logger.info("copying kernels and initrds for standalone distro")
        self.copy_boot_files(distro, isolinuxdir, None)

        self.logger.info("generating an isolinux.cfg")
        isolinuxcfg = os.path.join(isolinuxdir, "isolinux.cfg")
        cfg = open(isolinuxcfg, "w+")
        cfg.write(self.iso_template)

        if airgapped:
            repo_names_to_copy = {}

        for descendant in descendants:
            # if a list of profiles was given, skip any others and their systems
            if profiles and ((descendant.COLLECTION_TYPE == 'profile' and descendant.name not in profiles)
                             or (descendant.COLLECTION_TYPE == 'system' and descendant.profile not in profiles)):
                continue

            menu_indent = 0
            if descendant.COLLECTION_TYPE == 'system':
                menu_indent = 4

            data = utils.blender(self.api, False, descendant)

            # SUSE is not using 'text'. Instead 'textmode' is used as kernel option.
            utils.kopts_overwrite(None, distro, data['kernel_options'], self.settings)

            cfg.write("\n")
            cfg.write("LABEL %s\n" % descendant.name)
            if menu_indent:
                cfg.write("  MENU INDENT %d\n" % menu_indent)
            cfg.write("  MENU LABEL %s\n" % descendant.name)
            cfg.write("  kernel %s\n" % os.path.basename(distro.kernel))

            append_line = "  append initrd=%s" % os.path.basename(distro.initrd)
            if distro.breed == "redhat":
                append_line += " inst.ks=cdrom:/isolinux/%s.cfg" % descendant.name
            if distro.breed == "suse":
                append_line += " autoyast=file:///isolinux/%s.cfg install=cdrom:///" % descendant.name
                if "install" in data["kernel_options"]:
                    del data["kernel_options"]["install"]
            if distro.breed in ["ubuntu", "debian"]:
                append_line += " auto-install/enable=true preseed/file=/cdrom/isolinux/%s.cfg" % descendant.name

            # add remaining kernel_options to append_line
            append_line += self.add_remaining_kopts(data["kernel_options"])
            cfg.write(append_line)

            if descendant.COLLECTION_TYPE == 'profile':
                autoinstall_data = self.api.autoinstallgen.generate_autoinstall_for_profile(descendant.name)
            elif descendant.COLLECTION_TYPE == 'system':
                autoinstall_data = self.api.autoinstallgen.generate_autoinstall_for_system(descendant.name)

            if distro.breed == "redhat":
                cdregex = re.compile(r"^\s*url .*\n", re.IGNORECASE | re.MULTILINE)
                autoinstall_data = cdregex.sub("cdrom\n", autoinstall_data, count=1)

            if airgapped:
                descendant_repos = data['repos']
                for repo_name in descendant_repos:
                    repo_obj = self.api.find_repo(repo_name)
                    error_fmt = (descendant.COLLECTION_TYPE + " " + descendant.name + " refers to repo " + repo_name
                                 + ", which %%s; cannot build airgapped ISO")

                    if repo_obj is None:
                        utils.die(self.logger, error_fmt % "does not exist")
                    if not repo_obj.mirror_locally:
                        utils.die(self.logger, error_fmt % "is not configured for local mirroring")
                    # FIXME: don't hardcode
                    mirrordir = os.path.join(self.settings.webdir, "repo_mirror", repo_obj.name)
                    if not os.path.exists(mirrordir):
                        utils.die(self.logger, error_fmt % "has a missing local mirror directory")

                    repo_names_to_copy[repo_obj.name] = mirrordir

                    # update the baseurl in autoinstall_data to use the cdrom copy of this repo
                    reporegex = re.compile(r"^(\s*repo --name=" + repo_obj.name + " --baseurl=).*", re.MULTILINE)
                    autoinstall_data = reporegex.sub(r"\1" + "file:///mnt/source/repo_mirror/" + repo_obj.name,
                                                     autoinstall_data)

                # rewrite any split-tree repos, such as in redhat, to use cdrom
                srcreporegex = re.compile(r"^(\s*repo --name=\S+ --baseurl=).*/cobbler/distro_mirror/" + distro.name
                                          + r"/?(.*)", re.MULTILINE)
                autoinstall_data = srcreporegex.sub(r"\1" + "file:///mnt/source" + r"\2", autoinstall_data)

            autoinstall_name = os.path.join(isolinuxdir, "%s.cfg" % descendant.name)
            autoinstall_file = open(autoinstall_name, "w+")
            autoinstall_file.write(autoinstall_data)
            autoinstall_file.close()

        self.logger.info("done writing config")
        cfg.write("\n")
        cfg.write("MENU END\n")
        cfg.close()

        if airgapped:
            # copy any repos found in profiles or systems to the iso build
            repodir = os.path.abspath(os.path.join(isolinuxdir, "..", "repo_mirror"))
            if not os.path.exists(repodir):
                os.makedirs(repodir)

            for repo_name in repo_names_to_copy:
                src = repo_names_to_copy[repo_name]
                dst = os.path.join(repodir, repo_name)
                self.logger.info(" - copying repo '" + repo_name + "' for airgapped ISO")

                ok = utils.rsync_files(src, dst, "--exclude=TRANS.TBL --exclude=cache/ --no-g",
                                       logger=self.logger, quiet=True)
                if not ok:
                    utils.die(self.logger, "rsync of repo '" + repo_name + "' failed")

        # copy distro files last, since they take the most time
        cmd = "rsync -rlptgu --exclude=boot.cat --exclude=TRANS.TBL --exclude=isolinux/ %s/ %s/../"\
              % (filesource, isolinuxdir)
        self.logger.info("- copying distro %s files (%s)" % (distname, cmd))
        rc = utils.subprocess_call(self.logger, cmd, shell=True)
        if rc:
            utils.die(self.logger, "rsync of distro files failed")

    def run(self, iso=None, buildisodir=None, profiles=None, systems=None, distro=None,
            standalone: Optional[bool] = None, airgapped: Optional[bool] = None, source=None,
            exclude_dns: Optional[bool] = None, xorrisofs_opts: Optional[str] = None):
        """
        A

        :param iso: The name of the iso. Defaults to "autoinst.iso".
        :param buildisodir: This overwrites the directory from the settings in which the iso is built in.
        :param profiles:
        :param systems: Don't use that when building standalone isos.
        :param distro: (For standalone only)
        :param standalone: This means that no network connection is needed to install the generated iso.
        :type standalone: bool
        :param airgapped: This option implies standalone=True.
        :type airgapped: bool
        :param source: If the iso should be offline available this is the path to the sources of the image.
        :param exclude_dns: Whether the repositories have to be locally available or the internet is reachable.
        :param xorrisofs_opts: xorrisofs options to include additionally.
        """

        if airgapped is True:
            standalone = True

        # the distro option is for stand-alone builds only
        if not standalone and distro is not None:
            utils.die(self.logger, "The --distro option should only be used when creating a standalone or airgapped ISO")
        # if building standalone, we only want --distro and --profiles (optional), systems are disallowed
        if standalone:
            if systems is not None:
                utils.die(self.logger, "When building a standalone ISO, use --distro and --profiles only, not --systems")
            elif distro is None:
                utils.die(self.logger, "When building a standalone ISO, you must specify a --distro")
            if source is not None and not os.path.exists(source):
                utils.die(self.logger, "The source specified (%s) does not exist" % source)

            # insure all profiles specified are children of the distro
            if profiles:
                which_profiles = self.filter_systems_or_profiles(profiles, 'profile')
                for profile in which_profiles:
                    if profile.distro != distro:
                        utils.die(self.logger, "When building a standalone ISO, all --profiles must be under --distro")

        # if iso is none, create it in . as "autoinst.iso"
        if iso is None:
            iso = "autoinst.iso"

        if buildisodir is None:
            buildisodir = self.settings.buildisodir
        else:
            if not os.path.isdir(buildisodir):
                utils.die(self.logger, "The --tempdir specified is not a directory")

            (buildisodir_head, buildisodir_tail) = os.path.split(os.path.normpath(buildisodir))
            if buildisodir_tail != "buildiso":
                buildisodir = os.path.join(buildisodir, "buildiso")

        self.logger.info("using/creating buildisodir: %s" % buildisodir)
        if not os.path.exists(buildisodir):
            os.makedirs(buildisodir)
        else:
            shutil.rmtree(buildisodir)
            os.makedirs(buildisodir)

        # if base of buildisodir does not exist, fail create all profiles unless filtered by "profiles"

        imagesdir = os.path.join(buildisodir, "images")
        isolinuxdir = os.path.join(buildisodir, "isolinux")

        self.logger.info("building tree for isolinux")
        if not os.path.exists(imagesdir):
            os.makedirs(imagesdir)
        if not os.path.exists(isolinuxdir):
            os.makedirs(isolinuxdir)

        self.logger.info("copying miscellaneous files")

        files_to_copy = ["isolinux.bin", "menu.c32", "chain.c32",
                         "ldlinux.c32", "libcom32.c32", "libutil.c32"]

        optional_files = ["ldlinux.c32", "libcom32.c32", "libutil.c32"]

        syslinux_folders = ["/usr/share/syslinux/",
                            "/usr/lib/syslinux/modules/bios/",
                            "/usr/lib/syslinux/",
                            "/usr/lib/ISOLINUX/"]

        # file_copy_success will be used to check for missing files
        file_copy_success = {f: False for f in files_to_copy if f not in optional_files}
        for syslinux_folder in syslinux_folders:
            if os.path.isdir(os.path.join(syslinux_folder)):
                for file_to_copy in files_to_copy:
                    source_file = os.path.join(syslinux_folder, file_to_copy)
                    if os.path.exists(source_file):
                        utils.copyfile(source_file, os.path.join(isolinuxdir, file_to_copy), self.api)
                        file_copy_success[file_to_copy] = True

        if False in file_copy_success.values():
            for k, v in file_copy_success:
                if not v:
                    self.logger.error("File not found: %s" % k)
            utils.die(self.logger, "Required file(s) not found. Please check your syslinux installation")

        if standalone or airgapped:
            self.generate_standalone_iso(imagesdir, isolinuxdir, distro, source, airgapped, profiles)
        else:
            self.generate_netboot_iso(imagesdir, isolinuxdir, profiles, systems, exclude_dns)

        if xorrisofs_opts is None:
            xorrisofs_opts = ""
        else:
            xorrisofs_opts = xorrisofs_opts.strip()

        # using xorrisofs instead of mkisofs nowadays, it is available everywhere...
        cmd = "xorrisofs -o %s %s -r -b isolinux/isolinux.bin -c isolinux/boot.cat" % (iso, xorrisofs_opts)
        cmd = cmd + " -no-emul-boot -boot-load-size 4"
        cmd = cmd + r" -boot-info-table -V Cobbler\ Install -R -J %s" % buildisodir

        rc = utils.subprocess_call(self.logger, cmd, shell=True)
        if rc != 0:
            utils.die(self.logger, "xorrisofs failed")

        self.logger.info("ISO build complete")
        self.logger.info("You may wish to delete: %s" % buildisodir)
        self.logger.info("The output file is: %s" % iso)

# EOF
