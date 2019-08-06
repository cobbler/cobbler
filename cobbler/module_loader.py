"""
Module loader, adapted for cobbler usage

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

from future import standard_library
standard_library.install_aliases()

from configparser import ConfigParser

import glob
import os

from cobbler.cexceptions import CX
from cobbler import clogger
from cobbler.utils import _, log_exc

# add cobbler/modules to python path
import cobbler
mod_path = os.path.join(os.path.abspath(os.path.dirname(cobbler.__file__)), 'modules')

MODULE_CACHE = {}
MODULES_BY_CATEGORY = {}

cp = ConfigParser()
cp.read("/etc/cobbler/modules.conf")


def load_modules(module_path=mod_path, blacklist=None):
    logger = clogger.Logger()

    filenames = glob.glob("%s/*.py" % module_path)
    filenames += glob.glob("%s/*.pyc" % module_path)
    filenames += glob.glob("%s/*.pyo" % module_path)
    # Allow recursive modules
    filenames += glob.glob("%s/**/*.py" % module_path)
    filenames += glob.glob("%s/**/*.pyc" % module_path)
    filenames += glob.glob("%s/**/*.pyo" % module_path)

    for fn in filenames:
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

        __import_module(mod_path, modname, logger)

    return MODULE_CACHE, MODULES_BY_CATEGORY


def __import_module(module_path, modname, logger):
    try:
        blip = __import__("cobbler.modules.%s" % modname, globals(), locals(), [modname])
        if not hasattr(blip, "register"):
            if not modname.startswith("__init__"):
                errmsg = _("%(module_path)s/%(modname)s is not a proper module")
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
        log_exc(logger)


def get_module_by_name(name):
    return MODULE_CACHE.get(name, None)


def get_module_name(category, field, fallback_module_name=None):
    """
    Get module name from configuration file

    @param category str field category in configuration file
    @param field str field in configuration file
    @param fallback_module_name str default value used if category/field is
            not found in configuration file
    @raise CX if unable to find configuration file
    @return str module name
    """

    try:
        value = cp.get(category, field)
    except:
        if fallback_module_name is not None:
            value = fallback_module_name
        else:
            raise CX(_("Cannot find config file setting for: %s") % field)
    return value


def get_module_from_file(category, field, fallback_module_name=None):
    """
    Get Python module, based on name defined in configuration file

    @param category str field category in configuration file
    @param field str field in configuration file
    @param fallback_module_name str default value used if category/field is
            not found in configuration file
    @raise CX if unable to load Python module
    @return module Python module
    """

    module_name = get_module_name(category, field, fallback_module_name)
    rc = MODULE_CACHE.get(module_name, None)
    if rc is None:
        raise CX(_("Failed to load module for %s/%s") % (category, field))
    return rc


def get_modules_in_category(category):
    if category not in MODULES_BY_CATEGORY:
        return []
    return list(MODULES_BY_CATEGORY[category].values())


if __name__ == "__main__":
    print(load_modules(mod_path))
