#!/usr/bin/env python3

from future import standard_library
standard_library.install_aliases()
import os
import sys
import time
import logging
import glob as _glob
import distro

from builtins import str
from setuptools import setup
from setuptools import Command
from setuptools.command.install import install as _install
from setuptools import Distribution as _Distribution
from setuptools.command.build_py import build_py as _build_py
from setuptools import dep_util
from distutils.command.build import build as _build
from configparser import ConfigParser
from setuptools import find_packages
from sphinx.setup_command import BuildDoc

import codecs
from coverage import Coverage
import pwd
import shutil
import subprocess

from builtins import OSError

VERSION = "3.1.2"
OUTPUT_DIR = "config"

log = logging.getLogger("setup.py")


#####################################################################
# # Helper Functions #################################################
#####################################################################

def glob(*args, **kwargs):
    recursive = kwargs.get('recursive', False)
    results = []
    for arg in args:
        for elem in _glob.glob(arg):
            # Now check if we should handle/check those results.
            if os.path.isdir(elem):
                if os.path.islink(elem):
                    # We skip symlinks
                    pass
                else:
                    # We only handle directories if recursive was specified
                    if recursive:
                        results.extend(
                            # Add the basename of arg (the pattern) to elem and continue
                            glob(
                                os.path.join(elem, os.path.basename(arg)),
                                recursive=True))
            else:
                # Always append normal files
                results.append(elem)
    return results

#####################################################################


#####################################################################

def gen_build_version():
    buildepoch = int(os.environ.get('SOURCE_DATE_EPOCH', time.time()))
    builddate = time.asctime(time.gmtime(buildepoch))

    gitloc = "/usr/bin/git"
    gitdate = "?"
    gitstamp = "?"
    if not os.path.isfile(gitloc):
        print("warning: " + gitloc + " not found")
    else:
        cmd = subprocess.Popen([gitloc, "log", "--format=%h%n%ad", "-1"],
                               stdout=subprocess.PIPE)
        data = cmd.communicate()[0].strip()
        if cmd.returncode == 0:
            gitstamp, gitdate = data.split(b"\n")

    fd = open(os.path.join(OUTPUT_DIR, "version"), "w+")
    config = ConfigParser()
    config.add_section("cobbler")
    config.set("cobbler", "gitdate", str(gitdate))
    config.set("cobbler", "gitstamp", str(gitstamp))
    config.set("cobbler", "builddate", builddate)
    config.set("cobbler", "version", VERSION)
    config.set("cobbler", "version_tuple", str([int(x) for x in VERSION.split(".")]))
    config.write(fd)
    fd.close()

#####################################################################
# # Custom Distribution Class ########################################
#####################################################################


class Distribution(_Distribution):
    def __init__(self, *args, **kwargs):
        self.configure_files = []
        self.configure_values = {}
        self.man_pages = []
        _Distribution.__init__(self, *args, **kwargs)

#####################################################################
# # Modify Build Stage  ##############################################
#####################################################################


class build_py(_build_py):
    """Specialized Python source builder."""

    def run(self):
        gen_build_version()
        _build_py.run(self)

#####################################################################
# # Modify Build Stage  ##############################################
#####################################################################


class build(_build):
    """Specialized Python source builder."""

    def run(self):
        _build.run(self)

#####################################################################
# # Build man pages using Sphinx  ###################################
#####################################################################


class build_man(BuildDoc):
    def initialize_options(self):
        BuildDoc.initialize_options(self)
        self.builder = 'man'

#####################################################################
# # Configure files ##################################################
#####################################################################


