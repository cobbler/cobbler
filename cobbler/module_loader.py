"""
Module loader, adapted for cobbler usage

Copyright 2006-2009, Red Hat, Inc and Others
Adrian Likins <alikins@redhat.com>
Michael DeHaan <mdehaan@redhat.com>

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

import distutils.sysconfig
import os
import sys
import glob
from utils import _
from cexceptions import *
import ConfigParser

MODULE_CACHE = {}
MODULES_BY_CATEGORY = {}

cp = ConfigParser.ConfigParser()
cp.read("/etc/cobbler/modules.conf")

plib = distutils.sysconfig.get_python_lib()
mod_path="%s/cobbler/modules" % plib
sys.path.insert(0, mod_path)
sys.path.insert(1, "%s/cobbler" % plib)

def load_modules(module_path=mod_path, blacklist=None):
    filenames = glob.glob("%s/*.py" % module_path)
    filenames = filenames + glob.glob("%s/*.pyc" % module_path)
    filenames = filenames + glob.glob("%s/*.pyo" % module_path)

    mods = {}


    for fn in filenames:
        basename = os.path.basename(fn)
        if basename == "__init__.py":
            continue
        if basename[-3:] == ".py":
            modname = basename[:-3]
        elif basename[-4:] in [".pyc", ".pyo"]:
            modname = basename[:-4]


        try:
            blip =  __import__("modules.%s" % ( modname), globals(), locals(), [modname])
            if not hasattr(blip, "register"):
                if not modname.startswith("__init__"):
                    errmsg = _("%(module_path)s/%(modname)s is not a proper module")
                    print errmsg % {'module_path': module_path, 'modname':modname}
                continue
            category = blip.register()
            if category:
                MODULE_CACHE[modname] = blip
            if not MODULES_BY_CATEGORY.has_key(category):
                MODULES_BY_CATEGORY[category] = {}
            MODULES_BY_CATEGORY[category][modname] = blip
        except ImportError, e:
            print e
            raise

    return (MODULE_CACHE, MODULES_BY_CATEGORY)

def get_module_by_name(name):
    return MODULE_CACHE.get(name, None)

def get_module_from_file(category,field,fallback_module_name=None,just_name=False):

    try:
        value = cp.get(category,field)
    except:
        if fallback_module_name is not None:
            value = fallback_module_name
        else:
            raise CX(_("Cannot find config file setting for: %s") % field) 
    if just_name:
        return value
    rc = MODULE_CACHE.get(value, None)
    if rc is None:
        raise CX(_("Failed to load module for %s/%s") % (category,field))
    return rc

def get_modules_in_category(category):
    if not MODULES_BY_CATEGORY.has_key(category):
        return []
    return MODULES_BY_CATEGORY[category].values()

if __name__ == "__main__":
    print load_modules(module_path)

