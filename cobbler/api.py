"""
This module represents the Cobbler Python API. It is used by the XML-RPC API and can be used by external consumers.

Changelog:

Schema: From -> To

Current Schema: Please refer to the documentation visible of the individual methods.

V3.4.0 (unreleased)
    * Added:
        * ``clean_items_cache``
        * ``new_item``
        * ``deserialize_item``
        * ``input_string_or_list_no_inherit``
        * ``input_string_or_list``
        * ``input_string_or_dict``
        * ``input_string_or_dict_no_inherit``
        * ``input_boolean``
        * ``input_int``
    * Changed:
        * ``new_*``: Accepts kwargs as a last argument now (so a dict) that makes it possible to seed an object

V3.3.4 (unreleased)
    * No changes

V3.3.3
    * Added:
        * ``get_item_resolved_value``
        * ``set_item_resolved_value``
    * Changed:
        * ``dump_vars``: Added boolean parameter ``remove_dicts`` as a new last argument

V3.3.2
    * No changes

V3.3.1
    * Changes:
        * ``add_system``: Parameter ``check_for_duplicate_netinfo`` was removed
        * ``build_iso``: Replaced default ``None`` arguments with typed arguments
        * ``create_grub_images``: Renamed to ``mkloaders``

V3.3.0
    * Added:
        * ``menus``
        * ``copy_menu``
        * ``remove_menu``
        * ``rename_menu``
        * ``new_menu``
        * ``add_menu``
        * ``find_menu``
        * ``get_menus_since``
        * ``sync_systems``
        * ``sync_dns``
        * ``get_valid_obj_boot_loaders``
        * ``create_grub_images``
    * Changed:
        * Constructor: Added ``settingsfile_location`` and ``execute_settings_automigration`` as parameters
        * ``find_items``: Accept an empty ``str`` for ``what`` if the argument ``name`` is given.
        * ``dump_vars``: Parameter ``format`` was renamed to ``formatted_output``
        * ``generate_gpxe``: Renamed to ``generate_ipxe``; The second parameter is now ``image`` and accepts the name
          of one.
        * ``sync``: Accepts a new parameter called ``what`` which is a ``List[str]`` that signals what should be
          synced. An empty list signals a full sync.
        * ``sync_dhcp``: Parameter ``verbose`` was removed
    * Removed:
        * The ``logger`` arugment was removed from all methods
        * ``dlcontent``

V3.2.2
    * No changes

V3.2.1
    * Added primitive type annotations for all parameters of all methods

V3.2.0
    * No changes

V3.1.2
    * No changes

V3.1.1
    * No changes

V3.1.0
    * No changes

V3.0.1
    * No changes

V3.0.0
    * Added:
        * power_system: Replaces power_on, power_off, reboot, power_status
    * Changed:
        * import_tree: ``kickstart_file`` is now called ``autoinstall_file``
    * Removed:
        * ``update``
        * ``clear``
        * ``deserialize_raw``
        * ``deserialize_item_raw``
        * ``power_on`` - Replaced by power_system
        * ``power_off`` - Replaced by power_system
        * ``reboot`` - Replaced by power_system
        * ``power_status`` - Replaced by power_system

V2.8.5
    * Inital tracking of changes.

"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
import os
import pathlib
import random
import tempfile
import threading
from configparser import ConfigParser
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple, Union

from schema import SchemaError  # type: ignore

from cobbler import (
    autoinstall_manager,
    autoinstallgen,
    download_manager,
    enums,
    module_loader,
    power_manager,
    settings,
    tftpgen,
    utils,
    validate,
    yumgen,
)
from cobbler.actions import (
    acl,
    check,
    hardlink,
    importer,
    log,
    mkloaders,
    replicate,
    report,
    reposync,
    status,
)
from cobbler.actions import sync as sync_module
from cobbler.actions.buildiso.netboot import NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import manager
from cobbler.decorator import InheritableDictProperty
from cobbler.items import distro
from cobbler.items import image as image_module
from cobbler.items import menu
from cobbler.items import profile as profile_module
from cobbler.items import repo
from cobbler.items import system as system_module
from cobbler.items.abstract import base_item
from cobbler.utils import filesystem_helpers, input_converters, signatures

if TYPE_CHECKING:
    from cobbler.cobbler_collections.collection import (
        FIND_KWARGS,
        ITEM,
        ITEM_UNION,
        Collection,
    )
    from cobbler.cobbler_collections.distros import Distros
    from cobbler.cobbler_collections.images import Images
    from cobbler.cobbler_collections.menus import Menus
    from cobbler.cobbler_collections.profiles import Profiles
    from cobbler.cobbler_collections.repos import Repos
    from cobbler.cobbler_collections.systems import Systems


# notes on locking:
# - CobblerAPI is a singleton object
# - The XMLRPC variants allow 1 simultaneous request, therefore we flock on our settings file for now on a request by
#   request basis.


class CobblerAPI:
    """
    Python API module for Cobbler.
    See source for cobbler.py, or pydoc, for example usage.
    Cli apps and daemons should import api.py, and no other Cobbler code.
    """

    __shared_state: Dict[str, Any] = {}
    __has_loaded = False

    def __init__(
        self,
        is_cobblerd: bool = False,
        settingsfile_location: str = "/etc/cobbler/settings.yaml",
        execute_settings_automigration: bool = False,
    ):
        """
        Constructor

        :param is_cobblerd: Whether this API is run as a daemon or not.
        :param settingsfile_location: The location of the settings file on the disk.
        """

        # FIXME: this should be switchable through some simple system

        self.__dict__ = CobblerAPI.__shared_state
        self.mtime_location = "/var/lib/cobbler/.mtime"
        self.perms_ok = False
        if not CobblerAPI.__has_loaded:
            # NOTE: we do not log all API actions, because a simple CLI invocation may call adds and such to load the
            # config, which would just fill up the logs, so we'll do that logging at CLI level (and remote.py web
            # service level) instead.

            random.seed()
            self.is_cobblerd = is_cobblerd
            if is_cobblerd:
                main_thread = threading.main_thread()
                main_thread.setName("Daemon")

            self.logger = logging.getLogger()

            # FIXME: consolidate into 1 server instance

            self.selinux_enabled = utils.is_selinux_enabled()
            self.dist, self.os_version = utils.os_release()
            self._settings = self.__generate_settings(
                pathlib.Path(settingsfile_location), execute_settings_automigration
            )

            CobblerAPI.__has_loaded = True

            # load the modules first, or nothing else works...
            self.module_loader = module_loader.ModuleLoader(self)
            self.module_loader.load_modules()

            # In case the signatures can't be loaded, we can't validate distros etc. Thus, the raised exception should
            # not be caught.
            self.__load_signatures()

            self._collection_mgr = manager.CollectionManager(self)
            self.deserialize()

            self.authn = self.get_module_from_file(
                "authentication", "module", "authentication.configfile"
            )
            self.authz = self.get_module_from_file(
                "authorization", "module", "authorization.allowall"
            )

            # FIXME: pass more loggers around, and also see that those using things via tasks construct their own
            #  yumgen/tftpgen versus reusing this one, which has the wrong logger (most likely) for background tasks.

            self.autoinstallgen = autoinstallgen.AutoInstallationGen(self)
            self.yumgen = yumgen.YumGen(self)
            self.tftpgen = tftpgen.TFTPGen(self)
            self.__directory_startup_preparations()
            self.logger.debug("API handle initialized")
            self.perms_ok = True

    def __directory_startup_preparations(self) -> None:
        """
        This function prepares the daemon to be able to operate with directories that need to be handled before it can
        operate as designed.

        :raises FileNotFoundError: In case a directory required for operation is missing.
        """
        self.logger.debug("Creating necessary directories")
        required_directories = [
            pathlib.Path("/var/lib/cobbler"),
            pathlib.Path("/etc/cobbler"),
            pathlib.Path(self.settings().webdir),
            pathlib.Path(self.settings().tftpboot_location),
        ]
        for directory in required_directories:
            if not directory.is_dir():
                directory.mkdir()
                self.logger.info('Created required directory: "%s"', str(directory))
        filesystem_helpers.create_tftpboot_dirs(self)
        filesystem_helpers.create_web_dirs(self)
        filesystem_helpers.create_trigger_dirs(self)
        filesystem_helpers.create_json_database_dirs(self)

    def __load_signatures(self) -> None:
        try:
            signatures.load_signatures(self.settings().signature_path)
        except Exception as exception:
            self.logger.error(
                'Failed to load signatures from "%s"',
                self.settings().signature_path,
                exc_info=exception,
            )
            raise exception

        self.logger.info(
            "%d breeds and %d OS versions read from the signature file",
            len(signatures.get_valid_breeds()),
            len(signatures.get_valid_os_versions()),
        )

    def __generate_settings(
        self, settings_path: Path, execute_settings_automigration: bool = False
    ) -> settings.Settings:
        yaml_dict = settings.read_yaml_file(str(settings_path))

        if execute_settings_automigration is not None:  # type: ignore
            self.logger.info(
                'Daemon flag overwriting other possible values from "settings.yaml" for automigration!'
            )
            yaml_dict["auto_migrate_settings"] = execute_settings_automigration

        if yaml_dict.get("auto_migrate_settings", False):
            self.logger.info("Automigration executed")
            normalized_settings = settings.migrate(yaml_dict, settings_path)
        else:
            self.logger.info("Automigration NOT executed")
            # In case we have disabled the auto-migration, we still check if the settings are valid.
            try:
                normalized_settings = settings.validate_settings(yaml_dict)
            except SchemaError as error:
                raise ValueError(
                    "Settings are invalid and auto-migration is disabled. Please correct this manually!"
                ) from error

        # Use normalized or migrated dict and create settings object
        new_settings = settings.Settings()
        new_settings.from_dict(normalized_settings)

        if yaml_dict.get("auto_migrate_settings", False):
            # save to disk only when automigration was performed
            # to avoid creating duplicated files
            new_settings.save(str(settings_path))

        # Return object
        return new_settings

    # ==========================================================

    def is_selinux_enabled(self) -> bool:
        """
        Returns whether selinux is enabled on the Cobbler server.
        We check this just once at Cobbler API init time, because a restart is required to change this; this does
        /not/ check enforce/permissive, nor does it need to.
        """
        return self.selinux_enabled

    def is_selinux_supported(self) -> bool:
        """
        Returns whether or not the OS is sufficient enough to run with SELinux enabled (currently EL 5 or later).

        :returns: False per default. If Distro is Redhat and Version >= 5 then it returns true.
        """
        # FIXME: This detection is flawed. There is more than just Rhel with selinux and the original implementation was
        #        too broad.
        if ("red hat" in self.dist or "redhat" in self.dist) and self.os_version >= 5:
            return True
        # doesn't support public_content_t
        return False

    # ==========================================================

    def last_modified_time(self) -> float:
        """
        Returns the time of the last modification to Cobbler, made by any API instance, regardless of the serializer
        type.

        :returns: 0 if there is no file where the information required for this method is saved.
        """
        # FIXME: This fails in case the file required is not available
        if not os.path.exists(self.mtime_location):
            with open(self.mtime_location, "w", encoding="UTF-8") as mtime_fd:
                mtime_fd.write("0")
            return 0.0
        with open(self.mtime_location, "r", encoding="UTF-8") as mtime_fd:
            data = mtime_fd.read().strip()
        return float(data)

    # ==========================================================

    def log(
        self,
        msg: str,
        args: Optional[Union[str, List[Optional[str]], Dict[str, Any]]] = None,
        debug: bool = False,
    ) -> None:
        """
        Logs a message with the already initiated logger of this object.

        :param msg: The message to log.
        :param args: Optional message which gets appended to the main msg with a ';'.
        :param debug: Weather the logged message is a debug message (true) or info (false).

        .. deprecated:: 3.3.0
           We should use the standard logger.
        """
        if debug:
            logger = self.logger.debug
        else:
            logger = self.logger.info
        if args is None:
            logger("%s", msg)
        else:
            logger("%s; %s", msg, str(args))

    # ==========================================================

    def version(
        self, extended: bool = False
    ) -> Union[float, Dict[str, Union[str, List[Any]]]]:
        """
        What version is Cobbler?

        If extended == False, returns a float for backwards compatibility
        If extended == True, returns a dict:

            gitstamp      -- the last git commit hash
            gitdate       -- the last git commit date on the builder machine
            builddate     -- the time of the build
            version       -- something like "1.3.2"
            version_tuple -- something like [ 1, 3, 2 ]

        :param extended: False returns a float, True a Dictionary.
        """
        config = ConfigParser()
        config.read("/etc/cobbler/version")
        data: Dict[str, Union[str, List[Any]]] = {
            "gitdate": config.get("cobbler", "gitdate"),
            "gitstamp": config.get("cobbler", "gitstamp"),
            "builddate": config.get("cobbler", "builddate"),
            "version": config.get("cobbler", "version"),
            "version_tuple": [],
        }
        # don't actually read the version_tuple from the version file
        # mypy doesn't know that version the version key is controlled by us and we thus can safely assume that this
        # is a str
        for num in data["version"].split("."):  # type: ignore[union-attr]
            data["version_tuple"].append(int(num))  # type: ignore[union-attr]

        if not extended:
            # for backwards compatibility and use with koan's comparisons
            elems = data["version_tuple"]
            # This double conversion is required because of the typical floating point problems.
            # https://docs.python.org/3/tutorial/floatingpoint.html
            return float(
                format(
                    int(elems[0]) + 0.1 * int(elems[1]) + 0.001 * int(elems[2]), ".3f"
                )
            )
        return data

    # ==========================================================================

    def clean_items_cache(self, obj: Union[settings.Settings, Dict[str, Any]]):
        """
        Items cache invalidation in case of settings or singatures changes.
        Cobbler internal use only.
        """
        if obj is None or isinstance(obj, settings.Settings):  # type: ignore
            item_types = [
                "repo",
                "distro",
                "menu",
                "image",
                "profile",
                "system",
            ]
        elif obj == self.get_signatures():
            item_types = ["distro", "image", "profile", "system"]
        else:
            raise CX(f"Wrong object type {type(obj)} for cache invalidation!")

        for item_type in item_types:
            for item_obj in self.get_items(item_type):
                item_obj.cache.set_dict_cache(None, True)

    # ==========================================================

    def get_item(self, what: str, name: str) -> Optional["ITEM_UNION"]:
        """
        Get a general item.

        :param what: The item type to retrieve from the internal database.
        :param name: The name of the item to retrieve.
        :return: An item of the desired type.
        """
        # self.log("get_item", [what, name], debug=True)
        result = self._collection_mgr.get_items(what).get(name)
        return result  # type: ignore

    def get_items(self, what: str) -> "manager.COLLECTION_UNION":
        """
        Get all items of a collection.

        :param what: The collection to query.
        :return: The items which were queried. May return no items.
        """
        # self.log("get_items", [what], debug=True)
        items = self._collection_mgr.get_items(what)
        return items  # type: ignore

    def distros(self) -> "Distros":
        """
        Return the current list of distributions
        """
        return self._collection_mgr.distros()

    def profiles(self) -> "Profiles":
        """
        Return the current list of profiles
        """
        return self._collection_mgr.profiles()

    def systems(self) -> "Systems":
        """
        Return the current list of systems
        """
        return self._collection_mgr.systems()

    def repos(self) -> "Repos":
        """
        Return the current list of repos
        """
        return self._collection_mgr.repos()

    def images(self) -> "Images":
        """
        Return the current list of images
        """
        return self._collection_mgr.images()

    def settings(self) -> "settings.Settings":
        """
        Return the application configuration
        """
        return self._settings

    def menus(self) -> "Menus":
        """
        Return the current list of menus
        """
        return self._collection_mgr.menus()

    # =======================================================================

    def __item_resolved_helper(
        self, item_uuid: str, attribute: str
    ) -> "base_item.BaseItem":
        """
        This helper validates the common data for ``*_item_resolved_value``.

        :param item_uuid: The uuid for the item.
        :param attribute: The attribute name that is requested.
        :returns: The desired item to further process.
        :raises TypeError: If ``item_uuid`` or ``attribute`` are not a str.
        :raises ValueError: In case the uuid was invalid or the requested item did not exist.
        :raises AttributeError: In case the attribute did not exist on the item that was requested.
        """
        if not isinstance(item_uuid, str):  # type: ignore
            raise TypeError("item_uuid must be of type str!")

        if not validate.validate_uuid(item_uuid):
            raise ValueError("The given uuid did not have the correct format!")

        if not isinstance(attribute, str):  # type: ignore
            raise TypeError("attribute must be of type str!")

        # We pass return_list=False, thus the return type is Optional[ITEM]
        desired_item = self.find_items(
            "", {"uid": item_uuid}, return_list=False, no_errors=True
        )
        if desired_item is None:
            raise ValueError(f'Item with item_uuid "{item_uuid}" did not exist!')

        if isinstance(desired_item, list):
            raise ValueError("Ambiguous match during searching for resolved item!")

        if not hasattr(desired_item, attribute):
            raise AttributeError(
                f'Attribute "{attribute}" did not exist on item type "{desired_item.TYPE_NAME}".'
            )

        return desired_item

    def get_item_resolved_value(self, item_uuid: str, attribute: str) -> Any:
        """
        This method helps non Python API consumers to retrieve the final data of a field with inheritance.

        This does not help with network interfaces because they don't have a UUID at the moment and thus can't be
        queried via their UUID.

        :param item_uuid: The UUID of the item that should be retrieved.
        :param attribute: The attribute that should be retrieved.
        :raises ValueError: In case a value given was either malformed or the desired item did not exist.
        :raises TypeError: In case the type of the method arguments do have the wrong type.
        :raises AttributeError: In case the attribute specified is not available on the given item (type).
        :returns: The attribute value. Since this might be of type NetworkInterface we cannot yet set this explicitly.
        """
        desired_item = self.__item_resolved_helper(item_uuid, attribute)

        return getattr(desired_item, attribute)

    def set_item_resolved_value(
        self, item_uuid: str, attribute: str, value: Any
    ) -> None:
        """
        This method helps non Python API consumers to use the Python property setters without having access to the raw
        data of the object. In case you pass a dictionary the method tries to deduplicate it.

        This does not help with network interfaces because they don't have a UUID at the moment and thus can't be
        queried via their UUID.

        .. warning:: This function may throw any exception that is thrown by a setter of a Python property defined in
                     Cobbler.

        :param item_uuid: The UUID of the item that should be retrieved.
        :param attribute: The attribute that should be retrieved.
        :param value: The new value to set.
        :raises ValueError: In case a value given was either malformed or the desired item did not exist.
        :raises TypeError: In case the type of the method arguments do have the wrong type.
        :raises AttributeError: In case the attribute specified is not available on the given item (type).
        """
        desired_item = self.__item_resolved_helper(item_uuid, attribute)
        property_object_of_attribute = getattr(type(desired_item), attribute)
        # Check if value can be inherited or not
        if "inheritable" not in dir(property_object_of_attribute):
            if value == enums.VALUE_INHERITED:
                raise ValueError(
                    "<<inherit>> not allowed for non-inheritable properties."
                )
            setattr(desired_item, attribute, value)
            return
        # Deduplicate - only for dict
        if isinstance(property_object_of_attribute, InheritableDictProperty):
            parent_item = desired_item.logical_parent
            if hasattr(parent_item, attribute):
                parent_value = getattr(parent_item, attribute)
                dict_value = input_converters.input_string_or_dict(value)
                if isinstance(dict_value, str):
                    # This can only be the inherited case
                    dict_value = enums.VALUE_INHERITED
                else:
                    for key in parent_value:
                        if (
                            key in dict_value
                            and key in parent_value
                            and dict_value[key] == parent_value[key]
                        ):
                            dict_value.pop(key)
                setattr(desired_item, attribute, dict_value)
                return
        # Use property setter
        setattr(desired_item, attribute, value)

    # =======================================================================

    def copy_item(self, what: str, ref: "ITEM_UNION", newname: str) -> None:
        """
        General copy method which is called by the specific methods.

        :param what: The collection type which gets copied.
        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self.log(f"copy_item({what})", [ref.name, newname])
        self.get_items(what).copy(ref, newname)  # type: ignore

    def copy_distro(self, ref: "distro.Distro", newname: str) -> None:
        """
        This method copies a distro which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self._collection_mgr.distros().copy(ref, newname)

    def copy_profile(self, ref: "profile_module.Profile", newname: str) -> None:
        """
        This method copies a profile which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self._collection_mgr.profiles().copy(ref, newname)

    def copy_system(self, ref: "system_module.System", newname: str) -> None:
        """
        This method copies a system which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self._collection_mgr.systems().copy(ref, newname)

    def copy_repo(self, ref: "repo.Repo", newname: str) -> None:
        """
        This method copies a repository which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self._collection_mgr.repos().copy(ref, newname)

    def copy_image(self, ref: "image_module.Image", newname: str) -> None:
        """
        This method copies an image which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self._collection_mgr.images().copy(ref, newname)

    def copy_menu(self, ref: "menu.Menu", newname: str) -> None:
        """
        This method copies a file which is just different in the name of the object.

        :param ref: The object itself which gets copied.
        :param newname: The new name of the newly created object.
        """
        self._collection_mgr.menus().copy(ref, newname)

    # ==========================================================================

    def remove_item(
        self,
        what: str,
        ref: Union["ITEM_UNION", str],
        recursive: bool = False,
        delete: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Remove a general item. This method should not be used by an external api. Please use the specific
        remove_<itemtype> methods.

        :param what: The type of the item.
        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        """
        to_delete: Optional["ITEM_UNION"] = None
        if isinstance(ref, str):
            to_delete = self.get_item(what, ref)
            if to_delete is None:
                return  # nothing to remove
        else:
            to_delete = ref
        self.log(f"remove_item({what})", [to_delete.name])
        self.get_items(what).remove(
            to_delete.name,
            recursive=recursive,
            with_delete=delete,
            with_triggers=with_triggers,
        )

    def remove_distro(
        self,
        ref: Union["distro.Distro", str],
        recursive: bool = False,
        delete: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Remove a distribution from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        """
        self.remove_item(
            "distro",
            ref,
            recursive=recursive,
            delete=delete,
            with_triggers=with_triggers,
        )

    def remove_profile(
        self,
        ref: Union["profile_module.Profile", str],
        recursive: bool = False,
        delete: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Remove a profile from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        """
        self.remove_item(
            "profile",
            ref,
            recursive=recursive,
            delete=delete,
            with_triggers=with_triggers,
        )

    def remove_system(
        self,
        ref: Union["system_module.System", str],
        recursive: bool = False,
        delete: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Remove a system from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        """
        self.remove_item(
            "system",
            ref,
            recursive=recursive,
            delete=delete,
            with_triggers=with_triggers,
        )

    def remove_repo(
        self,
        ref: Union["repo.Repo", str],
        recursive: bool = False,
        delete: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Remove a repository from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        """
        self.remove_item(
            "repo", ref, recursive=recursive, delete=delete, with_triggers=with_triggers
        )

    def remove_image(
        self,
        ref: Union["image_module.Image", str],
        recursive: bool = False,
        delete: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Remove a image from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        """
        self.remove_item(
            "image",
            ref,
            recursive=recursive,
            delete=delete,
            with_triggers=with_triggers,
        )

    def remove_menu(
        self,
        ref: Union["menu.Menu", str],
        recursive: bool = False,
        delete: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Remove a menu from Cobbler.

        :param ref: The internal unique handle for the item.
        :param recursive: If the item should recursively should delete dependencies on itself.
        :param delete: Not known what this parameter does exactly.
        :param with_triggers: Whether you would like to have the removal triggers executed or not.
        """
        self.remove_item(
            "menu", ref, recursive=recursive, delete=delete, with_triggers=with_triggers
        )

    # ==========================================================================

    def rename_item(self, what: str, ref: "ITEM_UNION", newname: str) -> None:
        """
        Remove a general item. This method should not be used by an external api. Please use the specific
        rename_<itemtype> methods.

        :param what: The type of object which should be renamed.
        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        """
        self.log(f"rename_item({what})", [ref.name, newname])
        self.get_items(what).rename(ref, newname)  # type: ignore

    def rename_distro(self, ref: "distro.Distro", newname: str) -> None:
        """
        Rename a distro to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        """
        self.rename_item("distro", ref, newname)

    def rename_profile(self, ref: "profile_module.Profile", newname: str) -> None:
        """
        Rename a profile to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        """
        self.rename_item("profile", ref, newname)

    def rename_system(self, ref: "system_module.System", newname: str) -> None:
        """
        Rename a system to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        """
        self.rename_item("system", ref, newname)

    def rename_repo(self, ref: "repo.Repo", newname: str) -> None:
        """
        Rename a repository to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        """
        self.rename_item("repo", ref, newname)

    def rename_image(self, ref: "image_module.Image", newname: str) -> None:
        """
        Rename an image to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        """
        self.rename_item("image", ref, newname)

    def rename_menu(self, ref: "menu.Menu", newname: str) -> None:
        """
        Rename a menu to a new name.

        :param ref: The internal unique handle for the item.
        :param newname: The new name for the item.
        """
        self.rename_item("menu", ref, newname)

    # ==========================================================================

    def new_item(
        self, what: str = "", is_subobject: bool = False, **kwargs: Any
    ) -> "ITEM_UNION":
        """
        Creates a new (unconfigured) object. The object is not persisted.

        :param what: Specifies the type of object. Valid item types can be seen at
                     :func:`~cobbler.enums.ItemTypes`.
        :param is_subobject: If the object is a subobject of an already existing object or not.
        :return: The newly created object.
        """
        try:
            enums.ItemTypes(what)  # verify that <what> is an ItemTypes member
            return getattr(self, f"new_{what}")(is_subobject, **kwargs)
        except (ValueError, AttributeError) as error:
            raise Exception(f"internal error, collection name is {what}") from error

    def new_distro(self, is_subobject: bool = False, **kwargs: Any) -> "distro.Distro":
        """
        Returns a new empty distro object. This distro is not automatically persisted. Persistance is achieved via
        ``save()``.

        :param is_subobject: If the object is a subobject of an already existing object or not.
        :return: An empty Distro object.
        """
        self.log("new_distro", kwargs)
        return distro.Distro(self, is_subobject, **kwargs)

    def new_profile(
        self, is_subobject: bool = False, **kwargs: Any
    ) -> "profile_module.Profile":
        """
        Returns a new empty profile object. This profile is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty Profile object.
        """
        self.log("new_profile", kwargs)
        return profile_module.Profile(self, is_subobject, **kwargs)

    def new_system(
        self, is_subobject: bool = False, **kwargs: Any
    ) -> "system_module.System":
        """
        Returns a new empty system object. This system is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty System object.
        """
        self.log("new_system", kwargs)
        return system_module.System(self, is_subobject, **kwargs)

    def new_repo(self, is_subobject: bool = False, **kwargs: Any) -> "repo.Repo":
        """
        Returns a new empty repo object. This repository is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty repo object.
        """
        self.log("new_repo", kwargs)
        return repo.Repo(self, is_subobject, kwargs)

    def new_image(
        self, is_subobject: bool = False, **kwargs: Any
    ) -> "image_module.Image":
        """
        Returns a new empty image object. This image is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty image object.
        """
        self.log("new_image", kwargs)
        return image_module.Image(self, is_subobject, **kwargs)

    def new_menu(self, is_subobject: bool = False, **kwargs: Any) -> "menu.Menu":
        """
        Returns a new empty menu object. This file is not automatically persisted. Persistence is achieved via
        ``save()``.

        :param is_subobject: If the object created is a subobject or not.
        :return: An empty Menu object.
        """
        self.log("new_menu", kwargs)
        return menu.Menu(self, is_subobject, **kwargs)

    # ==========================================================================

    def add_item(
        self,
        what: str,
        ref: "ITEM_UNION",
        check_for_duplicate_names: bool = False,
        save: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Add an abstract item to a collection of its specific items. This is not meant for external use. Please reefer
        to one of the specific methods ``add_<type>``.

        :param what: The item type.
        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param with_triggers: If triggers should be run when the object is added.
        """
        self.log(f"add_item({what})", [ref.name])
        self.get_items(what).add(
            ref,  # type: ignore
            check_for_duplicate_names=check_for_duplicate_names,
            save=save,
            with_triggers=with_triggers,
        )

    def add_distro(
        self,
        ref: "distro.Distro",
        check_for_duplicate_names: bool = False,
        save: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Add a distribution to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param with_triggers: If triggers should be run when the object is added.
        """
        self.add_item(
            "distro",
            ref,
            check_for_duplicate_names=check_for_duplicate_names,
            save=save,
            with_triggers=with_triggers,
        )

    def add_profile(
        self,
        ref: "profile_module.Profile",
        check_for_duplicate_names: bool = False,
        save: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Add a profile to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param with_triggers: If triggers should be run when the object is added.
        """
        self.add_item(
            "profile",
            ref,
            check_for_duplicate_names=check_for_duplicate_names,
            save=save,
            with_triggers=with_triggers,
        )

    def add_system(
        self,
        ref: "system_module.System",
        check_for_duplicate_names: bool = False,
        save: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Add a system to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param with_triggers: If triggers should be run when the object is added.
        """
        self.add_item(
            "system",
            ref,
            check_for_duplicate_names=check_for_duplicate_names,
            save=save,
            with_triggers=with_triggers,
        )

    def add_repo(
        self,
        ref: "repo.Repo",
        check_for_duplicate_names: bool = False,
        save: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Add a repository to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param with_triggers: If triggers should be run when the object is added.
        """
        self.add_item(
            "repo",
            ref,
            check_for_duplicate_names=check_for_duplicate_names,
            save=save,
            with_triggers=with_triggers,
        )

    def add_image(
        self,
        ref: "image_module.Image",
        check_for_duplicate_names: bool = False,
        save: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Add an image to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param with_triggers: If triggers should be run when the object is added.
        """
        self.add_item(
            "image",
            ref,
            check_for_duplicate_names=check_for_duplicate_names,
            save=save,
            with_triggers=with_triggers,
        )

    def add_menu(
        self,
        ref: "menu.Menu",
        check_for_duplicate_names: bool = False,
        save: bool = True,
        with_triggers: bool = True,
    ) -> None:
        """
        Add a submenu to Cobbler.

        :param ref: The identifier for the object to add to a collection.
        :param check_for_duplicate_names: If the name should be unique or can be present multiple times.
        :param save: If the item should be persisted.
        :param with_triggers: If triggers should be run when the object is added.
        """
        self.add_item(
            "menu",
            ref,
            check_for_duplicate_names=check_for_duplicate_names,
            save=save,
            with_triggers=with_triggers,
        )

    # ==========================================================================

    def find_items(
        self,
        what: str = "",
        criteria: Optional[Dict[Any, Any]] = None,
        name: str = "",
        return_list: bool = True,
        no_errors: bool = False,
    ) -> Optional[Union["ITEM_UNION", List["ITEM_UNION"]]]:
        """
        This is the abstract base method for finding object int the api. It should not be used by external resources.
        Please reefer to the specific implementations of this method called ``find_<object type>``.

        :param what: The object type of the item to search for.
        :param criteria: The dictionary with the key-value pairs to find objects with.
        :param name: The name of the object.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :return: The list of items witch match the search criteria.
        """
        # self.log("find_items", [what])
        if criteria is None:
            criteria = {}

        if not isinstance(name, str):  # type: ignore
            raise TypeError('"name" must be of type str!')

        if not isinstance(what, str):  # type: ignore
            raise TypeError('"what" must be of type str!')

        if what != "" and not validate.validate_obj_type(what):
            raise ValueError("what needs to be a valid collection if it is non empty!")

        if what == "" and ("name" in criteria or name != ""):
            return self.__find_by_name(criteria.get("name", name))

        if what != "":
            return self.__find_with_collection(
                what, name, return_list, no_errors, criteria
            )
        return self.__find_without_collection(name, return_list, no_errors, criteria)

    def __find_with_collection(
        self,
        what: str,
        name: str,
        return_list: bool,
        no_errors: bool,
        criteria: Dict[Any, Any],
    ) -> Optional[Union["ITEM", List["ITEM"]]]:
        items = self._collection_mgr.get_items(what)
        return items.find(
            name=name, return_list=return_list, no_errors=no_errors, **criteria
        )  # type: ignore

    def __find_without_collection(
        self, name: str, return_list: bool, no_errors: bool, criteria: Dict[Any, Any]
    ) -> Optional[Union["ITEM_UNION", List["ITEM_UNION"]]]:
        collections = [
            "distro",
            "profile",
            "system",
            "repo",
            "image",
            "menu",
        ]
        for collection_name in collections:
            match = self.find_items(
                collection_name,
                criteria,
                name=name,
                return_list=return_list,
                no_errors=no_errors,
            )
            if match is not None:
                return match
        return None

    def __find_by_name(self, name: str) -> Optional["ITEM_UNION"]:
        """
        This is a magic method which just searches all collections for the specified name directly,
        :param name: The name of the item(s).
        :return: The found item or None.
        """
        if not isinstance(name, str):  # type: ignore
            raise TypeError("name of an object must be of type str!")
        collections = [
            "distro",
            "profile",
            "system",
            "repo",
            "image",
            "menu",
        ]
        for collection_name in collections:
            match = self.find_items(collection_name, name=name, return_list=False)
            if isinstance(match, list):
                raise ValueError("Ambiguous match during search!")
            if match is not None:
                return match
        return None

    def find_distro(
        self,
        name: str = "",
        return_list: bool = False,
        no_errors: bool = False,
        **kargs: "FIND_KWARGS",
    ) -> Optional[Union[List["distro.Distro"], "distro.Distro"]]:
        """
        Find a distribution via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.distros().find(
            name=name, return_list=return_list, no_errors=no_errors, **kargs
        )

    def find_profile(
        self,
        name: str = "",
        return_list: bool = False,
        no_errors: bool = False,
        **kargs: "FIND_KWARGS",
    ) -> Optional[Union[List["profile_module.Profile"], "profile_module.Profile"]]:
        """
        Find a profile via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.profiles().find(
            name=name, return_list=return_list, no_errors=no_errors, **kargs
        )

    def find_system(
        self,
        name: str = "",
        return_list: bool = False,
        no_errors: bool = False,
        **kargs: "FIND_KWARGS",
    ) -> Optional[Union[List["system_module.System"], "system_module.System"]]:
        """
        Find a system via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.systems().find(
            name=name, return_list=return_list, no_errors=no_errors, **kargs
        )

    def find_repo(
        self,
        name: str = "",
        return_list: bool = False,
        no_errors: bool = False,
        **kargs: "FIND_KWARGS",
    ) -> Optional[Union[List["repo.Repo"], "repo.Repo"]]:
        """
        Find a repository via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.repos().find(
            name=name, return_list=return_list, no_errors=no_errors, **kargs
        )

    def find_image(
        self,
        name: str = "",
        return_list: bool = False,
        no_errors: bool = False,
        **kargs: "FIND_KWARGS",
    ) -> Optional[Union[List["image_module.Image"], "image_module.Image"]]:
        """
        Find an image via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.images().find(
            name=name, return_list=return_list, no_errors=no_errors, **kargs
        )

    def find_menu(
        self,
        name: str = "",
        return_list: bool = False,
        no_errors: bool = False,
        **kargs: "FIND_KWARGS",
    ) -> Optional[Union[List["menu.Menu"], "menu.Menu"]]:
        """
        Find a menu via a name or keys specified in the ``**kargs``.

        :param name: The name to search for.
        :param return_list: If only the first result or all results should be returned.
        :param no_errors: Silence some errors which would raise if this turned to False.
        :param kargs: Additional key-value pairs which may help in finding the desired objects.
        :return: A single object or a list of all search results.
        """
        return self._collection_mgr.menus().find(
            name=name, return_list=return_list, no_errors=no_errors, **kargs
        )

    # ==========================================================================

    @staticmethod
    def __since(
        mtime: float,
        collector: Callable[[], "Collection[ITEM]"],
        collapse: bool = False,
    ) -> List["ITEM"]:
        """
        Called by get_*_since functions. This is an internal part of Cobbler.

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collector: The list of objects to filter after mtime.
        :param collapse: Whether the object should be collapsed to a dict or not. If not the item objects are used for
                         the list.
        :return: The list of objects which are newer then the given timestamp.
        """
        results2: List["ITEM"] = []
        item: "ITEM"
        for item in collector():
            if item.mtime == 0 or item.mtime >= mtime:
                if not collapse:
                    results2.append(item)
                else:
                    results2.append(item.to_dict())
        return results2

    def get_distros_since(
        self, mtime: float, collapse: bool = False
    ) -> List["distro.Distro"]:
        """
        Returns distros modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: collapse=True specifies returning a dict instead of objects.
        :return: The list of distros which are newer then the given timestamp.
        """
        return self.__since(mtime, self.distros, collapse=collapse)

    def get_profiles_since(
        self, mtime: float, collapse: bool = False
    ) -> List["profile_module.Profile"]:
        """
        Returns profiles modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of profiles which are newer then the given timestamp.
        """
        return self.__since(mtime, self.profiles, collapse=collapse)

    def get_systems_since(
        self, mtime: float, collapse: bool = False
    ) -> List["system_module.System"]:
        """
        Return systems modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of systems which are newer then the given timestamp.
        """
        return self.__since(mtime, self.systems, collapse=collapse)

    def get_repos_since(
        self, mtime: float, collapse: bool = False
    ) -> List["repo.Repo"]:
        """
        Return repositories modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of repositories which are newer then the given timestamp.
        """
        return self.__since(mtime, self.repos, collapse=collapse)

    def get_images_since(
        self, mtime: float, collapse: bool = False
    ) -> List["image_module.Image"]:
        """
        Return images modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of images which are newer then the given timestamp.
        """
        return self.__since(mtime, self.images, collapse=collapse)

    def get_menus_since(
        self, mtime: float, collapse: bool = False
    ) -> List["menu.Menu"]:
        """
        Return files modified since a certain time (in seconds since Epoch)

        :param mtime: The timestamp which marks the gate if an object is included or not.
        :param collapse: If True then this specifies that a list of dicts should be returned instead of a list of
                         objects.
        :return: The list of files which are newer then the given timestamp.
        """
        return self.__since(mtime, self.menus, collapse=collapse)

    # ==========================================================================

    @staticmethod
    def get_signatures() -> Dict[str, Any]:
        """
        This returns the local signature cache.

        :return: The dict containing all signatures.
        """
        return signatures.signature_cache

    def signature_update(self) -> None:
        """
        Update all signatures from the URL specified in the settings.
        """
        try:
            url = self.settings().signature_url
            dlmgr = download_manager.DownloadManager()
            # write temp json file
            with tempfile.NamedTemporaryFile() as tmpfile:
                sigjson = dlmgr.urlread(url)
                tmpfile.write(sigjson.text.encode())
                tmpfile.flush()
                self.logger.debug(
                    "Successfully got file from %s", self.settings().signature_url
                )
                # test the import without caching it
                try:
                    signatures.load_signatures(tmpfile.name, cache=False)
                except Exception:
                    self.logger.error(
                        "Downloaded signatures failed test load (tempfile = %s)",
                        tmpfile.name,
                    )

            # rewrite the real signature file and import it for real
            with open(
                self.settings().signature_path, "w", encoding="UTF-8"
            ) as signature_fd:
                signature_fd.write(sigjson.text)

            signatures.load_signatures(self.settings().signature_path)
            self.clean_items_cache(self.get_signatures())
        except Exception:
            utils.log_exc()

    # ==========================================================================

    def dump_vars(
        self,
        obj: "base_item.BaseItem",
        formatted_output: bool = False,
        remove_dicts: bool = False,
    ) -> Union[Dict[str, Any], str]:
        """
        Dump all known variables related to that object.

        :param obj: The object for which the variables should be dumped.
        :param formatted_output: If True the values will align in one column and be pretty printed for cli example.
        :param remove_dicts: If True the dictionaries will be put into str form.
        :return: A dictionary with all the information which could be collected.
        """
        return obj.dump_vars(formatted_output, remove_dicts)

    # ==========================================================================

    def auto_add_repos(self) -> None:
        """
        Import any repos this server knows about and mirror them. Run ``cobbler reposync`` to apply the changes.
        Credit: Seth Vidal.

        :raises ImportError
        """
        self.log("auto_add_repos")
        try:
            import dnf  # type: ignore
        except ImportError as error:
            raise ImportError("dnf is not installed") from error

        base = dnf.Base()  # type: ignore
        base.read_all_repos()  # type: ignore
        basearch = base.conf.substitutions["basearch"]  # type: ignore

        for repository in base.repos.iter_enabled():  # type: ignore
            auto_name: str = repository.id + "-" + base.conf.releasever + "-" + basearch  # type: ignore

            if self.find_repo(auto_name) is None:  # type: ignore
                cobbler_repo = self.new_repo()
                cobbler_repo.name = auto_name
                cobbler_repo.breed = enums.RepoBreeds.YUM
                cobbler_repo.arch = basearch
                cobbler_repo.comment = repository.name  # type: ignore
                baseurl = repository.baseurl  # type: ignore
                metalink = repository.metalink  # type: ignore
                mirrorlist = repository.mirrorlist  # type: ignore

                if metalink is not None:
                    mirror = metalink  # type: ignore
                    mirror_type = enums.MirrorType.METALINK
                elif mirrorlist is not None:
                    mirror = mirrorlist  # type: ignore
                    mirror_type = enums.MirrorType.MIRRORLIST
                elif len(baseurl) > 0:  # type: ignore
                    mirror = baseurl[0]  # type: ignore
                    mirror_type = enums.MirrorType.BASEURL
                else:
                    mirror = ""
                    mirror_type = enums.MirrorType.NONE

                cobbler_repo.mirror = mirror
                cobbler_repo.mirror_type = mirror_type
                self.log(f"auto repo adding: {auto_name}")
                self.add_repo(cobbler_repo)
            else:
                self.log(f"auto repo adding: {auto_name} - exists")

    # ==========================================================================

    def get_repo_config_for_profile(self, obj: "base_item.BaseItem") -> str:
        """
        Get the repository configuration for the specified profile

        :param obj: The profile to return the configuration for.
        :return: The repository configuration as a string.
        """
        return self.yumgen.get_yum_config(obj, True)

    def get_repo_config_for_system(self, obj: "base_item.BaseItem") -> str:
        """
        Get the repository configuration for the specified system.

        :param obj: The system to return the configuration for.
        :return: The repository configuration as a string.
        """
        return self.yumgen.get_yum_config(obj, False)

    # ==========================================================================

    def get_template_file_for_profile(self, obj: "ITEM_UNION", path: str) -> str:
        """
        Get the template for the specified profile.

        :param obj: The object which is related to that template.
        :param path: The path to the template.
        :return: The template as in its string representation.
        """
        template_results = self.tftpgen.write_templates(obj, False, path)
        if path in template_results:
            return template_results[path]
        return "# template path not found for specified profile"

    def get_template_file_for_system(self, obj: "ITEM_UNION", path: str) -> str:
        """
        Get the template for the specified system.

        :param obj: The object which is related to that template.
        :param path: The path to the template.
        :return: The template as in its string representation.
        """
        template_results = self.tftpgen.write_templates(obj, False, path)
        if path in template_results:
            return template_results[path]
        return "# template path not found for specified system"

    # ==========================================================================

    def generate_ipxe(self, profile: str, image: str, system: str) -> str:
        """
        Generate the ipxe configuration files. The system wins over the profile. Profile and System win over Image.

        :param profile: The profile to return the configuration for.
        :param image: The image to return the configuration for.
        :param system: The system to return the configuration for.
        :return: The generated configuration file.
        """
        self.log("generate_ipxe")
        data = ""
        if profile is None and image is None and system is None:  # type: ignore
            boot_menu = self.tftpgen.make_pxe_menu()
            if "ipxe" in boot_menu:
                data = boot_menu["ipxe"]
                if not isinstance(data, str):
                    raise ValueError("ipxe boot menu didn't have right type!")
        elif system:
            data = self.tftpgen.generate_ipxe("system", system)
        elif profile:
            data = self.tftpgen.generate_ipxe("profile", profile)
        elif image:
            data = self.tftpgen.generate_ipxe("image", image)
        return data

    # ==========================================================================

    def generate_bootcfg(self, profile: str = "", system: str = "") -> str:
        """
        Generate a boot configuration. The system wins over the profile.

        :param profile: The profile to return the configuration for.
        :param system: The system to return the configuration for.
        :return: The generated configuration file.
        """
        self.log("generate_bootcfg")
        if system:
            return self.tftpgen.generate_bootcfg("system", system)
        return self.tftpgen.generate_bootcfg("profile", profile)

    # ==========================================================================

    def generate_script(
        self, profile: Optional[str], system: Optional[str], name: str
    ) -> str:
        """
        Generate an autoinstall script for the specified profile or system. The system wins over the profile.

        :param profile: The profile name to generate the script for.
        :param system: The system name to generate the script for.
        :param name: The name of the script which should be generated. Must only contain alphanumeric characters, dots
                     and underscores.
        :return: The generated script or an error message.
        """
        self.log("generate_script")
        if system:
            return self.tftpgen.generate_script("system", system, name)
        if profile:
            return self.tftpgen.generate_script("profile", profile, name)
        return ""

    # ==========================================================================

    def check(self) -> List[str]:
        """
        See if all preqs for network booting are valid. This returns a list of strings containing instructions on things
        to correct. An empty list means there is nothing to correct, but that still doesn't mean there are configuration
        errors. This is mainly useful for human admins, who may, for instance, forget to properly set up their TFTP
        servers for PXE, etc.

        :return: A list of things to address.
        """
        self.log("check")
        action_check = check.CobblerCheck(self)
        return action_check.run()

    # ==========================================================================

    def validate_autoinstall_files(self) -> None:
        """
        Validate if any of the autoinstallation files are invalid and if yes report this.

        """
        self.log("validate_autoinstall_files")
        autoinstall_mgr = autoinstall_manager.AutoInstallationManager(self)
        autoinstall_mgr.validate_autoinstall_files()

    # ==========================================================================

    def sync_systems(self, systems: List[str], verbose: bool = False) -> None:
        """
        Take the values currently written to the configuration files in /etc, and /var, and build out the information
        tree found in /tftpboot. Any operations done in the API that have not been saved with serialize() will NOT be
        synchronized with this command.

        :param systems: List of specified systems that needs to be synced
        :param verbose: If the action should be just logged as needed or (if True) as much verbose as possible.
        """
        self.logger.info("sync_systems")
        if not (
            systems
            and isinstance(systems, list)  # type: ignore
            and all(isinstance(sys_name, str) for sys_name in systems)  # type: ignore
        ):
            if len(systems) < 1:
                self.logger.debug(
                    "sync_systems needs at least one system to do something. Bailing out early."
                )
                return
            raise TypeError("Systems must be a list of one or more strings.")
        sync_obj = self.get_sync(verbose=verbose)
        sync_obj.run_sync_systems(systems)

    # ==========================================================================

    def sync(self, verbose: bool = False, what: Optional[List[str]] = None) -> None:
        """
        Take the values currently written to the configuration files in /etc, and /var, and build out the information
        tree found in /tftpboot. Any operations done in the API that have not been saved with serialize() will NOT be
        synchronized with this command.

        :param verbose: If the action should be just logged as needed or (if True) as much verbose as possible.
        :param what:   List of strings what services to sync (e.g. dhcp and/or dns). Empty list for full sync.
        """
        # Empty what: Full sync
        if not what:
            self.logger.info("syncing all")
            sync_obj = self.get_sync(verbose=verbose)
            sync_obj.run()
            return
        # Non empty what: Specific sync
        if not isinstance(what, list):  # type: ignore
            raise TypeError("'what' needs to be of type list!")
        if "dhcp" in what:
            self.sync_dhcp()
        if "dns" in what:
            self.sync_dns()

    # ==========================================================================

    def sync_dns(self) -> None:
        """
        Only build out the DNS configuration.
        """
        if not self.settings().manage_dns:
            self.logger.info('"manage_dns" not set. Skipping DNS sync.')
            return
        self.logger.info("sync_dns")
        dns_module = self.get_module_from_file("dns", "module", "managers.bind")
        dns = dns_module.get_manager(self)
        dns.sync()

    # ==========================================================================

    def sync_dhcp(self) -> None:
        """
        Only build out the DHCP configuration.
        """
        if not self.settings().manage_dhcp:
            self.logger.info('"manage_dhcp" not set. Skipping DHCP sync.')
            return
        self.logger.info("sync_dhcp")
        dhcp_module = self.get_module_from_file("dhcp", "module", "managers.isc")
        dhcp = dhcp_module.get_manager(self)
        dhcp.sync()

    # ==========================================================================

    def get_sync(self, verbose: bool = False) -> "sync_module.CobblerSync":
        """
        Get a Cobbler Sync object which may be executed through the call of ``obj.run()``.

        :param verbose: If the action should be just logged as needed or (if True) as much verbose as possible.
        :return: An instance of the CobblerSync class to execute the sync with.
        """
        if not isinstance(verbose, bool):  # type: ignore
            raise TypeError("get_sync: verbose parameter needs to be of type bool!")
        dhcp = self.get_module_from_file("dhcp", "module", "managers.isc").get_manager(
            self
        )
        dns = self.get_module_from_file("dns", "module", "managers.bind").get_manager(
            self
        )
        tftpd = self.get_module_from_file(
            "tftpd",
            "module",
            "managers.in_tftpd",
        ).get_manager(self)

        return sync_module.CobblerSync(
            self, dhcp=dhcp, dns=dns, tftpd=tftpd, verbose=verbose
        )

    # ==========================================================================

    def reposync(
        self, name: Optional[str] = None, tries: int = 1, nofail: bool = False
    ) -> None:
        """
        Take the contents of ``/var/lib/cobbler/repos`` and update them -- or create the initial copy if no contents
        exist yet.

        :param name: The name of the repository to run reposync for.
        :param tries: How many tries should be executed before the action fails.
        :param nofail: If True then the action will fail, otherwise the action will just be skipped. This respects the
                       ``tries`` parameter.
        """
        self.log("reposync", [name])
        action_reposync = reposync.RepoSync(self, tries=tries, nofail=nofail)
        action_reposync.run(name)

    # ==========================================================================

    def status(self, mode: str) -> Union[Dict[Any, Any], str]:
        """
        Get the status of the current Cobbler instance.

        :param mode: "text" or anything else. Meaning whether the output is thought for the terminal or not.
        :return: The current status of Cobbler.
        """
        statusifier = status.CobblerStatusReport(self, mode)
        return statusifier.run()

    # ==========================================================================

    def import_tree(
        self,
        mirror_url: str,
        mirror_name: str,
        network_root: Optional[str] = None,
        autoinstall_file: Optional[str] = None,
        rsync_flags: Optional[str] = None,
        arch: Optional[str] = None,
        breed: Optional[str] = None,
        os_version: Optional[str] = None,
    ) -> bool:
        """
        Automatically import a directory tree full of distribution files.

        :param mirror_url: Can be a string that represents a path, a user@host syntax for SSH, or an rsync:// address.
                           If mirror_url is a filesystem path and mirroring is not desired, set network_root to
                           something like "nfs://path/to/mirror_url/root"
        :param mirror_name: The name of the mirror.
        :param network_root: the remote path (nfs/http/ftp) for the distro files
        :param autoinstall_file: user-specified response file, which will override the default
        :param rsync_flags: Additional flags that will be passed to the rsync call that will sync everything to the
                            Cobbler webroot.
        :param arch: user-specified architecture
        :param breed: user-specified breed
        :param os_version: user-specified OS version
        """
        distro_importer = importer.Importer(api=self)
        return distro_importer.run(
            mirror_url,
            mirror_name,
            network_root,
            autoinstall_file,
            rsync_flags,
            arch,
            breed,
            os_version,
        )

    # ==========================================================================

    def acl_config(
        self,
        adduser: Optional[str] = None,
        addgroup: Optional[str] = None,
        removeuser: Optional[str] = None,
        removegroup: Optional[str] = None,
    ) -> None:
        """
        Configures users/groups to run the Cobbler CLI as non-root.
        Pass in only one option at a time. Powers ``cobbler aclconfig``.

        :param adduser:
        :param addgroup:
        :param removeuser:
        :param removegroup:
        """
        action_acl = acl.AclConfig(self)
        action_acl.run(
            adduser=adduser,
            addgroup=addgroup,
            removeuser=removeuser,
            removegroup=removegroup,
        )

    # ==========================================================================

    def serialize(self) -> None:
        """
        Save the cobbler_collections to disk.
        Cobbler internal use only.
        """
        self._collection_mgr.serialize()

    def deserialize(self) -> None:
        """
        Load cobbler_collections from disk.
        Cobbler internal use only.
        """
        return self._collection_mgr.deserialize()

    def deserialize_item(self, obj: "base_item.BaseItem") -> Dict[str, Any]:
        """
        Load cobbler item from disk.
        Cobbler internal use only.
        """
        return self._collection_mgr.deserialize_one_item(obj)

    # ==========================================================================

    def get_module_by_name(self, module_name: str) -> Optional[ModuleType]:
        """
        Returns a loaded Cobbler module named 'name', if one exists, else None.
        Cobbler internal use only.

        :param module_name:
        :return:
        """
        return self.module_loader.get_module_by_name(module_name)

    def get_module_from_file(
        self, section: str, name: str, fallback: Optional[str] = None
    ) -> ModuleType:
        """
        Looks in ``/etc/cobbler/settings.yaml`` for a section called 'section' and a key called 'name', and then returns
        the module that corresponds to the value of that key.
        Cobbler internal use only.

        :param section: The section to look at.
        :param name: The name of the module to retrieve
        :param fallback: The default module in case the requested one is not found.
        :return: The requested Python Module.
        """
        return self.module_loader.get_module_from_file(section, name, fallback)

    def get_module_name_from_file(
        self, section: str, name: str, fallback: Optional[str] = None
    ) -> str:
        """
        Looks up a module the same as ``get_module_from_file`` but returns the module name rather than the module
        itself.

        :param section:
        :param name:
        :param fallback:
        :return:
        """
        return self.module_loader.get_module_name(section, name, fallback)

    def get_modules_in_category(self, category: str) -> List[ModuleType]:
        """
        Returns all modules in a given category, for instance "serializer", or "cli".
        Cobbler internal use only.

        :param category: The category to check.
        :return: The list of modules.
        """
        return self.module_loader.get_modules_in_category(category)

    # ==========================================================================

    def authenticate(self, user: str, password: str) -> bool:
        """
        (Remote) access control. This depends on the chosen authentication module.
        Cobbler internal use only.

        :param user: The username to check for authentication.
        :param password: The password to check for authentication.
        :return: Whether the action succeeded or not.
        """
        return_code: bool = self.authn.authenticate(self, user, password)
        self.log("authenticate", [user, str(return_code)])
        return return_code

    def authorize(
        self, user: str, resource: str, arg1: Optional[str] = None, arg2: Any = None
    ) -> int:
        """
        (Remote) access control. This depends on the chosen authorization module.
        Cobbler internal use only.

        :param user: The username to check for authorization.
        :param resource: The type of resource which should be checked for access from the supplied user.
        :param arg1: The actual resource to check for authorization.
        :param arg2: Not known what this parameter does exactly.
        :return: The return code of the action.
        """
        return_code: int = self.authz.authorize(self, user, resource, arg1, arg2)
        self.log(
            "authorize", [user, resource, arg1, arg2, str(return_code)], debug=True
        )
        return return_code

    # ==========================================================================

    def build_iso(
        self,
        iso: str = "autoinst.iso",
        profiles: Optional[List[str]] = None,
        systems: Optional[List[str]] = None,
        buildisodir: str = "",
        distro_name: str = "",
        standalone: bool = False,
        airgapped: bool = False,
        source: str = "",
        exclude_dns: bool = False,
        xorrisofs_opts: str = "",
    ) -> None:
        r"""
        Build an iso image which may be network bootable or not.

        :param iso: The name of the ISO. Defaults to ``autoinst.iso``.
        :param profiles: Use these profiles only
        :param systems: Use these systems only
        :param buildisodir: This overwrites the directory from the settings in which the iso is built in.
        :param distro_name: Used with ``--standalone`` and ``--airgapped`` to create a distro-based ISO including all
                       associated.
        :param standalone: This means that no network connection is needed to install the generated iso.
        :param airgapped: This option implies ``standalone=True``.
        :param source: If the iso should be offline available this is the path to the sources of the image.
        :param exclude_dns: Whether the repositories have to be locally available or the internet is reachable.
        :param xorrisofs_opts: ``xorrisofs`` options to include additionally.
        """
        if not isinstance(standalone, bool):  # type: ignore
            raise TypeError('Argument "standalone" needs to be of type bool!')
        if not isinstance(airgapped, bool):  # type: ignore
            raise TypeError('Argument "airgapped" needs to be of type bool!')
        if airgapped:
            standalone = True
        Builder = StandaloneBuildiso if standalone else NetbootBuildiso
        Builder(self).run(
            iso=iso,
            buildisodir=buildisodir,
            profiles=profiles,
            xorrisofs_opts=xorrisofs_opts,
            distro_name=distro_name,
            airgapped=airgapped,
            source=source,
            systems=systems,
            exclude_dns=exclude_dns,
        )

    # ==========================================================================

    def hardlink(self) -> int:
        """
        Hardlink all files where this is possible to improve performance.

        :return: The return code of the subprocess call which actually hardlinks the files.
        """
        linker = hardlink.HardLinker(api=self)
        return linker.run()

    # ==========================================================================

    def replicate(
        self,
        cobbler_master: Optional[str] = None,
        port: str = "80",
        distro_patterns: str = "",
        profile_patterns: str = "",
        system_patterns: str = "",
        repo_patterns: str = "",
        image_patterns: str = "",
        prune: bool = False,
        omit_data: bool = False,
        sync_all: bool = False,
        use_ssl: bool = False,
    ) -> None:
        """
        Pull down data/configs from a remote Cobbler server that is a master to this server.

        :param cobbler_master: The hostname/URL of the other Cobbler server
        :param port: The port to use for the replication task.
        :param distro_patterns: The pattern of distros which should be synced.
        :param profile_patterns: The pattern of profiles which should be synced.
        :param system_patterns: The pattern of systems which should be synced.
        :param repo_patterns: The pattern of repositories which should be synced.
        :param image_patterns: The pattern of images which should be synced.
        :param prune: Whether the object not on the master should be removed or not.
        :param omit_data: If the data downloaded by the current Cobbler server should be rsynced to the destination
                          server.
        :param sync_all: This parameter behaves similarly to a dry run argument. If True then everything will executed,
                         if False then only some things are synced.
        :param use_ssl: Whether SSL should be used (True) or not (False).
        """
        replicator = replicate.Replicate(self)
        replicator.run(
            cobbler_master=cobbler_master,
            port=port,
            distro_patterns=distro_patterns,
            profile_patterns=profile_patterns,
            system_patterns=system_patterns,
            repo_patterns=repo_patterns,
            image_patterns=image_patterns,
            prune=prune,
            omit_data=omit_data,
            sync_all=sync_all,
            use_ssl=use_ssl,
        )

    # ==========================================================================

    def report(
        self,
        report_what: str = "",
        report_name: str = "",
        report_type: str = "",
        report_fields: str = "",
        report_noheaders: bool = False,
    ) -> None:
        """
        Report functionality for Cobbler.

        :param report_what: The object type that should be reported.
        :param report_name: The name of the object which should be possibly reported.
        :param report_type: May be either "text", "csv", "mediawiki", "trac" or "doku".
        :param report_fields: Specify "all" or the fields you want to be reported.
        :param report_noheaders: If the column headers should be included in the output or not.
        """
        reporter = report.Report(self)
        reporter.run(
            report_what=report_what,
            report_name=report_name,
            report_type=report_type,
            report_fields=report_fields,
            report_noheaders=report_noheaders,
        )

    # ==========================================================================

    def power_system(
        self,
        system: "system_module.System",
        power_operation: str,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Optional[bool]:
        """
        Power on / power off / get power status /reboot a system.

        :param system: Cobbler system
        :param power_operation: power operation. Valid values: on, off, reboot, status
        :param user: power management user
        :param password: power management password
        :return: bool if operation was successful
        """
        power_mgr = power_manager.PowerManager(self)
        if power_operation == "on":
            power_mgr.power_on(system, user=user, password=password)
        elif power_operation == "off":
            power_mgr.power_off(system, user=user, password=password)
        elif power_operation == "status":
            return power_mgr.get_power_status(system, user=user, password=password)
        elif power_operation == "reboot":
            power_mgr.reboot(system, user=user, password=password)
        else:
            utils.die(
                f"invalid power operation '{power_operation}', expected on/off/status/reboot"
            )
        return None

    # ==========================================================================

    def clear_logs(self, system: "system_module.System") -> None:
        """
        Clears console and anamon logs for system

        :param system: The system to clear logs of.
        """
        log.LogTool(system, self).clear()

    # ==========================================================================

    def get_valid_obj_boot_loaders(
        self, obj: Union["distro.Distro", "image_module.Image"]
    ) -> List[str]:
        """
        Return the list of valid boot loaders for the object

        :param obj: The object for which the boot loaders should be looked up.
        :return: Get a list of all valid boot loaders.
        """
        return obj.supported_boot_loaders

    # ==========================================================================

    def mkloaders(self) -> None:
        """
        Create the GRUB installer images via this API call. It utilizes ``grub2-mkimage`` behind the curtain.
        """
        action = mkloaders.MkLoaders(self)
        action.run()

    # ==========================================================================

    def input_string_or_list_no_inherit(
        self, options: Optional[Union[str, List[Any]]]
    ) -> List[Any]:
        """
        .. seealso:: :func:`~cobbler.utils.input_converters.input_string_or_list_no_inherit`
        """
        return input_converters.input_string_or_list_no_inherit(options)

    def input_string_or_list(
        self, options: Optional[Union[str, List[Any]]]
    ) -> Union[List[Any], str]:
        """
        .. seealso:: :func:`~cobbler.utils.input_converters.input_string_or_list`
        """
        return input_converters.input_string_or_list(options)

    def input_string_or_dict(
        self,
        options: Union[str, List[Any], Dict[Any, Any]],
        allow_multiples: bool = True,
    ) -> Union[str, Dict[Any, Any]]:
        """
        .. seealso:: :func:`~cobbler.utils.input_converters.input_string_or_dict`
        """
        return input_converters.input_string_or_dict(
            options, allow_multiples=allow_multiples
        )

    def input_string_or_dict_no_inherit(
        self,
        options: Union[str, List[Any], Dict[Any, Any]],
        allow_multiples: bool = True,
    ) -> Dict[Any, Any]:
        """
        .. seealso:: :func:`~cobbler.utils.input_converters.input_string_or_dict_no_inherit`
        """
        return input_converters.input_string_or_dict_no_inherit(
            options, allow_multiples=allow_multiples
        )

    def input_boolean(self, value: Union[str, bool, int]) -> bool:
        """
        .. seealso:: :func:`~cobbler.utils.input_converters.input_boolean`
        """
        return input_converters.input_boolean(value)

    def input_int(self, value: Union[str, int, float]) -> int:
        """
        .. seealso:: :func:`~cobbler.utils.input_converters.input_int`
        """
        return input_converters.input_int(value)

    def get_tftp_file(self, path: str, offset: int, size: int) -> Tuple[bytes, int]:
        """
        Generate and return a file for a TFTP client.

        :param path: Path to file
        :param offset: Offset of the requested chunk in the file
        :param size: Size of the requested chunk in the file
        :return: The requested chunk and the length of the whole file
        """
        normalized_path = Path(os.path.normpath(os.path.join("/", path)))

        return self.tftpgen.generate_tftp_file(normalized_path, offset, size)
