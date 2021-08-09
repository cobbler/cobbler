"""
The name of the migration file is the target version.
One migration should update from version x to x + 1, where X is any Cobbler version and the migration updates to
any next version (e.g. 3.2.1 to 3.3.0).
The validation of the current version is in the file with the name of the version.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC


# This module should not try to read the settings from the disk. --> Responsibility from settings/__init__.py
# If this module needs to check the existence of a file, the path should be handed as an argument to the function.
# Any migrations of modules.conf should be ignored for now.

import configparser
import glob
import logging
import os
from importlib import import_module
from inspect import signature
from pathlib import Path
from types import ModuleType
from typing import Dict, List, Union

import cobbler

logger = logging.getLogger()
migrations_path = os.path.normpath(os.path.join(os.path.abspath(os.path.dirname(cobbler.__file__)),
                                                "settings/migrations"))


class CobblerVersion:
    """
    Specifies a Cobbler Version
    """

    # TODO: Implement greater, less, etc. methods

    def __init__(self):
        """
        Constructor
        """
        self.major: int = 0
        self.minor: int = 0
        self.patch: int = 0

    def __eq__(self, other: object):
        """
        Compares 2 CobblerVersion objects for equality. Necesarry for the tests.
        """
        if not isinstance(other, CobblerVersion):
            return False
        return self.major == other.major and self.minor == other.minor and self.patch == other.patch

    def __ne__(self, other: object):
        return not self.__eq__(other)

    def __lt__(self, other: object):
        if not isinstance(other, CobblerVersion):
            raise TypeError
        if self.major < other.major:
            return True
        if self.major.__eq__(other.major):
            if self.minor < other.minor:
                return True
            if self.minor.__eq__(other.minor):
                if self.patch < other.patch:
                    return True
        return False

    def __le__(self, other: object):
        if self.__lt__(other) or self.__eq__(other):
            return True
        return False

    def __gt__(self, other: object):
        if not isinstance(other, CobblerVersion):
            raise TypeError
        if self.major > other.major:
            return True
        if self.major.__eq__(other.major):
            if self.minor > other.minor:
                return True
            if self.minor.__eq__(other.minor):
                if self.patch > other.patch:
                    return True
        return False

    def __ge__(self, other: object):
        if self.__gt__(other) or self.__eq__(other):
            return True
        return False

    def __hash__(self):
        return hash((self.major, self.minor, self.patch))

    def __str__(self) -> str:
        return "CobblerVersion: %s.%s.%s" % (self.major, self.minor, self.patch)

    def __repr__(self) -> str:
        return "CobblerVersion(major=%s, minor=%s, patch=%s)" % (self.major, self.minor, self.patch)


EMPTY_VERSION = CobblerVersion()
VERSION_LIST: Dict[CobblerVersion, ModuleType] = {}


def __fill_version_list(version_list: List[str]) -> CobblerVersion:
    version = CobblerVersion()
    version.major = int(version_list[0])
    version.minor = int(version_list[1])
    version.patch = int(version_list[2])

    return version


def __validate_module(name: ModuleType, version: List[str]) -> bool:
    """
    Validates a given module according to certain criteria:
        * module must have certain methods implemented
        * those methods must have a certain signature

    :param name: The name of the module to validate.
    :param version: The migration version as List.
    :return: True if every criteria is met otherwise False.
    """
    module_methods = {"validate": "(settings:dict)->bool",
                      "normalize": "(settings:dict)->dict",
                      "migrate": "(settings:dict)->dict"}
    for (key, value) in module_methods.items():
        if not hasattr(name, key):
            return False
        sig = str(signature(getattr(name, key))).replace(" ", "")
        if value != sig:
            return False
    VERSION_LIST[__fill_version_list(version)] = name
    return True


def __load_migration_modules(name: str, version: List[str]):
    """
    Load migration specific modules

    :param name: The name of the module to load.
    :param version: The migration version as list.
    """
    try:
        module = import_module("cobbler.settings.migrations.%s" % name)
        logger.info("Loaded migrations: %s", name)
        # return value could be checked if necessary
        valid = __validate_module(module, version)
        if not valid:
            raise Exception("Module %s not valid!" % name)
    except Exception as e:
        logger.warning("Exception raised when loading migrations module %s", name)
        logger.exception(e)


def get_installed_version(filepath: Union[str, Path] = "/etc/cobbler/version") -> CobblerVersion:
    """
    Retrieve the current Cobbler version. Normally it can be read from /etc/cobbler/version

    :param filepath: The filepath of the version file, defaults to "/etc/cobbler/version"
    """
    # The format of the version file is the following:

    # [cobbler]
    # gitdate = Fri Aug 13 13:52:40 2021 +0200
    # gitstamp = 610d30d1
    # builddate = Mon Aug 16 07:22:38 2021
    # version = 3.2.1
    # version_tuple = [3, 2, 1]

    config = configparser.ConfigParser()
    if not config.read(filepath):
        # filepath does not exists
        return EMPTY_VERSION
    return __fill_version_list(config["cobbler"]["version"].split("."))


def discover_migrations(path: str = migrations_path):
    """
    Discovers the migration module for each Cobbler version and loads it if it is valid according to certain conditions:
        * the module must contain the following methods: validate(), normalize(), migrate()
        * those version must have a certain signature

    :param path: The path of the migration modules, defaults to migrations_path
    """
    filenames = glob.glob("%s/V[0-9]*_[0-9]*_[0-9]*.py" % path)
    for files in filenames:
        basename = files.replace(path, "")
        migration_name = ""
        if basename[0] == "/":
            basename = basename[1:]
        if basename[-3:] == ".py":
            migration_name = basename[:-3]
        # migration_name should now be something like V3_0_0
        # Remove leading V. Necessary to save values into CobblerVersion object
        version = migration_name[1:].split("_")
        __load_migration_modules(migration_name, version)


def auto_migrate(yaml_dict: dict, settings_path: Path) -> dict:
    """
    Auto migration to the most recent version.

    :param yaml_dict: The settings dict to migrate.
    :param settings_path: The path of the settings dict.
    :return: The migrated dict.
    """
    settings_version = EMPTY_VERSION
    for version in VERSION_LIST:
        if VERSION_LIST[version].validate(yaml_dict):
            settings_version = version
    if settings_version == EMPTY_VERSION:
        raise RuntimeError("Automigration not possible due to undiscoverable settings!")
    try:
        sorted_version_list = sorted(list(VERSION_LIST.keys()))
        migrations = sorted_version_list[sorted_version_list.index(settings_version):]
    except ValueError:
        # TODO: raised when index() could not found settings_version
        pass
    for index in range(0, len(migrations) - 1):
        if index == len(migrations) - 1:
            break
        yaml_dict = migrate(yaml_dict, settings_path, migrations[index], migrations[index + 1])
    return yaml_dict


def migrate(yaml_dict: dict, settings_path: Path,
            old: CobblerVersion = EMPTY_VERSION, new: CobblerVersion = EMPTY_VERSION) -> dict:
    """
    Migration to a specific version. If no old and new version is supplied it will call ``auto_migrate()``.

    :param yaml_dict: The settings dict to migrate.
    :param settings_path: The path of the settings dict.
    :param old: The version to migrate from, defaults to EMPTY_VERSION.
    :param new: The version to migrate to, defaults to EMPTY_VERSION.
    :raises ValueError: Raised if attempting to downgraade.
    :return: The migrated dict.
    """
    # If no version supplied do auto migrations
    if old == EMPTY_VERSION and new == EMPTY_VERSION:
        return auto_migrate(yaml_dict, settings_path)

    # If both versions are present, check if old < new and then migrate the appropriate versions.
    if old > new:
        raise ValueError("Downgrades are not supported!")

    # TODO: Test the correct behaviour of this
    sorted_version_list = sorted(list(VERSION_LIST.keys()))
    migration_list = sorted_version_list[sorted_version_list.index(old) + 1:sorted_version_list.index(new) + 1]
    for key in migration_list:
        yaml_dict = VERSION_LIST[key].migrate(yaml_dict)
    return yaml_dict


def validate(settings: dict, settings_path: Path = "") -> bool:
    """
    Wrapper function for the validate() methods of the individual migration modules.

    :param settings: The settings dict to validate.
    :param settings_path: TODO: not used at the moment
    :return: True if settings are valid, otherwise False.
    """
    version = get_installed_version()
    return VERSION_LIST[version].validate(settings)


def normalize(settings: dict) -> dict:
    """
    If data in ``settings`` is valid the validated data is returned.

    :param settings: The settings dict to validate.
    :return: The validated dict.
    """
    version = get_installed_version()
    return VERSION_LIST[version].normalize(settings)


discover_migrations()
