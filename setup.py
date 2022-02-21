#!/usr/bin/env python3

import os
import sys
import time
import logging
import glob as _glob

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


VERSION = "3.3.2"
OUTPUT_DIR = "config"

log = logging.getLogger("setup.py")

# # Configurable installation roots for various data files.
datadir = os.environ.get('DATAPATH', '/usr/share/cobbler')
docpath = os.environ.get('DOCPATH', "share/man")
etcpath = os.environ.get('ETCPATH', "/etc/cobbler")
libpath = os.environ.get('LIBPATH', "/var/lib/cobbler")
logpath = os.environ.get('LOG_PATH', "/var/log")
completion_path = os.environ.get('COMPLETION_PATH', "/usr/share/bash-completion/completions")
statepath = os.environ.get('STATEPATH', "/tmp/cobbler_settings/devinstall")
http_user = os.environ.get('HTTP_USER', "wwwrun")
httpd_service = os.environ.get('HTTPD_SERVICE', "apache2.service")
webconfig = os.environ.get('WEBCONFIG', "/etc/apache2/vhosts.d")
webroot = os.environ.get('WEBROOT', "/srv/www")
tftproot = os.environ.get('TFTPROOT', "/srv/tftpboot")
bind_zonefiles = os.environ.get('ZONEFILES', "/var/lib/named/")
shim_folder = os.environ.get('SHIM_FOLDER', "/usr/share/efi/*/")
shim_file = os.environ.get('SHIM_FILE', r"shim\.efi")
ipxe_folder = os.environ.get('IPXE_FOLDER', '/usr/share/ipxe/')
memdisk_folder = os.environ.get('MEMDISK_FOLDER', '/usr/share/syslinux')
pxelinux_folder = os.environ.get('PXELINUX_FOLDER', '/usr/share/syslinux')
syslinux_dir = os.environ.get('SYSLINUX_DIR', '/usr/share/syslinux')
grub_mod_folder = os.environ.get('GRUB_MOD_FOLDER', '/usr/share/grub2')


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


def read_readme_file():
    # read the contents of your README file
    this_directory = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(this_directory, 'README.md'), encoding='utf-8') as f:
        return f.read()

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
            gitstamp, gitdate = data.decode("utf8").split("\n")

    with open(os.path.join(OUTPUT_DIR, "version"), "w+") as version_file:
        config = ConfigParser()
        config.add_section("cobbler")
        config.set("cobbler", "gitdate", str(gitdate))
        config.set("cobbler", "gitstamp", str(gitstamp))
        config.set("cobbler", "builddate", builddate)
        config.set("cobbler", "version", VERSION)
        config.set("cobbler", "version_tuple", str([int(x) for x in VERSION.split(".")]))
        config.write(version_file)

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
        self._copy(os.path.join(self.statepath, 'cobbler.conf'), webconfig)
        self._copy(os.path.join(self.statepath, 'modules.conf'), etcpath)
        self._copy(os.path.join(self.statepath, 'settings.yaml'), etcpath)
        self._copy(os.path.join(self.statepath, 'users.conf'), etcpath)
        self._copy(os.path.join(self.statepath, 'users.digest'), etcpath)
        self._copy(os.path.join(self.statepath, 'dhcp.template'), etcpath)
        self._copy(os.path.join(self.statepath, 'dhcp6.template'), etcpath)
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
        self._copy(os.path.join(webconfig, 'cobbler.conf'), self.statepath)
        self._copy(os.path.join(etcpath, 'modules.conf'), self.statepath)
        self._copy(os.path.join(etcpath, 'settings.yaml'), self.statepath)
        self._copy(os.path.join(etcpath, 'users.conf'), self.statepath)
        self._copy(os.path.join(etcpath, 'users.digest'), self.statepath)
        self._copy(os.path.join(etcpath, 'dhcp.template'), self.statepath)
        self._copy(os.path.join(etcpath, 'dhcp6.template'), self.statepath)
        self._copy(os.path.join(etcpath, 'rsync.template'), self.statepath)


#####################################################################
# # Actual Setup.py Script ###########################################
#####################################################################


