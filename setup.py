#!/usr/bin/env python3

import os
import sys
import time
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


VERSION = "3.4.0"
OUTPUT_DIR = "config"

# # Configurable installation roots for various data files.
datadir = os.environ.get("DATAPATH", "/usr/share/cobbler")
docpath = os.environ.get("DOCPATH", "share/man")
etcpath = os.environ.get("ETCPATH", "/etc/cobbler")
libpath = os.environ.get("LIBPATH", "/var/lib/cobbler")
logpath = os.environ.get("LOG_PATH", "/var/log")
completion_path = os.environ.get(
    "COMPLETION_PATH", "/usr/share/bash-completion/completions"
)
statepath = os.environ.get("STATEPATH", "/tmp/cobbler_settings/devinstall")
http_user = os.environ.get("HTTP_USER", "wwwrun")
httpd_service = os.environ.get("HTTPD_SERVICE", "apache2.service")
webconfig = os.environ.get("WEBCONFIG", "/etc/apache2/vhosts.d")
webroot = os.environ.get("WEBROOT", "/srv/www")
tftproot = os.environ.get("TFTPROOT", "/srv/tftpboot")
bind_zonefiles = os.environ.get("ZONEFILES", "/var/lib/named/")
shim_folder = os.environ.get("SHIM_FOLDER", "/usr/share/efi/*/")
shim_file = os.environ.get("SHIM_FILE", r"shim\.efi")
ipxe_folder = os.environ.get("IPXE_FOLDER", "/usr/share/ipxe/")
memdisk_folder = os.environ.get("MEMDISK_FOLDER", "/usr/share/syslinux")
pxelinux_folder = os.environ.get("PXELINUX_FOLDER", "/usr/share/syslinux")
syslinux_dir = os.environ.get("SYSLINUX_DIR", "/usr/share/syslinux")
grub_mod_folder = os.environ.get("GRUB_MOD_FOLDER", "/usr/share/grub2")


#####################################################################
# # Helper Functions #################################################
#####################################################################


def glob(*args, **kwargs):
    recursive = kwargs.get("recursive", False)
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
                                recursive=True,
                            )
                        )
            else:
                # Always append normal files
                results.append(elem)
    return results


def read_readme_file():
    # read the contents of your README file
    this_directory = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
        return f.read()


#####################################################################


#####################################################################


def gen_build_version():
    buildepoch = int(os.environ.get("SOURCE_DATE_EPOCH", time.time()))
    builddate = time.asctime(time.gmtime(buildepoch))

    gitloc = "/usr/bin/git"
    gitdate = "?"
    gitstamp = "?"
    if not os.path.isfile(gitloc):
        print("warning: " + gitloc + " not found")
    else:
        cmd = subprocess.Popen(
            [gitloc, "log", "--format=%h%n%ad", "-1"], stdout=subprocess.PIPE
        )
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
        config.set(
            "cobbler", "version_tuple", str([int(x) for x in VERSION.split(".")])
        )
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
        self.builder = "man"


#####################################################################
# # Configure files ##################################################
#####################################################################


