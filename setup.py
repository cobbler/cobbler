#!/usr/bin/env python
import glob, os, time, yaml
from distutils.core import setup
import Cheetah.Template as Template
try:
    import subprocess
except:
    import cobbler.sub_process as subprocess


VERSION = "2.0.4"

TEMPLATES_DIR = "installer_templates"
DEFAULTS = os.path.join(TEMPLATES_DIR, "defaults")
MODULES_TEMPLATE = os.path.join(TEMPLATES_DIR, "modules.conf.template")
SETTINGS_TEMPLATE = os.path.join(TEMPLATES_DIR, "settings.template")
OUTPUT_DIR = "config"


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
        if os.system(cmd):
            print "Creation of %s manpage failed." % man
            exit(1) 

#####################################################################

def templatify(template, answers, output):
    """Fill in a template given the answers"""
    
    t = Template.Template(file=template, searchList=answers)
    data = t.respond()
    outf = open(output,"w")
    outf.write(data)
    outf.close()

def gen_build_version():
    """Pull metadata information from git when this build is from
    a git repo.
    """
    
    fd = open(os.path.join(OUTPUT_DIR, "version"),"w+")
    gitdate = "?"
    gitstamp = "?"
    builddate = time.asctime()
    if os.path.exists(".git"):
       # for builds coming from git, include the date of the last commit
       cmd = subprocess.Popen(["/usr/bin/git","log","-1"],stdout=subprocess.PIPE)
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
    """Activate the templating functionality with the defaults for
    input."""
    
    defaults_file = open(DEFAULTS)
    defaults_data = defaults_file.read()
    defaults_file.close()
    defaults = yaml.load(defaults_data)
    templatify(MODULES_TEMPLATE, defaults, os.path.join(OUTPUT_DIR, "modules.conf"))
    templatify(SETTINGS_TEMPLATE, defaults, os.path.join(OUTPUT_DIR, "settings"))

#####################################################################


#####################################################################
## Actual Setup.py Script ###########################################
#####################################################################
if __name__ == "__main__":
    
    gen_manpages()
    gen_build_version()
    gen_config()
    

    setup(
        name = "cobbler",
        version = VERSION,
        description = "Network Boot and Update Server",
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
            ("config",                      ["config/*"]),
            ("docs",                        ["docs/*.gz"]),
            ("installer_templates",         ["installer_templates/*"]),
            ("kickstarts",                  ["kickstarts/*"]),
            ("snippets",                    ["snippets/*"]),
            ("templates",                   ["templates/*"]),
            ("web",                         ["web/*.*"]),
            ("web/www/content",             ["web/content/*.*"]),
            ("web/cobbler_web",             ["web/cobbler_web/*.*"]),
            ("web/cobbler_web/templatetags",["web/cobbler_web/templatetags/*"]),
            ("web/cobbler_web/templates",   ["web/cobbler_web/templates/*"]),
            ("web/webui_sessions",          []),
            ("web/www/aux",                 ["aux/*"]),
            
            #Build empty directories to hold triggers
            ("trigger/add/distro/pre",      []),
            ("trigger/add/distro/post",     []),
            ("trigger/add/profile/pre",     []),
            ("trigger/add/profile/post",    []),
            ("trigger/add/system/pre",      []),
            ("trigger/add/system/post",     []),
            ("trigger/add/repo/pre" ,       []),
            ("trigger/add/repo/post",       []),
            ("trigger/delete/distro/pre",   []),
            ("trigger/delete/distro/post",  []),
            ("trigger/delete/profile/pre",  []),
            ("trigger/delete/profile/post", []),
            ("trigger/delete/system/pre",   []),
            ("trigger/delete/system/post",  []),
            ("trigger/delete/repo/pre",     []),
            ("trigger/delete/repo/post",    []),
            ("trigger/delete/repo/post",    []),
            ("trigger/install/pre",         []),
            ("trigger/install/post",        []),
            ("trigger/sync/pre",            []),
            ("trigger/sync/post",           []),
            ("trigger/change",              []),
            
            # logfiles
            ("log/kicklog",                 []),
            ("log/syslog",                  []),
            ("log/httpd/cobbler",           []),
            ("log/anamon",                  []),
            ("log/koan",                    []),
            ("log/tasks",                   []),
            
            # spoolpaths
            ("spool/koan",                  []),
            
            # web page directories that we own
            ("web/www/localmirror",         []),
            ("web/www/kickstarts",          []),
            ("web/www/kickstarts_sys",      []),
            ("web/www/repo_mirror",         []),
            ("web/www/ks_mirror",           []),
            ("web/www/ks_mirror/config",    []),
            ("web/www/distros",             []),
            ("web/www/images",              []),
            ("web/www/systems",             []),
            ("web/www/profiles",            []),
            ("web/www/links",               []),
            ("web/www/aux",                 []),
            
            # zone-specific templates directory
            ("zone_templates",              []),
        ]),
    )
