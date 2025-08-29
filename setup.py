#!/usr/bin/env python3

"""
Setup module for Cobbler
"""

import glob
import os
import pathlib
import shutil
import subprocess
import time
from configparser import ConfigParser

from setuptools import find_namespace_packages, setup
from setuptools.command.build_py import build_py

VERSION = "3.4.0"


def read_readme_file() -> str:
    """
    read the contents of your README file
    """
    this_directory = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(this_directory, "README.md"), encoding="utf-8") as f:
        return f.read()


class CobblerBuildPy(build_py):
    """Specialized Python source builder."""

    def run(self):
        self.gen_build_version()
        self.copy_manpages()
        super().run()

    def gen_build_version(self) -> None:
        """
        Generate the Cobbler version file which identifies the version of the backend.
        """
        print("gen_build_version called")
        buildepoch = int(os.environ.get("SOURCE_DATE_EPOCH", time.time()))
        builddate = time.asctime(time.gmtime(buildepoch))

        gitloc = "/usr/bin/git"
        gitdate = "?"
        gitstamp = "?"
        if not os.path.isfile(gitloc):
            self.announce(f"warning: {gitloc} not found", 3)
        else:
            cmd = subprocess.Popen(
                [gitloc, "log", "--format=%h%n%ad", "-1"], stdout=subprocess.PIPE
            )
            data = cmd.communicate()[0].strip()
            if cmd.returncode == 0:
                gitstamp, gitdate = data.decode("utf8").split("\n")

        config_dir = "cobbler/data/config"
        with open(
            os.path.join(config_dir, "version"), "w", encoding="UTF-8"
        ) as version_file:
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

    def copy_manpages(self) -> None:
        """
        Copy manpages to Python Source distribution if they exist.
        """
        print("copy_manpages called")
        man_target = pathlib.Path("cobbler/data/man/")
        man5_source = glob.glob("docs/_build/man/*.5")
        man8_source = glob.glob("docs/_build/man/*.8")
        (man_target / "man5").mkdir(parents=True, exist_ok=True)
        (man_target / "man8").mkdir(parents=True, exist_ok=True)
        for file in man5_source:
            self.announce(f"Copying manpage {file}", 3)
            shutil.copy(file, str(man_target / "man5"))
        for file in man8_source:
            self.announce(f"Copying manpage {file}", 3)
            shutil.copy(file, str(man_target / "man8"))


#####################################################################
## Actual Setup.py Script ###########################################
#####################################################################


if __name__ == "__main__":
    setup(
        cmdclass={
            "build_py": CobblerBuildPy,
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
            "pymongo<4.2",  # Cobbler requires Python 3.6; Version 4.2+ requires Python 3.7
            "distro",
            "python-ldap",
            "dnspython",
            "file-magic",
            "schema",
            "systemd-python",
            "gunicorn",
            "dataclasses; python_version < '3.7'",
        ],
        extras_require={
            "windows": [
                # "hivex",
                "pefile"
            ],
            "extra": ["psutil"],  # debugging startup performance
            "lint": [
                # pyright is not written in Python and has to be installed differently.
                "pyflakes",
                "pycodestyle",
                "pylint",
                "black==22.3.0",  # See .pre-commit-config.yaml
                "types-requests",
                "types-PyYAML",
                "types-psutil",
                "types-netaddr",
                "types-setuptools",
                "types-dataclasses",
                "types-mock",
                "isort",
            ],
            "test": [
                "pytest>6",
                "pytest-cov",
                "coverage",
                "pytest-mock>3.3.0",
                "pytest-benchmark",
                "legacycrypt; python_version > '3.12'",
            ],
            "docs": ["sphinx", "sphinx-rtd-theme", "sphinxcontrib-apidoc"],
            # We require the current version to properly detect duplicate issues
            # See: https://github.com/twisted/towncrier/releases/tag/22.8.0
            "changelog": ["towncrier>=22.8.0"],
        },
        packages=find_namespace_packages(
            exclude=["*tests*", "contrib*", "docs", "bin"]
        ),
        include_package_data=True,
        entry_points={
            "console_scripts": [
                "cobblerd = cobbler.cobblerd:main",
                "cobbler-settings = cobbler.settings.cli:main",
            ]
        },
    )
