#!/usr/bin/env python

import os
import sys
import time
import glob as _glob

from distutils.core import setup, Command
from distutils.command.build import build as _build
from distutils.command.install import install as _install
from distutils.command.build_py import build_py as _build_py
from distutils import log
from distutils import dep_util
from distutils.dist import Distribution as _Distribution
from ConfigParser import ConfigParser

import codecs
import unittest
import exceptions
import pwd
import shutil
import subprocess

try:
    import coverage
except:
    pass

VERSION = "2.9.0"
OUTPUT_DIR = "config"


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
    builddate = time.asctime()
    cmd = subprocess.Popen(["/usr/bin/git", "log", "--format=%h%n%ad", "-1"], stdout=subprocess.PIPE)
    data = cmd.communicate()[0].strip()
    if cmd.returncode == 0:
        gitstamp, gitdate = data.split("\n")
    else:
        gitdate = "?"
        gitstamp = "?"

    fd = open(os.path.join(OUTPUT_DIR, "version"), "w+")
    config = ConfigParser()
    config.add_section("cobbler")
    config.set("cobbler", "gitdate", gitdate)
    config.set("cobbler", "gitstamp", gitstamp)
    config.set("cobbler", "builddate", builddate)
    config.set("cobbler", "version", VERSION)
    config.set("cobbler", "version_tuple", [int(x) for x in VERSION.split(".")])
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
# # Configure files ##################################################
#####################################################################


