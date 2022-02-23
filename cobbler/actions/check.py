"""
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


import glob
import logging
import os
import re

from xmlrpc.client import ServerProxy

from cobbler import utils


class CobblerCheck:
    """
    Validates whether the system is reasonably well configured for
    serving up content. This is the code behind 'cobbler check'.
    """

    def __init__(self, api):
        """
        Constructor

        :param api: The API which holds all information.
        """
        self.api = api
        self.settings = api.settings()
        self.logger = logging.getLogger()
        self.checked_family = ""

    def run(self):
        """
        The CLI usage is "cobbler check" before "cobbler sync".

        :return: None if there are no errors, otherwise returns a list of things to correct prior to running application
                 'for real'.
        """
        status = []
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

    def check_for_ksvalidator(self, status):
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

    def check_for_cman(self, status):
        """
        Check if the fence agents are available. This is done through checking if the binary ``fence_ilo`` is present
        in ``/sbin`` or ``/usr/sbin``.

        :param status: The status list with possible problems. The status list with possible problems.
        """
        # not doing rpm -q here to be cross-distro friendly
        if not os.path.exists("/sbin/fence_ilo") and not os.path.exists("/usr/sbin/fence_ilo"):
            status.append("fencing tools were not found, and are required to use the (optional) power management "
                          "features. install cman or fence-agents to use them")

    def check_service(self, status, which, notes=""):
        """
        Check if the service command is available or the old init.d system has to be used.

        :param status: The status list with possible problems.
        :param which: The service to check for.
        :param notes: A manual not to attach.
        """
        if notes != "":
            notes = " (NOTE: %s)" % notes
        return_code = 0
        if utils.is_supervisord():
            with ServerProxy('http://localhost:9001/RPC2') as server:
                process_info = server.supervisor.getProcessInfo(which)
                if process_info['statename'] != "RUNNING":
                    status.append("service %s is not running%s" % (which, notes))
                    return
        elif utils.is_systemd():
            return_code = utils.subprocess_call("systemctl status %s > /dev/null 2>/dev/null" % which,
                                                shell=True)
            if return_code != 0:
                status.append("service %s is not running%s" % (which, notes))
                return
        elif self.checked_family in ("redhat", "suse"):
            if os.path.exists("/etc/rc.d/init.d/%s" % which):
                return_code = utils.subprocess_call("/sbin/service %s status > /dev/null 2>/dev/null" % which,
                                                    shell=True)
            if return_code != 0:
                status.append("service %s is not running%s" % (which, notes))
                return
        elif self.checked_family == "debian":
            # we still use /etc/init.d
            if os.path.exists("/etc/init.d/%s" % which):
                return_code = utils.subprocess_call("/etc/init.d/%s status /dev/null 2>/dev/null" % which,
                                                    shell=True)
            if return_code != 0:
                status.append("service %s is not running%s" % (which, notes))
                return
        else:
            status.append("Unknown distribution type, cannot check for running service %s" % which)
            return

    def check_iptables(self, status):
        """
        Check if iptables is running. If yes print the needed ports. This is unavailable on Debian, SUSE and CentOS7 as
        a service. However this only indicates that the way of persisting the iptable rules are persisted via other
        means.

        :param status: The status list with possible problems.
        """
        # TODO: Rewrite check to be able to verify this is in more cases
        if os.path.exists("/etc/rc.d/init.d/iptables"):
            return_code = utils.subprocess_call("/sbin/service iptables status >/dev/null 2>/dev/null",
                                                shell=True)
            if return_code == 0:
                status.append("since iptables may be running, ensure 69, 80/443, and %(xmlrpc)s are unblocked"
                              % {"xmlrpc": self.settings.xmlrpc_port})

    def check_yum(self, status):
        """
        Check if the yum-stack is available. On Debian based distros this will always return without checking.

        :param status: The status list with possible problems.
        """
        # FIXME: Replace this with calls which check for the path of these tools.
        if self.checked_family == "debian":
            return

        if not os.path.exists("/usr/bin/createrepo"):
            status.append("createrepo package is not installed, needed for cobbler import and cobbler reposync, "
                          "install createrepo?")

        if not os.path.exists("/usr/bin/dnf") and not os.path.exists("/usr/bin/reposync"):
            status.append("reposync not installed, install yum-utils")

        if os.path.exists("/usr/bin/dnf") and not os.path.exists("/usr/bin/reposync"):
            status.append("reposync is not installed, install yum-utils or dnf-plugins-core")

        if not os.path.exists("/usr/bin/dnf") and not os.path.exists("/usr/bin/yumdownloader"):
            status.append("yumdownloader is not installed, install yum-utils")

        if os.path.exists("/usr/bin/dnf") and not os.path.exists("/usr/bin/yumdownloader"):
            status.append("yumdownloader is not installed, install yum-utils or dnf-plugins-core")

    def check_debmirror(self, status):
        """
        Check if debmirror is available and the config file for it exists. If the distro family is suse then this will
        pass without checking.

        :param status: The status list with possible problems.
        """
        if self.checked_family == "suse":
            return

        if not os.path.exists("/usr/bin/debmirror"):
            status.append("debmirror package is not installed, it will be required to manage debian deployments and "
                          "repositories")
        if os.path.exists("/etc/debmirror.conf"):
            with open("/etc/debmirror.conf") as f:
                re_dists = re.compile(r'@dists=')
                re_arches = re.compile(r'@arches=')
                for line in f.readlines():
                    if re_dists.search(line) and not line.strip().startswith("#"):
                        status.append("comment out 'dists' on /etc/debmirror.conf for proper debian support")
                    if re_arches.search(line) and not line.strip().startswith("#"):
                        status.append("comment out 'arches' on /etc/debmirror.conf for proper debian support")

    def check_name(self, status):
        """
        If the server name in the config file is still set to localhost automatic installations run from koan will not
        have proper kernel line parameters.

        :param status: The status list with possible problems.
        """
        if self.settings.server == "127.0.0.1":
            status.append("The 'server' field in /etc/cobbler/settings.yaml must be set to something other than localhost, "
                          "or automatic installation features will not work.  This should be a resolvable hostname or "
                          "IP for the boot server as reachable by all machines that will use it.")
        if self.settings.next_server_v4 == "127.0.0.1":
            status.append("For PXE to be functional, the 'next_server_v4' field in /etc/cobbler/settings.yaml must be set to "
                          "something other than 127.0.0.1, and should match the IP of the boot server on the PXE "
                          "network.")
        if self.settings.next_server_v6 == "::1":
            status.append("For PXE to be functional, the 'next_server_v6' field in /etc/cobbler/settings.yaml must be set to "
                          "something other than ::1, and should match the IP of the boot server on the PXE network.")

    def check_selinux(self, status):
        """
        Suggests various SELinux rules changes to run Cobbler happily with SELinux in enforcing mode.

        :param status: The status list with possible problems.
        """
        # FIXME: this method could use some refactoring in the future.
        if self.checked_family == "debian":
            return

        enabled = self.api.is_selinux_enabled()
        if enabled:
            status.append("SELinux is enabled. Please review the following wiki page for details on ensuring Cobbler "
                          "works correctly in your SELinux environment:\n    "
                          "https://github.com/cobbler/cobbler/wiki/Selinux")

    def check_for_default_password(self, status):
        """
        Check if the default password of Cobbler was changed.

        :param status: The status list with possible problems.
        """
        default_pass = self.settings.default_password_crypted
        if default_pass == "$1$mF86/UHC$WvcIcX2t6crBz2onWxyac.":
            status.append("The default password used by the sample templates for newly installed machines ("
                          "default_password_crypted in /etc/cobbler/settings.yaml) is still set to 'cobbler' and should be "
                          "changed, try: \"openssl passwd -1 -salt 'random-phrase-here' 'your-password-here'\" to "
                          "generate new one")

    def check_for_unreferenced_repos(self, status):
        """
        Check if there are repositories which are not used and thus could be removed.

        :param status: The status list with possible problems.
        """
        repos = []
        referenced = []
        not_found = []
        for r in self.api.repos():
            repos.append(r.name)
        for p in self.api.profiles():
            my_repos = p.repos
            if my_repos != "<<inherit>>":
                referenced.extend(my_repos)
        for r in referenced:
            if r not in repos and r != "<<inherit>>":
                not_found.append(r)
        if len(not_found) > 0:
            status.append("One or more repos referenced by profile objects is no longer defined in Cobbler: %s"
                          % ", ".join(not_found))

    def check_for_unsynced_repos(self, status):
        """
        Check if there are unsynchronized repositories which need an update.

        :param status: The status list with possible problems.
        """
        need_sync = []
        for r in self.api.repos():
            if r.mirror_locally == 1:
                lookfor = os.path.join(self.settings.webdir, "repo_mirror", r.name)
                if not os.path.exists(lookfor):
                    need_sync.append(r.name)
        if len(need_sync) > 0:
            status.append("One or more repos need to be processed by cobbler reposync for the first time before "
                          "automating installations using them: %s" % ", ".join(need_sync))

    def check_dhcpd_bin(self, status):
        """
        Check if dhcpd is installed.

        :param status: The status list with possible problems.
        """
        if not os.path.exists("/usr/sbin/dhcpd"):
            status.append("dhcpd is not installed")

    def check_dnsmasq_bin(self, status):
        """
        Check if dnsmasq is installed.

        :param status: The status list with possible problems.
        """
        return_code = utils.subprocess_call("dnsmasq --help")
        if return_code != 0:
            status.append("dnsmasq is not installed and/or in path")

    def check_bind_bin(self, status):
        """
        Check if bind is installed.

        :param status: The status list with possible problems.
        """
        return_code = utils.subprocess_call("named -v")
        # it should return something like "BIND 9.6.1-P1-RedHat-9.6.1-6.P1.fc11"
        if return_code != 0:
            status.append("named is not installed and/or in path")

    def check_for_wget_curl(self, status):
        """
        Check to make sure wget or curl is installed

        :param status: The status list with possible problems.
        """
        rc_wget = utils.subprocess_call("wget --help")
        rc_curl = utils.subprocess_call("curl --help")
        if rc_wget != 0 and rc_curl != 0:
            status.append("Neither wget nor curl are installed and/or available in $PATH. Cobbler requires that one "
                          "of these utilities be installed.")

    def check_bootloaders(self, status):
        """
        Check if network bootloaders are installed

        :param status: The status list with possible problems.
        """
        # FIXME: move zpxe.rexx to loaders

        bootloaders = {
            "menu.c32": ["/usr/share/syslinux/menu.c32",
                         "/usr/lib/syslinux/menu.c32",
                         "/var/lib/cobbler/loaders/menu.c32"],
            "pxelinux.0": ["/usr/share/syslinux/pxelinux.0",
                           "/usr/lib/syslinux/pxelinux.0",
                           "/var/lib/cobbler/loaders/pxelinux.0"],
            "efi": ["/var/lib/cobbler/loaders/grub-x86.efi",
                    "/var/lib/cobbler/loaders/grub-x86_64.efi"],
        }

        # look for bootloaders at the glob locations above
        found_bootloaders = []
        items = list(bootloaders.keys())
        for loader_name in items:
            patterns = bootloaders[loader_name]
            for pattern in patterns:
                matches = glob.glob(pattern)
                if len(matches) > 0:
                    found_bootloaders.append(loader_name)
        not_found = []

        # invert the list of what we've found so we can report on what we haven't found
        for loader_name in items:
            if loader_name not in found_bootloaders:
                not_found.append(loader_name)

        if len(not_found) > 0:
            status.append("some network boot-loaders are missing from /var/lib/cobbler/loaders. If you only want to "
                          "handle x86/x86_64 netbooting, you may ensure that you have installed a *recent* version "
                          "of the syslinux package installed and can ignore this message entirely. Files in this "
                          "directory, should you want to support all architectures, should include pxelinux.0, and"
                          "menu.c32.")

    def check_tftpd_dir(self, status):
        """
        Check if cobbler.conf's tftpboot directory exists

        :param status: The status list with possible problems.
        """
        if self.checked_family == "debian":
            return

        bootloc = self.settings.tftpboot_location
        if not os.path.exists(bootloc):
            status.append("please create directory: %(dirname)s" % {"dirname": bootloc})

    def check_ctftpd_dir(self, status):
        """
        Check if ``cobbler.conf``'s tftpboot directory exists.

        :param status: The status list with possible problems.
        """
        if self.checked_family == "debian":
            return

        bootloc = self.settings.tftpboot_location
        if not os.path.exists(bootloc):
            status.append("please create directory: %(dirname)s" % {"dirname": bootloc})

    def check_rsync_conf(self, status):
        """
        Check that rsync is enabled to autostart.

        :param status: The status list with possible problems.
        """
        if self.checked_family == "debian":
            return

        if os.path.exists("/usr/lib/systemd/system/rsyncd.service"):
            if not os.path.exists("/etc/systemd/system/multi-user.target.wants/rsyncd.service"):
                status.append("enable and start rsyncd.service with systemctl")

    def check_dhcpd_conf(self, status):
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
            f = open(self.settings.dhcpd_conf)
            for line in f.readlines():
                if line.find("next-server") != -1:
                    match_next = True
                if line.find("filename") != -1:
                    match_file = True
            if not match_next:
                status.append("expecting next-server entry in %(file)s" % {"file": self.settings.dhcpd_conf})
            if not match_file:
                status.append("missing file: %(file)s" % {"file": self.settings.dhcpd_conf})
        else:
            status.append("missing file: %(file)s" % {"file": self.settings.dhcpd_conf})