class build_cfg(Command):

    description = "configure files (copy and substitute options)"

    user_options = [
        ('install-base=', None, "base installation directory"),
        ('install-platbase=', None, "base installation directory for platform-specific files "),
        ('install-purelib=', None, "installation directory for pure Python module distributions"),
        ('install-platlib=', None, "installation directory for non-pure module distributions"),
        ('install-lib=', None, "installation directory for all module distributions " + "(overrides --install-purelib and --install-platlib)"),
        ('install-headers=', None, "installation directory for C/C++ headers"),
        ('install-scripts=', None, "installation directory for Python scripts"),
        ('install-data=', None, "installation directory for data files"),
        ('force', 'f', "forcibly build everything (ignore file timestamps")
    ]

    boolean_options = ['force']

    def initialize_options(self):
        self.build_dir = None
        self.force = None
        self.install_base = None
        self.install_platbase = None
        self.install_scripts = None
        self.install_data = None
        self.install_purelib = None
        self.install_platlib = None
        self.install_lib = None
        self.install_headers = None
        self.root = None

    def finalize_options(self):
        self.set_undefined_options(
            'build',
            ('build_base', 'build_dir'),
            ('force', 'force')
        )
        self.set_undefined_options(
            'install',
            ('install_base', 'install_base'),
            ('install_platbase', 'install_platbase'),
            ('install_scripts', 'install_scripts'),
            ('install_data', 'install_data'),
            ('install_purelib', 'install_purelib'),
            ('install_platlib', 'install_platlib'),
            ('install_lib', 'install_lib'),
            ('install_headers', 'install_headers'),
            ('root', 'root')
        )

        if self.root:
            # We need the unrooted versions of this values
            for name in ('lib', 'purelib', 'platlib', 'scripts', 'data', 'headers'):
                attr = "install_" + name
                setattr(self, attr, '/' + os.path.relpath(getattr(self, attr), self.root))

        # Check if we are running under a virtualenv
        if hasattr(sys, 'real_prefix'):
            virtualenv = sys.prefix
        else:
            virtualenv = ""

        # The values to expand.
        self.configure_values = {
            'python_executable': sys.executable,
            'virtualenv': virtualenv,
            'install_base': os.path.normpath(self.install_base),
            'install_platbase': os.path.normpath(self.install_platbase),
            'install_scripts': os.path.normpath(self.install_scripts),
            'install_data': os.path.normpath(self.install_data),
            'install_purelib': os.path.normpath(self.install_purelib),
            'install_platlib': os.path.normpath(self.install_platlib),
            'install_lib': os.path.normpath(self.install_lib),
            'install_headers': os.path.normpath(self.install_headers),
        }
        self.configure_values.update(self.distribution.configure_values)

    def run(self):
        # On dry-run ignore missing source files.
        if self.dry_run:
            mode = 'newer'
        else:
            mode = 'error'
        # Work on all files
        for infile in self.distribution.configure_files:
            # We copy the files to build/
            outfile = os.path.join(self.build_dir, infile)
            # check if the file is out of date
            if self.force or dep_util.newer_group([infile, 'setup.py'], outfile, mode):
                # It is. Configure it
                self.configure_one_file(infile, outfile)

    def configure_one_file(self, infile, outfile):
        log.info("configuring %s" % infile)
        if not self.dry_run:
            # Read the file
            with codecs.open(infile, 'r', 'utf-8') as fh:
                before = fh.read()
            # Substitute the variables
            # Create the output directory if necessary
            outdir = os.path.dirname(outfile)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            # Write it into build/
            with codecs.open(outfile, 'w', 'utf-8') as fh:
                fh.write(self.substitute_values(before, self.configure_values))
            # The last step is to copy the permission bits
            shutil.copymode(infile, outfile)

    def substitute_values(self, string, values):
        for name, val in list(values.items()):
            # print("replacing @@%s@@ with %s" % (name, val))
            string = string.replace("@@%s@@" % (name), val)
        return string


def has_configure_files(build):
    """Check if the distribution has configuration files to work on."""
    return bool(build.distribution.configure_files)


def has_man_pages(build):
    """Check if the distribution has configuration files to work on."""
    return bool(build.distribution.man_pages)


build.sub_commands.extend((
    ('build_man', has_man_pages),
    ('build_cfg', has_configure_files)
))


#####################################################################
# # Modify Install Stage  ############################################
#####################################################################


