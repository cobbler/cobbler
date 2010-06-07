#!/usr/bin/env python
import glob, os
from distutils.core import setup


## Helper Functions #################################################
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

def make_manpages():
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
        if os.spawn(cmd):
            print "Creation of %s manpage failed." % man
            exit(1) 



## Actual Setup Script ##############################################
if __name__ == "__main__":
    
    make_manpages()
    
#    See the comment associated with data_files listings which use these below
#    #Django Configuration
#    dj_config   = "/etc/httpd/conf.d/"
#    dj_sessions  = "/var/lib/cobbler/webui_sessions"

    setup(
        name = "cobbler",
        version = "2.0.4",
        description = "Boot server configurator",
        long_description = "Cobbler is a network install server.  Cobbler supports PXE, virtualized installs, and reinstalling existing Linux machines.  The last two modes use a helper tool, 'koan', that integrates with cobbler.  There is also a web interface 'cobbler-web'.  Cobbler's advanced features include importing distributions from DVDs and rsync mirrors, kickstart templating, integrated yum mirroring, and built-in DHCP/DNS Management.  Cobbler has a XMLRPC API for integration with other applications.",  
        author = "Michael DeHaan",
        author_email = "mdehaan@redhat.com",
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
            "web", 
            "web.cobbler_web", 
            "web.cobbler_web.templatetags",
        ],
        package_dir = {
            "cobbler_web": "web/cobbler_web",
        },
#If only our target was python >= 2.4
#        package_data = {
#            "web": ["web/content/*"],
#            "web.cobbler_web": ["templates/*.tmpl"],
#        },
        scripts = [
            "scripts/cobbler",
            "scripts/cobblerd",
            "scripts/cobbler-ext-nodes",
            "scripts/koan",
            "scripts/cobbler-register",
        ],
        data_files = proc_data_files([
            ("aux",                 ["aux/*"]),
            ("config",              ["config/*"]),
            ("docs",                ["docs/*.gz"]),
            ("installer_templates", ["installer_templates/*"]),
            ("kickstarts",          ["kickstarts/*"]),
            ("snippets",            ["snippets/*"]),
            ("templates",           ["templates/*"]),
            ("web/content",         ["web/content/*"]),
            ("web/templates",       ["web/cobbler_web/templates/*"]),
#These need to be placed in the RPM or whatever OS specific installer is being used...
#            (dj_config,     ['config/cobbler_web.conf']),
#            (dj_sessions,   []),
        ]),
    )
