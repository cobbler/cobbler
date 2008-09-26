#!/usr/bin/python

import sys
from distutils.core import setup, Extension
import string

VERSION = "1.2.5"
SHORT_DESC = "Network Boot and Update Server"
LONG_DESC = """
Cobbler is a network boot and update server.  Cobbler supports PXE, provisioning virtualized images, and reinstalling existing Linux machines.  The last two modes require a helper tool called 'koan' that integrates with cobbler.  Cobbler's advanced features include importing distributions from DVDs and rsync mirrors, kickstart templating, integrated yum mirroring, and built-in DHCP/DNS Management.  Cobbler also has a Python and XMLRPC API for integration with other applications.
"""

if __name__ == "__main__":
        # docspath="share/doc/koan-%s/" % VERSION
        bashpath = "/etc/bash_completion.d/"
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
        vw_ksmirror   = "/var/www/cobbler/ks_mirror"
        vw_ksmirrorc  = "/var/www/cobbler/ks_mirror/config"
        vw_images     = "/var/www/cobbler/images"
        vw_distros    = "/var/www/cobbler/distros"
        vw_systems    = "/var/www/cobbler/systems"
        vw_profiles   = "/var/www/cobbler/profiles"
        vw_links      = "/var/www/cobbler/links"
        zone_templates = "/etc/cobbler/zone_templates"
        tftp_cfg      = "/tftpboot/pxelinux.cfg"
        tftp_images   = "/tftpboot/images"
        rotpath       = "/etc/logrotate.d"
        # cgipath       = "/var/www/cgi-bin/cobbler"
        modpython     = "/var/www/cobbler/web"
        modpythonsvc  = "/var/www/cobbler/svc"
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
                    "cobbler/server", 
                    "cobbler/webui",
                ],
                scripts = ["scripts/cobbler", "scripts/cobblerd", "scripts/cobbler-completion"],
                data_files = [ 
                                (modpython, ['scripts/index.py']),
                                (modpythonsvc, ['scripts/services.py']),
                                # cgi files
                                # (cgipath,   ['scripts/nopxe.cgi']),
                                # (cgipath,   ['scripts/install_trigger.cgi']),
 
                                # miscellaneous config files
                                (rotpath,  ['config/cobblerd_rotate']),
                                (wwwconf,  ['config/cobbler.conf']),
                                (wwwconf,  ['config/cobbler_svc.conf']),
                                (cobpath,  ['config/completions']),
                                (cobpath,  ['config/cobbler_hosts']),
                                (etcpath,  ['config/modules.conf']),
                                (etcpath,  ['config/users.digest']),
                                (etcpath,  ['config/rsync.exclude']),
                                (etcpath,  ['config/users.conf']),
                                (initpath, ['config/cobblerd']),
                                (etcpath,  ['config/settings']),
                                # (bashpath, ['config/cobbler_bash']), 

                                # backups for upgrades
                                (backpath, []),

                                # bootloaders and syslinux support files
                                (cobpath,  ['loaders/elilo-3.6-ia64.efi']),
                                (cobpath,  ['loaders/menu.c32']),
                                ("/var/lib/cobbler/config/distros.d",  []),
                                ("/var/lib/cobbler/config/profiles.d", []),
                                ("/var/lib/cobbler/config/systems.d",  []),
                                ("/var/lib/cobbler/config/repos.d",    []),
                                ("/var/lib/cobbler/config/images.d",   []),

                                # sample kickstart files
                                (etcpath,  ['kickstarts/legacy.ks']),
                                (etcpath,  ['kickstarts/sample.ks']),
                                (etcpath,  ['kickstarts/sample_end.ks']),
                                (etcpath,  ['kickstarts/default.ks']),
 
                                # templates for DHCP, DNS, and syslinux configs
				(etcpath,  ['templates/dhcp.template']),
				(etcpath,  ['templates/dnsmasq.template']),
                                (etcpath,  ['templates/named.template']),
				(etcpath,  ['templates/pxedefault.template']),
				(etcpath,  ['templates/pxesystem.template']),
				(etcpath,  ['templates/pxesystem_s390x.template']),
				(etcpath,  ['templates/pxesystem_ia64.template']),
				(etcpath,  ['templates/pxeprofile.template']),
				(etcpath,  ['templates/pxelocal.template']),
                                (etcpath,  ['templates/zone.template']),

                                # kickstart dir
                                (vl_kick,  []),

                                # useful kickstart snippets that we ship
                                (snippets, ['snippets/partition_select']),
                                (snippets, ['snippets/pre_partition_select']),
                                (snippets, ['snippets/main_partition_select']),
                                (snippets, ['snippets/post_install_kernel_options']),

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
                                (vw_ksmirror,       []),
                                (vw_ksmirrorc,      []),
                                (vw_distros,        []),
                                (vw_images,         []),
                                (vw_systems,        []),
                                (vw_profiles,       []),
                                (vw_links,          []),

                                # zone-specific templates directory
                                (zone_templates,    []),

                                # tftp directories that we own
                                (tftp_cfg,          []),
                                (tftp_images,       []),

                                # Web UI templates for object viewing & modification
                                # FIXME: other templates to add as they are created.
                                # slurp in whole directory?

                                (wwwtmpl,           ['webui_templates/empty.tmpl']),
                                (wwwtmpl,           ['webui_templates/blank.tmpl']),
                                (wwwtmpl,           ['webui_templates/enoaccess.tmpl']),
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
                                (wwwtmpl,           ['webui_templates/ksfile_new.tmpl']),
                                (wwwtmpl,           ['webui_templates/ksfile_list.tmpl']),

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
                                ("%sinstall/pre" % trigpath,         [ "triggers/status_pre.trigger"]),
                                ("%sinstall/post" % trigpath,        [ "triggers/status_post.trigger"]),
                                ("%ssync/pre" % trigpath,            []),
                                ("%ssync/post" % trigpath,           [ "triggers/restart-services.trigger" ])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

