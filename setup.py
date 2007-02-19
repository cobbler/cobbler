#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.4.0"
SHORT_DESC = "Boot and update server configurator"
LONG_DESC = """
Cobbler is a command line tool for configuration of boot/provisioning, and update servers which is also accessible as a Python library.  Cobbler supports PXE, provisioning virtualized images, and reinstalling machines that are already up and running (over SSH).  The last two modes require a helper tool called 'koan' that integrates with cobbler.  Cobbler's advanced features include importing distributions from rsync mirrors, kickstart templating, integrated yum mirroring (and linking repository setup with kickstarts), plus managing dhcpd.conf.
"""

if __name__ == "__main__":
        # docspath="share/doc/koan-%s/" % VERSION
        manpath  = "share/man/man1/"
        cobpath  = "/var/lib/cobbler/"
        etcpath  = "/etc/cobbler/"
        wwwpath  = "/var/www/cobbler/"
        initpath = "/etc/init.d/"
        logpath  = "/var/log/cobbler/"
        logpath2 = "/var/log/cobbler/kicklog"
        logpath3 = "/var/log/cobbler/syslog"
        vw_localmirror = "/var/www/cobbler/localmirror"
        vw_kickstarts  = "/var/www/cobbler/kickstarts"
        vw_kickstarts_sys  = "/var/www/cobbler/kickstarts_sys"
        vw_repomirror = "/var/www/cobbler/repo_mirror"
        vw_ksmirror   = "/var/www/cobbler/ks_mirror"
        vw_images     = "/var/www/cobbler/images"
        vw_distros    = "/var/www/cobbler/distros"
        vw_systems    = "/var/www/cobbler/systems"
        vw_profiles   = "/var/www/cobbler/profiles"
        tftp_cfg      = "/tftpboot/pxelinux.cfg"
        tftp_images   = "/tftpboot/images"
        setup(
                name="cobbler",
                version = VERSION,
                author = "Michael DeHaan",
                author_email = "mdehaan@redhat.com",
                url = "http://cobbler.et.redhat.com/",
                license = "GPL",
                packages = [
                    "cobbler",
                    "cobbler/yaml", 
                    "cobbler/Cheetah",
                    "cobbler/Cheetah/Macros",
                    "cobbler/Cheetah/Templates",
                    "cobbler/Cheetah/Tests",
                    "cobbler/Cheetah/Tools",
                    "cobbler/Cheetah/Utils",
                ],
                scripts = ["cobbler/cobbler", "cobbler/cobbler_syslogd"],
                data_files = [
                                # (docspath, ['README']),
                                (wwwpath,  ['watcher.py']),
                                (cobpath,  ['elilo-3.6-ia64.efi']),
                                (cobpath,  ['menu.c32']),
                                (etcpath,  ['kickstart_fc5.ks']),
                                (etcpath,  ['kickstart_fc6.ks']),
                                (etcpath,  ['kickstart_fc6_domU.ks']),
                                (etcpath,  ['default.ks']),
				(etcpath,  ['dhcp.template']),
                                (manpath,  ['cobbler.1.gz']),
                                (etcpath,  ['rsync.exclude']),
                                (initpath, ['cobblersyslogd']),
                                (logpath,  []),
                                (logpath2, []),
                                (logpath3, []),
                                (vw_localmirror,    []),
                                (vw_kickstarts,     []),
                                (vw_kickstarts_sys, []),
                                (vw_repomirror,     []),
                                (vw_ksmirror,       []),
                                (vw_distros,        []),
                                (vw_images,         []),
                                (vw_systems,        []),
                                (vw_profiles,       []),
                                (tftp_cfg,          []),
                                (tftp_images,       []),
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

