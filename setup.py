#!/usr/bin/python

import sys
import os.path
from distutils.core import setup, Extension
import string
import cobbler.yaml as yaml
import cobbler.sub_process as subprocess
import Cheetah.Template as Template
import time

VERSION = "1.3.4"
SHORT_DESC = "Network Boot and Update Server"
LONG_DESC = """
Cobbler is a network boot and update server.  Cobbler supports PXE, provisioning virtualized images, and reinstalling existing Linux machines.  The last two modes require a helper tool called 'koan' that integrates with cobbler.  Cobbler's advanced features include importing distributions from DVDs and rsync mirrors, kickstart templating, integrated yum mirroring, and built-in DHCP/DNS Management.  Cobbler also has a Python and XMLRPC API for integration with other applications.
"""
TEMPLATES_DIR = "installer_templates"
DEFAULTS = os.path.join(TEMPLATES_DIR, "defaults")
MODULES_TEMPLATE = os.path.join(TEMPLATES_DIR, "modules.conf.template")
SETTINGS_TEMPLATE = os.path.join(TEMPLATES_DIR, "settings.template")
OUTPUT_DIR = "config"

# =========================================================        
def templatify(template, answers, output):
    t = Template.Template(file=template, searchList=answers)
    open(output,"w").write(t.respond())

def gen_build_version():
    fd = open(os.path.join(OUTPUT_DIR, "version"),"w+")
    gitdate = "?"
    gitstamp = "?"
    builddate = time.asctime()
    if os.path.exists(".git"): 
       # for builds coming from git, include the date of the last commit
       cmd = subprocess.Popen(["/usr/bin/git","log"],stdout=subprocess.PIPE)
       data = cmd.communicate()[0].strip()
       for line in data.split("\n"):
           if line.startswith("commit"):
               tokens = line.split(" ",1)
               gitstamp = tokens[1].strip()
           if line.startswith("Date:"):
               tokens = line.split(":",1)
               gitdate = tokens[1].strip()
               break
    data = {
       "gitdate" : gitdate,
       "gitstamp"      : gitstamp,
       "builddate"     : builddate,
       "version"       : VERSION,
       "version_tuple" : [ int(x) for x in VERSION.split(".")]
    }
    fd.write(yaml.dump(data))
    fd.close()
    

def gen_config():
    defaults = {}
    data = yaml.loadFile(DEFAULTS).next()
    defaults.update(data)
    templatify(MODULES_TEMPLATE, defaults, os.path.join(OUTPUT_DIR, "modules.conf"))
    templatify(SETTINGS_TEMPLATE, defaults, os.path.join(OUTPUT_DIR, "settings"))

