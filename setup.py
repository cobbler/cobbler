#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.4.6"
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
        vw_links      = "/var/www/cobbler/links"
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
                    "cobbler/yaml" 
                ],
                scripts = ["scripts/cobbler", "scripts/cobbler_syslogd"],
                data_files = [
                                # (docspath, ['README']),
                                (wwwpath,  ['scripts/watcher.py']),
                                (cobpath,  ['loaders/elilo-3.6-ia64.efi']),
                                (cobpath,  ['loaders/menu.c32']),
                                (etcpath,  ['kickstarts/kickstart_fc5.ks']),
                                (etcpath,  ['kickstarts/kickstart_fc6.ks']),
                                (etcpath,  ['kickstarts/kickstart_fc6_domU.ks']),
                                (etcpath,  ['kickstarts/default.ks']),
				(etcpath,  ['templates/dhcp.template']),
				(etcpath,  ['templates/pxedefault.template']),
				(etcpath,  ['templates/pxesystem.template']),
				(etcpath,  ['templates/pxesystem_ia64.template']),
				(etcpath,  ['templates/pxeprofile.template']),
                                (manpath,  ['docs/cobbler.1.gz']),
                                (etcpath,  ['templates/rsync.exclude']),
                                (initpath, ['scripts/cobblersyslogd']),
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
                                (vw_links,          []),
                                (tftp_cfg,          []),
                                (tftp_images,       []),
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