class build_cfg(Command):

    description = "configure files (copy and substitute options)"

    user_options = [
        ('install-base=', None, "base installation directory"),
        ('install-platbase=', None, "base installation directory for platform-specific files "),
        ('install-purelib=', None, "installation directory for pure Python module distributions"),
        ('install-platlib=', None, "installation directory for non-pure module distributions"),
        ('install-lib=', None, "installation directory for all module distributions " +
         "(overrides --install-purelib and --install-platlib)"),
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
        self.announce("configuring %s" % (infile), log.INFO)
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
        for name, val in values.iteritems():
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
# # Build man pages ##################################################
#####################################################################


class build_man(Command):

    decription = "build man pages"

    user_options = [
        ('force', 'f', "forcibly build everything (ignore file timestamps")
    ]

    boolean_options = ['force']

    def initialize_options(self):
        self.build_dir = None
        self.force = None

    def finalize_options(self):
        self.set_undefined_options(
            'build',
            ('build_base', 'build_dir'),
            ('force', 'force')
        )

    def run(self):
        """Generate the man pages... this is currently done through POD,
        possible future version may do this through some Python mechanism
        (maybe conversion from ReStructured Text (.rst))...
        """
        # On dry-run ignore missing source files.
        if self.dry_run:
            mode = 'newer'
        else:
            mode = 'error'
        # Work on all files
        for infile in self.distribution.man_pages:
            # We copy the files to build/
            outfile = os.path.join(self.build_dir, os.path.splitext(infile)[0] + '.gz')
            # check if the file is out of date
            if self.force or dep_util.newer_group([infile], outfile, mode):
                # It is. Configure it
                self.build_one_file(infile, outfile)

    _COMMAND = 'pod2man --center="%s" --release="" %s | gzip -c > %s'

    def build_one_file(self, infile, outfile):
        man = os.path.splitext(os.path.splitext(os.path.basename(infile))[0])[0]
        self.announce("building %s manpage" % (man), log.INFO)
        if not self.dry_run:
            # Create the output directory if necessary
            outdir = os.path.dirname(outfile)
            if not os.path.exists(outdir):
                os.makedirs(outdir)
            # Now create the manpage
            cmd = build_man._COMMAND % ('man', infile, outfile)
            if os.system(cmd):
                self.announce("Creation of %s manpage failed." % man, log.ERROR)
                exit(1)


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
        except exceptions.OSError as e:
            # We only check for errno = 1 (EPERM) here because its kinda
            # expected when installing as a non root user.
            if e.errno == 1:
                self.warn("Could not change owner: You have insufficient permissions.")
            else:
                raise e

    def run(self):
        # Run the usual stuff.
        _install.run(self)

        # Hand over some directories to the webserver user
        path = os.path.join(self.install_data, 'share/cobbler/web')
        try:
            self.change_owner(path, http_user)
        except KeyError, e:
            # building RPMs in a mock chroot, user 'apache' won't exist
            log.warn("Error in 'chown apache %s': %s" % (path, e))
        if not os.path.abspath(libpath):
            # The next line only works for absolute libpath
            raise Exception("libpath is not absolute.")
        path = os.path.join(self.root + libpath, 'webui_sessions')
        try:
            self.change_owner(path, http_user)
        except KeyError, e:
            log.warn("Error in 'chown apache %s': %s" % (path, e))


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
        testfiles = []
        testdirs = []

        for d in testdirs:
            testdir = os.path.join(os.getcwd(), "tests", d)

            for t in _glob.glob(os.path.join(testdir, '*.py')):
                if t.endswith('__init__.py'):
                    continue
                testfile = '.'.join(['tests', d,
                                     os.path.splitext(os.path.basename(t))[0]])
                testfiles.append(testfile)

        tests = unittest.TestLoader().loadTestsFromNames(testfiles)
        runner = unittest.TextTestRunner(verbosity=1)

        if coverage:
            coverage.erase()
            coverage.start()

        result = runner.run(tests)

        if coverage:
            coverage.stop()
        sys.exit(int(bool(len(result.failures) > 0 or
                          len(result.errors) > 0)))

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
            self.announce("copying %s/ to %s/" % (frm, to), log.DEBUG)
            if not self.dry_run:
                if os.path.exists(to):
                    shutil.rmtree(to)
                shutil.copytree(frm, to)
        else:
            self.announce("copying %s to %s" % (frm, os.path.join(to, os.path.basename(frm))), log.DEBUG)
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
        self.announce("restoring the current configuration from %s" % self.statepath, log.INFO)
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
        self.announce("backing up the current configuration to %s" % self.statepath, log.INFO)
        if os.path.exists(self.statepath):
            self.announce("deleting existing %s" % self.statepath, log.DEBUG)
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

    # Trailing slashes on these vars is to allow for easy
    # later configuration of relative paths if desired.
    docpath = "share/man/man1"
    etcpath = "/etc/cobbler/"
    initpath = "/etc/init.d/"
    libpath = "/var/lib/cobbler/"
    logpath = "/var/log/"
    statepath = "/tmp/cobbler_settings/devinstall"

    if os.path.exists("/etc/SuSE-release"):
        webconfig = "/etc/apache2/conf.d"
        webroot = "/srv/www/"
        http_user = "wwwrun"
        defaultpath = "/etc/sysconfig/"
    elif os.path.exists("/etc/debian_version"):
        if os.path.exists("/etc/apache2/conf-available"):
            webconfig = "/etc/apache2/conf-available"
        else:
            webconfig = "/etc/apache2/conf.d"
        webroot = "/srv/www/"
        http_user = "www-data"
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
        long_description="Cobbler is a network install server.  Cobbler supports PXE, virtualized installs, and reinstalling existing Linux machines.  The last two modes use a helper tool, 'koan', that integrates with cobbler.  There is also a web interface 'cobbler-web'.  Cobbler's advanced features include importing distributions from DVDs and rsync mirrors, automatic OS installation templating, integrated yum mirroring, and built-in DHCP/DNS Management.  Cobbler has a XMLRPC API for integration with other applications.",
        author="Team Cobbler",
        author_email="cobbler@lists.fedorahosted.org",
        url="https://cobbler.github.io",
        license="GPLv2+",
        requires=[
            "mod_python",
            "cobbler",
        ],
        packages=[
            "cobbler",
            "cobbler/modules",
            "cobbler/web",
            "cobbler/web/templatetags",
        ],
        scripts=[
            "bin/cobbler",
            "bin/cobblerd",
            "bin/cobbler-ext-nodes",
        ],
        configure_values={
            'webroot': os.path.normpath(webroot),
            'defaultpath': os.path.normpath(defaultpath),
        },
        configure_files=[
            "config/cobbler/settings",
            "config/apache/cobbler.conf",
            "config/apache/cobbler_web.conf",
            "config/service/cobblerd.service",
            "config/service/cobblerd"
        ],
        man_pages=[
            'docs/man/cobbler.1.pod',
        ],
        data_files=[
            # tftpd, hide in /usr/sbin
            ("sbin", ["bin/tftpd.py"]),
            ("%s" % webconfig, ["build/config/apache/cobbler.conf"]),
            ("%s" % webconfig, ["build/config/apache/cobbler_web.conf"]),
            ("%s" % initpath, ["build/config/service/cobblerd"]),
            ("%s" % docpath, glob("build/docs/man/*.1.gz")),
            ("%s/templates" % libpath, glob("autoinstall_templates/*")),
            ("%s/templates/install_profiles" % libpath, glob("autoinstall_templates/install_profiles/*")),
            ("%s/snippets" % libpath, glob("autoinstall_snippets/*", recursive=True)),
            ("%s/scripts" % libpath, glob("autoinstall_scripts/*")),
            ("%s" % libpath, ["config/cobbler/distro_signatures.json"]),
            ("share/cobbler/web", glob("web/*.*")),
            ("%s" % webcontent, glob("web/static/*")),
            ("%s" % webimages, glob("web/static/images/*")),
            ("share/cobbler/web/templates", glob("web/templates/*")),
            ("%swebui_sessions" % libpath, []),
            ("%sloaders" % libpath, []),
            ("%scobbler/aux" % webroot, glob("aux/*")),
            # Configuration
            ("%s" % etcpath, ["build/config/apache/cobbler.conf",
                              "build/config/apache/cobbler_web.conf",
                              "build/config/service/cobblerd",
                              "build/config/service/cobblerd.service",
                              "build/config/cobbler/settings"]),
            ("%ssettings.d" % etcpath, glob("config/cobbler/settings.d/*")),
            ("%s" % etcpath, ["config/bash/cobbler_bash",
                              "config/cobbler/auth.conf",
                              "config/cobbler/modules.conf",
                              "config/cobbler/mongodb.conf",
                              "config/cobbler/users.conf",
                              "config/cobbler/users.digest",
                              "config/cheetah/cheetah_macros",
                              "config/rotate/cobblerd_rotate",
                              "config/rsync/import_rsync_whitelist",
                              "config/rsync/rsync.exclude",
                              "config/version"]),
            ("%s" % etcpath, glob("templates/etc/*")),
            ("%siso" % etcpath, glob("templates/iso/*")),
            ("%sboot_loader_conf" % etcpath, glob("templates/boot_loader_conf/*")),
            ("%sreporting" % etcpath, glob("templates/reporting/*")),
            ("%spower" % etcpath, glob("templates/power/*")),
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
            ("%scobbler/aux" % webroot, []),
            ("%scobbler/pub" % webroot, []),
            ("%scobbler/rendered" % webroot, []),
            ("%scobbler/images" % webroot, []),
            # A script that isn't really data, wsgi script
            ("%scobbler/svc/" % webroot, ["bin/services.py"]),
            # zone-specific templates directory
            ("%szone_templates" % etcpath, []),
        ],
    )