class install(_install):
    """Specialised python package installer.

    It does some required chown calls in addition to the usual stuff.
    """

    def __init__(self, *args):
        _install.__init__(self, *args)

    def change_owner(self, path, owner):
        user = pwd.getpwnam(owner)
        try:
            log.info("changing mode of %s" % path)
            if not self.dry_run:
                # os.walk does not include the toplevel directory
                os.lchown(path, user.pw_uid, -1)
                # Now walk the directory and change them all
                for root, dirs, files in os.walk(path):
                    for dirname in dirs:
                        os.lchown(os.path.join(root, dirname), user.pw_uid, -1)
                    for filename in files:
                        os.lchown(os.path.join(root, filename), user.pw_uid, -1)
        except OSError as e:
            # We only check for errno = 1 (EPERM) here because its kinda
            # expected when installing as a non root user.
            if e.errno == 1:
                self.warn("Could not change owner: You have insufficient permissions.")
            else:
                raise e

    def run(self):
        # Run the usual stuff.
        _install.run(self)

        # If --root wasn't specified default to /usr/local
        if self.root is None:
            self.root = "/usr/local"

        # Hand over some directories to the webserver user
        path = os.path.join(self.install_data, 'share/cobbler/web')
        try:
            self.change_owner(path, http_user)
        except Exception as e:
            # building RPMs in a mock chroot, user 'apache' won't exist
            log.warning("Error in 'chown apache %s': %s" % (path, e))
        if not os.path.abspath(libpath):
            # The next line only works for absolute libpath
            raise Exception("libpath is not absolute.")
        # libpath is hardcoded in the code everywhere
        # therefor cant relocate using self.root
        path = os.path.join(self.root + libpath, 'webui_sessions')
        try:
            self.change_owner(path, http_user)
        except Exception as e:
            # building RPMs in a mock chroot, user 'apache' won't exist
            log.warning("Error in 'chown apache %s': %s" % (path, e))


#####################################################################
# # Test Command #####################################################
#####################################################################


class test_command(Command):
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pytest

        cov = Coverage()
        cov.erase()
        cov.start()

        result = pytest.main()

        cov.stop()
        cov.save()
        cov.html_report(directory="covhtml")
        sys.exit(int(bool(len(result.failures) > 0 or len(result.errors) > 0)))


#####################################################################
# # state command base class #########################################
#####################################################################

class statebase(Command):

    user_options = [
        ('statepath=', None, 'directory to backup configuration'),
        ('root=', None, 'install everything relative to this alternate root directory')
    ]

    def initialize_options(self):
        self.statepath = statepath
        self.root = None

    def finalize_options(self):
        pass

    def _copy(self, frm, to):
        if os.path.isdir(frm):
            to = os.path.join(to, os.path.basename(frm))
            log.debug("copying %s/ to %s/" % (frm, to))
            if not self.dry_run:
                if os.path.exists(to):
                    shutil.rmtree(to)
                shutil.copytree(frm, to)
        else:
            log.debug("copying %s to %s" % (frm, os.path.join(to, os.path.basename(frm))))
            if not self.dry_run:
                shutil.copy2(frm, to)

#####################################################################
# # restorestate command #############################################
#####################################################################


class restorestate(statebase):

    def _copy(self, frm, to):
        if self.root:
            to = self.root + to
        statebase._copy(self, frm, to)

    def run(self):
        log.info("restoring the current configuration from %s" % self.statepath)
        if not os.path.exists(self.statepath):
            self.warn("%s does not exist. Skipping" % self.statepath)
            return
        self._copy(os.path.join(self.statepath, 'collections'), libpath)
        self._copy(os.path.join(self.statepath, 'cobbler_web.conf'), webconfig)
        self._copy(os.path.join(self.statepath, 'cobbler.conf'), webconfig)
        self._copy(os.path.join(self.statepath, 'modules.conf'), etcpath)
        self._copy(os.path.join(self.statepath, 'settings'), etcpath)
        self._copy(os.path.join(self.statepath, 'users.conf'), etcpath)
        self._copy(os.path.join(self.statepath, 'users.digest'), etcpath)
        self._copy(os.path.join(self.statepath, 'dhcp.template'), etcpath)
        self._copy(os.path.join(self.statepath, 'rsync.template'), etcpath)

#####################################################################
# # savestate command ################################################
#####################################################################


