#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.5.2"
SHORT_DESC = "Network Boot and Update Server"
LONG_DESC = """
Cobbler is a network boot and update server.  Cobbler supports PXE, provisioning virtualized images, and reinstalling existing Linux machines.  The last two modes require a helper tool called 'koan' that integrates with cobbler.  Cobbler's advanced features include importing distributions from DVDs and rsync mirrors, kickstart templating, integrated yum mirroring, and built-in DHCP Management.  Cobbler has a Python API for integration with other GPL systems management applications.
"""

if __name__ == "__main__":
        # docspath="share/doc/koan-%s/" % VERSION
        manpath  = "share/man/man1/"
        cobpath  = "/var/lib/cobbler/"
        etcpath  = "/etc/cobbler/"
        wwwconf  = "/etc/httpd/conf.d/"
        wwwpath  = "/var/www/cobbler/"
        initpath = "/etc/init.d/"
        logpath  = "/var/log/cobbler/"
        logpath2 = "/var/log/cobbler/kicklog"
        logpath3 = "/var/log/cobbler/syslog"
        snippets = "/var/lib/cobbler/snippets"
        vw_localmirror = "/var/www/cobbler/localmirror"
        vw_kickstarts  = "/var/www/cobbler/kickstarts"
        vw_kickstarts_sys  = "/var/www/cobbler/kickstarts_sys"
        vw_repomirror = "/var/www/cobbler/repo_mirror"
        vw_ksmirror   = "/var/www/cobbler/ks_mirror"
        vw_ksmirrorc  = "/var/www/cobbler/ks_mirror/config"
        vw_images     = "/var/www/cobbler/images"
        vw_distros    = "/var/www/cobbler/distros"
        vw_systems    = "/var/www/cobbler/systems"
        vw_profiles   = "/var/www/cobbler/profiles"
        vw_links      = "/var/www/cobbler/links"
        tftp_cfg      = "/tftpboot/pxelinux.cfg"
        tftp_images   = "/tftpboot/images"
        rotpath       = "/etc/logrotate.d"
        cgipath       = "/var/www/cgi-bin"
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
                scripts = ["scripts/cobbler", "scripts/cobblerd"],
                data_files = [ 
                                (cgipath,  ['scripts/findks.cgi', 'scripts/nopxe.cgi']),
                                (rotpath,  ['config/cobblerd_rotate']),
                                (wwwconf,  ['config/cobbler.conf']),
                                (cobpath,  ['loaders/elilo-3.6-ia64.efi']),
                                (cobpath,  ['loaders/menu.c32']),
                                (etcpath,  ['kickstarts/kickstart_fc5.ks']),
                                (etcpath,  ['kickstarts/kickstart_fc6.ks']),
                                (etcpath,  ['kickstarts/kickstart_fc6_domU.ks']),
                                (etcpath,  ['kickstarts/default.ks']),
				(etcpath,  ['templates/dhcp.template']),
				(etcpath,  ['templates/dnsmasq.template']),
				(etcpath,  ['templates/pxedefault.template']),
				(etcpath,  ['templates/pxesystem.template']),
				(etcpath,  ['templates/pxesystem_ia64.template']),
				(etcpath,  ['templates/pxeprofile.template']),
                                (snippets, ['snippets/partition_select']),
                                (manpath,  ['docs/cobbler.1.gz']),
                                (etcpath,  ['config/rsync.exclude']),
                                (initpath, ['config/cobblerd']),
                                (logpath,  []),
                                (logpath2, []),
                                (logpath3, []),
                                (vw_localmirror,    []),
                                (vw_kickstarts,     []),
                                (vw_kickstarts_sys, []),
                                (vw_repomirror,     []),
                                (vw_ksmirror,       []),
                                (vw_ksmirrorc,      []),
                                (vw_distros,        []),
                                (vw_images,         []),
                                (vw_systems,        []),
                                (vw_profiles,       []),
                                (vw_links,          []),
                                (tftp_cfg,          []),
                                (tftp_images,       []),
                                ("/var/lib/cobbler/triggers/add/distro/pre",      []),
                                ("/var/lib/cobbler/triggers/add/distro/post",     []),
                                ("/var/lib/cobbler/triggers/add/profile/pre",     []),
                                ("/var/lib/cobbler/triggers/add/profile/post",    []),
                                ("/var/lib/cobbler/triggers/add/system/pre",      []),
                                ("/var/lib/cobbler/triggers/add/system/post",     []),
                                ("/var/lib/cobbler/triggers/add/repo/pre",        []),
                                ("/var/lib/cobbler/triggers/add/repo/post",       []),
                                ("/var/lib/cobbler/triggers/delete/distro/pre",   []),
                                ("/var/lib/cobbler/triggers/delete/distro/post",  []),
                                ("/var/lib/cobbler/triggers/delete/profile/pre",  []),
                                ("/var/lib/cobbler/triggers/delete/profile/post", []),
                                ("/var/lib/cobbler/triggers/delete/system/pre",   []),
                                ("/var/lib/cobbler/triggers/delete/system/post",  []),
                                ("/var/lib/cobbler/triggers/delete/repo/pre",     []),
                                ("/var/lib/cobbler/triggers/delete/repo/post",    [])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