if __name__ == "__main__":
        gen_build_version()
        gen_config()
        # docspath="share/doc/koan-%s/" % VERSION
        
        # etc configs
        etcpath     = "/etc/cobbler"
        initpath    = "/etc/init.d"
        rotpath       = "/etc/logrotate.d"
        powerpath   = etcpath + "/power"
        pxepath     = etcpath + "/pxe"
        zonepath    = etcpath + "/zone_templates"
        
        # lib paths
        libpath     = "/var/lib/cobbler"
        backpath    = libpath + "/backup"
        trigpath    = libpath + "/triggers"
        snippetpath = libpath + "/snippets"
        kickpath    = libpath + "/kickstarts"
        dbpath      = libpath + "/config"

        # share paths
        sharepath   = "/usr/share/cobbler"
        itemplates  = sharepath + "/installer_templates"
        wwwtmpl     = sharepath + "/webui_templates"
        manpath     = "share/man/man1"
        
        # www paths
        wwwpath  = "/var/www/cobbler"
        if os.path.exists("/etc/SuSE-release"):
            wwwconf  = "/etc/apache2/conf.d"
        else:
            wwwconf  = "/etc/httpd/conf.d"
        wwwcon   = wwwpath + "/webui"
        vw_localmirror = wwwpath + "/localmirror"
        vw_kickstarts  = wwwpath + "/kickstarts"
        vw_kickstarts_sys  = wwwpath + "/kickstarts_sys"
        vw_repomirror = wwwpath + "/repo_mirror"
        vw_ksmirror   = wwwpath + "/ks_mirror"
        vw_ksmirrorc  = wwwpath + "/ks_mirror/config"
        vw_images     = wwwpath + "/images"
        vw_distros    = wwwpath + "/distros"
        vw_systems    = wwwpath + "/systems"
        vw_profiles   = wwwpath + "/profiles"
        vw_links      = wwwpath + "/links"
        # cgipath       = "/var/www/cgi-bin/cobbler"
        modpython     = wwwpath + "/web"
        modpythonsvc  = wwwpath + "/svc"
        
        # log paths
        logpath  = "/var/log/cobbler"
        logpath2 = logpath + "/kicklog"
        logpath3 = logpath + "/syslog"
        logpath4 = "/var/log/httpd/cobbler"

        # tftp paths        
        tftp_cfg      = "/tftpboot/pxelinux.cfg"
        tftp_images   = "/tftpboot/images"
        

        # hack to bundle jquery until we have packaging guidelines to avoid JS bundling
        # bundling is evil, but temporary.

        def file_slurper(arg, dirname, fnames):
           # FIXME: shell glob would be simpler
           for fn in fnames:
               fn2 = os.path.join(dirname,fn)
               if os.path.isfile(fn2):
                   if not fn2 in arg:
                       arg.append(fn2)
               else:
                   # don't recurse
                   fnames.remove(fn)
 
        jui_files = []
        jui_files2 = []
        jui_files3 = []
        jui_files4 = []
        jui_files5 = []
        os.path.walk("./webui_content/jquery.ui/ui", file_slurper, jui_files)
        os.path.walk("./webui_content/jquery.ui/ui/i18n", file_slurper, jui_files2)
        os.path.walk("./webui_content/jquery.ui/themes", file_slurper, jui_files3)
        os.path.walk("./webui_content/jquery.ui/themes/flora", file_slurper, jui_files4)
        os.path.walk("./webui_content/jquery.ui/themes/flora/i", file_slurper, jui_files5)
        
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
                scripts = [
                    "scripts/cobbler", 
                    "scripts/cobblerd", 
                    "scripts/cobbler-ext-nodes", 
                ],
                data_files = [ 
                                (modpython, ['scripts/index.py']),
                                (modpythonsvc, ['scripts/services.py']),
 
                                # miscellaneous config files
                                (rotpath,  ['config/cobblerd_rotate']),
                                (wwwconf,  ['config/cobbler.conf']),
                                (wwwconf,  ['config/cobbler_svc.conf']),
                                (libpath,  ['config/cobbler_hosts']),
                                (etcpath,  ['config/modules.conf']),
                                (etcpath,  ['config/users.digest']),
                                (etcpath,  ['config/rsync.exclude']),
                                (etcpath,  ['config/users.conf']),
                                (etcpath,  ['config/acls.conf']),
                                (etcpath,  ['config/cheetah_macros']),
                                (initpath, ['config/cobblerd']),
                                (etcpath,  ['config/settings']),

                                # backups for upgrades
                                (backpath, []),

                                # for --version support across distros
                                (libpath,  ['config/version']),

                                # bootloaders and syslinux support files
                                (libpath,  ['loaders/elilo-3.8-ia64.efi']),
                                (libpath,  ['loaders/menu.c32']),
                                (libpath,  ['loaders/yaboot-1.3.14']),
                                
                                # database/serializer
                                (dbpath + "/distros.d",  []),
                                (dbpath + "/profiles.d", []),
                                (dbpath + "/systems.d",  []),
                                (dbpath + "/repos.d",    []),
                                (dbpath + "/images.d",   []),

                                # sample kickstart files
                                (kickpath,  ['kickstarts/legacy.ks']),
                                (kickpath,  ['kickstarts/sample.ks']),
                                (kickpath,  ['kickstarts/sample_end.ks']),
                                (kickpath,  ['kickstarts/default.ks']),
                                (kickpath,  ['kickstarts/pxerescue.ks']),
                                
                                # seed files for debian
                                (kickpath,  ['kickstarts/sample.seed']),
 
                                # templates for DHCP, DNS
				(etcpath,  ['templates/dhcp.template']),
				(etcpath,  ['templates/dnsmasq.template']),
                                (etcpath,  ['templates/named.template']),
                                (etcpath,  ['templates/zone.template']),
                                
                                # templates for syslinux PXE configs
				(pxepath,  ['templates/pxedefault.template']),
				(pxepath,  ['templates/pxesystem.template']),
				(pxepath,  ['templates/pxesystem_s390x.template']),
				(pxepath,  ['templates/pxesystem_ia64.template']),
				(pxepath,  ['templates/pxesystem_ppc.template']),
				(pxepath,  ['templates/pxeprofile.template']),
				(pxepath,  ['templates/pxelocal.template']),

                                # templates for power management
                                (powerpath, ['templates/power_apc_snmp.template']), 
                                (powerpath, ['templates/power_ipmilan.template']),
                                (powerpath, ['templates/power_bullpap.template']),     
                                (powerpath, ['templates/power_ipmitool.template']),
                                (powerpath, ['templates/power_drac.template']),        
                                (powerpath, ['templates/power_rsa.template']),
                                (powerpath, ['templates/power_ether_wake.template']),  
                                (powerpath, ['templates/power_wti.template']),
                                (powerpath, ['templates/power_ilo.template']),
                                (powerpath, ['templates/power_lpar.template']),        
                                (powerpath, ['templates/power_bladecenter.template']),        
                                (powerpath, ['templates/power_virsh.template']),        

                                # templates for /usr/bin/cobbler-setup
                                (itemplates, ['installer_templates/modules.conf.template']),
                                (itemplates, ['installer_templates/settings.template']),
                                (itemplates, ['installer_templates/defaults']),

                                # useful kickstart snippets that we ship
                                (snippetpath, ['snippets/partition_select']),
                                (snippetpath, ['snippets/pre_partition_select']),
                                (snippetpath, ['snippets/main_partition_select']),
                                (snippetpath, ['snippets/post_install_kernel_options']),
                                (snippetpath, ['snippets/network_config']),
                                (snippetpath, ['snippets/pre_install_network_config']),
                                (snippetpath, ['snippets/post_install_network_config']),
                                (snippetpath, ['snippets/func_install_if_enabled']),
                                (snippetpath, ['snippets/func_register_if_enabled']),
                                (snippetpath, ['snippets/download_config_files']),
                                (snippetpath, ['snippets/koan_environment']),
                                (snippetpath, ['snippets/redhat_register']),

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
                                (zonepath,    []),

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
                                (wwwtmpl,           ['webui_templates/image_list.tmpl']),
                                (wwwtmpl,           ['webui_templates/image_edit.tmpl']),

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
				(wwwcon,            ['docs/wui.html']),
                                (wwwcon,            ['docs/cobbler.html']),

                                #(wwwcon,           ['webui_content/icon_16_sync.png']),
                                #(wwwcon,           ['webui_content/list-expand.png']),
                                #(wwwcon,           ['webui_content/list-collapse.png']),
                                #(wwwcon,           ['webui_content/list-parent.png']),

                                (wwwcon,            ['webui_content/cobbler.js']),
                                (wwwcon,            ['webui_content/style.css']),
                                (wwwcon,            ['webui_content/logo-cobbler.png']),
                                (wwwcon,            ['webui_content/cobblerweb.css']),

                                # Directories to hold cobbler triggers
                                ("%s/add/distro/pre" % trigpath,      []),
                                ("%s/add/distro/post" % trigpath,     []),
                                ("%s/add/profile/pre" % trigpath,     []),
                                ("%s/add/profile/post" % trigpath,    []),
                                ("%s/add/system/pre" % trigpath,      []),
                                ("%s/add/system/post" % trigpath,     []),
                                ("%s/add/repo/pre" % trigpath,        []),
                                ("%s/add/repo/post" % trigpath,       []),
                                ("%s/delete/distro/pre" % trigpath,   []),
                                ("%s/delete/distro/post" % trigpath,  []),
                                ("%s/delete/profile/pre" % trigpath,  []),
                                ("%s/delete/profile/post" % trigpath, []),
                                ("%s/delete/system/pre" % trigpath,   []),
                                ("%s/delete/system/post" % trigpath,  []),
                                ("%s/delete/repo/pre" % trigpath,     []),
                                ("%s/delete/repo/post" % trigpath,    []),
                                ("%s/delete/repo/post" % trigpath,    []),
                                ("%s/install/pre" % trigpath,         [ "triggers/status_pre.trigger"]),
                                ("%s/install/post" % trigpath,        [ "triggers/status_post.trigger"]),
                                ("%s/sync/pre" % trigpath,            []),
                                ("%s/sync/post" % trigpath,           [ "triggers/restart-services.trigger" ])
                             ],
                description = SHORT_DESC,
                long_description = LONG_DESC
        )