class savestate(statebase):

    description = "Backup the current configuration to /tmp/cobbler_settings."

    def _copy(self, frm, to):
        if self.root:
            frm = self.root + frm
        statebase._copy(self, frm, to)

    def run(self):
        log.info("backing up the current configuration to %s" % self.statepath)
        if os.path.exists(self.statepath):
            log.debug("deleting existing %s" % self.statepath)
            if not self.dry_run:
                shutil.rmtree(self.statepath)
        if not self.dry_run:
            os.makedirs(self.statepath)
        self._copy(os.path.join(libpath, 'collections'), self.statepath)
        self._copy(os.path.join(webconfig, 'cobbler_web.conf'), self.statepath)
        self._copy(os.path.join(webconfig, 'cobbler.conf'), self.statepath)
        self._copy(os.path.join(etcpath, 'modules.conf'), self.statepath)
        self._copy(os.path.join(etcpath, 'settings'), self.statepath)
        self._copy(os.path.join(etcpath, 'users.conf'), self.statepath)
        self._copy(os.path.join(etcpath, 'users.digest'), self.statepath)
        self._copy(os.path.join(etcpath, 'dhcp.template'), self.statepath)
        self._copy(os.path.join(etcpath, 'rsync.template'), self.statepath)


#####################################################################
# # Actual Setup.py Script ###########################################
#####################################################################


