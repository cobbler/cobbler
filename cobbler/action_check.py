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
import os
import re

import clogger
import utils
from utils import _


class CobblerCheck:
    """
    Validates whether the system is reasonably well configured for
    serving up content.  This is the code behind 'cobbler check'.
    """

    def __init__(self, collection_mgr, logger=None):
        """
        Constructor
        """
        self.collection_mgr = collection_mgr
        self.settings = collection_mgr.settings()
        if logger is None:
            logger = clogger.Logger()
        self.logger = logger

    def run(self):
        """
        Returns None if there are no errors, otherwise returns a list
        of things to correct prior to running application 'for real'.
        (The CLI usage is "cobbler check" before "cobbler sync")
        """
        status = []
        self.checked_family = utils.get_family()
        self.check_name(status)
        self.check_selinux(status)
        if self.settings.manage_dhcp:
            mode = self.collection_mgr.api.get_sync().dhcp.what()
            if mode == "isc":
                self.check_dhcpd_bin(status)
                self.check_dhcpd_conf(status)
                self.check_service(status, "dhcpd")
            elif mode == "dnsmasq":
                self.check_dnsmasq_bin(status)
                self.check_service(status, "dnsmasq")

        if self.settings.manage_dns:
            mode = self.collection_mgr.api.get_sync().dns.what()
            if mode == "bind":
                self.check_bind_bin(status)
                self.check_service(status, "named")
            elif mode == "dnsmasq" and not self.settings.manage_dhcp:
                self.check_dnsmasq_bin(status)
                self.check_service(status, "dnsmasq")

        mode = self.collection_mgr.api.get_sync().tftpd.what()
        if mode == "in_tftpd":
            self.check_tftpd_bin(status)
            self.check_tftpd_dir(status)
            self.check_tftpd_conf(status)
        elif mode == "tftpd_py":
            self.check_ctftpd_bin(status)
            self.check_ctftpd_dir(status)
            self.check_ctftpd_conf(status)

        self.check_service(status, "cobblerd")

        self.check_bootloaders(status)
        self.check_for_wget_curl(status)
        self.check_rsync_conf(status)
        self.check_httpd(status)
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
        if self.checked_family == "debian":
            return

        if not os.path.exists("/usr/bin/ksvalidator"):
            status.append("ksvalidator was not found, install pykickstart")

    def check_for_cman(self, status):
        # not doing rpm -q here to be cross-distro friendly
        if not os.path.exists("/sbin/fence_ilo") and not os.path.exists("/usr/sbin/fence_ilo"):
            status.append("fencing tools were not found, and are required to use the (optional) power management features. install cman or fence-agents to use them")

    def check_service(self, status, which, notes=""):
        if notes != "":
            notes = " (NOTE: %s)" % notes
        rc = 0
        if self.checked_family in ("redhat", "suse"):
            if os.path.exists("/etc/rc.d/init.d/%s" % which):
                rc = utils.subprocess_call(self.logger, "/sbin/service %s status > /dev/null 2>/dev/null" % which, shell=True)
            if rc != 0:
                status.append(_("service %s is not running%s") % (which, notes))
                return
        elif self.checked_family == "debian":
            # we still use /etc/init.d
            if os.path.exists("/etc/init.d/%s" % which):
                rc = utils.subprocess_call(self.logger, "/etc/init.d/%s status /dev/null 2>/dev/null" % which, shell=True)
            if rc != 0:
                status.append(_("service %s is not running%s") % (which, notes))
                return
        else:
            status.append(_("Unknown distribution type, cannot check for running service %s" % which))
            return

    def check_iptables(self, status):
        if os.path.exists("/etc/rc.d/init.d/iptables"):
            rc = utils.subprocess_call(self.logger, "/sbin/service iptables status >/dev/null 2>/dev/null", shell=True)
            if rc == 0:
                status.append(_("since iptables may be running, ensure 69, 80/443, and %(xmlrpc)s are unblocked") % {"xmlrpc": self.settings.xmlrpc_port})

    def check_yum(self, status):
        if self.checked_family == "debian":
            return

        if not os.path.exists("/usr/bin/createrepo"):
            status.append(_("createrepo package is not installed, needed for cobbler import and cobbler reposync, install createrepo?"))
        if not os.path.exists("/usr/bin/dnf") and not os.path.exists("/usr/bin/reposync"):
            status.append(_("reposync is not installed, need for cobbler reposync, install/upgrade yum-utils?"))
        if not os.path.exists("/usr/bin/yumdownloader"):
            status.append(_("yumdownloader is not installed, needed for cobbler repo add with --rpm-list parameter, install/upgrade yum-utils?"))
        if self.settings.reposync_flags.find("-l"):
            if self.checked_family in ("redhat", "suse"):
                yum_utils_ver = utils.subprocess_get(self.logger, "/usr/bin/rpmquery --queryformat=%{VERSION} yum-utils", shell=True)
                if yum_utils_ver < "1.1.17":
                    status.append(_("yum-utils need to be at least version 1.1.17 for reposync -l, current version is %s") % yum_utils_ver)

    def check_debmirror(self, status):
        if not os.path.exists("/usr/bin/debmirror"):
            status.append(_("debmirror package is not installed, it will be required to manage debian deployments and repositories"))
        if os.path.exists("/etc/debmirror.conf"):
            f = open("/etc/debmirror.conf")
            re_dists = re.compile(r'@dists=')
            re_arches = re.compile(r'@arches=')
            for line in f.readlines():
                if re_dists.search(line) and not line.strip().startswith("#"):
                    status.append(_("comment out 'dists' on /etc/debmirror.conf for proper debian support"))
                if re_arches.search(line) and not line.strip().startswith("#"):
                    status.append(_("comment out 'arches' on /etc/debmirror.conf for proper debian support"))

    def check_name(self, status):
        """
        If the server name in the config file is still set to localhost
        automatic installations run from koan will not have proper kernel line
        parameters.
        """
        if self.settings.server == "127.0.0.1":
            status.append(_("The 'server' field in /etc/cobbler/settings must be set to something other than localhost, or automatic installation features will not work.  This should be a resolvable hostname or IP for the boot server as reachable by all machines that will use it."))
        if self.settings.next_server == "127.0.0.1":
            status.append(_("For PXE to be functional, the 'next_server' field in /etc/cobbler/settings must be set to something other than 127.0.0.1, and should match the IP of the boot server on the PXE network."))

    def check_selinux(self, status):
        """
        Suggests various SELinux rules changes to run Cobbler happily with
        SELinux in enforcing mode.  FIXME: this method could use some
        refactoring in the future.
        """
        if self.checked_family == "debian":
            return

        enabled = self.collection_mgr.api.is_selinux_enabled()
        if enabled:
            status.append(_("SELinux is enabled. Please review the following wiki page for details on ensuring cobbler works correctly in your SELinux environment:\n    https://github.com/cobbler/cobbler/wiki/Selinux"))

    def check_for_default_password(self, status):
        default_pass = self.settings.default_password_crypted
        if default_pass == "$1$mF86/UHC$WvcIcX2t6crBz2onWxyac.":
            status.append(_("The default password used by the sample templates for newly installed machines (default_password_crypted in /etc/cobbler/settings) is still set to 'cobbler' and should be changed, try: \"openssl passwd -1 -salt 'random-phrase-here' 'your-password-here'\" to generate new one"))

    def check_for_unreferenced_repos(self, status):
        repos = []
        referenced = []
        not_found = []
        for r in self.collection_mgr.api.repos():
            repos.append(r.name)
        for p in self.collection_mgr.api.profiles():
            my_repos = p.repos
            if my_repos != "<<inherit>>":
                referenced.extend(my_repos)
        for r in referenced:
            if r not in repos and r != "<<inherit>>":
                not_found.append(r)
        if len(not_found) > 0:
            status.append(_("One or more repos referenced by profile objects is no longer defined in cobbler: %s") % ", ".join(not_found))

    def check_for_unsynced_repos(self, status):
        need_sync = []
        for r in self.collection_mgr.repos():
            if r.mirror_locally == 1:
                lookfor = os.path.join(self.settings.webdir, "repo_mirror", r.name)
                if not os.path.exists(lookfor):
                    need_sync.append(r.name)
        if len(need_sync) > 0:
            status.append(_("One or more repos need to be processed by cobbler reposync for the first time before automating installations using them: %s") % ", ".join(need_sync))

    def check_httpd(self, status):
        """
        Check if Apache is installed.
        """
        if self.checked_family == "redhat":
            rc = utils.subprocess_get(self.logger, "httpd -v")
        elif self.checked_family == "suse":
            rc = utils.subprocess_get(self.logger, "httpd2 -v")
        else:
            rc = utils.subprocess_get(self.logger, "apache2 -v")
        if rc.find("Server") == -1:
            status.append("Apache (httpd) is not installed and/or in path")

    def check_dhcpd_bin(self, status):
        """
        Check if dhcpd is installed
        """
        if not os.path.exists("/usr/sbin/dhcpd"):
            status.append("dhcpd is not installed")

    def check_dnsmasq_bin(self, status):
        """
        Check if dnsmasq is installed
        """
        rc = utils.subprocess_get(self.logger, "dnsmasq --help")
        if rc.find("Valid options") == -1:
            status.append("dnsmasq is not installed and/or in path")

    def check_bind_bin(self, status):
        """
        Check if bind is installed.
        """
        rc = utils.subprocess_get(self.logger, "named -v")
        # it should return something like "BIND 9.6.1-P1-RedHat-9.6.1-6.P1.fc11"
        if rc.find("BIND") == -1:
            status.append("named is not installed and/or in path")

    def check_for_wget_curl(self, status):
        """
        Check to make sure wget or curl is installed
        """
        rc1 = utils.subprocess_call(self.logger, "which wget")
        rc2 = utils.subprocess_call(self.logger, "which curl")
        if rc1 != 0 and rc2 != 0:
            status.append("Neither wget nor curl are installed and/or available in $PATH. Cobbler requires that one of these utilities be installed.")

    def check_bootloaders(self, status):
        """
        Check if network bootloaders are installed
        """
        # FIXME: move zpxe.rexx to loaders

        bootloaders = {
            "menu.c32": ["/usr/share/syslinux/menu.c32",
                         "/usr/lib/syslinux/menu.c32",
                         "/var/lib/cobbler/loaders/menu.c32"],
            "yaboot": ["/var/lib/cobbler/loaders/yaboot*"],
            "pxelinux.0": ["/usr/share/syslinux/pxelinux.0",
                           "/usr/lib/syslinux/pxelinux.0",
                           "/var/lib/cobbler/loaders/pxelinux.0"],
            "efi": ["/var/lib/cobbler/loaders/grub-x86.efi",
                    "/var/lib/cobbler/loaders/grub-x86_64.efi"],
        }

        # look for bootloaders at the glob locations above
        found_bootloaders = []
        items = bootloaders.keys()
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
            status.append("some network boot-loaders are missing from /var/lib/cobbler/loaders, you may run 'cobbler get-loaders' to download them, or, if you only want to handle x86/x86_64 netbooting, you may ensure that you have installed a *recent* version of the syslinux package installed and can ignore this message entirely.  Files in this directory, should you want to support all architectures, should include pxelinux.0, menu.c32, and yaboot. The 'cobbler get-loaders' command is the easiest way to resolve these requirements.")

    def check_tftpd_bin(self, status):
        """
        Check if tftpd is installed
        """
        if self.checked_family == "debian":
            return

        if not os.path.exists("/etc/xinetd.d/tftp"):
            status.append("missing /etc/xinetd.d/tftp, install tftp-server?")

    def check_tftpd_dir(self, status):
        """
        Check if cobbler.conf's tftpboot directory exists
        """
        if self.checked_family == "debian":
            return

        bootloc = utils.tftpboot_location()
        if not os.path.exists(bootloc):
            status.append(_("please create directory: %(dirname)s") % {"dirname": bootloc})

    def check_tftpd_conf(self, status):
        """
        Check that configured tftpd boot directory matches with actual
        Check that tftpd is enabled to autostart
        """
        if self.checked_family == "debian":
            return

        if os.path.exists("/etc/xinetd.d/tftp"):
            f = open("/etc/xinetd.d/tftp")
            re_disable = re.compile(r'disable.*=.*yes')
            for line in f.readlines():
                if re_disable.search(line) and not line.strip().startswith("#"):
                    status.append(_("change 'disable' to 'no' in %(file)s") % {"file": "/etc/xinetd.d/tftp"})
        else:
            status.append("missing configuration file: /etc/xinetd.d/tftp")

    def check_ctftpd_bin(self, status):
        """
        Check if the Cobbler tftp server is installed
        """
        if self.checked_family == "debian":
            return

        if not os.path.exists("/etc/xinetd.d/ctftp"):
            status.append("missing /etc/xinetd.d/ctftp")

    def check_ctftpd_dir(self, status):
        """
        Check if cobbler.conf's tftpboot directory exists
        """
        if self.checked_family == "debian":
            return

        bootloc = utils.tftpboot_location()
        if not os.path.exists(bootloc):
            status.append(_("please create directory: %(dirname)s") % {"dirname": bootloc})

    def check_ctftpd_conf(self, status):
        """
        Check that configured tftpd boot directory matches with actual
        Check that tftpd is enabled to autostart
        """
        if self.checked_family == "debian":
            return

        if os.path.exists("/etc/xinetd.d/tftp"):
            f = open("/etc/xinetd.d/tftp")
            re_disable = re.compile(r'disable.*=.*no')
            for line in f.readlines():
                if re_disable.search(line) and not line.strip().startswith("#"):
                    status.append(_("change 'disable' to 'yes' in %(file)s") % {"file": "/etc/xinetd.d/tftp"})
        if os.path.exists("/etc/xinetd.d/ctftp"):
            f = open("/etc/xinetd.d/ctftp")
            re_disable = re.compile(r'disable.*=.*yes')
            for line in f.readlines():
                if re_disable.search(line) and not line.strip().startswith("#"):
                    status.append(_("change 'disable' to 'no' in %(file)s") % {"file": "/etc/xinetd.d/ctftp"})
        else:
            status.append("missing configuration file: /etc/xinetd.d/ctftp")

    def check_rsync_conf(self, status):
        """
        Check that rsync is enabled to autostart
        """
        if self.checked_family == "debian":
            return

        if os.path.exists("/etc/xinetd.d/rsync"):
            f = open("/etc/xinetd.d/rsync")
            re_disable = re.compile(r'disable.*=.*yes')
            for line in f.readlines():
                if re_disable.search(line) and not line.strip().startswith("#"):
                    status.append(_("change 'disable' to 'no' in %(file)s") % {"file": "/etc/xinetd.d/rsync"})
        else:
            status.append(_("file %(file)s does not exist") % {"file": "/etc/xinetd.d/rsync"})

    def check_dhcpd_conf(self, status):
        """
        NOTE: this code only applies if cobbler is *NOT* set to generate
        a dhcp.conf file

        Check that dhcpd *appears* to be configured for pxe booting.
        We can't assure file correctness.  Since a cobbler user might
        have dhcp on another server, it's okay if it's not there and/or
        not configured correctly according to automated scans.
        """
        if not (self.settings.manage_dhcp == 0):
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
                status.append(_("expecting next-server entry in %(file)s") % {"file": self.settings.dhcpd_conf})
            if not match_file:
                status.append(_("missing file: %(file)s") % {"file": self.settings.dhcpd_conf})
        else:
            status.append(_("missing file: %(file)s") % {"file": self.settings.dhcpd_conf})

# EOF