class build_cfg(Command):

    description = "configure files (copy and substitute options)"

    user_options = [
        ("install-base=", None, "base installation directory"),
        (
            "install-platbase=",
            None,
            "base installation directory for platform-specific files ",
        ),
        (
            "install-purelib=",
            None,
            "installation directory for pure Python module distributions",
        ),
        (
            "install-platlib=",
            None,
            "installation directory for non-pure module distributions",
        ),
        (
            "install-lib=",
            None,
            "installation directory for all module distributions "
            + "(overrides --install-purelib and --install-platlib)",
        ),
        ("install-headers=", None, "installation directory for C/C++ headers"),
        ("install-scripts=", None, "installation directory for Python scripts"),
        ("install-data=", None, "installation directory for data files"),
        ("force", "f", "forcibly build everything (ignore file timestamps"),
    ]

    boolean_options = ["force"]

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
            "build", ("build_base", "build_dir"), ("force", "force")
        )
        self.set_undefined_options(
            "install",
            ("install_base", "install_base"),
            ("install_platbase", "install_platbase"),
            ("install_scripts", "install_scripts"),
            ("install_data", "install_data"),
            ("install_purelib", "install_purelib"),
            ("install_platlib", "install_platlib"),
            ("install_lib", "install_lib"),
            ("install_headers", "install_headers"),
            ("root", "root"),
        )

        if self.root:
            # We need the unrooted versions of this values
            for name in ("lib", "purelib", "platlib", "scripts", "data", "headers"):
                attr = "install_" + name
                setattr(
                    self, attr, "/" + os.path.relpath(getattr(self, attr), self.root)
                )

        # Check if we are running under a virtualenv
        if hasattr(sys, "real_prefix"):
            virtualenv = sys.prefix
        else:
            virtualenv = ""

        # The values to expand.
        self.configure_values = {
            "python_executable": sys.executable,
            "virtualenv": virtualenv,
            "install_base": os.path.normpath(self.install_base),
            "install_platbase": os.path.normpath(self.install_platbase),
            "install_scripts": os.path.normpath(self.install_scripts),
            "install_data": os.path.normpath(self.install_data),
            "install_purelib": os.path.normpath(self.install_purelib),
            "install_platlib": os.path.normpath(self.install_platlib),
            "install_lib": os.path.normpath(self.install_lib),
            "install_headers": os.path.normpath(self.install_headers),
        }
        self.configure_values.update(self.distribution.configure_values)

    def run(self):
        # On dry-run ignore missing source files.
        if self.dry_run:
            mode = "newer"
        else:
            mode = "error"
        # Work on all files
        for infile in self.distribution.configure_files:
            # We copy the files to build/
            outfile = os.path.join(self.build_dir, infile)
            # check if the file is out of date
            if self.force or dep_util.newer_group([infile, "setup.py"], outfile, mode):
                # It is. Configure it
                self.configure_one_file(infile, outfile)

    def configure_one_file(self, infile, outfile):
        self.announce("configuring %s" % infile, 3)
        if not self.dry_run:
            # Read the file
            with codecs.open(infile, "r", "utf-8") as fh:
                before = fh.read()
            # Substitute the variables
            # Create the output directory if necessary
            outdir = os.path.dirname(outfile)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            # Write it into build/
            with codecs.open(outfile, "w", "utf-8") as fh:
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


build.sub_commands.extend(
    (("build_man", has_man_pages), ("build_cfg", has_configure_files))
)


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
            self.announce("changing mode of %s" % path, 3)
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
        ("statepath=", None, "directory to backup configuration"),
        ("root=", None, "install everything relative to this alternate root directory"),
    ]

    def initialize_options(self):
        self.statepath = statepath
        self.root = None

    def finalize_options(self):
        pass

    def _copy(self, frm, to):
        if os.path.isdir(frm):
            to = os.path.join(to, os.path.basename(frm))
            self.announce("copying %s/ to %s/" % (frm, to), 3)
            if not self.dry_run:
                if os.path.exists(to):
                    shutil.rmtree(to)
                shutil.copytree(frm, to)
        else:
            self.announce(
                "copying %s to %s" % (frm, os.path.join(to, os.path.basename(frm))), 3
            )
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
        self.announce("restoring the current configuration from %s" % self.statepath, 3)
        if not os.path.exists(self.statepath):
            self.warn("%s does not exist. Skipping" % self.statepath)
            return
        self._copy(os.path.join(self.statepath, "collections"), libpath)
        self._copy(os.path.join(self.statepath, "cobbler.conf"), webconfig)
        self._copy(os.path.join(self.statepath, "settings.yaml"), etcpath)
        self._copy(os.path.join(self.statepath, "users.conf"), etcpath)
        self._copy(os.path.join(self.statepath, "users.digest"), etcpath)
        self._copy(os.path.join(self.statepath, "dhcp.template"), etcpath)
        self._copy(os.path.join(self.statepath, "dhcp6.template"), etcpath)
        self._copy(os.path.join(self.statepath, "rsync.template"), etcpath)


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
        self.announce("backing up the current configuration to %s" % self.statepath, 3)
        if os.path.exists(self.statepath):
            self.announce("deleting existing %s" % self.statepath, 3)
            if not self.dry_run:
                shutil.rmtree(self.statepath)
        if not self.dry_run:
            os.makedirs(self.statepath)
        self._copy(os.path.join(libpath, "collections"), self.statepath)
        self._copy(os.path.join(webconfig, "cobbler.conf"), self.statepath)
        self._copy(os.path.join(etcpath, "settings.yaml"), self.statepath)
        self._copy(os.path.join(etcpath, "users.conf"), self.statepath)
        self._copy(os.path.join(etcpath, "users.digest"), self.statepath)
        self._copy(os.path.join(etcpath, "dhcp.template"), self.statepath)
        self._copy(os.path.join(etcpath, "dhcp6.template"), self.statepath)
        self._copy(os.path.join(etcpath, "rsync.template"), self.statepath)


