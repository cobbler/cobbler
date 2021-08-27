"""
Module loader, adapted for Cobbler usage

Copyright 2006-2009, Red Hat, Inc and Others
Adrian Likins <alikins@redhat.com>
Michael DeHaan <michael.dehaan AT gmail>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""
import logging
from configparser import ConfigParser
from importlib import import_module

import glob
import os
from typing import Optional, Dict, Any

from cobbler.cexceptions import CX
from cobbler.utils import log_exc

# add cobbler/modules to python path
import cobbler

# TODO: add os.path.normpath()
mod_path = os.path.join(os.path.abspath(os.path.dirname(cobbler.__file__)), 'modules')

MODULE_CACHE: Dict[str, Any] = {}
MODULES_BY_CATEGORY: Dict[str, Dict[str, Any]] = {}


logger = logging.getLogger()


def load_modules(module_path: str = mod_path):
    """
    Load the modules from the path handed to the function into Cobbler.

    :param module_path: The path which should be considered as the root module path.
    :return: Two dictionary's with the dynamically loaded modules.
    """

    filenames = glob.glob("%s/*.py" % module_path)
    filenames += glob.glob("%s/*.pyc" % module_path)
    filenames += glob.glob("%s/*.pyo" % module_path)
    # Allow recursive modules
    filenames += glob.glob("%s/**/*.py" % module_path)
    filenames += glob.glob("%s/**/*.pyc" % module_path)
    filenames += glob.glob("%s/**/*.pyo" % module_path)

    for fn in filenames:
        # FIXME: Use module_path instead of mod_path
        basename = fn.replace(mod_path, '')
        modname = ""

        if basename.__contains__("__pycache__") or basename.__contains__("__init__.py"):
            continue

        if basename[0] == "/":
            basename = basename[1:]

        basename = basename.replace("/", ".")

        if basename[-3:] == ".py":
            modname = basename[:-3]
        elif basename[-4:] in [".pyc", ".pyo"]:
            modname = basename[:-4]

        # FIXME: Use module_path instead of mod_path
        __import_module(mod_path, modname)

    return MODULE_CACHE, MODULES_BY_CATEGORY


def __import_module(module_path: str, modname: str):
    """
    Import a module which is not part of the core functionality of Cobbler.

    :param module_path: The path to the module.
    :param modname: The name of the module.
    """
    try:
        blip = import_module("cobbler.modules.%s" % modname)
        if not hasattr(blip, "register"):
            if not modname.startswith("__init__"):
                errmsg = "%(module_path)s/%(modname)s is not a proper module"
                print(errmsg % {'module_path': module_path, 'modname': modname})
            return None
        category = blip.register()
        if category:
            MODULE_CACHE[modname] = blip
        if category not in MODULES_BY_CATEGORY:
            MODULES_BY_CATEGORY[category] = {}
        MODULES_BY_CATEGORY[category][modname] = blip
    except Exception:
        logger.info('Exception raised when loading module %s' % modname)
        log_exc()


def get_module_by_name(name: str):
    """
    Get a module by its name. The category of the module is not needed.

    :param name: The name of the module.
    :return: The module asked by the function parameter.
    """
    return MODULE_CACHE.get(name, None)


def get_module_name(category: str, field: str, fallback_module_name: Optional[str] = None) -> str:
    """
    Get module name from configuration file (currently hardcoded ``/etc/cobbler/modules.conf``).

    :param category: Field category in configuration file.
    :param field: Field in configuration file
    :param fallback_module_name: Default value used if category/field is not found in configuration file
    :raises FileNotFoundError: If unable to find configuration file.
    :raises ValueError: If the category does not exist or the field is empty.
    :raises CX: If the field could not be read and no fallback_module_name was given.
    :returns: The name of the module.
    """
    modules_conf_path = "/etc/cobbler/modules.conf"
    if not os.path.exists(modules_conf_path):
        raise FileNotFoundError("Configuration file at \"%s\" not found" % modules_conf_path)

    cp = ConfigParser()
    cp.read(modules_conf_path)

    # FIXME: We can't enabled this check since it is to strict atm.
    # if category not in MODULES_BY_CATEGORY:
    # raise ValueError("category must be one of: %s" % MODULES_BY_CATEGORY.keys())

    if field.isspace():
        raise ValueError("field cannot be empty. Did you mean \"module\" maybe?")

    try:
        value = cp.get(category, field)
    except:
        if fallback_module_name is not None:
            value = fallback_module_name
        else:
            raise CX("Cannot find config file setting for: %s" % field)
    return value


def get_module_from_file(category: str, field: str, fallback_module_name: Optional[str] = None):
    """
    Get Python module, based on name defined in configuration file

    :param category: field category in configuration file
    :param field: field in configuration file
    :param fallback_module_name: default value used if category/field is not found in configuration file
    :raises CX: If unable to load Python module
    :returns: A Python module.
    """

    module_name = get_module_name(category, field, fallback_module_name)
    requested_module = MODULE_CACHE.get(module_name, None)
    if requested_module is None:
        raise CX("Failed to load module for %s/%s" % (category, field))
    return requested_module


def get_modules_in_category(category: str) -> list:
    """
    Return all modules of a module category.

    :param category: The module category.
    :return: A list of all modules of that category. Returns an empty list if the Category does not exist.
    """
    if category not in MODULES_BY_CATEGORY:
        # FIXME: We can't enabled this check since it is to strict atm.
        # raise ValueError("category must be one of: %s" % MODULES_BY_CATEGORY.keys())
        return []
    return list(MODULES_BY_CATEGORY[category].values())
