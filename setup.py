#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "0.6.5"
SHORT_DESC = "Network Boot and Update Server"
LONG_DESC = """
Cobbler is a network boot and update server.  Cobbler supports PXE, provisioning virtualized images, and reinstalling existing Linux machines.  The last two modes require a helper tool called 'koan' that integrates with cobbler.  Cobbler's advanced features include importing distributions from DVDs and rsync mirrors, kickstart templating, integrated yum mirroring, and built-in DHCP Management.  Cobbler has a Python API for integration with other GPL systems management applications.
"""

if __name__ == "__main__":
        # docspath="share/doc/koan-%s/" % VERSION
        manpath  = "share/man/man1/"
        cobpath  = "/var/lib/cobbler/"
        backpath = "/var/lib/cobbler/backup/"
        trigpath = "/var/lib/cobbler/triggers/"
        etcpath  = "/etc/cobbler/"
        wwwconf  = "/etc/httpd/conf.d/"
        wwwpath  = "/var/www/cobbler/"
        wwwgfx   = "/var/www/cobbler/webui/"
        initpath = "/etc/init.d/"
        logpath  = "/var/log/cobbler/"
        logpath2 = "/var/log/cobbler/kicklog"
        logpath3 = "/var/log/cobbler/syslog"
        logpath4 = "/var/log/httpd/cobbler"
        snippets = "/var/lib/cobbler/snippets"
        vl_kick  = "/var/lib/cobbler/kickstarts"
        wwwtmpl  = "/usr/share/cobbler/webui_templates/"
        vw_localmirror = "/var/www/cobbler/localmirror"
        vw_kickstarts  = "/var/www/cobbler/kickstarts"
        vw_kickstarts_sys  = "/var/www/cobbler/kickstarts_sys"
        vw_repomirror = "/var/www/cobbler/repo_mirror"
        vw_repoprofile = "/var/www/cobbler/repos_profile"
        vw_reposystem =  "/var/www/cobbler/repos_system"
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
        cgipath       = "/var/www/cgi-bin/cobbler"
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
                    "cobbler/modules", 
                    "cobbler/webui",
                ],
                scripts = ["scripts/cobbler", "scripts/cobblerd"],
                data_files = [ 
                                
                                # cgi files
                                (cgipath,  ['scripts/findks.cgi', 'scripts/nopxe.cgi']),
                                (cgipath,  ['scripts/webui.cgi']),
 
                                # miscellaneous config files
                                (cgipath,  ['config/.htaccess']),
                                (cgipath,  ['config/.htpasswd']),
                                (rotpath,  ['config/cobblerd_rotate']),
                                (wwwconf,  ['config/cobbler.conf']),
                                (cobpath,  ['config/cobbler_hosts']),
                                (etcpath,  ['config/modules.conf']),
                                (etcpath,  ['config/auth.conf']),
                                (etcpath,  ['config/webui-cherrypy.cfg']),
                                (etcpath,  ['config/rsync.exclude']),
                                (initpath, ['config/cobblerd']),
                                (cobpath,  ['config/settings']),

                                # backups for upgrades
                                (backpath, []),

                                # bootloaders and syslinux support files
                                (cobpath,  ['loaders/elilo-3.6-ia64.efi']),
                                (cobpath,  ['loaders/menu.c32']),

                                # sample kickstart files
                                (etcpath,  ['kickstarts/kickstart_fc5.ks']),
                                (etcpath,  ['kickstarts/kickstart_fc6.ks']),
                                (etcpath,  ['kickstarts/kickstart_fc6_domU.ks']),
                                (etcpath,  ['kickstarts/default.ks']),
 
                                # templates for DHCP and syslinux configs
				(etcpath,  ['templates/dhcp.template']),
				(etcpath,  ['templates/dnsmasq.template']),
				(etcpath,  ['templates/pxedefault.template']),
				(etcpath,  ['templates/pxesystem.template']),
				(etcpath,  ['templates/pxesystem_ia64.template']),
				(etcpath,  ['templates/pxeprofile.template']),

                                # kickstart dir
                                (vl_kick,  []),

                                # useful kickstart snippets that we ship
                                (snippets, ['snippets/partition_select']),

                                # documentation
                                (manpath,  ['docs/cobbler.1.gz']),

                                # logfiles
                                (logpath,  []),
                                (logpath2, []),
                                (logpath3, []),
				(logpath4, []),

                                # web page directories that we own
                                (vw_localmirror,    []),
                                (vw_kickstarts,     []),
                                (vw_kickstarts_sys, []),
                                (vw_repomirror,     []),
                                (vw_repoprofile,    []),
                                (vw_reposystem,     []),
                                (vw_ksmirror,       []),
                                (vw_ksmirrorc,      []),
                                (vw_distros,        []),
                                (vw_images,         []),
                                (vw_systems,        []),
                                (vw_profiles,       []),
                                (vw_links,          []),

                                # tftp directories that we own
                                (tftp_cfg,          []),
                                (tftp_images,       []),

                                # Web UI templates for object viewing & modification
                                # FIXME: other templates to add as they are created.
                                # slurp in whole directory?

                                (wwwtmpl,           ['webui_templates/empty.tmpl']),
                                (wwwtmpl,           ['webui_templates/blank.tmpl']),
                                (wwwtmpl,           ['webui_templates/distro_list.tmpl']),
                                (wwwtmpl,           ['webui_templates/distro_edit.tmpl']),
                                (wwwtmpl,           ['webui_templates/profile_list.tmpl']),
                                (wwwtmpl,           ['webui_templates/profile_edit.tmpl']),
                                (wwwtmpl,           ['webui_templates/system_list.tmpl']),
                                (wwwtmpl,           ['webui_templates/system_edit.tmpl']),
                                (wwwtmpl,           ['webui_templates/repo_list.tmpl']),
                                (wwwtmpl,           ['webui_templates/repo_edit.tmpl']),

                                # Web UI common templates 
                                (wwwtmpl,           ['webui_templates/paginate.tmpl']),
                                (wwwtmpl,           ['webui_templates/message.tmpl']),
                                (wwwtmpl,           ['webui_templates/error_page.tmpl']),
                                (wwwtmpl,           ['webui_templates/master.tmpl']),
                                (wwwtmpl,           ['webui_templates/item.tmpl']),
                                (wwwtmpl,           ['webui_templates/index.tmpl']),

                                # Web UI kickstart file editing
                                (wwwtmpl,           ['webui_templates/ksfile_edit.tmpl']),
                                (wwwtmpl,           ['webui_templates/ksfile_list.tmpl']),
                                (wwwtmpl,           ['webui_templates/ksfile_view.tmpl']),

                                # Web UI support files
				(wwwgfx,            ['docs/wui.html']),
                                (wwwgfx,            ['docs/cobbler.html']),
				(wwwgfx,            []),
                                (wwwgfx,            ['webui_content/icon_16_sync.png']),
                                (wwwgfx,            ['webui_content/list-expand.png']),
                                (wwwgfx,            ['webui_content/list-collapse.png']),
                                (wwwgfx,            ['webui_content/list-parent.png']),
                                (wwwgfx,            ['webui_content/cobbler.js']),
                                (wwwgfx,            ['webui_content/style.css']),
                                (wwwgfx,            ['webui_content/logo-cobbler.png']),
                                (wwwgfx,            ['webui_content/cobblerweb.css']),
 
                                # Directories to hold cobbler triggers
                                ("%sadd/distro/pre" % trigpath,      []),
                                ("%sadd/distro/post" % trigpath,     []),
                                ("%sadd/profile/pre" % trigpath,     []),
                                ("%sadd/profile/post" % trigpath,    []),
                                ("%sadd/system/pre" % trigpath,      []),
                                ("%sadd/system/post" % trigpath,     []),
                                ("%sadd/repo/pre" % trigpath,        []),
                                ("%sadd/repo/post" % trigpath,       []),
                                ("%sdelete/distro/pre" % trigpath,   []),
                                ("%sdelete/distro/post" % trigpath,  []),
                                ("%sdelete/profile/pre" % trigpath,  []),
                                ("%sdelete/profile/post" % trigpath, []),
                                ("%sdelete/system/pre" % trigpath,   []),
                                ("%sdelete/system/post" % trigpath,  []),
                                ("%sdelete/repo/pre" % trigpath,     []),
                                ("%sdelete/repo/post" % trigpath,    []),
                                ("%sdelete/repo/post" % trigpath,    []),
                                ("%ssync/pre" % trigpath,            []),
                                ("%ssync/post" % trigpath,           [ "triggers/restart-services.trigger" ])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

