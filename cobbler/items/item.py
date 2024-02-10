"""
Cobbler module that contains the code for a generic Cobbler item.

Changelog:

V3.4.0 (unreleased):
    * Split ``Item`` into ``BaseItem``, ``InheritableItem`` and ``BootableItem``.
    * (Re-)Added Cache implementation with the following new methods and properties:
        * ``cache``
        * ``inmemery``
        * ``clean_cache()``
    * Overhauled the parent/child system:
        * ``children`` is now inside ``item.py``.
        * ``tree_walk()`` was added.
        * ``logical_parent`` was added.
        * ``get_parent()`` was added which returns the internal reference that is used to return the object of the
          ``parent`` property.
    * Removed:
        * ``mgmt_classes``
        * ``mgmt_parameters``
        * ``fetchable_files``
        * ``last_cached_mtime``
V3.3.4 (unreleased):
    * No changes
V3.3.3:
    * Added:
        * ``grab_tree``
V3.3.2:
    * No changes
V3.3.1:
    * No changes
V3.3.0:
    * This release switched from pure attributes to properties (getters/setters).
    * Added:
        * ``depth``: int
        * ``comment``: str
        * ``owners``: Union[list, str]
        * ``mgmt_classes``: Union[list, str]
        * ``mgmt_classes``: Union[dict, str]
        * ``conceptual_parent``: Union[distro, profile]
    * Removed:
        * collection_mgr: collection_mgr
        * Remove unreliable caching:
            * ``get_from_cache()``
            * ``set_cache()``
            * ``remove_from_cache()``
    * Changed:
        * Constructor: Takes an instance of ``CobblerAPI`` instead of ``CollectionManager``.
        * ``children``: dict -> list
        * ``ctime``: int -> float
        * ``mtime``: int -> float
        * ``uid``: str
        * ``kernel_options``: dict -> Union[dict, str]
        * ``kernel_options_post``: dict -> Union[dict, str]
        * ``autoinstall_meta``: dict -> Union[dict, str]
        * ``fetchable_files``: dict -> Union[dict, str]
        * ``boot_files``: dict -> Union[dict, str]
V3.2.2:
    * No changes
V3.2.1:
    * No changes
V3.2.0:
    * No changes
V3.1.2:
    * No changes
V3.1.1:
    * No changes
V3.1.0:
    * No changes
V3.0.1:
    * No changes
V3.0.0:
    * Added:
        * ``collection_mgr``: collection_mgr
        * ``kernel_options``: dict
        * ``kernel_options_post``: dict
        * ``autoinstall_meta``: dict
        * ``fetchable_files``: dict
        * ``boot_files``: dict
        * ``template_files``: dict
        * ``name``: str
        * ``last_cached_mtime``: int
    * Changed:
        * Rename: ``cached_datastruct`` -> ``cached_dict``
    * Removed:
        * ``config``
V2.8.5:
    * Added:
        * ``config``: ?
        * ``settings``: settings
        * ``is_subobject``: bool
        * ``parent``: Union[distro, profile]
        * ``children``: dict
        * ``log_func``: collection_mgr.api.log
        * ``ctime``: int
        * ``mtime``: int
        * ``uid``: str
        * ``last_cached_mtime``: int
        * ``cached_datastruct``: str
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>
