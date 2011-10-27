#!/usr/bin/env python
import glob, os, time, yaml
from distutils.core import setup
from distutils.command.build_py import build_py as _build_py

try:
    import subprocess
except:
    import cobbler.sub_process as subprocess


VERSION = "2.3.1"
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
        print("building %s man page." % man)
        if os.system(cmd):
            print "Creation of %s manpage failed." % man
            exit(1)

#####################################################################

def gen_build_version():
    fd = open(os.path.join(OUTPUT_DIR, "version"),"w+")
    gitdate = "?"
    gitstamp = "?"
    builddate = time.asctime()
    if os.path.exists(".git"):
       # for builds coming from git, include the date of the last commit
       cmd = subprocess.Popen(["/usr/bin/git","log","--format=%h%n%ad","-1"],stdout=subprocess.PIPE)
       data = cmd.communicate()[0].strip()
       if cmd.returncode == 0:
           gitstamp, gitdate = data.split("\n")
    data = {
       "gitdate" : gitdate,
       "gitstamp"      : gitstamp,
       "builddate"     : builddate,
       "version"       : VERSION,
       "version_tuple" : [ int(x) for x in VERSION.split(".")]
    }
    fd.write(yaml.dump(data))
    fd.close()

#####################################################################


#####################################################################
## Modify Build Stage  ##############################################
#####################################################################

class build_py(_build_py):
    """Specialized Python source builder."""

    def run(self):
        gen_manpages()
        gen_build_version()
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

    if os.path.exists("/etc/SuSE-release"):
        webconfig  = "/etc/apache2/conf.d"
        webroot     = "/srv/www/"
    elif os.path.exists("/etc/debian_version"):
        webconfig  = "/etc/apache2/conf.d"
        webroot     = "/usr/share/cobbler/webroot/"
    else:
        webconfig  = "/etc/httpd/conf.d"
        webroot     = "/var/www/"

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
            # tftpd, hide in /usr/sbin
            ("/usr/sbin", ["scripts/tftpd.py"]),

            ("%s" % webconfig,              ["config/cobbler.conf"]),
            ("%s" % webconfig,              ["config/cobbler_web.conf"]),
            ("%s" % initpath,               ["config/cobblerd"]),
            ("%s" % docpath,                ["docs/*.gz"]),
            ("installer_templates",         ["installer_templates/*"]),
            ("%skickstarts" % libpath,      ["kickstarts/*"]),
            ("%ssnippets" % libpath,        ["snippets/*"]),
            ("web",                         ["web/*.*"]),
            ("%s" % webcontent,             ["web/content/*.*"]),
            ("web/cobbler_web",             ["web/cobbler_web/*.*"]),
            ("web/cobbler_web/templatetags",["web/cobbler_web/templatetags/*"]),
            ("web/cobbler_web/templates",   ["web/cobbler_web/templates/*"]),
            ("%swebui_sessions" % libpath,  []),
            ("%sloaders" % libpath,         []),
            ("%scobbler/aux" % webroot,     ["aux/*"]),

            #Configuration
            ("%s" % etcpath,                ["config/*"]),
            ("%s" % etcpath,                ["templates/etc/*"]),
            ("%siso" % etcpath,             ["templates/iso/*"]),
            ("%spxe" % etcpath,             ["templates/pxe/*"]),
            ("%sreporting" % etcpath,       ["templates/reporting/*"]),
            ("%spower" % etcpath,           ["templates/power/*"]),
            ("%sldap" % etcpath,            ["templates/ldap/*"]),

            #Build empty directories to hold triggers
            ("%striggers/add/distro/pre" % libpath,       []),
            ("%striggers/add/distro/post" % libpath,      []),
            ("%striggers/add/profile/pre" % libpath,      []),
            ("%striggers/add/profile/post" % libpath,     []),
            ("%striggers/add/system/pre" % libpath,       []),
            ("%striggers/add/system/post" % libpath,      []),
            ("%striggers/add/repo/pre" % libpath,         []),
            ("%striggers/add/repo/post" % libpath,        []),
            ("%striggers/add/mgmtclass/pre" % libpath,    []),
            ("%striggers/add/mgmtclass/post" % libpath,   []),
            ("%striggers/add/package/pre" % libpath,      []),
            ("%striggers/add/package/post" % libpath,     []),
            ("%striggers/add/file/pre" % libpath,         []),
            ("%striggers/add/file/post" % libpath,        []),
            ("%striggers/delete/distro/pre" % libpath,    []),
            ("%striggers/delete/distro/post" % libpath,   []),
            ("%striggers/delete/profile/pre" % libpath,   []),
            ("%striggers/delete/profile/post" % libpath,  []),
            ("%striggers/delete/system/pre" % libpath,    []),
            ("%striggers/delete/system/post" % libpath,   []),
            ("%striggers/delete/repo/pre" % libpath,      []),
            ("%striggers/delete/repo/post" % libpath,     []),
            ("%striggers/delete/mgmtclass/pre" % libpath, []),
            ("%striggers/delete/mgmtclass/post" % libpath,[]),
            ("%striggers/delete/package/pre" % libpath,   []),
            ("%striggers/delete/package/post" % libpath,  []),
            ("%striggers/delete/file/pre" % libpath,      []),
            ("%striggers/delete/file/post" % libpath,     []),
            ("%striggers/install/pre" % libpath,          []),
            ("%striggers/install/post" % libpath,         []),
            ("%striggers/install/firstboot" % libpath,    []),
            ("%striggers/sync/pre" % libpath,             []),
            ("%striggers/sync/post" % libpath,            []),
            ("%striggers/change" % libpath,               []),

            #Build empty directories to hold the database
            ("%sconfig" % libpath,               []),
            ("%sconfig/distros.d" % libpath,     []),
            ("%sconfig/images.d" % libpath,      []),
            ("%sconfig/profiles.d" % libpath,    []),
            ("%sconfig/repos.d" % libpath,       []),
            ("%sconfig/systems.d" % libpath,     []),
            ("%sconfig/mgmtclasses.d" % libpath, []),
            ("%sconfig/packages.d" % libpath,    []),
            ("%sconfig/files.d" % libpath,       []),
            
            #Build empty directories to hold koan localconfig
            ("/var/lib/koan/config",             []),

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
            ("%scobbler/repo_mirror" % webroot,         []),
            ("%scobbler/ks_mirror" % webroot,           []),
            ("%scobbler/ks_mirror/config" % webroot,    []),
            ("%scobbler/links" % webroot,               []),
            ("%scobbler/aux" % webroot,                 []),

            #A script that isn't really data, wsgi script
            ("%scobbler/svc/" % webroot,     ["scripts/services.py"]),

            # zone-specific templates directory
            ("%szone_templates" % etcpath,                []),
        ]),
    )