#####################################################################
# # Actual Setup.py Script ###########################################
#####################################################################


if __name__ == "__main__":
    setup(
        distclass=Distribution,
        cmdclass={
            "build": build,
            "build_py": build_py,
            "test": test_command,
            "install": install,
            "savestate": savestate,
            "restorestate": restorestate,
            "build_cfg": build_cfg,
            "build_man": build_man,
        },
        name="cobbler",
        version=VERSION,
        description="Network Boot and Update Server",
        long_description=read_readme_file(),
        long_description_content_type="text/markdown",
        author="Team Cobbler",
        author_email="cobbler.project@gmail.com",
        project_urls={
            "Website": "https://cobbler.github.io",
            "Documentation (Users)": "https://cobbler.readthedocs.io/en/latest",
            "Documentation (Devs)": "https://github.com/cobbler/cobbler/wiki",
            "Source": "https://github.com/cobbler/cobbler",
            "Tracker": "https://github.com/cobbler/cobbler/issues",
        },
        license="GPLv2+",
        classifiers=[
            "Development Status :: 5 - Production/Stable",
            "License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)",
            "Programming Language :: Python :: 3.6",
            "Topic :: System :: Installation/Setup",
            "Topic :: System :: Systems Administration",
            "Intended Audience :: System Administrators",
            "Natural Language :: English",
            "Operating System :: POSIX :: Linux",
        ],
        keywords=["pxe", "autoinstallation", "dhcp", "tftp", "provisioning"],
        install_requires=[
            "requests",
            "pyyaml",
            "netaddr",
            "Cheetah3",
            "pymongo",
            "distro",
            "python-ldap",
            "dnspython",
            "file-magic",
            "schema",
            "gunicorn",
            "importlib-resources",
        ],
        extras_require={
            "lint": [
                "pyflakes",
                "pycodestyle",
                "pylint",
                "black",
                "mypy",
                "pre-commit",
            ],
            "test": ["pytest>6", "pytest-cov", "codecov", "pytest-mock"],
            "docs": ["sphinx", "sphinx-rtd-theme", "sphinxcontrib-apidoc"],
        },
        packages=find_packages(exclude=["*tests*"]),
        scripts=[
            "bin/cobbler",
            "bin/cobblerd",
            "bin/cobbler-ext-nodes",
            "bin/cobbler-settings",
        ],
        configure_values={
            "webroot": os.path.normpath(webroot),
            "tftproot": os.path.normpath(tftproot),
            "httpd_service": httpd_service,
            "bind_zonefiles": bind_zonefiles,
            "shim_folder": shim_folder,
            "shim_file": shim_file,
            "ipxe_folder": ipxe_folder,
            "memdisk_folder": memdisk_folder,
            "pxelinux_folder": pxelinux_folder,
            "syslinux_dir": syslinux_dir,
            "grub_mod_folder": grub_mod_folder,
        },
        configure_files=[
            "config/apache/cobbler.conf",
            "config/nginx/cobbler.conf",
            "config/cobbler/settings.yaml",
            "config/service/cobblerd.service",
            # "templates/etc/named.template",
            # "templates/etc/secondary.template",
        ],
        man_pages=["docs/cobblerd.rst", "docs/cobbler-conf.rst", "docs/cobbler.rst"],
        data_files=[
            ("%s" % webconfig, ["build/config/apache/cobbler.conf"]),
            ("%s" % libpath, ["config/cobbler/distro_signatures.json"]),
            ("share/cobbler/bin", glob("scripts/*")),
            ("%s/loaders" % libpath, []),
            ("%s/misc" % libpath, glob("misc/*")),
            # Configuration
            (f"{etcpath}/apache", ["build/config/apache/cobbler.conf"]),
            (f"{etcpath}/nginx", ["build/config/nginx/cobbler.conf"]),
            (
                "%s" % etcpath,
                [
                    "build/config/service/cobblerd.service",
                    "build/config/cobbler/settings.yaml",
                ],
            ),
            (
                "%s" % etcpath,
                [
                    "config/cobbler/auth.conf",
                    "config/cobbler/users.conf",
                    "config/cobbler/users.digest",
                    "config/cheetah/cheetah_macros",
                    "config/rotate/cobblerd_rotate",
                    "config/rsync/import_rsync_whitelist",
                    "config/rsync/rsync.exclude",
                    "config/service/cobblerd-gunicorn.service",
                    "config/version",
                ],
            ),
            ("%s" % etcpath, glob("cobbler/etc/*")),
            # completion_file
            ("%s" % completion_path, ["config/bash/completion/cobbler"]),
            ("%s/grub_config" % libpath, glob("config/grub/*")),
            # ToDo: Find a nice way to copy whole config/grub structure recursively
            # files
            ("%s/grub_config/grub" % libpath, glob("config/grub/grub/*")),
            # dirs
            ("%s/grub_config/grub/system" % libpath, []),
            ("%s/grub_config/grub/system_link" % libpath, []),
            # logfiles
            ("%s/cobbler/kicklog" % logpath, []),
            ("%s/cobbler/syslog" % logpath, []),
            ("%s/httpd/cobbler" % logpath, []),
            ("%s/cobbler/anamon" % logpath, []),
            ("%s/cobbler/tasks" % logpath, []),
            ("%s" % etcpath, ["config/cobbler/logging_config.conf"]),
            # man pages
            ("%s/man1" % docpath, glob("build/sphinx/man/*.1")),
            ("%s/man5" % docpath, glob("build/sphinx/man/*.5")),
            ("%s/man8" % docpath, glob("build/sphinx/man/*.8")),
            # tests
            ("%s/tests" % datadir, glob("tests/*.py")),
            ("%s/tests/actions" % datadir, glob("tests/actions/*.py")),
            (
                "%s/tests/actions/buildiso" % datadir,
                glob("tests/actions/buildiso/*.py"),
            ),
            ("%s/tests/api" % datadir, glob("tests/api/*.py")),
            ("%s/tests/cli" % datadir, glob("tests/cli/*.py")),
            ("%s/tests/collections" % datadir, glob("tests/collections/*.py")),
            ("%s/tests/items" % datadir, glob("tests/items/*.py")),
            ("%s/tests/modules" % datadir, glob("tests/modules/*.py")),
            (
                "%s/tests/modules/authentication" % datadir,
                glob("tests/modules/authentication/*.py"),
            ),
            (
                "%s/tests/modules/authorization" % datadir,
                glob("tests/modules/authorization/*.py"),
            ),
            (
                "%s/tests/modules/installation" % datadir,
                glob("tests/modules/installation/*.py"),
            ),
            (
                "%s/tests/modules/managers" % datadir,
                glob("tests/modules/managers/*.py"),
            ),
            (
                "%s/tests/modules/serializer" % datadir,
                glob("tests/modules/serializer/*.py"),
            ),
            ("%s/tests/settings" % datadir, glob("tests/settings/*.py")),
            (
                "%s/tests/settings/migrations" % datadir,
                glob("tests/settings/migrations/*.py"),
            ),
            ("%s/tests/special_cases" % datadir, glob("tests/special_cases/*.py")),
            ("%s/tests/test_data" % datadir, glob("tests/test_data/*")),
            ("%s/tests/test_data/V2_8_5" % datadir, glob("tests/test_data/V2_8_5/*")),
            ("%s/tests/test_data/V3_0_0" % datadir, glob("tests/test_data/V3_0_0/*")),
            (
                "%s/tests/test_data/V3_0_0/settings.d" % datadir,
                glob("tests/test_data/V3_0_0/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_0_1" % datadir, glob("tests/test_data/V3_0_1/*")),
            (
                "%s/tests/test_data/V3_0_1/settings.d" % datadir,
                glob("tests/test_data/V3_0_1/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_1_0" % datadir, glob("tests/test_data/V3_1_0/*")),
            (
                "%s/tests/test_data/V3_1_0/settings.d" % datadir,
                glob("tests/test_data/V3_1_0/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_1_1" % datadir, glob("tests/test_data/V3_1_1/*")),
            (
                "%s/tests/test_data/V3_1_1/settings.d" % datadir,
                glob("tests/test_data/V3_1_1/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_1_2" % datadir, glob("tests/test_data/V3_1_2/*")),
            (
                "%s/tests/test_data/V3_1_2/settings.d" % datadir,
                glob("tests/test_data/V3_1_2/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_2_0" % datadir, glob("tests/test_data/V3_2_0/*")),
            (
                "%s/tests/test_data/V3_2_0/settings.d" % datadir,
                glob("tests/test_data/V3_2_0/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_2_1" % datadir, glob("tests/test_data/V3_2_1/*")),
            (
                "%s/tests/test_data/V3_2_1/settings.d" % datadir,
                glob("tests/test_data/V3_2_1/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_3_0" % datadir, glob("tests/test_data/V3_3_0/*")),
            (
                "%s/tests/test_data/V3_3_0/settings.d" % datadir,
                glob("tests/test_data/V3_3_0/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_3_1" % datadir, glob("tests/test_data/V3_3_1/*")),
            (
                "%s/tests/test_data/V3_3_1/settings.d" % datadir,
                glob("tests/test_data/V3_3_1/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_3_2" % datadir, glob("tests/test_data/V3_3_2/*")),
            (
                "%s/tests/test_data/V3_3_2/settings.d" % datadir,
                glob("tests/test_data/V3_3_2/settings.d/*"),
            ),
            ("%s/tests/test_data/V3_3_3" % datadir, glob("tests/test_data/V3_3_3/*")),
            (
                "%s/tests/test_data/V3_3_3/settings.d" % datadir,
                glob("tests/test_data/V3_3_3/settings.d/*"),
            ),
            ("%s/tests/xmlrpcapi" % datadir, glob("tests/xmlrpcapi/*.py")),
            ("%s/tests/test_data/V3_4_0" % datadir, glob("tests/test_data/V3_4_0/*")),
            ("%s/tests/utils" % datadir, glob("tests/utils/*.py")),
            # tests containers subpackage
            ("%s/docker" % datadir, glob("docker/*")),
            ("%s/docker/debs" % datadir, glob("docker/debs/*")),
            ("%s/docker/debs/Debian_10" % datadir, glob("docker/debs/Debian_10/*")),
            (
                "%s/docker/debs/Debian_10/supervisord" % datadir,
                glob("docker/debs/Debian_10/supervisord/*"),
            ),
            (
                "%s/docker/debs/Debian_10/supervisord/conf.d" % datadir,
                glob("docker/debs/Debian_10/supervisord/conf.d/*"),
            ),
            ("%s/docker/debs/Debian_11" % datadir, glob("docker/debs/Debian_11/*")),
            (
                "%s/docker/debs/Debian_11/supervisord" % datadir,
                glob("docker/debs/Debian_11/supervisord/*"),
            ),
            (
                "%s/docker/debs/Debian_11/supervisord/conf.d" % datadir,
                glob("docker/debs/Debian_11/supervisord/conf.d/*"),
            ),
            ("%s/docker/develop" % datadir, glob("docker/develop/*")),
            ("%s/docker/develop/openldap" % datadir, glob("docker/develop/openldap/*")),
            ("%s/docker/develop/pam" % datadir, glob("docker/develop/pam/*")),
            ("%s/docker/develop/scripts" % datadir, glob("docker/develop/scripts/*")),
            (
                "%s/docker/develop/supervisord" % datadir,
                glob("docker/develop/supervisord/*"),
            ),
            (
                "%s/docker/develop/supervisord/conf.d" % datadir,
                glob("docker/develop/supervisord/conf.d/*"),
            ),
            ("%s/docker/rpms" % datadir, glob("docker/rpms/*")),
            ("%s/docker/rpms/Fedora_34" % datadir, glob("docker/rpms/Fedora_34/*")),
            (
                "%s/docker/rpms/Fedora_34/supervisord" % datadir,
                glob("docker/rpms/Fedora_34/supervisord/*"),
            ),
            (
                "%s/docker/rpms/Fedora_34/supervisord/conf.d" % datadir,
                glob("docker/rpms/Fedora_34/supervisord/conf.d/*"),
            ),
            (
                "%s/docker/rpms/Rocky_Linux_8" % datadir,
                glob("docker/rpms/Rocky_Linux_8/*"),
            ),
            (
                "%s/docker/rpms/opensuse_leap" % datadir,
                glob("docker/rpms/opensuse_leap/*"),
            ),
            (
                "%s/docker/rpms/opensuse_leap/supervisord" % datadir,
                glob("docker/rpms/opensuse_leap/supervisord/*"),
            ),
            (
                "%s/docker/rpms/opensuse_leap/supervisord/conf.d" % datadir,
                glob("docker/rpms/opensuse_leap/supervisord/conf.d/*"),
            ),
            (
                "%s/docker/rpms/opensuse_tumbleweed" % datadir,
                glob("docker/rpms/opensuse_tumbleweed/*"),
            ),
            (
                "%s/docker/rpms/opensuse_tumbleweed/supervisord" % datadir,
                glob("docker/rpms/opensuse_tumbleweed/supervisord/*"),
            ),
            (
                "%s/docker/rpms/opensuse_tumbleweed/supervisord/conf.d" % datadir,
                glob("docker/rpms/opensuse_tumbleweed/supervisord/conf.d/*"),
            ),
        ],
    )