if __name__ == "__main__":
    # # Configurable installation roots for various data files.

    # Trailing slashes on these vars is to allow for easy later configuration of relative paths if desired.
    docpath = "share/man"
    etcpath = "/etc/cobbler/"
    libpath = "/var/lib/cobbler/"
    logpath = "/var/log/"
    completion_path = "/usr/share/bash-completion/completions"
    statepath = "/tmp/cobbler_settings/devinstall"
    httpd_service = "httpd.service"
    suse_release = "suse" in distro.like()

    if suse_release:
        webconfig = "/etc/apache2/vhosts.d"
        webroot = "/srv/www/"
        http_user = "wwwrun"
        httpd_service = "apache2.service"
        defaultpath = "/etc/sysconfig/"
    elif distro.id() in ("debian", "ubuntu"):
        webconfig = "/etc/apache2/conf-available"
        webroot = "/var/www/"
        http_user = "www-data"
        httpd_service = "apache2.service"
        defaultpath = "/etc/default/"
    else:
        webconfig = "/etc/httpd/conf.d"
        webroot = "/var/www/"
        http_user = "apache"
        defaultpath = "/etc/sysconfig/"

    webcontent = webroot + "cobbler_webui_content/"
    webimages = webcontent + "/images"

    setup(
        distclass=Distribution,
        cmdclass={
            'build': build,
            'build_py': build_py,
            'test': test_command,
            'install': install,
            'savestate': savestate,
            'restorestate': restorestate,
            'build_cfg': build_cfg,
            'build_man': build_man
        },
        name="cobbler",
        version=VERSION,
        description="Network Boot and Update Server",
        long_description="Cobbler is a network install server. Cobbler supports PXE, virtualized installs, "
                         "and reinstalling existing Linux machines. The last two modes use a helper tool, 'koan', "
                         "that integrates with cobbler. There is also a web interface 'cobbler-web'. Cobbler's "
                         "advanced features include importing distributions from DVDs and rsync mirrors, automatic OS "
                         "installation templating, integrated yum mirroring, and built-in DHCP/DNS Management. "
                         "Cobbler has a XMLRPC API for integration with other applications.",
        author="Team Cobbler",
        author_email="cobbler.project@gmail.com",
        url="https://cobbler.github.io",
        license="GPLv2+",
        setup_requires=[
            "coverage",
            "distro",
            "future",
            "setuptools",
            "sphinx",
        ],
        install_requires=[
            "mod_wsgi",
            "requests",
            "future",
            "pyyaml",
            "simplejson",
            "netaddr",
            "Cheetah3",
            "Django",
            "pymongo",
            "distro",
            "ldap3",
            "dnspython",
            "tornado",
        ],
        extras_require={"lint": ["pyflakes", "pycodestyle"], "test": ["pytest", "pytest-cov", "codecov"]},
        packages=find_packages(exclude=["*tests*"]),
        scripts=[
            "bin/cobbler",
            "bin/cobblerd",
            "bin/cobbler-ext-nodes",
        ],
        configure_values={
            'webroot': os.path.normpath(webroot),
            'defaultpath': os.path.normpath(defaultpath),
            'httpd_service': httpd_service,
        },
        configure_files=[
            "config/cobbler/settings",
            "config/apache/cobbler.conf",
            "config/apache/cobbler_web.conf",
            "config/service/cobblerd.service",
        ],
        man_pages=[
            'docs/cobblerd.rst',
            'docs/cobbler-conf.rst',
            'docs/cobbler.rst'
        ],
        data_files=[
            # tftpd, hide in /usr/sbin
            ("sbin", ["bin/tftpd.py"]),
            ("sbin", ["bin/fence_ipmitool"]),
            ("%s" % webconfig, ["build/config/apache/cobbler.conf"]),
            ("%s" % webconfig, ["build/config/apache/cobbler_web.conf"]),
            ("%stemplates" % libpath, glob("autoinstall_templates/*")),
            ("%stemplates/install_profiles" % libpath, glob("autoinstall_templates/install_profiles/*")),
            ("%ssnippets" % libpath, glob("autoinstall_snippets/*", recursive=True)),
            ("%sscripts" % libpath, glob("autoinstall_scripts/*")),
            ("%s" % libpath, ["config/cobbler/distro_signatures.json"]),
            ("share/cobbler/web", glob("web/*.*")),
            ("%s" % webcontent, glob("web/static/*")),
            ("%s" % webimages, glob("web/static/images/*")),
            ("share/cobbler/bin", glob("scripts/*.sh")),
            ("share/cobbler/web/templates", glob("web/templates/*")),
            ("%swebui_sessions" % libpath, []),
            ("%sloaders" % libpath, []),
            ("%scobbler/misc" % webroot, glob("misc/*")),
            # Configuration
            ("%s" % etcpath, ["build/config/apache/cobbler.conf",
                              "build/config/apache/cobbler_web.conf",
                              "build/config/service/cobblerd.service",
                              "build/config/cobbler/settings"]),
            ("%ssettings.d" % etcpath, glob("config/cobbler/settings.d/*")),
            ("%s" % etcpath, ["config/cobbler/auth.conf",
                              "config/cobbler/modules.conf",
                              "config/cobbler/mongodb.conf",
                              "config/cobbler/users.conf",
                              "config/cobbler/users.digest",
                              "config/cheetah/cheetah_macros",
                              "config/rotate/cobblerd_rotate",
                              "config/rsync/import_rsync_whitelist",
                              "config/rsync/rsync.exclude",
                              "config/version"]),
            ("%s" % etcpath, glob("cobbler/etc/*")),
            ("%s" % etcpath, ["templates/etc/named.template",
                              "templates/etc/genders.template",
                              "templates/etc/secondary.template",
                              "templates/etc/zone.template",
                              "templates/etc/dnsmasq.template",
                              "templates/etc/rsync.template",
                              "templates/etc/dhcp.template",
                              "templates/etc/ndjbdns.template"]),
            ("%siso" % etcpath, glob("templates/iso/*")),
            ("%sboot_loader_conf" % etcpath, glob("templates/boot_loader_conf/*")),
            # completion_file
            ("%s" % completion_path, ["config/bash/completion/cobbler"]),
            ("%sgrub_config" % libpath, glob("config/grub/*")),
            # ToDo: Find a nice way to copy whole config/grub structure recursively
            # files
            ("%sgrub_config/grub" % libpath, glob("config/grub/grub/*")),
            # dirs
            ("%sgrub_config/grub/system" % libpath, []),
            ("%sgrub_config/grub/system_link" % libpath, []),
            ("%sreporting" % etcpath, glob("templates/reporting/*")),
            # Build empty directories to hold triggers
            ("%striggers/add/distro/pre" % libpath, []),
            ("%striggers/add/distro/post" % libpath, []),
            ("%striggers/add/profile/pre" % libpath, []),
            ("%striggers/add/profile/post" % libpath, []),
            ("%striggers/add/system/pre" % libpath, []),
            ("%striggers/add/system/post" % libpath, []),
            ("%striggers/add/repo/pre" % libpath, []),
            ("%striggers/add/repo/post" % libpath, []),
            ("%striggers/add/mgmtclass/pre" % libpath, []),
            ("%striggers/add/mgmtclass/post" % libpath, []),
            ("%striggers/add/package/pre" % libpath, []),
            ("%striggers/add/package/post" % libpath, []),
            ("%striggers/add/file/pre" % libpath, []),
            ("%striggers/add/file/post" % libpath, []),
            ("%striggers/delete/distro/pre" % libpath, []),
            ("%striggers/delete/distro/post" % libpath, []),
            ("%striggers/delete/profile/pre" % libpath, []),
            ("%striggers/delete/profile/post" % libpath, []),
            ("%striggers/delete/system/pre" % libpath, []),
            ("%striggers/delete/system/post" % libpath, []),
            ("%striggers/delete/repo/pre" % libpath, []),
            ("%striggers/delete/repo/post" % libpath, []),
            ("%striggers/delete/mgmtclass/pre" % libpath, []),
            ("%striggers/delete/mgmtclass/post" % libpath, []),
            ("%striggers/delete/package/pre" % libpath, []),
            ("%striggers/delete/package/post" % libpath, []),
            ("%striggers/delete/file/pre" % libpath, []),
            ("%striggers/delete/file/post" % libpath, []),
            ("%striggers/install/pre" % libpath, []),
            ("%striggers/install/post" % libpath, []),
            ("%striggers/install/firstboot" % libpath, []),
            ("%striggers/sync/pre" % libpath, []),
            ("%striggers/sync/post" % libpath, []),
            ("%striggers/change" % libpath, []),
            ("%striggers/task/distro/pre" % libpath, []),
            ("%striggers/task/distro/post" % libpath, []),
            ("%striggers/task/profile/pre" % libpath, []),
            ("%striggers/task/profile/post" % libpath, []),
            ("%striggers/task/system/pre" % libpath, []),
            ("%striggers/task/system/post" % libpath, []),
            ("%striggers/task/repo/pre" % libpath, []),
            ("%striggers/task/repo/post" % libpath, []),
            ("%striggers/task/mgmtclass/pre" % libpath, []),
            ("%striggers/task/mgmtclass/post" % libpath, []),
            ("%striggers/task/package/pre" % libpath, []),
            ("%striggers/task/package/post" % libpath, []),
            ("%striggers/task/file/pre" % libpath, []),
            ("%striggers/task/file/post" % libpath, []),
            # Build empty directories to hold the database
            ("%scollections" % libpath, []),
            ("%scollections/distros" % libpath, []),
            ("%scollections/images" % libpath, []),
            ("%scollections/profiles" % libpath, []),
            ("%scollections/repos" % libpath, []),
            ("%scollections/systems" % libpath, []),
            ("%scollections/mgmtclasses" % libpath, []),
            ("%scollections/packages" % libpath, []),
            ("%scollections/files" % libpath, []),
            # logfiles
            ("%scobbler/kicklog" % logpath, []),
            ("%scobbler/syslog" % logpath, []),
            ("%shttpd/cobbler" % logpath, []),
            ("%scobbler/anamon" % logpath, []),
            ("%scobbler/tasks" % logpath, []),
            # web page directories that we own
            ("%scobbler/localmirror" % webroot, []),
            ("%scobbler/repo_mirror" % webroot, []),
            ("%scobbler/distro_mirror" % webroot, []),
            ("%scobbler/distro_mirror/config" % webroot, []),
            ("%scobbler/links" % webroot, []),
            ("%scobbler/misc" % webroot, []),
            ("%scobbler/pub" % webroot, []),
            ("%scobbler/rendered" % webroot, []),
            ("%scobbler/images" % webroot, []),
            # A script that isn't really data, wsgi script
            ("%scobbler/svc/" % webroot, ["svc/services.py"]),
            # A script that isn't really data, wsgi script
            ("share/cobbler/web/", ["cobbler/web/settings.py"]),
            # zone-specific templates directory
            ("%szone_templates" % etcpath, glob("templates/zone_templates/*")),
            ("%s" % etcpath, ["config/cobbler/logging_config.conf"]),
            # man pages
            ("%s/man1" % docpath, glob("build/sphinx/man/*.1")),
            ("%s/man5" % docpath, glob("build/sphinx/man/*.5")),
            ("%s/man8" % docpath, glob("build/sphinx/man/*.8")),
        ],
    )