if __name__ == "__main__":
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
        long_description=read_readme_file(),
        long_description_content_type='text/markdown',
        author="Team Cobbler",
        author_email="cobbler.project@gmail.com",
        project_urls={
            'Website': 'https://cobbler.github.io',
            'Documentation (Users)': 'https://cobbler.readthedocs.io/en/latest',
            'Documentation (Devs)': 'https://github.com/cobbler/cobbler/wiki',
            'Source': 'https://github.com/cobbler/cobbler',
            'Tracker': 'https://github.com/cobbler/cobbler/issues'
        },
        license="GPLv2+",
        setup_requires=[
            "coverage",
            "distro",
            "setuptools",
            "sphinx",
        ],
        install_requires=[
            "mod_wsgi",
            "requests",
            "pyyaml",
            "netaddr",
            "Cheetah3",
            "pymongo",
            "distro",
            "python-ldap",
            "dnspython",
            "file-magic",
            "schema"
        ],
        extras_require={
            "lint": ["pyflakes", "pycodestyle"],
            "test": ["pytest", "pytest-cov", "codecov", "pytest-mock"]
        },
        packages=find_packages(exclude=["*tests*"]),
        scripts=[
            "bin/cobbler",
            "bin/cobblerd",
            "bin/cobbler-ext-nodes",
            "bin/cobbler-settings"
        ],
        configure_values={
            'webroot': os.path.normpath(webroot),
            'tftproot': os.path.normpath(tftproot),
            'httpd_service': httpd_service,
            'bind_zonefiles': bind_zonefiles,
            'shim_folder': shim_folder,
            'shim_file': shim_file,
            'ipxe_folder': ipxe_folder,
            'memdisk_folder': memdisk_folder,
            'pxelinux_folder': pxelinux_folder,
            'syslinux_dir': syslinux_dir,
            'grub_mod_folder': grub_mod_folder
        },
        configure_files=[
            "cobbler/settings/migrations/V3_3_1.py",
            "config/apache/cobbler.conf",
            "config/cobbler/settings.yaml",
            "config/service/cobblerd.service",
            "templates/etc/named.template",
            "templates/etc/secondary.template",
        ],
        man_pages=[
            'docs/cobblerd.rst',
            'docs/cobbler-conf.rst',
            'docs/cobbler.rst'
        ],
        data_files=[
            ("%s" % webconfig, ["build/config/apache/cobbler.conf"]),
            ("%s/templates" % libpath, glob("autoinstall_templates/*")),
            ("%s/templates/install_profiles" % libpath, glob("autoinstall_templates/install_profiles/*")),
            ("%s/snippets" % libpath, glob("autoinstall_snippets/*", recursive=True)),
            ("%s/scripts" % libpath, glob("autoinstall_scripts/*")),
            ("%s" % libpath, ["config/cobbler/distro_signatures.json"]),
            ("share/cobbler/bin", glob("scripts/*")),
            ("%s/loaders" % libpath, []),
            ("%s/cobbler/misc" % webroot, glob("misc/*")),
            # Configuration
            ("%s" % etcpath, ["build/config/apache/cobbler.conf",
                              "build/config/service/cobblerd.service",
                              "build/config/cobbler/settings.yaml"]),
            ("%s/settings.d" % etcpath, glob("config/cobbler/settings.d/*")),
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
                              "templates/etc/dhcp6.template",
                              "templates/etc/ndjbdns.template"]),
            ("%s/iso" % etcpath, glob("templates/iso/*")),
            ("%s/boot_loader_conf" % etcpath, glob("templates/boot_loader_conf/*")),
            # completion_file
            ("%s" % completion_path, ["config/bash/completion/cobbler"]),
            ("%s/grub_config" % libpath, glob("config/grub/*")),
            # ToDo: Find a nice way to copy whole config/grub structure recursively
            # files
            ("%s/grub_config/grub" % libpath, glob("config/grub/grub/*")),
            # dirs
            ("%s/boot" % tftproot, []),
            ("%s/etc" % tftproot, []),
            ("%s/grub" % tftproot, []),
            ("%s/images" % tftproot, []),
            ("%s/images2" % tftproot, []),
            ("%s/ppc" % tftproot, []),
            ("%s/s390x" % tftproot, []),
            ("%s/pxelinux.cfg" % tftproot, []),
            ("%s/ipxe" % tftproot, []),
            ("%s/grub/system" % tftproot, []),
            ("%s/grub/system_link" % tftproot, []),
            ("%s/grub_config/grub/system" % libpath, []),
            ("%s/grub_config/grub/system_link" % libpath, []),
            ("%s/reporting" % etcpath, glob("templates/reporting/*")),
            # Build empty directories to hold triggers
            ("%s/triggers/add/distro/pre" % libpath, []),
            ("%s/triggers/add/distro/post" % libpath, []),
            ("%s/triggers/add/profile/pre" % libpath, []),
            ("%s/triggers/add/profile/post" % libpath, []),
            ("%s/triggers/add/system/pre" % libpath, []),
            ("%s/triggers/add/system/post" % libpath, []),
            ("%s/triggers/add/repo/pre" % libpath, []),
            ("%s/triggers/add/repo/post" % libpath, []),
            ("%s/triggers/add/mgmtclass/pre" % libpath, []),
            ("%s/triggers/add/mgmtclass/post" % libpath, []),
            ("%s/triggers/add/package/pre" % libpath, []),
            ("%s/triggers/add/package/post" % libpath, []),
            ("%s/triggers/add/file/pre" % libpath, []),
            ("%s/triggers/add/file/post" % libpath, []),
            ("%s/triggers/add/menu/pre" % libpath, []),
            ("%s/triggers/add/menu/post" % libpath, []),
            ("%s/triggers/delete/distro/pre" % libpath, []),
            ("%s/triggers/delete/distro/post" % libpath, []),
            ("%s/triggers/delete/profile/pre" % libpath, []),
            ("%s/triggers/delete/profile/post" % libpath, []),
            ("%s/triggers/delete/system/pre" % libpath, []),
            ("%s/triggers/delete/system/post" % libpath, []),
            ("%s/triggers/delete/repo/pre" % libpath, []),
            ("%s/triggers/delete/repo/post" % libpath, []),
            ("%s/triggers/delete/mgmtclass/pre" % libpath, []),
            ("%s/triggers/delete/mgmtclass/post" % libpath, []),
            ("%s/triggers/delete/package/pre" % libpath, []),
            ("%s/triggers/delete/package/post" % libpath, []),
            ("%s/triggers/delete/file/pre" % libpath, []),
            ("%s/triggers/delete/file/post" % libpath, []),
            ("%s/triggers/delete/menu/pre" % libpath, []),
            ("%s/triggers/delete/menu/post" % libpath, []),
            ("%s/triggers/install/pre" % libpath, []),
            ("%s/triggers/install/post" % libpath, []),
            ("%s/triggers/install/firstboot" % libpath, []),
            ("%s/triggers/sync/pre" % libpath, []),
            ("%s/triggers/sync/post" % libpath, []),
            ("%s/triggers/change" % libpath, []),
            ("%s/triggers/task/distro/pre" % libpath, []),
            ("%s/triggers/task/distro/post" % libpath, []),
            ("%s/triggers/task/profile/pre" % libpath, []),
            ("%s/triggers/task/profile/post" % libpath, []),
            ("%s/triggers/task/system/pre" % libpath, []),
            ("%s/triggers/task/system/post" % libpath, []),
            ("%s/triggers/task/repo/pre" % libpath, []),
            ("%s/triggers/task/repo/post" % libpath, []),
            ("%s/triggers/task/mgmtclass/pre" % libpath, []),
            ("%s/triggers/task/mgmtclass/post" % libpath, []),
            ("%s/triggers/task/package/pre" % libpath, []),
            ("%s/triggers/task/package/post" % libpath, []),
            ("%s/triggers/task/file/pre" % libpath, []),
            ("%s/triggers/task/file/post" % libpath, []),
            ("%s/triggers/task/menu/pre" % libpath, []),
            ("%s/triggers/task/menu/post" % libpath, []),
            # Build empty directories to hold the database
            ("%s/collections" % libpath, []),
            ("%s/collections/distros" % libpath, []),
            ("%s/collections/images" % libpath, []),
            ("%s/collections/profiles" % libpath, []),
            ("%s/collections/repos" % libpath, []),
            ("%s/collections/systems" % libpath, []),
            ("%s/collections/mgmtclasses" % libpath, []),
            ("%s/collections/packages" % libpath, []),
            ("%s/collections/files" % libpath, []),
            ("%s/collections/menus" % libpath, []),
            # logfiles
            ("%s/cobbler/kicklog" % logpath, []),
            ("%s/cobbler/syslog" % logpath, []),
            ("%s/httpd/cobbler" % logpath, []),
            ("%s/cobbler/anamon" % logpath, []),
            ("%s/cobbler/tasks" % logpath, []),
            # web page directories that we own
            ("%s/cobbler/localmirror" % webroot, []),
            ("%s/cobbler/repo_mirror" % webroot, []),
            ("%s/cobbler/distro_mirror" % webroot, []),
            ("%s/cobbler/distro_mirror/config" % webroot, []),
            ("%s/cobbler/links" % webroot, []),
            ("%s/cobbler/misc" % webroot, []),
            ("%s/cobbler/pub" % webroot, []),
            ("%s/cobbler/rendered" % webroot, []),
            ("%s/cobbler/images" % webroot, []),
            # A script that isn't really data, wsgi script
            ("%s/cobbler/svc/" % webroot, ["svc/services.py"]),
            # zone-specific templates directory
            ("%s/zone_templates" % etcpath, glob("templates/zone_templates/*")),
            # windows-specific templates directory
            ("%s/windows" % etcpath, glob("templates/windows/*")),
            ("%s" % etcpath, ["config/cobbler/logging_config.conf"]),
            # man pages
            ("%s/man1" % docpath, glob("build/sphinx/man/*.1")),
            ("%s/man5" % docpath, glob("build/sphinx/man/*.5")),
            ("%s/man8" % docpath, glob("build/sphinx/man/*.8")),
            ("%s/tests" % datadir, glob("tests/*.py")),
            ("%s/tests/cli" % datadir, glob("tests/cli/*.py")),
            ("%s/tests/modules" % datadir, glob("tests/modules/*.py")),
            ("%s/tests/modules/authentication" % datadir, glob("tests/modules/authentication/*.py")),
            ("%s/tests/xmlrpcapi" % datadir, glob("tests/xmlrpcapi/*.py")),
        ],
    )
