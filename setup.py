#!/usr/bin/env python
import glob, os, time, yaml
from distutils.core import setup
from distutils.command.build_py import build_py as _build_py

VERSION = "2.1.0"


#####################################################################
## Helper Functions #################################################
#####################################################################


#####################################################################

def explode_glob_path(path):
    """Take a glob and hand back the full recursive expansion,
    ignoring links.
    """
    
    result = []
    includes = glob.glob(path)
    for item in includes:
        if os.path.isdir(item) and not os.path.islink(item):
            result.extend(explode_glob_path(os.path.join(item, "*")))
        else:
            result.append(item)
    return result


def proc_data_files(data_files):
    """Because data_files doesn't natively support globs... 
    let's add them.
    """
    
    result = []
    for dir,files in data_files:
        includes = []
        for item in files:
            includes.extend(explode_glob_path(item))
        result.append((dir, includes))
    return result

#####################################################################

def gen_manpages():
    """Generate the man pages... this is currently done through POD, 
    possible future version may do this through some Python mechanism 
    (maybe conversion from ReStructured Text (.rst))...
    """
    
    manpages = {
        "cobbler":          'pod2man --center="cobbler" --release="" ./docs/cobbler.pod | gzip -c > ./docs/cobbler.1.gz',
        "koan":             'pod2man --center="koan" --release="" ./docs/koan.pod | gzip -c > ./docs/koan.1.gz',
        "cobbler-register": 'pod2man --center="cobbler-register" --release="" ./docs/cobbler-register.pod | gzip -c > ./docs/cobbler-register.1.gz',
    }
    
    #Actually build them
    for man, cmd in manpages.items():
        print("building %s man page." % man)
        if os.system(cmd):
            print "Creation of %s manpage failed." % man
            exit(1) 

#####################################################################


#####################################################################
## Modify Build Stage  ##############################################
#####################################################################

class build_py(_build_py):
    """Specialized Python source builder."""
    
    def run(self):
        gen_manpages()
#        gen_build_version()
        _build_py.run(self)


#####################################################################
## Actual Setup.py Script ###########################################
#####################################################################
if __name__ == "__main__":
    ## Configurable installation roots for various data files.
    
    # Trailing slashes on these vars is to allow for easy
    # later configuration of relative paths if desired.
    docpath     = "/usr/share/man/man1"
    etcpath     = "/etc/cobbler/"
    initpath    = "/etc/init.d/"
    libpath     = "/var/lib/cobbler/"
    logpath     = "/var/log/"
    
    webroot     = "/var/www/"
    webconfig   = "/etc/httpd/conf.d/"
    webcontent  = webroot + "cobbler_webui_content/"
    

    setup(
        cmdclass={'build_py': build_py},
        name = "cobbler",
        version = VERSION,
        description = "Network Boot and Update Server",
        long_description = "Cobbler is a network install server.  Cobbler supports PXE, virtualized installs, and reinstalling existing Linux machines.  The last two modes use a helper tool, 'koan', that integrates with cobbler.  There is also a web interface 'cobbler-web'.  Cobbler's advanced features include importing distributions from DVDs and rsync mirrors, kickstart templating, integrated yum mirroring, and built-in DHCP/DNS Management.  Cobbler has a XMLRPC API for integration with other applications.",  
        author = "Team Cobbler",
        author_email = "cobbler@lists.fedorahosted.org",
        url = "http://fedorahosted.org/cobbler/",
        license = "GPLv2+",
        requires = [
            "mod_python",
            "cobbler",
        ],
        packages = [
            "cobbler",
            "cobbler/modules", 
            "koan", 
        ],
        package_dir = {
            "cobbler_web": "web/cobbler_web",
        },
        scripts = [
            "scripts/cobbler",
            "scripts/cobblerd",
            "scripts/cobbler-ext-nodes",
            "scripts/koan",
            "scripts/cobbler-register",
        ],
        data_files = proc_data_files([
            ("%s" % webconfig,              ["config/cobbler_web.conf"]),
            ("%s" % initpath,               ["config/cobblerd"]),
            ("%s" % etcpath,                ["config/*"]),
            ("%s" % docpath,                ["docs/*.gz"]),
            ("installer_templates",         ["installer_templates/*"]),
            ("%skickstarts" % libpath,      ["kickstarts/*"]),
            ("%ssnippets" % libpath,        ["snippets/*"]),
            ("%stemplates" % etcpath,       ["templates/*"]),
            ("web",                         ["web/*.*"]),
            ("%sweb/content" % webcontent,  ["web/content/*.*"]),
            ("web/cobbler_web",             ["web/cobbler_web/*.*"]),
            ("web/cobbler_web/templatetags",["web/cobbler_web/templatetags/*"]),
            ("web/cobbler_web/templates",   ["web/cobbler_web/templates/*"]),
            ("%swebui_sessions" % libpath,  []),
            ("%scobbler/aux" % webroot,     ["aux/*"]),
            
            #Build empty directories to hold triggers
            ("%striggers/add/distro/pre" % libpath,     []),
            ("%striggers/add/distro/post" % libpath,    []),
            ("%striggers/add/profile/pre" % libpath,    []),
            ("%striggers/add/profile/post" % libpath,   []),
            ("%striggers/add/system/pre" % libpath,     []),
            ("%striggers/add/system/post" % libpath,    []),
            ("%striggers/add/repo/pre" % libpath,       []),
            ("%striggers/add/repo/post" % libpath,      []),
            ("%striggers/delete/distro/pre" % libpath,  []),
            ("%striggers/delete/distro/post" % libpath, []),
            ("%striggers/delete/profile/pre" % libpath, []),
            ("%striggers/delete/profile/post" % libpath,[]),
            ("%striggers/delete/system/pre" % libpath,  []),
            ("%striggers/delete/system/post" % libpath, []),
            ("%striggers/delete/repo/pre" % libpath,    []),
            ("%striggers/delete/repo/post" % libpath,   []),
            ("%striggers/delete/repo/post" % libpath,   []),
            ("%striggers/install/pre" % libpath,        []),
            ("%striggers/install/post" % libpath,       []),
            ("%striggers/sync/pre" % libpath,           []),
            ("%striggers/sync/post" % libpath,          []),
            ("%striggers/change" % libpath,             []),
            
            # logfiles
            ("%scobbler/kicklog" % logpath,             []),
            ("%scobbler/syslog" % logpath,              []),
            ("%shttpd/cobbler" % logpath,               []),
            ("%scobbler/anamon" % logpath,              []),
            ("%skoan" % logpath,                        []),
            ("%scobbler/tasks" % logpath,               []),
            
            # spoolpaths
            ("spool/koan",                              []),
            
            # web page directories that we own
            ("%scobbler/localmirror" % webroot,         []),
            ("%scobbler/kickstarts" % webroot,          []),
            ("%scobbler/kickstarts_sys" % webroot,      []),
            ("%scobbler/repo_mirror" % webroot,         []),
            ("%scobbler/ks_mirror" % webroot,           []),
            ("%scobbler/ks_mirror/config" % webroot,    []),
            ("%scobbler/distros" % webroot,             []),
            ("%scobbler/images" % webroot,              []),
            ("%scobbler/systems" % webroot,             []),
            ("%scobbler/profiles" % webroot,            []),
            ("%scobbler/links" % webroot,               []),
            ("%scobbler/aux" % webroot,                 []),
            
            # zone-specific templates directory
            ("%szone_templates" % etcpath,              []),
        ]),
    )
