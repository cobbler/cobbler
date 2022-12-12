"""
Module loader, adapted for Cobbler usage
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Adrian Likins <alikins@redhat.com>
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
from importlib import import_module

import glob
import os
from typing import Optional, Dict, Any

from cobbler.cexceptions import CX
from cobbler.utils import log_exc

# add cobbler/modules to python path
import cobbler


class ModuleLoader:
    """
    Class for dynamically loading Cobbler Plugins on startup
    """

    def __init__(self, api, module_path: str = ""):
        """
        Constructor to initialize the ModuleLoader class.

        :param api: CobblerAPI
        :param module_path: The path which should be considered as the root module path. If this an empty string, try to
                            auto-detect the path.
        """
        self.logger = logging.getLogger()
        self.mod_path = os.path.join(
            os.path.abspath(os.path.dirname(cobbler.__file__)), "modules"
        )
        if module_path:
            self.mod_path = module_path
        self.module_cache: Dict[str, Any] = {}
        self.modules_by_category: Dict[str, Dict[str, Any]] = {}
        self.api = api

    def load_modules(self):
        """
        Load the modules from the path handed to the function into Cobbler.

        :return: Two dictionary's with the dynamically loaded modules.
        """

        filenames = glob.glob(f"{self.mod_path}/*.py")
        filenames += glob.glob(f"{self.mod_path}/*.pyc")
        filenames += glob.glob(f"{self.mod_path}/*.pyo")
        # Allow recursive modules
        filenames += glob.glob(f"{self.mod_path}/**/*.py")
        filenames += glob.glob(f"{self.mod_path}/**/*.pyc")
        filenames += glob.glob(f"{self.mod_path}/**/*.pyo")

        for filename in filenames:
            basename = filename.replace(self.mod_path, "")
            modname = ""

            if "__pycache__" in basename or "__init__.py" in basename:
                continue

            if basename[0] == "/":
                basename = basename[1:]

            basename = basename.replace("/", ".")

            if basename[-3:] == ".py":
                modname = basename[:-3]
            elif basename[-4:] in [".pyc", ".pyo"]:
                modname = basename[:-4]

            self.__import_module(modname)

        return self.module_cache, self.modules_by_category

    def __import_module(self, modname: str):
        """
        Import a module which is not part of the core functionality of Cobbler.

        :param modname: The name of the module.
        """
        try:
            blip = import_module(f"cobbler.modules.{modname}")
            if not hasattr(blip, "register"):
                self.logger.debug(
                    "%s.%s is not a proper module", self.mod_path, modname
                )
                return None
            category = blip.register()
            if category:
                self.module_cache[modname] = blip
            if category not in self.modules_by_category:
                self.modules_by_category[category] = {}
            self.modules_by_category[category][modname] = blip
        except Exception:
            self.logger.info("Exception raised when loading module %s", modname)
            log_exc()

    def get_module_by_name(self, name: str):
        """
        Get a module by its name. The category of the module is not needed.

        :param name: The name of the module.
        :return: The module asked by the function parameter.
        """
        return self.module_cache.get(name, None)

    def get_module_name(
        self, category: str, field: str, fallback_module_name: Optional[str] = None
    ) -> str:
        """
        Get module name from the settings.

        :param category: Field category in configuration file.
        :param field: Field in configuration file
        :param fallback_module_name: Default value used if category/field is not found in configuration file
        :raises FileNotFoundError: If unable to find configuration file.
        :raises ValueError: If the category does not exist or the field is empty.
        :raises CX: If the field could not be read and no fallback_module_name was given.
        :returns: The name of the module.
        """
        # FIXME: We can't enabled this check since it is to strict atm.
        # if category not in MODULES_BY_CATEGORY:
        # raise ValueError("category must be one of: %s" % MODULES_BY_CATEGORY.keys())

        if field.isspace():
            raise ValueError('field cannot be empty. Did you mean "module" maybe?')

        try:
            value = self.api.settings().modules.get(category, {}).get("module")
            if value is None:
                raise ModuleNotFoundError("Requested module could not be retrieved")
        except Exception as exception:
            if fallback_module_name is None:
                raise CX(
                    f"Cannot find config file setting for: {category}.{field}"
                ) from exception
            value = fallback_module_name
            self.logger.warning(
                'Requested module "%s.%s" not found. Using fallback module: "%s"',
                category,
                field,
                value,
            )
        return value

    def get_module_from_file(
        self, category: str, field: str, fallback_module_name: Optional[str] = None
    ):
        """
        Get Python module, based on name defined in configuration file

        :param category: field category in configuration file
        :param field: field in configuration file
        :param fallback_module_name: default value used if category/field is not found in configuration file
        :raises CX: If unable to load Python module
        :returns: A Python module.
        """

        module_name = self.get_module_name(category, field, fallback_module_name)
        requested_module = self.module_cache.get(module_name, None)
        if requested_module is None:
            raise CX(f"Failed to load module for {category}.{field}")
        return requested_module

    def get_modules_in_category(self, category: str) -> list:
        """
        Return all modules of a module category.

        :param category: The module category.
        :return: A list of all modules of that category. Returns an empty list if the Category does not exist.
        """
        if category not in self.modules_by_category:
            # FIXME: We can't enabled this check since it is to strict atm.
            # raise ValueError("category must be one of: %s" % MODULES_BY_CATEGORY.keys())
            return []
        return list(self.modules_by_category[category].values())
