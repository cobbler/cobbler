"""
Cobbler Trigger Module that checks against a list of hardcoded potential common errors in a Cobbler installation.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import glob
import logging
import os
import re
from typing import TYPE_CHECKING, List
from xmlrpc.client import ServerProxy

from cobbler import utils
from cobbler.utils import process_management

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI


class CobblerCheck:
    """
    Validates whether the system is reasonably well configured for
    serving up content. This is the code behind 'cobbler check'.
    """

    def __init__(self, api: "CobblerAPI") -> None:
        """
        Constructor

        :param api: The API which holds all information.
        """
        self.api = api
        self.settings = api.settings()
        self.logger = logging.getLogger()
        self.checked_family = ""

    def run(self) -> List[str]:
        """
        The CLI usage is "cobbler check" before "cobbler sync".

        :return: None if there are no errors, otherwise returns a list of things to correct prior to running application
                 'for real'.
        """
        status: List[str] = []
        self.checked_family = utils.get_family()
        self.check_name(status)
        self.check_selinux(status)
        if self.settings.manage_dhcp:
            mode = self.api.get_sync().dhcp.what()
            if mode == "isc":
                self.check_dhcpd_bin(status)
                self.check_dhcpd_conf(status)
                self.check_service(status, "dhcpd")
            elif mode == "dnsmasq":
                self.check_dnsmasq_bin(status)
                self.check_service(status, "dnsmasq")

        if self.settings.manage_dns:
            mode = self.api.get_sync().dns.what()
            if mode == "bind":
                self.check_bind_bin(status)
                self.check_service(status, "named")
            elif mode == "dnsmasq" and not self.settings.manage_dhcp:
                self.check_dnsmasq_bin(status)
                self.check_service(status, "dnsmasq")

        mode = self.api.get_sync().tftpd.what()
        if mode == "in_tftpd":
            self.check_tftpd_dir(status)
        elif mode == "tftpd_py":
            self.check_ctftpd_dir(status)

        self.check_service(status, "cobblerd")

        self.check_bootloaders(status)
        self.check_for_wget_curl(status)
        self.check_rsync_conf(status)
        self.check_iptables(status)
        self.check_yum(status)
        self.check_debmirror(status)
        self.check_for_ksvalidator(status)
        self.check_for_default_password(status)
        self.check_for_unreferenced_repos(status)
        self.check_for_unsynced_repos(status)
        self.check_for_cman(status)

        return status

    def check_for_ksvalidator(self, status: List[str]) -> None:
        """
        Check if the ``ksvalidator`` is present in ``/usr/bin``.

        :param status: The status list with possible problems. The status list with possible problems.
        """
        # FIXME: This tools is cross-platform via Python. Thus all distros can have it.
        # ubuntu also identifies as "debian"
        if self.checked_family in ["debian", "suse"]:
            return

        if not os.path.exists("/usr/bin/ksvalidator"):
            status.append("ksvalidator was not found, install pykickstart")

    @staticmethod
    def check_for_cman(status: List[str]) -> None:
        """
        Check if the fence agents are available. This is done through checking if the binary ``fence_ilo`` is present
        in ``/sbin`` or ``/usr/sbin``.

        :param status: The status list with possible problems. The status list with possible problems.
        """
        # not doing rpm -q here to be cross-distro friendly
        if not os.path.exists("/sbin/fence_ilo") and not os.path.exists(
            "/usr/sbin/fence_ilo"
        ):
            status.append(
                "fencing tools were not found, and are required to use the (optional) power management "
                "features. install cman or fence-agents to use them"
            )

    def check_service(self, status: List[str], which: str, notes: str = "") -> None:
        """
        Check if the service command is available or the old init.d system has to be used.

        :param status: The status list with possible problems.
        :param which: The service to check for.
        :param notes: A manual not to attach.
        """
        if notes != "":
            notes = f" (NOTE: {notes})"
        return_code = 0
        if process_management.is_supervisord():
            with ServerProxy("http://localhost:9001/RPC2") as server:
                process_info = server.supervisor.getProcessInfo(which)
                if (
                    isinstance(process_info, dict)
                    and process_info["statename"] != "RUNNING"
                ):
                    status.append(f"service {which} is not running{notes}")
                    return
        elif process_management.is_systemd():
            return_code = utils.subprocess_call(
                ["systemctl", "status", which], shell=False
            )
            if return_code != 0:
                status.append(f'service "{which}" is not running{notes}')
                return
        elif self.checked_family in ("redhat", "suse"):
            if os.path.exists(f"/etc/rc.d/init.d/{which}"):
                return_code = utils.subprocess_call(
                    ["/sbin/service", which, "status"], shell=False
                )
            if return_code != 0:
                status.append(f"service {which} is not running{notes}")
                return
        elif self.checked_family == "debian":
            # we still use /etc/init.d
            if os.path.exists(f"/etc/init.d/{which}"):
                return_code = utils.subprocess_call(
                    [f"/etc/init.d/{which}", "status"], shell=False
                )
            if return_code != 0:
                status.append(f"service {which} is not running{notes}")
                return
        else:
            status.append(
                f"Unknown distribution type, cannot check for running service {which}"
            )
            return

    def check_iptables(self, status: List[str]) -> None:
        """
        Check if iptables is running. If yes print the needed ports. This is unavailable on Debian, SUSE and CentOS7 as
        a service. However this only indicates that the way of persisting the iptable rules are persisted via other
        means.

        :param status: The status list with possible problems.
        """
        # TODO: Rewrite check to be able to verify this is in more cases
        if os.path.exists("/etc/rc.d/init.d/iptables"):
            return_code = utils.subprocess_call(
                ["/sbin/service", "iptables", "status"], shell=False
            )
            if return_code == 0:
                status.append(
                    f"since iptables may be running, ensure 69, 80/443, and {self.settings.xmlrpc_port} are unblocked"
                )

    def check_yum(self, status: List[str]) -> None:
        """
        Check if the yum-stack is available. On Debian based distros this will always return without checking.

        :param status: The status list with possible problems.
        """
        # FIXME: Replace this with calls which check for the path of these tools.
        if self.checked_family == "debian":
            return

        if not os.path.exists("/usr/bin/createrepo"):
            status.append(
                "createrepo package is not installed, needed for cobbler import and cobbler reposync, "
                "install createrepo?"
            )

        if not os.path.exists("/usr/bin/dnf") and not os.path.exists(
            "/usr/bin/reposync"
        ):
            status.append("reposync not installed, install yum-utils")

        if os.path.exists("/usr/bin/dnf") and not os.path.exists("/usr/bin/reposync"):
            status.append(
                "reposync is not installed, install yum-utils or dnf-plugins-core"
            )

        if not os.path.exists("/usr/bin/dnf") and not os.path.exists(
            "/usr/bin/yumdownloader"
        ):
            status.append("yumdownloader is not installed, install yum-utils")

        if os.path.exists("/usr/bin/dnf") and not os.path.exists(
            "/usr/bin/yumdownloader"
        ):
            status.append(
                "yumdownloader is not installed, install yum-utils or dnf-plugins-core"
            )

    def check_debmirror(self, status: List[str]) -> None:
        """
        Check if debmirror is available and the config file for it exists. If the distro family is suse then this will
        pass without checking.

        :param status: The status list with possible problems.
        """
        if self.checked_family == "suse":
            return

        if not os.path.exists("/usr/bin/debmirror"):
            status.append(
                "debmirror package is not installed, it will be required to manage debian deployments and "
                "repositories"
            )
        if os.path.exists("/etc/debmirror.conf"):
            with open("/etc/debmirror.conf", encoding="UTF-8") as debmirror_fd:
                re_dists = re.compile(r"@dists=")
                re_arches = re.compile(r"@arches=")
                for line in debmirror_fd.readlines():
                    if re_dists.search(line) and not line.strip().startswith("#"):
                        status.append(
                            "comment out 'dists' on /etc/debmirror.conf for proper debian support"
                        )
                    if re_arches.search(line) and not line.strip().startswith("#"):
                        status.append(
                            "comment out 'arches' on /etc/debmirror.conf for proper debian support"
                        )

    def check_name(self, status: List[str]) -> None:
        """
        If the server name in the config file is still set to localhost automatic installations run from koan will not
        have proper kernel line parameters.

        :param status: The status list with possible problems.
        """
        if self.settings.server == "127.0.0.1":
            status.append(
                "The 'server' field in /etc/cobbler/settings.yaml must be set to something other than localhost, "
                "or automatic installation features will not work.  This should be a resolvable hostname or "
                "IP for the boot server as reachable by all machines that will use it."
            )
        if self.settings.next_server_v4 == "127.0.0.1":
            status.append(
                "For PXE to be functional, the 'next_server_v4' field in /etc/cobbler/settings.yaml must be set to "
                "something other than 127.0.0.1, and should match the IP of the boot server on the PXE "
                "network."
            )
        if self.settings.next_server_v6 == "::1":
            status.append(
                "For PXE to be functional, the 'next_server_v6' field in /etc/cobbler/settings.yaml must be set to "
                "something other than ::1, and should match the IP of the boot server on the PXE network."
            )

    def check_selinux(self, status: List[str]) -> None:
        """
        Suggests various SELinux rules changes to run Cobbler happily with SELinux in enforcing mode.

        :param status: The status list with possible problems.
        """
        # FIXME: this method could use some refactoring in the future.
        if self.checked_family == "debian":
            return

        enabled = self.api.is_selinux_enabled()
        if enabled:
            status.append(
                "SELinux is enabled. Please review the following wiki page for details on ensuring Cobbler "
                "works correctly in your SELinux environment:\n    "
                "https://cobbler.readthedocs.io/en/latest/user-guide/selinux.html"
            )

    def check_for_default_password(self, status: List[str]) -> None:
        """
        Check if the default password of Cobbler was changed.

        :param status: The status list with possible problems.
        """
        default_pass = self.settings.default_password_crypted
        if default_pass == "$1$mF86/UHC$WvcIcX2t6crBz2onWxyac.":
            status.append(
                "The default password used by the sample templates for newly installed machines ("
                "default_password_crypted in /etc/cobbler/settings.yaml) is still set to 'cobbler' and should be "
                "changed, try: \"openssl passwd -1 -salt 'random-phrase-here' 'your-password-here'\" to "
                "generate new one"
            )

    def check_for_unreferenced_repos(self, status: List[str]) -> None:
        """
        Check if there are repositories which are not used and thus could be removed.

        :param status: The status list with possible problems.
        """
        repos: List[str] = []
        referenced: List[str] = []
        not_found: List[str] = []
        for repo in self.api.repos():
            repos.append(repo.name)
        for profile in self.api.profiles():
            my_repos = profile.repos
            if my_repos != "<<inherit>>":
                referenced.extend(my_repos)
        for repo in referenced:
            if repo not in repos and repo != "<<inherit>>":
                not_found.append(repo)
        if len(not_found) > 0:
            status.append(
                "One or more repos referenced by profile objects is no longer defined in Cobbler:"
                f" {', '.join(not_found)}"
            )

    def check_for_unsynced_repos(self, status: List[str]) -> None:
        """
        Check if there are unsynchronized repositories which need an update.

        :param status: The status list with possible problems.
        """
        need_sync: List[str] = []
        for repo in self.api.repos():
            if repo.mirror_locally is True:
                lookfor = os.path.join(self.settings.webdir, "repo_mirror", repo.name)
                if not os.path.exists(lookfor):
                    need_sync.append(repo.name)
        if len(need_sync) > 0:
            status.append(
                "One or more repos need to be processed by cobbler reposync for the first time before "
                f"automating installations using them: {', '.join(need_sync)}"
            )

    @staticmethod
    def check_dhcpd_bin(status: List[str]) -> None:
        """
        Check if dhcpd is installed.

        :param status: The status list with possible problems.
        """
        if not os.path.exists("/usr/sbin/dhcpd"):
            status.append("dhcpd is not installed")

    @staticmethod
    def check_dnsmasq_bin(status: List[str]) -> None:
        """
        Check if dnsmasq is installed.

        :param status: The status list with possible problems.
        """
        return_code = utils.subprocess_call(["dnsmasq", "--help"], shell=False)
        if return_code != 0:
            status.append("dnsmasq is not installed and/or in path")

    @staticmethod
    def check_bind_bin(status: List[str]) -> None:
        """
        Check if bind is installed.

        :param status: The status list with possible problems.
        """
        return_code = utils.subprocess_call(["named", "-v"], shell=False)
        # it should return something like "BIND 9.6.1-P1-RedHat-9.6.1-6.P1.fc11"
        if return_code != 0:
            status.append("named is not installed and/or in path")

    @staticmethod
    def check_for_wget_curl(status: List[str]) -> None:
        """
        Check to make sure wget or curl is installed

        :param status: The status list with possible problems.
        """
        rc_wget = utils.subprocess_call(["wget", "--help"], shell=False)
        rc_curl = utils.subprocess_call(["curl", "--help"], shell=False)
        if rc_wget != 0 and rc_curl != 0:
            status.append(
                "Neither wget nor curl are installed and/or available in $PATH. Cobbler requires that one "
                "of these utilities be installed."
            )

    @staticmethod
    def check_bootloaders(status: List[str]) -> None:
        """
        Check if network bootloaders are installed

        :param status: The status list with possible problems.
        """
        # FIXME: move zpxe.rexx to loaders

        bootloaders = {
            "menu.c32": [
                "/usr/share/syslinux/menu.c32",
                "/usr/lib/syslinux/menu.c32",
                "/var/lib/cobbler/loaders/menu.c32",
            ],
            "pxelinux.0": [
                "/usr/share/syslinux/pxelinux.0",
                "/usr/lib/syslinux/pxelinux.0",
                "/var/lib/cobbler/loaders/pxelinux.0",
            ],
            "efi": [
                "/var/lib/cobbler/loaders/grub-x86.efi",
                "/var/lib/cobbler/loaders/grub-x86_64.efi",
            ],
        }

        # look for bootloaders at the glob locations above
        found_bootloaders: List[str] = []
        items = list(bootloaders.keys())
        for loader_name in items:
            patterns = bootloaders[loader_name]
            for pattern in patterns:
                matches = glob.glob(pattern)
                if len(matches) > 0:
                    found_bootloaders.append(loader_name)
        not_found: List[str] = []

        # invert the list of what we've found so we can report on what we haven't found
        for loader_name in items:
            if loader_name not in found_bootloaders:
                not_found.append(loader_name)

        if len(not_found) > 0:
            status.append(
                "some network boot-loaders are missing from /var/lib/cobbler/loaders. If you only want to "
                "handle x86/x86_64 netbooting, you may ensure that you have installed a *recent* version "
                "of the syslinux package installed and can ignore this message entirely. Files in this "
                "directory, should you want to support all architectures, should include pxelinux.0, and"
                "menu.c32."
            )

    def check_tftpd_dir(self, status: List[str]) -> None:
        """
        Check if cobbler.conf's tftpboot directory exists

        :param status: The status list with possible problems.
        """
        if self.checked_family == "debian":
            return

        bootloc = self.settings.tftpboot_location
        if not os.path.exists(bootloc):
            status.append(f"please create directory: {bootloc}")

    def check_ctftpd_dir(self, status: List[str]) -> None:
        """
        Check if ``cobbler.conf``'s tftpboot directory exists.

        :param status: The status list with possible problems.
        """
        if self.checked_family == "debian":
            return

        bootloc = self.settings.tftpboot_location
        if not os.path.exists(bootloc):
            status.append(f"please create directory: {bootloc}")

    def check_rsync_conf(self, status: List[str]) -> None:
        """
        Check that rsync is enabled to autostart.

        :param status: The status list with possible problems.
        """
        if self.checked_family == "debian":
            return

        if os.path.exists("/usr/lib/systemd/system/rsyncd.service"):
            if not os.path.exists(
                "/etc/systemd/system/multi-user.target.wants/rsyncd.service"
            ):
                status.append("enable and start rsyncd.service with systemctl")

    def check_dhcpd_conf(self, status: List[str]) -> None:
        """
        NOTE: this code only applies if Cobbler is *NOT* set to generate a ``dhcp.conf`` file.

        Check that dhcpd *appears* to be configured for pxe booting. We can't assure file correctness. Since a Cobbler
        user might have dhcp on another server, it's okay if it's not there and/or not configured correctly according
        to automated scans.

        :param status: The status list with possible problems.
        """
        if self.settings.manage_dhcp:
            return

        if os.path.exists(self.settings.dhcpd_conf):
            match_next = False
            match_file = False
            with open(self.settings.dhcpd_conf, encoding="UTF-8") as dhcpd_conf_fd:
                for line in dhcpd_conf_fd.readlines():
                    if line.find("next-server") != -1:
                        match_next = True
                    if line.find("filename") != -1:
                        match_file = True
            if not match_next:
                status.append(
                    f"expecting next-server entry in {self.settings.dhcpd_conf}"
                )
            if not match_file:
                status.append(f"missing file: {self.settings.dhcpd_conf}")
        else:
            status.append(f"missing file: {self.settings.dhcpd_conf}")
