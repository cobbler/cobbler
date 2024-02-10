"""
This module contains all code related to the Cobbler XML-RPC API.

Changelog:

Schema: From -> To

Current Schema: Please refer to the documentation visible of the individual methods.

V3.4.0 (unreleased)
    * Added:
        * ``set_item_resolved_value``
        * ``input_string_or_list_no_inherit``
        * ``input_string_or_list``
        * ``input_string_or_dict``
        * ``input_string_or_dict_no_inherit``
        * ``input_boolean``
        * ``input_int``

V3.3.4 (unreleased)
    * No changes

V3.3.3
    * Added:
        * ``get_item_resolved_value``
        * ``dump_vars``

V3.3.2
    * No changes

V3.3.1
    * Changed:
        * ``background_mkgrub``: Renamed to ``background_mkloaders``

V3.3.0
    * Added:
        * ``background_syncsystems``
        * ``background_mkgrub``
        * ``get_menu``
        * ``find_menu``
        * ``get_menu_handle``
        * ``remove_menu``
        * ``copy_menu``
        * ``rename_menu``
        * ``new_menu``
        * ``modify_menu``
        * ``save_menu``
        * ``get_valid_distro_boot_loaders``
        * ``get_valid_image_boot_loaders``
        * ``get_valid_profile_boot_loaders``
        * ``get_valid_system_boot_loaders``
        * ``get_menus_since``
        * ``get_menu_as_rendered``
    * Changed:
        * ``generate_gpxe``: Renamed to ``generate_ipxe``
    * Removed:
        * ``background_dlcontent``
        * ``get_distro_for_koan``
        * ``get_profile_for_koan``
        * ``get_system_for_koan``
        * ``get_repo_for_koan``
        * ``get_image_for_koan``
        * ``get_mgmtclass_for_koan``
        * ``get_package_for_koan``
        * ``get_file_for_koan``
        * ``get_file_for_koan``

V3.2.2
    * No changes

V3.2.1
    * Added:
        * ``auto_add_repos``

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
        * ``generate_profile_autoinstall``
        * ``generate_system_autoinstall``
        * ``get_valid_archs``
        * ``read_autoinstall_template``
        * ``write_autoinstall_template``
        * ``remove_autoinstall_template``
        * ``read_autoinstall_snippet``
        * ``write_autoinstall_snippet``
        * ``remove_autoinstall_snippet``
    * Changed:
        * ``get_kickstart_templates``: Renamed to ``get_autoinstall_templates``
        * ``get_snippets``: Renamed to ``get_autoinstall_snippets``
        * ``is_kickstart_in_use``: Renamed to ``is_autoinstall_in_use``
        * ``generate_kickstart``: Renamed to ``generate_autoinstall``
    * Removed:
        * ``update``
        * ``read_or_write_kickstart_template``
        * ``read_or_write_snippet``

V2.8.5
    * Inital tracking of changes.

"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import base64
import errno
import fcntl
import keyword
import logging
import os
import random
import re
import stat
import time
import xmlrpc.server
from socketserver import ThreadingMixIn
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)
from xmlrpc.server import SimpleXMLRPCRequestHandler

from cobbler import autoinstall_manager, configgen, enums, tftpgen, utils
from cobbler.cexceptions import CX
from cobbler.items import system
from cobbler.items.abstract import base_item
from cobbler.items.network_interface import NetworkInterface
from cobbler.utils import signatures
from cobbler.utils.event import CobblerEvent
from cobbler.utils.thread import CobblerThread
from cobbler.validate import (
    validate_autoinstall_script_name,
    validate_obj_name,
    validate_uuid,
)

if TYPE_CHECKING:
    import xmlrpc.client

    from cobbler.api import CobblerAPI
    from cobbler.cobbler_collections.collection import ITEM, ITEM_UNION
    from cobbler.items.distro import Distro
    from cobbler.items.image import Image
    from cobbler.items.profile import Profile


EVENT_TIMEOUT = 7 * 24 * 60 * 60  # 1 week
CACHE_TIMEOUT = 10 * 60  # 10 minutes


class CobblerXMLRPCInterface:
    """
    This is the interface used for all XMLRPC methods, for instance, as used by koan or CobblerWeb.

    Most read-write operations require a token returned from "login". Read operations do not.
    """

    def __init__(self, api: "CobblerAPI"):
        """
        Constructor. Requires a Cobbler API handle.

        :param api: The api to use for resolving the required information.
        """
        self.api = api
        self.logger = logging.getLogger()
        self.token_cache: Dict[str, Tuple[Any, ...]] = {}
        self.unsaved_items: Dict[str, Tuple[float, "ITEM_UNION"]] = {}
        self.timestamp = self.api.last_modified_time()
        self.events: Dict[str, CobblerEvent] = {}
        self.shared_secret = utils.get_shared_secret()
        random.seed(time.time())
        self.tftpgen = tftpgen.TFTPGen(api)
        self.autoinstall_mgr = autoinstall_manager.AutoInstallationManager(api)

    def check(self, token: str) -> List[str]:
        """
        Returns a list of all the messages/warnings that are things that admin may want to correct about the
        configuration of the Cobbler server. This has nothing to do with "check_access" which is an auth/authz function
        in the XMLRPC API.

        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: A list of things to address.
        """
        self.check_access(token, "check")
        return self.api.check()

    def background_buildiso(self, options: Dict[str, Any], token: str) -> str:
        """
        Generates an ISO in /var/www/cobbler/pub that can be used to install profiles without using PXE.

        :param options: This parameter does contain the options passed from the CLI or remote API who called this.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """
        webdir = self.api.settings().webdir

        def runner(self: CobblerThread):
            if not isinstance(self.options, dict):
                raise ValueError("Options need to be dict for background_buildiso!")
            self.remote.api.build_iso(
                self.options.get("iso", webdir + "/pub/generated.iso"),
                self.options.get("profiles", None),
                self.options.get("systems", None),
                self.options.get("buildisodir", ""),
                self.options.get("distro", ""),
                self.options.get("standalone", False),
                self.options.get("airgapped", False),
                self.options.get("source", ""),
                self.options.get("exclude_dns", False),
                self.options.get("xorrisofs_opts", ""),
            )

        def on_done(self: CobblerThread):
            if not isinstance(self.options, dict):
                raise ValueError("Options need to be dict for background_buildiso!")
            if self.options.get("iso", "") == webdir + "/pub/generated.iso":
                msg = 'ISO now available for <A HREF="/cobbler/pub/generated.iso">download</A>'
                self.remote._new_event(msg)

        return self.__start_task(
            runner, token, "buildiso", "Build Iso", options, on_done
        )

    def background_aclsetup(self, options: Dict[str, Any], token: str) -> str:
        """
        Get the acl configuration from the config and set the acls in the backgroud.

        :param options: Not known what this parameter does.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """

        def runner(self: CobblerThread):
            if not isinstance(self.options, dict):
                raise ValueError(
                    "self.options needs to be dict for background_aclsetup!"
                )
            self.remote.api.acl_config(
                self.options.get("adduser", None),
                self.options.get("addgroup", None),
                self.options.get("removeuser", None),
                self.options.get("removegroup", None),
            )

        return self.__start_task(
            runner, token, "aclsetup", "(CLI) ACL Configuration", options
        )

    def background_sync(self, options: Dict[str, Any], token: str) -> str:
        """
        Run a full Cobbler sync in the background.

        :param options: Possible options: verbose, dhcp, dns
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """

        def runner(self: CobblerThread):
            if isinstance(self.options, list):
                raise ValueError("options for background_sync need to be dict!")
            what: List[str] = []
            if self.options.get("dhcp", False):
                what.append("dhcp")
            if self.options.get("dns", False):
                what.append("dns")
            self.remote.api.sync(self.options.get("verbose", False), what=what)

        return self.__start_task(runner, token, "sync", "Sync", options)

    def background_syncsystems(self, options: Dict[str, Any], token: str) -> str:
        """
        Run a lite Cobbler sync in the background with only systems specified.

        :param options: Unknown what this parameter does.
        :param token: The API-token obtained via the login() method.
        :return: The id of the task that was started.
        """

        def runner(self: "CobblerThread"):
            if isinstance(self.options, list):
                raise ValueError("options for background_syncsystems need to be dict!")
            self.remote.api.sync_systems(
                self.options.get("systems", []), self.options.get("verbose", False)
            )

        return self.__start_task(runner, token, "syncsystems", "Syncsystems", options)

    def background_hardlink(self, options: Dict[str, Any], token: str) -> str:
        """
        Hardlink all files as a background task.

        :param options: Not known what this parameter does.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """

        def runner(self: "CobblerThread"):
            self.remote.api.hardlink()

        return self.__start_task(runner, token, "hardlink", "Hardlink", options)

    def background_validate_autoinstall_files(
        self, options: Dict[str, Any], token: str
    ) -> str:
        """
        Validate all autoinstall files in the background.

        :param options: Not known what this parameter does.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """

        def runner(self: "CobblerThread"):
            return self.remote.api.validate_autoinstall_files()

        return self.__start_task(
            runner,
            token,
            "validate_autoinstall_files",
            "Automated installation files validation",
            options,
        )

    def background_replicate(self, options: Dict[str, Any], token: str) -> str:
        """
        Replicate Cobbler in the background to another Cobbler instance.

        :param options: Not known what this parameter does.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """

        def runner(self: "CobblerThread"):
            # FIXME: defaults from settings here should come from views, fix in views.py
            if isinstance(self.options, list):
                raise ValueError("options for background_replicate need to be dict!")
            self.remote.api.replicate(
                self.options.get("master", None),
                self.options.get("port", ""),
                self.options.get("distro_patterns", ""),
                self.options.get("profile_patterns", ""),
                self.options.get("system_patterns", ""),
                self.options.get("repo_patterns", ""),
                self.options.get("image_patterns", ""),
                self.options.get("prune", False),
                self.options.get("omit_data", False),
                self.options.get("sync_all", False),
                self.options.get("use_ssl", False),
            )

        return self.__start_task(runner, token, "replicate", "Replicate", options)

    def background_import(self, options: Dict[str, Any], token: str) -> str:
        """
        Import an ISO image in the background.

        :param options: Not known what this parameter does.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """

        def runner(self: "CobblerThread"):
            if isinstance(self.options, list):
                raise ValueError("options for background_import need to be dict!")
            self.remote.api.import_tree(
                self.options.get("path", None),
                self.options.get("name", None),
                self.options.get("available_as", None),
                self.options.get("autoinstall_file", None),
                self.options.get("rsync_flags", None),
                self.options.get("arch", None),
                self.options.get("breed", None),
                self.options.get("os_version", None),
            )

        return self.__start_task(runner, token, "import", "Media import", options)

    def background_reposync(self, options: Dict[str, Any], token: str) -> str:
        """
        Run a reposync in the background.

        :param options: Not known what this parameter does.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """

        def runner(self: "CobblerThread"):
            # NOTE: WebUI passes in repos here, CLI passes only:
            if isinstance(self.options, list):
                raise ValueError("options for background_reposync need to be dict!")

            repos = options.get("repos", [])
            only = options.get("only", None)
            if only is not None:
                repos = [only]
            nofail = options.get("nofail", len(repos) > 0)

            if len(repos) > 0:
                for name in repos:
                    self.remote.api.reposync(
                        tries=self.options.get("tries", 3), name=name, nofail=nofail
                    )
            else:
                self.remote.api.reposync(
                    tries=self.options.get("tries", 3), name=None, nofail=nofail
                )

        return self.__start_task(runner, token, "reposync", "Reposync", options)

    def background_power_system(self, options: Dict[str, Any], token: str) -> str:
        """
        Power a system asynchronously in the background.

        :param options: Not known what this parameter does.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """

        def runner(self: "CobblerThread"):
            if isinstance(self.options, list):
                raise ValueError("options for background_power_system need to be dict!")

            for system_name in self.options.get("systems", []):
                try:
                    system_obj = self.remote.api.find_system(name=system_name)
                    if system_obj is None or isinstance(system_obj, list):
                        raise ValueError(f'System with name "{system_name}" not found')
                    self.remote.api.power_system(
                        system_obj, self.options.get("power", "")
                    )
                except Exception as error:
                    self.logger.warning(
                        f"failed to execute power task on {str(system_name)}, exception: {str(error)}"
                    )

        self.check_access(token, "power_system")
        return self.__start_task(
            runner,
            token,
            "power",
            f"Power management ({options.get('power', '')})",
            options,
        )

    def power_system(self, system_id: str, power: str, token: str) -> bool:
        """Execute power task synchronously.

        Returns true if the operation succeeded or if the system is powered on (in case of status).
        False otherwise.

        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method. All
                      tasks require tokens.
        :param system_id: system handle
        :param power: power operation (on/off/status/reboot)
        """
        system_obj = self.api.find_system(
            criteria={"uid": system_id}, return_list=False
        )
        if system_obj is None or isinstance(system_obj, list):
            raise ValueError(f'System with uid "{system_id}" not found')
        self.check_access(token, "power_system", system_obj.name)
        result = self.api.power_system(system_obj, power)
        return True if result is None else result

    def background_signature_update(self, options: Dict[str, Any], token: str) -> str:
        """
        Run a signature update in the background.

        :param options: Not known what this parameter does.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The id of the task which was started.
        """

        def runner(self: "CobblerThread"):
            self.remote.api.signature_update()

        self.check_access(token, "sigupdate")
        return self.__start_task(
            runner, token, "sigupdate", "Updating Signatures", options
        )

    def background_mkloaders(self, options: Dict[str, Any], token: str) -> str:
        """
        TODO

        :param options: TODO
        :param token: TODO
        :return: TODO
        """

        def runner(self: "CobblerThread"):
            return self.api.mkloaders()

        return self.__start_task(
            runner, token, "mkloaders", "Create bootable bootloader images", options
        )

    def get_events(self, for_user: str = "") -> Dict[str, List[Union[str, float]]]:
        """
        Returns a dict(key=event id) = [ statetime, name, state, [read_by_who] ]

        :param for_user: (Optional) Filter events the user has not seen yet. If left unset, it will return all events.
        :return: A dictionary with all the events (or all filtered events).
        """
        # Check for_user not none
        if not isinstance(for_user, str):  # type: ignore
            raise TypeError('"for_user" must be of type str (may be empty str)!')

        # return only the events the user has not seen
        events_filtered: Dict[str, List[Union[str, float]]] = {}
        for event_details in self.events.values():
            if for_user in event_details.read_by_who:
                continue

            events_filtered[event_details.event_id] = list(event_details)  # type: ignore
            # If a user is given (and not already in read list), add read tag, so user won't get the event twice
            if for_user and for_user not in event_details.read_by_who:
                event_details.read_by_who.append(for_user)

        return events_filtered

    def get_event_log(self, event_id: str) -> str:
        """
        Returns the contents of a task log. Events that are not task-based do not have logs.

        :param event_id: The event-id generated by Cobbler.
        :return: The event log or a ``?``.
        """
        if not isinstance(event_id, str):  # type: ignore
            raise TypeError('"event_id" must be of type str!')
        if event_id not in self.events:
            # This ensures the event_id is valid, and we only read files we want to read.
            return "?"
        path = f"/var/log/cobbler/tasks/{event_id}.log"
        self._log(f"getting log for {event_id}")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as event_log_fd:
                data = str(event_log_fd.read())
            return data
        return "?"

    def _new_event(self, name: str) -> CobblerEvent:
        """
        Generate a new event in the in memory event list.

        :param name: The name of the event.
        """
        new_event = CobblerEvent(name=name, statetime=time.time())
        self.events[new_event.event_id] = new_event
        return new_event

    def __start_task(
        self,
        thr_obj_fn: Callable[["CobblerThread"], None],
        token: str,
        role_name: str,
        name: str,
        args: Dict[str, Any],
        on_done: Optional[Callable[["CobblerThread"], None]] = None,
    ):
        """
        Starts a new background task.

        :param thr_obj_fn: function handle to run in a background thread
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method. All
                      tasks require tokens.
        :param role_name: used to check token against authn/authz layers
        :param name: display name to show in logs/events
        :param args: usually this is a single dict, containing options
        :param on_done: an optional second function handle to run after success (and only success)
        :return: a task id.
        """
        self.check_access(token, role_name)
        new_event = self._new_event(name=name)

        self._log(f"create_task({name}); event_id({new_event.event_id})")

        thr_obj = CobblerThread(
            new_event.event_id, self, args, role_name, self.api, thr_obj_fn, on_done
        )
        thr_obj.start()
        return new_event.event_id

    def get_task_status(self, event_id: str) -> List[Union[str, float, List[str]]]:
        """
        Get the current status of the task.

        :param event_id: The unique id of the task.
        :return: The event status.
        """
        if not isinstance(event_id, str):  # type: ignore
            raise TypeError('"event_id" must be of type str!')
        if event_id not in self.events:
            raise CX("no event with that id")
        # The following works because __getitem__ is implemented.
        return list(self.events[event_id])  # type: ignore

    def last_modified_time(self, token: Optional[str] = None) -> float:
        """
        Return the time of the last modification to any object. Used to verify from a calling application that no
        Cobbler objects have changed since last check. This method is implemented in the module api under the same name.

        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: 0 if there is no file where the information required for this method is saved.
        """
        return self.api.last_modified_time()

    def ping(self) -> bool:
        """
        Deprecated method. Now does nothing.

        :return: Always True
        """
        return True

    def get_user_from_token(self, token: Optional[str]) -> str:
        """
        Given a token returned from login, return the username that logged in with it.

        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :return: The username if the token was valid.
        :raises CX: If the token supplied to the function is invalid.
        :raises ValueError: In case "token" did not fulfil the requirements to be a token.
        """
        if not CobblerXMLRPCInterface.__is_token(token):
            raise ValueError('"token" did not have the correct format or type!')
        if token not in self.token_cache:
            raise CX(f"invalid token: {token}")
        return self.token_cache[token][1]

    def _log(
        self,
        msg: str,
        token: Optional[str] = None,
        name: Optional[str] = None,
        object_id: Optional[str] = None,
        attribute: Optional[str] = None,
        debug: bool = False,
        error: bool = False,
    ):
        """
        Helper function to write data to the log file from the XMLRPC remote implementation.
        Takes various optional parameters that should be supplied when known.

        :param msg: The message to log.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param name: The name of the object should be supplied when it is known.
        :param object_id: The object id should be supplied when it is known.
        :param attribute: Additional attributes should be supplied if known.
        :param debug: If the message logged is a debug message.
        :param error: If the message logged is an error message.
        """
        if not all(
            (isinstance(error, bool), isinstance(debug, bool), isinstance(msg, str))  # type: ignore
        ):
            return
        # add the user editing the object, if supplied
        m_user = "?"
        if token is not None:
            try:
                m_user = self.get_user_from_token(token)
            except Exception:
                # invalid or expired token?
                m_user = "???"
        msg = f"REMOTE {msg}; user({m_user})"

        if name is not None:
            if not validate_obj_name(name):
                return
            msg = f"{msg}; name({name})"

        if object_id is not None:
            if not validate_uuid(object_id):
                return
            msg = f"{msg}; object_id({object_id})"

        # add any attributes being modified, if any
        if attribute:
            if (
                isinstance(attribute, str) and attribute.isidentifier()  # type: ignore
            ) or keyword.iskeyword(attribute):
                return
            msg = f"{msg}; attribute({attribute})"

        # log to the correct logger
        if error:
            self.logger.error(msg)
        elif debug:
            self.logger.debug(msg)
        else:
            self.logger.info(msg)

    def __sort(
        self, data: Iterable["ITEM"], sort_field: Optional[str] = None
    ) -> List["ITEM"]:
        """
        Helper function used by the various find/search functions to return object representations in order.

        :param data: The data to sort.
        :param sort_field: If the field contained in this starts with "!" then this sorts backwards.
        :return: The data sorted by the ``sort_field``.
        """
        sort_fields = ["name"]
        sort_rev = False
        if sort_field is not None:
            if sort_field.startswith("!"):
                sort_field = sort_field[1:]
                sort_rev = True
            sort_fields.insert(0, sort_field)
        sortdata = [(x.sort_key(sort_fields), x) for x in data]
        if sort_rev:
            sortdata.sort(reverse=True)
        else:
            sortdata.sort()
        return [x for (_, x) in sortdata]

    def __paginate(
        self,
        data: Sequence["ITEM"],
        page: int = 1,
        items_per_page: int = 25,
        token: Optional[str] = None,
    ) -> Tuple[Sequence["ITEM"], Dict[str, Union[List[int], int]]]:
        """
        Helper function to support returning parts of a selection, for example, for use in a web app where only a part
        of the results are to be presented on each screen.

        :param data: The data to paginate.
        :param page: The page to show.
        :param items_per_page: The number of items per page.
        :param token: The API-token obtained via the login() method.
        :return: The paginated items.
        """
        default_page = 1
        default_items_per_page = 25

        try:
            page = int(page)
            if page < 1:
                page = default_page
        except Exception:
            page = default_page
        try:
            items_per_page = int(items_per_page)
            if items_per_page <= 0:
                items_per_page = default_items_per_page
        except Exception:
            items_per_page = default_items_per_page

        num_items = len(data)
        num_pages = ((num_items - 1) // items_per_page) + 1
        if num_pages == 0:
            num_pages = 1
        if page > num_pages:
            page = num_pages
        start_item = items_per_page * (page - 1)
        end_item = start_item + items_per_page
        if start_item > num_items:
            start_item = num_items - 1
        if end_item > num_items:
            end_item = num_items
        data = data[start_item:end_item]

        if page > 1:
            prev_page = page - 1
        else:
            prev_page = -1
        if page < num_pages:
            next_page = page + 1
        else:
            next_page = -1

        return (
            data,
            {
                "page": page,
                "prev_page": prev_page,
                "next_page": next_page,
                "pages": list(range(1, num_pages + 1)),
                "num_pages": num_pages,
                "num_items": num_items,
                "start_item": start_item,
                "end_item": end_item,
                "items_per_page": items_per_page,
                "items_per_page_list": [10, 20, 50, 100, 200, 500],
            },
        )

    def __get_object(self, object_id: str) -> "ITEM_UNION":
        """
        Helper function. Given an object id, return the actual object.

        :param object_id: The id for the object to retrieve.
        :return: The item to the corresponding id.
        """
        if object_id in self.unsaved_items:
            return self.unsaved_items[object_id][1]
        obj = self.api.find_items("", criteria={"uid": object_id}, return_list=False)
        if obj is None or isinstance(obj, list):
            raise ValueError("Object not found or ambigous match!")
        return obj

    def get_item_resolved_value(
        self, item_uuid: str, attribute: str
    ) -> Union[str, int, float, List[Any], Dict[Any, Any]]:
        """
        .. seealso:: Logically identical to :func:`~cobbler.api.CobblerAPI.get_item_resolved_value`
        """
        self._log(f"get_item_resolved_value({item_uuid})", attribute=attribute)
        return_value: Optional[
            Union[str, int, float, enums.ConvertableEnum, List[Any], Dict[Any, Any]]
        ] = self.api.get_item_resolved_value(item_uuid, attribute)
        if return_value is None:
            self._log(
                f"get_item_resolved_value({item_uuid}): returned None",
                attribute=attribute,
            )
            raise ValueError(
                f'None is not a valid value for the resolved attribute "{attribute}". Please fix the item(s) '
                f'starting at uuid "{item_uuid}"'
            )
        if isinstance(return_value, enums.ConvertableEnum):
            return return_value.value
        if isinstance(
            return_value,
            (
                enums.DHCP,
                enums.NetworkInterfaceType,
                enums.BaudRates,
                base_item.BaseItem,
            ),
        ):
            return return_value.name
        if isinstance(return_value, dict):
            if (
                attribute == "interfaces"
                and len(return_value) > 0
                and all(
                    isinstance(value, NetworkInterface)
                    for value in return_value.values()
                )
            ):
                interface_return_value: Dict[Any, Any] = {}
                for interface_name in return_value:
                    interface_return_value[interface_name] = return_value[
                        interface_name
                    ].to_dict(resolved=True)
                return interface_return_value
            return self.xmlrpc_hacks(return_value)

        if not isinstance(
            return_value, (str, int, float, bool, tuple, bytes, bytearray, dict, list)
        ):
            self._log(
                f"get_item_resolved_value({item_uuid}): Cannot return XML-RPC compliant type. Please add a case to"
                f' convert type "{type(return_value)}" to an XML-RPC compliant type!'
            )
            raise ValueError(
                "Cannot return XML-RPC compliant type. See logs for more information!"
            )
        return return_value

    def set_item_resolved_value(
        self, item_uuid: str, attribute: str, value: Any, token: Optional[str] = None
    ):
        """
        .. seealso:: Logically identical to :func:`~cobbler.api.CobblerAPI.set_item_resolved_value`
        """
        self._log(f"get_item_resolved_value({item_uuid})", attribute=attribute)
        # Duplicated logic to check from api.py method, but we require this to check the access of the user.
        if not validate_uuid(item_uuid):
            raise ValueError("The given uuid did not have the correct format!")
        obj = self.api.find_items(
            "", {"uid": item_uuid}, return_list=False, no_errors=True
        )
        if obj is None or isinstance(obj, list):
            raise ValueError(f'Item with item_uuid "{item_uuid}" did not exist!')
        self.check_access(token, f"modify_{obj.COLLECTION_TYPE}", obj.name, attribute)
        return self.api.set_item_resolved_value(item_uuid, attribute, value)

    def get_item(
        self, what: str, name: str, flatten: bool = False, resolved: bool = False
    ):
        """
        Returns a dict describing a given object.

        :param what: "distro", "profile", "system", "image", "repo", etc
        :param name: the object name to retrieve
        :param flatten: reduce dicts to string representations (True/False)
        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                         objects raw value.
        :return: The item or None.
        """
        self._log(f"get_item({what},{name})")
        requested_item = self.api.get_item(what, name)
        if requested_item is not None:
            requested_item = requested_item.to_dict(resolved=resolved)
            if flatten:
                requested_item = utils.flatten(requested_item)
        return self.xmlrpc_hacks(requested_item)

    def get_distro(
        self,
        name: str,
        flatten: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ):
        """
        Get a distribution.

        :param name: The name of the distribution to get.
        :param flatten: If the item should be flattened.
        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                         objects raw value.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: Not used with this method currently.
        :return: The item or None.
        """
        return self.get_item("distro", name, flatten=flatten, resolved=resolved)

    def get_profile(
        self,
        name: str,
        flatten: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ):
        """
        Get a profile.

        :param name: The name of the profile to get.
        :param flatten: If the item should be flattened.
        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                         objects raw value.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: Not used with this method currently.
        :return: The item or None.
        """
        return self.get_item("profile", name, flatten=flatten, resolved=resolved)

    def get_system(
        self,
        name: str,
        flatten: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ):
        """
        Get a system.

        :param name: The name of the system to get.
        :param flatten: If the item should be flattened.
        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                         objects raw value.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: Not used with this method currently.
        :return: The item or None.
        """
        return self.get_item("system", name, flatten=flatten, resolved=resolved)

    def get_repo(
        self,
        name: str,
        flatten: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ):
        """
        Get a repository.

        :param name: The name of the repository to get.
        :param flatten: If the item should be flattened.
        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                         objects raw value.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: Not used with this method currently.
        :return: The item or None.
        """
        return self.get_item("repo", name, flatten=flatten, resolved=resolved)

    def get_image(
        self,
        name: str,
        flatten: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ):
        """
        Get an image.

        :param name: The name of the image to get.
        :param flatten: If the item should be flattened.
        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                         objects raw value.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: Not used with this method currently.
        :return: The item or None.
        """
        return self.get_item("image", name, flatten=flatten, resolved=resolved)

    def get_menu(
        self,
        name: str,
        flatten: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ):
        """
        Get a menu.

        :param name: The name of the file to get.
        :param flatten: If the item should be flattened.
        :param resolved: If this is True, Cobbler will resolve the values to its final form, rather than give you the
                         objects raw value.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: Not used with this method currently.
        :return: The item or None.
        """
        return self.get_item("menu", name, flatten=flatten, resolved=resolved)

    def get_items(self, what: str) -> List[Dict[str, Any]]:
        """
        Individual list elements are the same for get_item.

        :param what: is the name of a Cobbler object type, as described for get_item.
        :return: This returns a list of dicts.
        """
        items = [x.to_dict() for x in self.api.get_items(what)]
        return self.xmlrpc_hacks(items)  # type: ignore

    def get_item_names(self, what: str) -> List[str]:
        """
        This is just like get_items, but transmits less data.

        :param what: is the name of a Cobbler object type, as described for get_item.
        :return: Returns a list of object names (keys) for the given object type.
        """
        return [x.name for x in self.api.get_items(what)]

    def get_distros(
        self,
        page: Any = None,
        results_per_page: Any = None,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Dict[str, Any]]:
        """
        This returns all distributions.

        :param page: This parameter is not used currently.
        :param results_per_page: This parameter is not used currently.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: The list with all distros.
        """
        return self.get_items("distro")

    def get_profiles(
        self,
        page: Any = None,
        results_per_page: Any = None,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Dict[str, Any]]:
        """
        This returns all profiles.

        :param page: This parameter is not used currently.
        :param results_per_page: This parameter is not used currently.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: The list with all profiles.
        """
        return self.get_items("profile")

    def get_systems(
        self,
        page: Any = None,
        results_per_page: Any = None,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Dict[str, Any]]:
        """
        This returns all Systems.

        :param page: This parameter is not used currently.
        :param results_per_page: This parameter is not used currently.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: The list of all systems.
        """
        return self.get_items("system")

    def get_repos(
        self,
        page: Any = None,
        results_per_page: Any = None,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Dict[str, Any]]:
        """
        This returns all repositories.

        :param page: This parameter is not used currently.
        :param results_per_page: This parameter is not used currently.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: The list of all repositories.
        """
        return self.get_items("repo")

    def get_images(
        self,
        page: Any = None,
        results_per_page: Any = None,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Dict[str, Any]]:
        """
        This returns all images.

        :param page: This parameter is not used currently.
        :param results_per_page: This parameter is not used currently.
        :param token: The API-token obtained via the login() method. The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: The list of all images.
        """
        return self.get_items("image")

    def get_menus(
        self,
        page: Any = None,
        results_per_page: Any = None,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Dict[str, Any]]:
        """
        This returns all menus.

        :param page: This parameter is not used currently.
        :param results_per_page: This parameter is not used currently.
        :param token: The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: The list of all files.
        """
        return self.get_items("menu")

    def find_items(
        self,
        what: str,
        criteria: Optional[Dict[str, Any]] = None,
        sort_field: Optional[str] = None,
        expand: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Any]:
        """Works like get_items but also accepts criteria as a dict to search on.

        Example: ``{ "name" : "*.example.org" }``

        Wildcards work as described by 'pydoc fnmatch'.

        :param what: The object type to find.
        :param criteria: The criteria an item needs to match.
        :param sort_field: The field to sort the results after.
        :param expand: Not only get the names but also the complete object in form of a dict.
        :param resolved: This only has an effect when ``expand = True``. It returns the resolved representation of the
                         object instead of the raw data.
        :returns: A list of dicts.
        """
        if criteria is None:
            criteria = {}
        # self._log("find_items(%s); criteria(%s); sort(%s)" % (what, criteria, sort_field))
        if "name" in criteria:
            name = criteria.pop("name")
            items = self.api.find_items(what, criteria=criteria, name=name)
        else:
            items = self.api.find_items(what, criteria=criteria)
        if items is None:
            return []
        items = self.__sort(items, sort_field)  # type: ignore
        if not expand:
            items = [x.name for x in items]  # type: ignore
        else:
            items = [x.to_dict(resolved=resolved) for x in items]  # type: ignore
        return self.xmlrpc_hacks(items)  # type: ignore

    def find_distro(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        expand: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Any]:
        """
        Find a distro matching certain criteria.

        :param criteria: The criteria a distribution needs to match.
        :param expand: Not only get the names but also the complete object in form of a dict.
        :param resolved: This only has an effect when ``expand = True``. It returns the resolved representation of the
                         object instead of the raw data.
        :param token: The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: All distributions which have matched the criteria.
        """
        return self.find_items("distro", criteria, expand=expand, resolved=resolved)

    def find_profile(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        expand: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Any]:
        """
        Find a profile matching certain criteria.

        :param criteria: The criteria a distribution needs to match.
        :param expand: Not only get the names but also the complete object in form of a dict.
        :param resolved: This only has an effect when ``expand = True``. It returns the resolved representation of the
                         object instead of the raw data.
        :param token: The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: All profiles which have matched the criteria.
        """
        return self.find_items("profile", criteria, expand=expand, resolved=resolved)

    def find_system(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        expand: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Any]:
        """
        Find a system matching certain criteria.

        :param criteria: The criteria a distribution needs to match.
        :param expand: Not only get the names but also the complete object in form of a dict.
        :param resolved: This only has an effect when ``expand = True``. It returns the resolved representation of the
                         object instead of the raw data.
        :param token: The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: All systems which have matched the criteria.
        """
        return self.find_items("system", criteria, expand=expand, resolved=resolved)

    def find_repo(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        expand: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Any]:
        """
        Find a repository matching certain criteria.

        :param criteria: The criteria a distribution needs to match.
        :param expand: Not only get the names but also the complete object in form of a dict.
        :param resolved: This only has an effect when ``expand = True``. It returns the resolved representation of the
                         object instead of the raw data.
        :param token: The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: All repositories which have matched the criteria.
        """
        return self.find_items("repo", criteria, expand=expand, resolved=resolved)

    def find_image(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        expand: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Any]:
        """
        Find an image matching certain criteria.

        :param criteria: The criteria a distribution needs to match.
        :param expand: Not only get the names but also the complete object in form of a dict.
        :param resolved: This only has an effect when ``expand = True``. It returns the resolved representation of the
                         object instead of the raw data.
        :param token: The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: All images which have matched the criteria.
        """
        return self.find_items("image", criteria, expand=expand, resolved=resolved)

    def find_menu(
        self,
        criteria: Optional[Dict[str, Any]] = None,
        expand: bool = False,
        resolved: bool = False,
        token: Optional[str] = None,
        **rest: Any,
    ) -> List[Any]:
        """
        Find a menu matching certain criteria.

        :param criteria: The criteria a distribution needs to match.
        :param expand: Not only get the names but also the complete object in form of a dict.
        :param resolved: This only has an effect when ``expand = True``. It returns the resolved representation of the
                         object instead of the raw data.
        :param token: The API-token obtained via the login() method.
        :param rest: This parameter is not used currently.
        :return: All files which have matched the criteria.
        """
        return self.find_items("menu", criteria, expand=expand, resolved=resolved)

    def find_items_paged(
        self,
        what: str,
        criteria: Optional[Dict[str, Any]] = None,
        sort_field: Optional[str] = None,
        page: int = 1,
        items_per_page: int = 25,
        resolved: bool = False,
        token: Optional[str] = None,
    ):
        """
        Returns a list of dicts as with find_items but additionally supports returning just a portion of the total
        list, for instance in supporting a web app that wants to show a limited amount of items per page.

        :param what: The object type to find.
        :param criteria: The criteria a distribution needs to match.
        :param sort_field: The field to sort the results after.
        :param page: The page to return
        :param items_per_page: The number of items per page.
        :param resolved: This only has an effect when ``expand = True``. It returns the resolved representation of the
                         object instead of the raw data.
        :param token: The API-token obtained via the login() method.
        :return: The found items.
        """
        self._log(
            f"find_items_paged({what}); criteria({criteria}); sort({sort_field})",
            token=token,
        )
        if criteria is None:
            items = self.api.get_items(what)
        else:
            items = self.api.find_items(what, criteria=criteria)
        items = self.__sort(items, sort_field)  # type: ignore
        (items, pageinfo) = self.__paginate(items, page, items_per_page)  # type: ignore
        items = [x.to_dict(resolved=resolved) for x in items]  # type: ignore
        return self.xmlrpc_hacks({"items": items, "pageinfo": pageinfo})

    def has_item(self, what: str, name: str, token: Optional[str] = None):
        """
        Returns True if a given collection has an item with a given name, otherwise returns False.

        :param what: The collection to search through.
        :param name: The name of the item.
        :param token: The API-token obtained via the login() method.
        :return: True if item was found, otherwise False.
        """
        self._log(f"has_item({what})", token=token, name=name)
        found = self.api.get_item(what, name)
        if found is None:
            return False
        return True

    def get_item_handle(self, what: str, name: str) -> str:
        """
        Given the name of an object (or other search parameters), return a reference (object id) that can be used with
        ``modify_*`` functions or ``save_*`` functions to manipulate that object.

        :param what: The collection where the item is living in.
        :param name: The name of the item.
        :return: The handle of the desired object.
        """
        found = self.api.get_item(what, name)
        if found is None:
            raise CX(f"internal error, unknown {what} name {name}")
        return found.uid

    def get_distro_handle(self, name: str):
        """
        Get a handle for a distribution which allows you to use the functions ``modify_*`` or ``save_*`` to manipulate
        it.

        :param name: The name of the item.
        :return: The handle of the desired object.
        """
        return self.get_item_handle("distro", name)

    def get_profile_handle(self, name: str):
        """
        Get a handle for a profile which allows you to use the functions ``modify_*`` or ``save_*`` to manipulate it.

        :param name: The name of the item.
        :return: The handle of the desired object.
        """
        return self.get_item_handle("profile", name)

    def get_system_handle(self, name: str):
        """
        Get a handle for a system which allows you to use the functions ``modify_*`` or ``save_*`` to manipulate it.

        :param name: The name of the item.
        :return: The handle of the desired object.
        """
        return self.get_item_handle("system", name)

    def get_repo_handle(self, name: str):
        """
        Get a handle for a repository which allows you to use the functions ``modify_*`` or ``save_*`` to manipulate it.

        :param name: The name of the item.
        :return: The handle of the desired object.
        """
        return self.get_item_handle("repo", name)

    def get_image_handle(self, name: str):
        """
        Get a handle for an image which allows you to use the functions ``modify_*`` or ``save_*`` to manipulate it.

        :param name: The name of the item.
        :return: The handle of the desired object.
        """
        return self.get_item_handle("image", name)

    def get_menu_handle(self, name: str):
        """
        Get a handle for a menu which allows you to use the functions ``modify_*`` or ``save_*`` to manipulate it.

        :param name: The name of the item.
        :return: The handle of the desired object.
        """
        return self.get_item_handle("menu", name)

    def remove_item(
        self, what: str, name: str, token: str, recursive: bool = True
    ) -> bool:
        """
        Deletes an item from a collection.
        Note that this requires the name of the distro, not an item handle.

        :param what: The item type of the item to remove.
        :param name: The name of the item to remove.
        :param token: The API-token obtained via the login() method.
        :param recursive: If items which are depending on this one should be erased too.
        :return: True if the action was successful.
        """
        self._log(
            f"remove_item ({what}, recursive={recursive})", name=name, token=token
        )
        obj = self.api.get_item(what, name)
        if obj is None:
            return False
        self.check_access(token, f"remove_{what}", obj.name)
        self.api.remove_item(
            what, name, delete=True, with_triggers=True, recursive=recursive
        )
        return True

    def remove_distro(self, name: str, token: str, recursive: bool = True):
        """
        Deletes a distribution from Cobbler.

        :param name: The name of the item to remove.
        :param token: The API-token obtained via the login() method.
        :param recursive: If items which are depending on this one should be erased too.
        :return: True if the action was successful.
        """
        return self.remove_item("distro", name, token, recursive)

    def remove_profile(self, name: str, token: str, recursive: bool = True):
        """
        Deletes a profile from Cobbler.

        :param name: The name of the item to remove.
        :param token: The API-token obtained via the login() method.
        :param recursive: If items which are depending on this one should be erased too.
        :return: True if the action was successful.
        """
        return self.remove_item("profile", name, token, recursive)

    def remove_system(self, name: str, token: str, recursive: bool = True):
        """
        Deletes a system from Cobbler.

        :param name: The name of the item to remove.
        :param token: The API-token obtained via the login() method.
        :param recursive: If items which are depending on this one should be erased too.
        :return: True if the action was successful.
        """
        return self.remove_item("system", name, token, recursive)

    def remove_repo(self, name: str, token: str, recursive: bool = True):
        """
        Deletes a repository from Cobbler.

        :param name: The name of the item to remove.
        :param token: The API-token obtained via the login() method.
        :param recursive: If items which are depending on this one should be erased too.
        :return: True if the action was successful.
        """
        return self.remove_item("repo", name, token, recursive)

    def remove_image(self, name: str, token: str, recursive: bool = True):
        """
        Deletes an image from Cobbler.

        :param name: The name of the item to remove.
        :param token: The API-token obtained via the login() method.
        :param recursive: If items which are depending on this one should be erased too.
        :return: True if the action was successful.
        """
        return self.remove_item("image", name, token, recursive)

    def remove_menu(self, name: str, token: str, recursive: bool = True):
        """
        Deletes a menu from Cobbler.

        :param name: The name of the item to remove.
        :param token: The API-token obtained via the login() method.
        :param recursive: If items which are depending on this one should be erased too.
        :return: True if the action was successful.
        """
        return self.remove_item("menu", name, token, recursive)

    def copy_item(
        self, what: str, object_id: str, newname: str, token: Optional[str] = None
    ):
        """
        Creates a new object that matches an existing object, as specified by an id.

        :param what: The item type which should be copied.
        :param object_id: The object id of the item in question.
        :param newname: The new name for the copied object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        self._log(f"copy_item({what})", object_id=object_id, token=token)
        self.check_access(token, f"copy_{what}")
        obj = self.api.find_items(what, criteria={"uid": object_id}, return_list=False)
        if obj is None or isinstance(obj, list):
            raise ValueError(f'Item with id "{object_id}" not found.')
        self.api.copy_item(what, obj, newname)
        return True

    def copy_distro(self, object_id: str, newname: str, token: Optional[str] = None):
        """
        Copies a distribution and renames it afterwards.

        :param object_id: The object id of the item in question.
        :param newname: The new name for the copied object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.copy_item("distro", object_id, newname, token)

    def copy_profile(self, object_id: str, newname: str, token: Optional[str] = None):
        """
        Copies a profile and renames it afterwards.

        :param object_id: The object id of the item in question.
        :param newname: The new name for the copied object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.copy_item("profile", object_id, newname, token)

    def copy_system(self, object_id: str, newname: str, token: Optional[str] = None):
        """
        Copies a system and renames it afterwards.

        :param object_id: The object id of the item in question.
        :param newname: The new name for the copied object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.copy_item("system", object_id, newname, token)

    def copy_repo(self, object_id: str, newname: str, token: Optional[str] = None):
        """
        Copies a repository and renames it afterwards.

        :param object_id: The object id of the item in question.
        :param newname: The new name for the copied object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.copy_item("repo", object_id, newname, token)

    def copy_image(self, object_id: str, newname: str, token: Optional[str] = None):
        """
        Copies an image and renames it afterwards.

        :param object_id: The object id of the item in question.
        :param newname: The new name for the copied object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.copy_item("image", object_id, newname, token)

    def copy_menu(self, object_id: str, newname: str, token: Optional[str] = None):
        """
        Copies a menu and rename it afterwards.

        :param object_id: The object id of the item in question.
        :param newname: The new name for the copied object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.copy_item("menu", object_id, newname, token)

    def rename_item(
        self, what: str, object_id: str, newname: str, token: Optional[str] = None
    ) -> bool:
        """
        Renames an object specified by object_id to a new name.

        :param what: The type of object which shall be renamed to a new name.
        :param object_id: The id which refers to the object.
        :param newname: The new name for the object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        self._log(f"rename_item({what})", object_id=object_id, token=token)
        if token is None:
            raise ValueError('"token" must be provided to rename an item!')
        self.check_access(token, f"modify_{what}")
        obj = self.api.find_items(what, criteria={"uid": object_id}, return_list=False)
        if obj is None or isinstance(obj, list):
            raise ValueError(f'Item with id "{object_id}" not found!')
        self.api.rename_item(what, obj, newname)
        return True

    def rename_distro(
        self, object_id: str, newname: str, token: Optional[str] = None
    ) -> bool:
        """
        Renames a distribution specified by object_id to a new name.

        :param object_id: The id which refers to the object.
        :param newname: The new name for the object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.rename_item("distro", object_id, newname, token)

    def rename_profile(
        self, object_id: str, newname: str, token: Optional[str] = None
    ) -> bool:
        """
        Renames a profile specified by object_id to a new name.

        :param object_id: The id which refers to the object.
        :param newname: The new name for the object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.rename_item("profile", object_id, newname, token)

    def rename_system(
        self, object_id: str, newname: str, token: Optional[str] = None
    ) -> bool:
        """
        Renames a system specified by object_id to a new name.

        :param object_id: The id which refers to the object.
        :param newname: The new name for the object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.rename_item("system", object_id, newname, token)

    def rename_repo(
        self, object_id: str, newname: str, token: Optional[str] = None
    ) -> bool:
        """
        Renames a repository specified by object_id to a new name.

        :param object_id: The id which refers to the object.
        :param newname: The new name for the object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.rename_item("repo", object_id, newname, token)

    def rename_image(
        self, object_id: str, newname: str, token: Optional[str] = None
    ) -> bool:
        """
        Renames an image specified by object_id to a new name.

        :param object_id: The id which refers to the object.
        :param newname: The new name for the object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.rename_item("image", object_id, newname, token)

    def rename_menu(
        self, object_id: str, newname: str, token: Optional[str] = None
    ) -> bool:
        """
        Renames a menu specified by object_id to a new name.

        :param object_id: The id which refers to the object.
        :param newname: The new name for the object.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        return self.rename_item("menu", object_id, newname, token)

    def new_item(
        self, what: str, token: str, is_subobject: bool = False, **kwargs: Any
    ) -> str:
        """Creates a new (unconfigured) object, returning an object handle that can be used.

        Creates a new (unconfigured) object, returning an object handle that can be used with ``modify_*`` methods and
        then finally ``save_*`` methods. The handle only exists in memory until saved.

        :param what: specifies the type of object: ``distro``, ``profile``, ``system``, ``repo``, ``image`` or ``menu``.
        :param token: The API-token obtained via the login() method.
        :param is_subobject: If the object is a subobject of an already existing object or not.
        :return: The object id for the newly created object.
        """
        self._log(f"new_item({what})", token=token)
        self.check_access(token, f"new_{what}")
        new_item = self.api.new_item(what, is_subobject, **kwargs)
        self.unsaved_items[new_item.uid] = (time.time(), new_item)
        return new_item.uid

    def new_distro(self, token: str):
        """
        See ``new_item()``.

        :param token: The API-token obtained via the login() method.
        :return: The object id for the newly created object.
        """
        return self.new_item("distro", token)

    def new_profile(self, token: str):
        """
        See ``new_item()``.

        :param token: The API-token obtained via the login() method.
        :return: The object id for the newly created object.
        """
        return self.new_item("profile", token)

    def new_subprofile(self, token: str):
        """
        See ``new_item()``.

        :param token: The API-token obtained via the login() method.
        :return: The object id for the newly created object.
        """
        return self.new_item("profile", token, is_subobject=True)

    def new_system(self, token: str):
        """
        See ``new_item()``.

        :param token: The API-token obtained via the login() method.
        :return: The object id for the newly created object.
        """
        return self.new_item("system", token)

    def new_repo(self, token: str):
        """
        See ``new_item()``.

        :param token: The API-token obtained via the login() method.
        :return: The object id for the newly created object.
        """
        return self.new_item("repo", token)

    def new_image(self, token: str):
        """
        See ``new_item()``.

        :param token: The API-token obtained via the login() method.
        :return: The object id for the newly created object.
        """
        return self.new_item("image", token)

    def new_menu(self, token: str):
        """
        See ``new_item()``.

        :param token: The API-token obtained via the login() method.
        :return: The object id for the newly created object.
        """
        return self.new_item("menu", token)

    def modify_item(
        self,
        what: str,
        object_id: str,
        attribute: str,
        arg: Union[str, int, float, List[str], Dict[str, Any]],
        token: str,
    ) -> bool:
        """
        Adjusts the value of a given field, specified by 'what' on a given object id. Allows modification of certain
        attributes on newly created or existing distro object handle.

        :param what: The type of object to modify.1
        :param object_id: The id of the object which shall be modified.
        :param attribute: The attribute name which shall be edited.
        :param arg: The new value for the argument.
        :param token: The API-token obtained via the login() method.
        :return: True if the action was successful. Otherwise False.
        """
        self._log(
            f"modify_item({what})",
            object_id=object_id,
            attribute=attribute,
            token=token,
        )
        obj = self.__get_object(object_id)
        self.check_access(token, f"modify_{what}", obj.name, attribute)

        if what == "system":
            if attribute == "modify_interface":
                obj.modify_interface(arg)  # type: ignore
                return True
            if attribute == "delete_interface":
                obj.delete_interface(arg)  # type: ignore
                return True
            if attribute == "rename_interface":
                obj.rename_interface(  # type: ignore
                    old_name=arg.get("interface", ""),  # type: ignore
                    new_name=arg.get("rename_interface", ""),  # type: ignore
                )
                return True

        if hasattr(obj, attribute):
            setattr(obj, attribute, arg)
            return True
        return False

    def modify_distro(self, object_id: str, attribute: str, arg: Any, token: str):
        """
        Modify a single attribute of a distribution.

        :param object_id: The id of the object which shall be modified.
        :param attribute: The attribute name which shall be edited.
        :param arg: The new value for the argument.
        :param token: The API-token obtained via the login() method.
        :return: True if the action was successful. Otherwise False.
        """
        return self.modify_item("distro", object_id, attribute, arg, token)

    def modify_profile(self, object_id: str, attribute: str, arg: Any, token: str):
        """
        Modify a single attribute of a profile.

        :param object_id: The id of the object which shall be modified.
        :param attribute: The attribute name which shall be edited.
        :param arg: The new value for the argument.
        :param token: The API-token obtained via the login() method.
        :return: True if the action was successful. Otherwise False.
        """
        return self.modify_item("profile", object_id, attribute, arg, token)

    def modify_system(self, object_id: str, attribute: str, arg: Any, token: str):
        """
        Modify a single attribute of a system.

        :param object_id: The id of the object which shall be modified.
        :param attribute: The attribute name which shall be edited.
        :param arg: The new value for the argument.
        :param token: The API-token obtained via the login() method.
        :return: True if the action was successful. Otherwise False.
        """
        return self.modify_item("system", object_id, attribute, arg, token)

    def modify_image(self, object_id: str, attribute: str, arg: Any, token: str):
        """
        Modify a single attribute of an image.

        :param object_id: The id of the object which shall be modified.
        :param attribute: The attribute name which shall be edited.
        :param arg: The new value for the argument.
        :param token: The API-token obtained via the login() method.
        :return: True if the action was successful. Otherwise False.
        """
        return self.modify_item("image", object_id, attribute, arg, token)

    def modify_repo(self, object_id: str, attribute: str, arg: Any, token: str):
        """
        Modify a single attribute of a repository.

        :param object_id: The id of the object which shall be modified.
        :param attribute: The attribute name which shall be edited.
        :param arg: The new value for the argument.
        :param token: The API-token obtained via the login() method.
        :return: True if the action was successful. Otherwise False.
        """
        return self.modify_item("repo", object_id, attribute, arg, token)

    def modify_menu(self, object_id: str, attribute: str, arg: Any, token: str):
        """
        Modify a single attribute of a menu.

        :param object_id: The id of the object which shall be modified.
        :param attribute: The attribute name which shall be edited.
        :param arg: The new value for the argument.
        :param token: The API-token obtained via the login() method.
        :return: True if the action was successful. Otherwise False.
        """
        return self.modify_item("menu", object_id, attribute, arg, token)

    def modify_setting(
        self,
        setting_name: str,
        value: Union[str, bool, float, int, Dict[Any, Any], List[Any]],
        token: str,
    ) -> int:
        """
        Modify a single attribute of a setting.

        :param setting_name: The name of the setting which shall be adjusted.
        :param value: The new value for the setting.
        :param token: The API-token obtained via the login() method.
        :return: 0 on success, 1 on error.
        """
        if not self.api.settings().allow_dynamic_settings:
            self._log(
                "modify_setting - feature turned off but was tried to be accessed",
                token=token,
            )
            return 1
        self._log(f"modify_setting({setting_name})", token=token)
        if not hasattr(self.api.settings(), setting_name):
            self.logger.warning("Setting did not exist!")
            return 1
        self.check_access(token, "modify_setting")
        self._log(f"modify_setting({setting_name})", token=token)
        try:
            if isinstance(getattr(self.api.settings(), setting_name), str):
                value = str(value)
            elif isinstance(getattr(self.api.settings(), setting_name), bool):
                value = self.api.input_boolean(value)  # type: ignore
            elif isinstance(getattr(self.api.settings(), setting_name), int):
                value = int(value)  # type: ignore
            elif isinstance(getattr(self.api.settings(), setting_name), float):
                value = float(value)  # type: ignore
            elif isinstance(getattr(self.api.settings(), setting_name), list):
                value = self.api.input_string_or_list_no_inherit(value)  # type: ignore
            elif isinstance(getattr(self.api.settings(), setting_name), dict):
                value = self.api.input_string_or_dict_no_inherit(value)  # type: ignore
            else:
                self.logger.error(
                    "modify_setting(%s) - Wrong type for value", setting_name
                )
                return 1
        except TypeError:
            return 1
        except ValueError:
            return 1

        setattr(self.api.settings(), setting_name, value)
        self.api.clean_items_cache(self.api.settings())
        self.api.settings().save()
        return 0

    def auto_add_repos(self, token: str):
        """
        :param token: The API-token obtained via the login() method.
        """
        self.check_access(token, "new_repo", token)
        self.api.auto_add_repos()
        return True

    def __is_interface_field(self, field_name: str) -> bool:
        """
        Checks if the field in ``f`` is related to a network interface.

        :param field_name: The fieldname to check.
        :return: True if the fields is related to a network interface, otherwise False.
        """
        if field_name in ("interface", "delete_interface", "rename_interface"):
            return True

        fields: List[str] = []
        for key, value in NetworkInterface.__dict__.items():
            if isinstance(value, property):
                fields.append(key)

        return field_name in fields

    def xapi_object_edit(
        self,
        object_type: str,
        object_name: str,
        edit_type: str,
        attributes: Dict[str, Union[str, int, float, List[str]]],
        token: str,
    ):
        """Extended API: New style object manipulations, 2.0 and later.

        Extended API: New style object manipulations, 2.0 and later preferred over using ``new_*``, ``modify_*```,
        ``save_*`` directly. Though we must preserve the old ways for backwards compatibility these cause much less
        XMLRPC traffic.

        Ex: xapi_object_edit("distro","el5","add",{"kernel":"/tmp/foo","initrd":"/tmp/foo"},token)

        :param object_type: The object type which corresponds to the collection type the object is in.
        :param object_name: The name of the object under question.
        :param edit_type: One of 'add', 'rename', 'copy', 'remove'
        :param attributes: The attributes which shall be edited. This should be JSON-style string.
        :param token: The API-token obtained via the login() method.
        :return: True if the action succeeded.
        """
        self.check_access(token, f"xedit_{object_type}", token)

        if object_name.strip() == "":
            raise ValueError("xapi_object_edit() called without an object name")

        handle = ""
        if edit_type in ("add", "rename"):
            if edit_type == "rename":
                # This is built by the CLI and thus we can be sure that this is the case!
                tmp_name: str = attributes["newname"]  # type: ignore
            else:
                tmp_name = object_name
            try:
                handle = self.get_item_handle(object_type, tmp_name)
            except CX:
                pass
            if handle:
                raise CX(
                    "It seems unwise to overwrite the object %s, try 'edit'", tmp_name
                )

        if edit_type == "add":
            is_subobject = object_type == "profile" and "parent" in attributes
            if is_subobject and "distro" in attributes:
                raise ValueError("You can't change both 'parent' and 'distro'")
            if object_type == "system":
                if "profile" not in attributes and "image" not in attributes:
                    raise ValueError(
                        "You must specify a 'profile' or 'image' for new systems"
                    )
            handle = self.new_item(object_type, token, is_subobject=is_subobject)
        else:
            handle = self.get_item_handle(object_type, object_name)

        if edit_type == "rename":
            self.rename_item(object_type, handle, attributes["newname"], token)  # type: ignore
            # After we did the rename we don't want to do anything anymore. Saving the item is done during renaming.
            return True

        if edit_type == "copy":
            is_subobject = object_type == "profile" and "parent" in attributes
            if is_subobject:
                if "distro" in attributes:
                    raise ValueError("You can't change both 'parent' and 'distro'")
                self.copy_item(object_type, handle, attributes["newname"], token)  # type: ignore
                handle = self.get_item_handle("profile", attributes["newname"])  # type: ignore
                self.modify_item(
                    "profile", handle, "parent", attributes["parent"], token
                )
            else:
                self.copy_item(object_type, handle, attributes["newname"], token)  # type: ignore
                handle = self.get_item_handle(object_type, attributes["newname"])  # type: ignore

        if edit_type in ["copy"]:
            del attributes["name"]
            del attributes["newname"]

        if edit_type != "remove":
            # FIXME: this doesn't know about interfaces yet!
            # if object type is system and fields add to dict and then modify when done, rather than now.
            priority_attributes = ["name", "parent", "distro", "profile", "image"]
            for attr_name in priority_attributes:
                if attr_name in attributes:
                    self.modify_item(
                        object_type, handle, attr_name, attributes.pop(attr_name), token
                    )
            have_interface_keys = False
            for (key, value) in attributes.items():
                if self.__is_interface_field(key):
                    have_interface_keys = True
                if object_type != "system" or not self.__is_interface_field(key):
                    # in place modifications allow for adding a key/value pair while keeping other k/v pairs intact.
                    if key in [
                        "autoinstall_meta",
                        "kernel_options",
                        "kernel_options_post",
                        "template_files",
                        "boot_files",
                        "params",
                    ] and attributes.get("in_place"):
                        details = self.get_item(object_type, object_name)
                        new_value = details[key]  # type: ignore
                        parsed_input = self.api.input_string_or_dict(value)  # type: ignore
                        if isinstance(parsed_input, dict):
                            for (input_key, input_value) in parsed_input.items():
                                if input_key.startswith("~") and len(input_key) > 1:
                                    del new_value[input_key[1:]]  # type: ignore
                                else:
                                    new_value[input_key] = input_value  # type: ignore
                        else:
                            # If this is a str it MUST be the inherited case at this point.
                            new_value = enums.VALUE_INHERITED
                        value = new_value  # type: ignore

                    self.modify_item(object_type, handle, key, value, token)  # type: ignore

            if object_type == "system" and have_interface_keys:
                self.__interface_edits(handle, attributes, object_name)
        else:
            # remove item
            recursive = attributes.get("recursive", False)
            if object_type in ["profile", "menu"] and recursive is False:
                childs = len(
                    self.api.find_items(  # type: ignore
                        object_type, criteria={"parent": attributes["name"]}
                    )
                )
                if childs > 0:
                    raise CX(
                        f"Can't delete this {object_type} there are {childs} sub{object_type}s and 'recursive' is"
                        " set to 'False'"
                    )

            self.remove_item(object_type, object_name, token, recursive=recursive)  # type: ignore
            return True

        # FIXME: use the bypass flag or not?
        self.save_item(object_type, handle, token)
        return True

    def __interface_edits(
        self, handle: str, attributes: Dict[str, Any], object_name: str
    ):
        """
        Handles all edits in relation to network interfaces.

        :param handle: XML-RPC handle for the system that is being edited.
        :param attributes: The attributes that are being passed by the CLI to the server.
        :param object_name: The system name.
        """
        # This if is taking care of interface logic. The interfaces are a dict, thus when we get the obj via
        # the api we get references to the original interfaces dict. Thus this trick saves us the pain of
        # writing the modified obj back to the collection. Always remember that dicts are mutable.
        system_to_edit: "system.System" = self.__get_object(handle)  # type: ignore
        if system_to_edit is None:  # type: ignore
            raise ValueError(
                f'No system found with the specified name (name given: "{object_name}")!'
            )

        if "delete_interface" in attributes:
            if attributes.get("interface") is None:
                raise ValueError("Interface is required for deletion.")
            system_to_edit.delete_interface(attributes.get("interface", ""))
            return

        if "rename_interface" in attributes:
            system_to_edit.rename_interface(
                attributes.get("interface", ""), attributes.get("rename_interface", "")
            )
            return

        # If we don't have an explicit interface name use the default interface or require an explicit
        # interface if default cannot be found.
        if len(system_to_edit.interfaces) > 1 and attributes.get("interface") is None:
            if "default" not in system_to_edit.interfaces.keys():
                raise ValueError("Interface is required.")
            interface_name = "default"
        if len(system_to_edit.interfaces) == 1:
            interface_name = attributes.get(
                "interface", next(iter(system_to_edit.interfaces))
            )
        else:
            interface_name = attributes.get("interface", "default")
        attributes.pop("interface", None)
        self.logger.debug('Interface "%s" is being edited.', interface_name)
        interface = system_to_edit.interfaces.get(interface_name)
        if interface is None:
            # If the interface is not existing, create a new one.
            interface = NetworkInterface(self.api)
        for attribute_key in attributes:
            if self.__is_interface_field(attribute_key):
                if hasattr(interface, attribute_key):
                    setattr(interface, attribute_key, attributes[attribute_key])
                else:
                    self.logger.warning(
                        'Network interface field "%s" could not be set. Skipping it.',
                        attribute_key,
                    )
            else:
                self.logger.debug("Field %s was not an interface field.", attribute_key)
        system_to_edit.interfaces.update({interface_name: interface})

    def save_item(
        self, what: str, object_id: str, token: str, editmode: str = "bypass"
    ):
        """
        Saves a newly created or modified object to disk. Calling save is required for any changes to persist.

        :param what: The type of object which shall be saved. This corresponds to the collections.
        :param object_id: The id of the object to save.
        :param token: The API-token obtained via the login() method.
        :param editmode: The mode which shall be used to persist the changes. Currently "new" and "bypass" are
                         supported.
        :return: True if the action succeeded.
        """
        self._log(f"save_item({what})", object_id=object_id, token=token)
        obj = self.__get_object(object_id)
        self.check_access(token, f"save_{what}", obj.name)
        if editmode == "new":
            self.api.add_item(what, obj, check_for_duplicate_names=True)
        else:
            self.api.add_item(what, obj)
        if object_id in self.unsaved_items:
            del self.unsaved_items[object_id]
        return True

    def save_distro(self, object_id: str, token: str, editmode: str = "bypass"):
        """
        Saves a newly created or modified object to disk. Calling save is required for any changes to persist.

        :param object_id: The id of the object to save.
        :param token: The API-token obtained via the login() method.
        :param editmode: The mode which shall be used to persist the changes. Currently "new" and "bypass" are
                         supported.
        :return: True if the action succeeded.
        """
        return self.save_item("distro", object_id, token, editmode=editmode)

    def save_profile(self, object_id: str, token: str, editmode: str = "bypass"):
        """
        Saves a newly created or modified object to disk. Calling save is required for any changes to persist.

        :param object_id: The id of the object to save.
        :param token: The API-token obtained via the login() method.
        :param editmode: The mode which shall be used to persist the changes. Currently "new" and "bypass" are
                         supported.
        :return: True if the action succeeded.
        """
        return self.save_item("profile", object_id, token, editmode=editmode)

    def save_system(self, object_id: str, token: str, editmode: str = "bypass"):
        """
        Saves a newly created or modified object to disk. Calling save is required for any changes to persist.

        :param object_id: The id of the object to save.
        :param token: The API-token obtained via the login() method.
        :param editmode: The mode which shall be used to persist the changes. Currently "new" and "bypass" are
                         supported.
        :return: True if the action succeeded.
        """
        return self.save_item("system", object_id, token, editmode=editmode)

    def save_image(self, object_id: str, token: str, editmode: str = "bypass"):
        """
        Saves a newly created or modified object to disk. Calling save is required for any changes to persist.

        :param object_id: The id of the object to save.
        :param token: The API-token obtained via the login() method.
        :param editmode: The mode which shall be used to persist the changes. Currently "new" and "bypass" are
                         supported.
        :return: True if the action succeeded.
        """
        return self.save_item("image", object_id, token, editmode=editmode)

    def save_repo(self, object_id: str, token: str, editmode: str = "bypass"):
        """
        Saves a newly created or modified object to disk. Calling save is required for any changes to persist.

        :param object_id: The id of the object to save.
        :param token: The API-token obtained via the login() method.
        :param editmode: The mode which shall be used to persist the changes. Currently "new" and "bypass" are
                         supported.
        :return: True if the action succeeded.
        """
        return self.save_item("repo", object_id, token, editmode=editmode)

    def save_menu(self, object_id: str, token: str, editmode: str = "bypass"):
        """
        Saves a newly created or modified object to disk. Calling save is required for any changes to persist.

        :param object_id: The id of the object to save.
        :param token: The API-token obtained via the login() method.
        :param editmode: The mode which shall be used to persist the changes. Currently "new" and "bypass" are
                         supported.
        :return: True if the action succeeded.
        """
        return self.save_item("menu", object_id, token, editmode=editmode)

    def get_autoinstall_templates(self, token: Optional[str] = None, **rest: Any):
        """
        Returns all of the automatic OS installation templates that are in use by the system.

        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: A list with all templates.
        """
        self._log("get_autoinstall_templates", token=token)
        # self.check_access(token, "get_autoinstall_templates")
        return self.autoinstall_mgr.get_autoinstall_templates()

    def get_autoinstall_snippets(self, token: Optional[str] = None, **rest: Any):
        """
        Returns all the automatic OS installation templates' snippets.

        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: A list with all snippets.
        """

        self._log("get_autoinstall_snippets", token=token)
        return self.autoinstall_mgr.get_autoinstall_snippets()

    def is_autoinstall_in_use(self, ai: str, token: Optional[str] = None, **rest: Any):
        """
        Check if the autoinstall for a system is in use.

        :param ai: The name of the system which could potentially be in autoinstall mode.
        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: True if this is the case, otherwise False.
        """
        self._log("is_autoinstall_in_use", token=token)
        return self.autoinstall_mgr.is_autoinstall_in_use(ai)

    def generate_autoinstall(
        self,
        profile: Optional[str] = None,
        system: Optional[str] = None,
        REMOTE_ADDR: Optional[Any] = None,
        REMOTE_MAC: Optional[Any] = None,
        **rest: Any,
    ) -> str:
        """
        Generate the autoinstallation file and return it.

        :param profile: The profile to generate the file for.
        :param system: The system to generate the file for.
        :param REMOTE_ADDR: This is dropped in this method since it is not needed here.
        :param REMOTE_MAC: This is dropped in this method since it is not needed here.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The str representation of the file.
        """
        # ToDo: Remove unneed params: REMOTE_ADDR, REMOTE_MAC, rest
        self._log("generate_autoinstall")
        try:
            return self.autoinstall_mgr.generate_autoinstall(profile, system)
        except Exception:
            utils.log_exc()
            return (
                "# This automatic OS installation file had errors that prevented it from being rendered "
                "correctly.\n# The cobbler.log should have information relating to this failure."
            )

    def generate_profile_autoinstall(self, profile: str):
        """
        Generate a profile autoinstallation.

        :param profile: The profile to generate the file for.
        :return: The str representation of the file.
        """
        return self.generate_autoinstall(profile=profile)

    def generate_system_autoinstall(self, system: str):
        """
        Generate a system autoinstallation.

        :param system: The system to generate the file for.
        :return: The str representation of the file.
        """
        return self.generate_autoinstall(system=system)

    def generate_ipxe(
        self,
        profile: Optional[str] = None,
        image: Optional[str] = None,
        system: Optional[str] = None,
        **rest: Any,
    ) -> str:
        """
        Generate the ipxe configuration.

        :param profile: The profile to generate iPXE config for.
        :param image: The image to generate iPXE config for.
        :param system: The system to generate iPXE config for.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The configuration as a str representation.
        """
        self._log("generate_ipxe")
        return self.api.generate_ipxe(profile, image, system)  # type: ignore

    def generate_bootcfg(
        self, profile: Optional[str] = None, system: Optional[str] = None, **rest: Any
    ) -> str:
        """
        This generates the bootcfg for a system which is related to a certain profile.

        :param profile: The profile which is associated to the system.
        :param system: The system which the bootcfg should be generated for.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The generated bootcfg.
        """
        self._log("generate_bootcfg")
        profile_name = "" if profile is None else profile
        system_name = "" if system is None else system
        return self.api.generate_bootcfg(profile_name, system_name)

    def generate_script(
        self,
        profile: Optional[str] = None,
        system: Optional[str] = None,
        name: str = "",
    ) -> str:
        """
        This generates the autoinstall script for a system or profile. Profile and System cannot be both given, if they
        are, Profile wins.

        :param profile: The profile name to generate the script for.
        :param system: The system name to generate the script for.
        :param name: Name of the generated script. Must only contain alphanumeric characters, dots and underscores.
        :return: Some generated script.
        """
        # This is duplicated from tftpgen.py to prevent log poisoning via a template engine (Cheetah, Jinja2).
        if not validate_autoinstall_script_name(name):
            raise ValueError('"name" handed to generate_script was not valid!')
        self._log(f'generate_script, name is "{name}"')
        return self.api.generate_script(profile, system, name)

    def dump_vars(
        self, item_uuid: str, formatted_output: bool = False, remove_dicts: bool = True
    ):
        """
        This function dumps all variables related to an object. The difference to the above mentioned function is that
        it accepts the item uid instead of the Python object itself.

        .. seealso:: Logically identical to :func:`~cobbler.api.CobblerAPI.dump_vars`
        """
        obj = self.api.find_items(
            "", {"uid": item_uuid}, return_list=False, no_errors=True
        )
        if obj is None or isinstance(obj, list):
            raise ValueError(f'Item with uuid "{item_uuid}" does not exist!')
        self.api.dump_vars(obj, formatted_output, remove_dicts)

    def get_blended_data(
        self, profile: Optional[str] = None, system: Optional[str] = None
    ):
        """
        Combine all data which is available from a profile and system together and return it.

        .. deprecated:: 3.4.0
           Please make use of the dump_vars endpoint.

        :param profile: The profile of the system.
        :param system: The system for which the data should be rendered.
        :return: All values which could be blended together through the inheritance chain.
        """
        if profile is not None and profile != "":
            obj = self.api.find_profile(profile)
            if obj is None or isinstance(obj, list):
                raise CX(f"profile not found: {profile}")
        elif system is not None and system != "":
            obj = self.api.find_system(system)
            if obj is None or isinstance(obj, list):
                raise CX(f"system not found: {system}")
        else:
            raise CX("internal error, no system or profile specified")
        data = utils.blender(self.api, True, obj)
        return self.xmlrpc_hacks(data)

    def get_settings(self, token: Optional[str] = None, **rest: Any) -> Dict[str, Any]:
        """
        Return the contents of our settings file, which is a dict.

        :param token: The API-token obtained via the login() method.
        :param rest: Unused parameter.
        :return: Get the settings which are currently in Cobbler present.
        """
        # self._log("get_settings", token=token)
        results = self.api.settings().to_dict()
        # self._log("my settings are: %s" % results, debug=True)
        return self.xmlrpc_hacks(results)  # type: ignore

    def get_signatures(
        self, token: Optional[str] = None, **rest: Any
    ) -> Dict[Any, Any]:
        """
        Return the contents of the API signatures

        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: Get the content of the currently loaded signatures file.
        """
        self._log("get_signatures", token=token)
        results = self.api.get_signatures()
        return self.xmlrpc_hacks(results)  # type: ignore

    def get_valid_breeds(self, token: Optional[str] = None, **rest: Any) -> List[str]:
        """
        Return the list of valid breeds as read in from the distro signatures data

        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: All valid OS-Breeds which are present in Cobbler.
        """
        self._log("get_valid_breeds", token=token)
        results = signatures.get_valid_breeds()
        results.sort()
        return self.xmlrpc_hacks(results)  # type: ignore

    def get_valid_os_versions_for_breed(
        self, breed: str, token: Optional[str] = None, **rest: Any
    ) -> List[str]:
        """
        Return the list of valid os_versions for the given breed

        :param breed: The OS-Breed which is requested.
        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: All valid OS-versions for a certain breed.
        """
        self._log("get_valid_os_versions_for_breed", token=token)
        results = signatures.get_valid_os_versions_for_breed(breed)
        results.sort()
        return self.xmlrpc_hacks(results)  # type: ignore

    def get_valid_os_versions(
        self, token: Optional[str] = None, **rest: Any
    ) -> List[str]:
        """
        Return the list of valid os_versions as read in from the distro signatures data

        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: Get all valid OS-Versions
        """
        self._log("get_valid_os_versions", token=token)
        results = signatures.get_valid_os_versions()
        results.sort()
        return self.xmlrpc_hacks(results)  # type: ignore

    def get_valid_archs(self, token: Optional[str] = None) -> List[str]:
        """
        Return the list of valid architectures as read in from the distro signatures data

        :param token: The API-token obtained via the login() method.
        :return: Get a list of all valid architectures.
        """
        self._log("get_valid_archs", token=token)
        results = signatures.get_valid_archs()
        results.sort()
        return self.xmlrpc_hacks(results)  # type: ignore

    def get_valid_distro_boot_loaders(
        self, distro_name: Optional[str], token: Optional[str] = None
    ):
        """
        Return the list of valid boot loaders for the distro

        :param token: The API-token obtained via the login() method.
        :param distro_name: The name of the distro for which the boot loaders should be looked up.
        :return: Get a list of all valid boot loaders.
        """
        self._log("get_valid_distro_boot_loaders", token=token)
        if distro_name is None:
            return utils.get_supported_system_boot_loaders()
        obj = self.api.find_distro(distro_name)
        if obj is None or isinstance(obj, list):
            return f"# object not found: {distro_name}"
        return self.api.get_valid_obj_boot_loaders(obj)

    def get_valid_image_boot_loaders(
        self, image_name: Optional[str], token: Optional[str] = None
    ):
        """
        Return the list of valid boot loaders for the image

        :param token: The API-token obtained via the login() method.
        :param image_name: The name of the image for which the boot loaders should be looked up.
        :return: Get a list of all valid boot loaders.
        """
        self._log("get_valid_image_boot_loaders", token=token)
        if image_name is None:
            return utils.get_supported_system_boot_loaders()
        obj = self.api.find_image(image_name)
        if obj is None:
            return f"# object not found: {image_name}"
        return self.api.get_valid_obj_boot_loaders(obj)  # type: ignore

    def get_valid_profile_boot_loaders(
        self, profile_name: Optional[str], token: Optional[str] = None
    ):
        """
        Return the list of valid boot loaders for the profile

        :param token: The API-token obtained via the login() method.
        :param profile_name: The name of the profile for which the boot loaders should be looked up.
        :return: Get a list of all valid boot loaders.
        """
        self._log("get_valid_profile_boot_loaders", token=token)
        if profile_name is None:
            return utils.get_supported_system_boot_loaders()
        obj = self.api.find_profile(profile_name)
        if obj is None or isinstance(obj, list):
            return f"# object not found: {profile_name}"
        distro = obj.get_conceptual_parent()
        return self.api.get_valid_obj_boot_loaders(distro)  # type: ignore

    def get_valid_system_boot_loaders(
        self, system_name: Optional[str], token: Optional[str] = None
    ) -> List[str]:
        """
        Return the list of valid boot loaders for the system

        :param token: The API-token obtained via the login() method.
        :param system_name: The name of the system for which the boot loaders should be looked up.
        :return: Get a list of all valid boot loaders.get_valid_archs
        """
        self._log("get_valid_system_boot_loaders", token=token)
        if system_name is None:
            return utils.get_supported_system_boot_loaders()
        obj = self.api.find_system(system_name)
        if obj is None or isinstance(obj, list):
            return [f"# object not found: {system_name}"]
        parent = obj.get_conceptual_parent()

        if parent and parent.COLLECTION_TYPE == "profile":
            return parent.boot_loaders  # type: ignore
        return self.api.get_valid_obj_boot_loaders(parent)  # type: ignore

    def get_repo_config_for_profile(self, profile_name: str, **rest: Any):
        """
        Return the yum configuration a given profile should use to obtain all of it's Cobbler associated repos.

        :param profile_name: The name of the profile for which the repository config should be looked up.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The repository configuration for the profile.
        """
        obj = self.api.find_profile(profile_name)
        if obj is None or isinstance(obj, list):
            return f"# object not found: {profile_name}"
        return self.api.get_repo_config_for_profile(obj)

    def get_repo_config_for_system(self, system_name: str, **rest: Any):
        """
        Return the yum configuration a given profile should use to obtain all of it's Cobbler associated repos.

        :param system_name: The name of the system for which the repository config should be looked up.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The repository configuration for the system.
        """
        obj = self.api.find_system(system_name)
        if obj is None or isinstance(obj, list):
            return f"# object not found: {system_name}"
        return self.api.get_repo_config_for_system(obj)

    def get_template_file_for_profile(self, profile_name: str, path: str, **rest: Any):
        """
        Return the templated file requested for this profile

        :param profile_name: The name of the profile to get the template file for.
        :param path: The path to the template which is requested.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The template file as a str representation.
        """
        obj = self.api.find_profile(profile_name)
        if obj is None or isinstance(obj, list):
            return f"# object not found: {profile_name}"
        return self.api.get_template_file_for_profile(obj, path)

    def get_template_file_for_system(self, system_name: str, path: str, **rest: Any):
        """
        Return the templated file requested for this system

        :param system_name: The name of the system to get the template file for.
        :param path: The path to the template which is requested.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The template file as a str representation.
        """
        obj = self.api.find_system(system_name)
        if obj is None or isinstance(obj, list):
            return f"# object not found: {system_name}"
        return self.api.get_template_file_for_system(obj, path)

    def register_new_system(
        self, info: Dict[str, Any], token: Optional[str] = None, **rest: Any
    ) -> int:
        """
        If register_new_installs is enabled in settings, this allows /usr/bin/cobbler-register (part of the koan
        package) to add new system records remotely if they don't already exist.
        There is a cobbler_register snippet that helps with doing this automatically for new installs but it can also be
        used for existing installs.

        See "AutoRegistration" on the Wiki.

        :param info: The system information which is provided by the system.
        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: Return 0 if everything succeeded.
        """

        if not self.api.settings().register_new_installs:
            raise CX("registration is disabled in cobbler settings")

        # validate input
        name = info.get("name", "")
        profile = info.get("profile", "")
        hostname = info.get("hostname", "")
        interfaces = info.get("interfaces", {})
        ilen = len(list(interfaces.keys()))

        if name == "":
            raise CX("no system name submitted")
        if profile == "":
            raise CX("profile not submitted")
        if ilen == 0:
            raise CX("no interfaces submitted")
        if ilen >= 64:
            raise CX("too many interfaces submitted")

        # validate things first
        name = info.get("name", "")
        inames = list(interfaces.keys())
        if self.api.find_system(name=name):
            raise CX("system name conflicts")
        if hostname != "" and self.api.find_system(hostname=hostname):
            raise CX("hostname conflicts")

        for iname in inames:
            mac = info["interfaces"][iname].get("mac_address", "")
            ip_address = info["interfaces"][iname].get("ip_address", "")
            if ip_address.find("/") != -1:
                raise CX("no CIDR ips are allowed")
            if mac == "":
                raise CX(f"missing MAC address for interface {iname}")
            if mac != "":
                system = self.api.find_system(mac_address=mac)
                if system is not None:
                    raise CX(f"mac conflict: {mac}")
            if ip_address != "":
                system = self.api.find_system(ip_address=ip_address)
                if system is not None:
                    raise CX(f"ip conflict: {ip_address}")

        # looks like we can go ahead and create a system now
        obj = self.api.new_system()
        obj.profile = profile
        obj.name = name
        if hostname != "":
            obj.hostname = hostname
        obj.netboot_enabled = False
        for iname in inames:
            if info["interfaces"][iname].get("bridge", "") == 1:
                # don't add bridges
                continue
            mac = info["interfaces"][iname].get("mac_address", "")
            ip_address = info["interfaces"][iname].get("ip_address", "")
            netmask = info["interfaces"][iname].get("netmask", "")
            if mac == "?":
                # see koan/utils.py for explanation of network info discovery
                continue
            obj.interfaces = {
                iname: {
                    "mac_address": mac,
                    "ip_address": ip_address,
                    "netmask": netmask,
                }
            }
            if hostname != "":
                obj.hostname = hostname
            if ip_address not in ("", "?"):
                obj.interfaces[iname].ip_address = ip_address
            if netmask not in ("", "?"):
                obj.interfaces[iname].netmask = netmask
        self.api.add_system(obj)
        return 0

    def disable_netboot(
        self, name: str, token: Optional[str] = None, **rest: Any
    ) -> bool:
        """
        This is a feature used by the ``pxe_just_once`` support, see manpage. Sets system named "name" to no-longer PXE.
        Disabled by default as this requires public API access and is technically a read-write operation.

        :param name: The name of the system to disable netboot for.
        :param token: The API-token obtained via the login() method.
        :param rest: This parameter is unused.
        :return: A boolean indicated the success of the action.
        """
        self._log("disable_netboot", token=token, name=name)
        # used by nopxe.cgi
        if not self.api.settings().pxe_just_once:
            # feature disabled!
            return False
        # triggers should be enabled when calling nopxe
        triggers_enabled = self.api.settings().nopxe_with_triggers
        obj = self.api.systems().find(name=name)
        if obj is None:
            # system not found!
            return False
        if isinstance(obj, list):
            # Duplicate entries found - can't be but mypy requires this check
            return False
        obj.netboot_enabled = False
        # disabling triggers and sync to make this extremely fast.
        self.api.systems().add(
            obj,
            save=True,
            with_triggers=triggers_enabled,
            with_sync=False,
            quick_pxe_update=True,
        )
        # re-generate dhcp configuration
        self.api.sync_dhcp()
        return True

    def upload_log_data(
        self,
        sys_name: str,
        file: str,
        size: int,
        offset: int,
        data: "xmlrpc.client.Binary",
        token: Optional[str] = None,
    ) -> bool:
        """
        This is a logger function used by the "anamon" logging system to upload all sorts of misc data from Anaconda.
        As it's a bit of a potential log-flooder, it's off by default and needs to be enabled in our settings.

        :param sys_name: The name of the system for which to upload log data.
        :param file: The file where the log data should be put.
        :param size: The size of the data which will be received.
        :param offset: The offset in the file where the data will be written to.
        :param data: The data that should be logged.
        :param token: The API-token obtained via the login() method.
        :return: True if everything succeeded.
        """
        if not self.api.settings().anamon_enabled:
            # Feature disabled!
            return False

        if not self.__validate_log_data_params(
            sys_name, file, size, offset, data.data, token
        ):
            return False

        self._log(
            f"upload_log_data (file: '{file}', size: {size}, offset: {offset})",
            token=token,
            name=sys_name,
        )

        # Find matching system or profile record
        obj = self.api.find_system(name=sys_name)
        if obj is None or isinstance(obj, list):
            obj = self.api.find_profile(name=sys_name)
            if obj is None or isinstance(obj, list):
                # system or profile not found!
                self._log(
                    "upload_log_data - WARNING - system or profile not found in Cobbler",
                    token=token,
                    name=sys_name,
                )
                return False

        return self.__upload_file(obj.name, file, size, offset, data.data)

    def __validate_log_data_params(
        self,
        sys_name: str,
        logfile_name: str,
        size: int,
        offset: int,
        data: bytes,
        token: Optional[str] = None,
    ) -> bool:
        # Validate all types
        if not (
            isinstance(sys_name, str)  # type: ignore
            and isinstance(logfile_name, str)  # type: ignore
            and isinstance(size, int)  # type: ignore
            and isinstance(offset, int)  # type: ignore
            and isinstance(data, bytes)  # type: ignore
        ):
            self.logger.warning(
                "upload_log_data - One of the parameters handed over had an invalid type!"
            )
            return False
        if token is not None and not isinstance(token, str):  # type: ignore
            self.logger.warning(
                "upload_log_data - token was given but had an invalid type."
            )
            return False
        # Validate sys_name with item regex
        if not re.fullmatch(base_item.RE_OBJECT_NAME, sys_name):
            self.logger.warning(
                "upload_log_data - The provided sys_name contained invalid characters!"
            )
            return False
        # Validate logfile_name - this uses the script name validation, possibly we need our own for this one later
        if not validate_autoinstall_script_name(logfile_name):
            self.logger.warning(
                "upload_log_data - The provided file contained invalid characters!"
            )
            return False
        return True

    def __upload_file(
        self, sys_name: str, logfile_name: str, size: int, offset: int, data: bytes
    ) -> bool:
        """
        Files can be uploaded in chunks, if so the size describes the chunk rather than the whole file. The offset
        indicates where the chunk belongs the special offset -1 is used to indicate the final chunk.

        :param sys_name: the name of the system
        :param logfile_name: the name of the file
        :param size: size of contents (bytes)
        :param offset: the offset of the chunk
        :param data: base64 encoded file contents
        :return: True if the action succeeded.
        """
        if offset != -1:
            if size != len(data):
                return False

        # FIXME: Get the base directory from Cobbler app-settings
        anamon_base_directory = "/var/log/cobbler/anamon"
        anamon_sys_directory = os.path.join(anamon_base_directory, sys_name)

        file_name = os.path.join(anamon_sys_directory, logfile_name)
        normalized_path = os.path.normpath(file_name)
        if not normalized_path.startswith(anamon_sys_directory):
            self.logger.warning(
                "upload_log_data: built path for the logfile was outside of the Cobbler-Anamon log "
                "directory!"
            )
            return False

        if not os.path.isdir(anamon_sys_directory):
            os.mkdir(anamon_sys_directory, 0o755)

        try:
            file_stats = os.lstat(file_name)
        except OSError as error:
            if error.errno == errno.ENOENT:
                pass
            else:
                raise
        else:
            if not stat.S_ISREG(file_stats.st_mode):
                raise CX(f"destination not a file: {file_name}")

        # TODO: See if we can simplify this at a later point
        uploaded_file_fd = os.open(
            file_name, os.O_RDWR | os.O_CREAT | os.O_CLOEXEC, 0o644
        )
        # log_error("fd=%r" %fd)
        try:
            if offset == 0 or (offset == -1 and size == len(data)):
                # truncate file
                fcntl.lockf(uploaded_file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    os.ftruncate(uploaded_file_fd, 0)
                    # log_error("truncating fd %r to 0" %fd)
                finally:
                    fcntl.lockf(uploaded_file_fd, fcntl.LOCK_UN)
            if offset == -1:
                os.lseek(uploaded_file_fd, 0, 2)
            else:
                os.lseek(uploaded_file_fd, offset, 0)
            # write contents
            fcntl.lockf(
                uploaded_file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB, len(data), 0, 2
            )
            try:
                os.write(uploaded_file_fd, data)
                # log_error("wrote contents")
            finally:
                fcntl.lockf(uploaded_file_fd, fcntl.LOCK_UN, len(data), 0, 2)
            if offset == -1:
                # truncate file
                fcntl.lockf(uploaded_file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                try:
                    os.ftruncate(uploaded_file_fd, size)
                    # log_error("truncating fd %r to size %r" % (fd,size))
                finally:
                    fcntl.lockf(uploaded_file_fd, fcntl.LOCK_UN)
        finally:
            os.close(uploaded_file_fd)
        return True

    def run_install_triggers(
        self,
        mode: str,
        objtype: str,
        name: str,
        ip: str,
        token: Optional[str] = None,
        **rest: Any,
    ):
        """
        This is a feature used to run the pre/post install triggers.
        See CobblerTriggers on Wiki for details

        :param mode: The mode of the triggers. May be "pre", "post" or "firstboot".
        :param objtype: The type of object. This should correspond to the collection type.
        :param name: The name of the object.
        :param ip: The ip of the objet.
        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: True if everything worked correctly.
        """
        self._log("run_install_triggers", token=token)

        if mode not in ("pre", "post", "firstboot"):
            return False
        if objtype not in ("system", "profile"):
            return False

        # The trigger script is called with name,mac, and ip as arguments 1,2, and 3 we do not do API lookups here
        # because they are rather expensive at install time if reinstalling all of a cluster all at once.
        # We can do that at "cobbler check" time.
        utils.run_triggers(
            self.api,
            None,
            f"/var/lib/cobbler/triggers/install/{mode}/*",
            additional=[objtype, name, ip],
        )
        return True

    def version(self, token: Optional[str] = None, **rest: Any):
        """
        Return the Cobbler version for compatibility testing with remote applications.
        See api.py for documentation.

        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The short version of Cobbler.
        """
        self._log("version", token=token)
        return self.api.version()

    def extended_version(
        self, token: Optional[str] = None, **rest: Any
    ) -> Dict[str, Union[str, List[str]]]:
        """
        Returns the full dictionary of version information.  See api.py for documentation.

        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The extended version of Cobbler
        """
        self._log("version", token=token)
        return self.api.version(extended=True)  # type: ignore

    def get_distros_since(
        self, mtime: float
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        Return all of the distro objects that have been modified after mtime.

        :param mtime: The time after which all items should be included. Everything before this will be excluded.
        :return: The list of items which were modified after ``mtime``.
        """
        data = self.api.get_distros_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_profiles_since(
        self, mtime: float
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        See documentation for get_distros_since

        :param mtime: The time after which all items should be included. Everything before this will be excluded.
        :return: The list of items which were modified after ``mtime``.
        """
        data = self.api.get_profiles_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_systems_since(
        self, mtime: float
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        See documentation for get_distros_since

        :param mtime: The time after which all items should be included. Everything before this will be excluded.
        :return: The list of items which were modified after ``mtime``.
        """
        data = self.api.get_systems_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_repos_since(
        self, mtime: float
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        See documentation for get_distros_since

        :param mtime: The time after which all items should be included. Everything before this will be excluded.
        :return: The list of items which were modified after ``mtime``.
        """
        data = self.api.get_repos_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_images_since(
        self, mtime: float
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        See documentation for get_distros_since

        :param mtime: The time after which all items should be included. Everything before this will be excluded.
        :return: The list of items which were modified after ``mtime``.
        """
        data = self.api.get_images_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_menus_since(
        self, mtime: float
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        See documentation for get_distros_since

        :param mtime: The time after which all items should be included. Everything before this will be excluded.
        :return: The list of items which were modified after ``mtime``.
        """
        data = self.api.get_menus_since(mtime, collapse=True)
        return self.xmlrpc_hacks(data)

    def get_repos_compatible_with_profile(
        self, profile: str, token: Optional[str] = None, **rest: Any
    ) -> List[Dict[Any, Any]]:
        """
        Get repos that can be used with a given profile name.

        :param profile: The profile to check for compatibility.
        :param token: The API-token obtained via the login() method.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The list of compatible repositories.
        """
        self._log("get_repos_compatible_with_profile", token=token)
        profile_obj = self.api.find_profile(profile)
        if profile_obj is None or isinstance(profile_obj, list):
            self.logger.info(
                'The profile name supplied ("%s") for get_repos_compatible_with_profile was not'
                "existing",
                profile,
            )
            return []
        results: List[Dict[Any, Any]] = []
        distro: Optional["Distro"] = profile_obj.get_conceptual_parent()  # type: ignore
        if distro is None:
            raise ValueError("Distro not found!")
        for current_repo in self.api.repos():
            # There be dragons!
            # Accept all repos that are src/noarch but otherwise filter what repos are compatible with the profile based
            # on the arch of the distro.
            # FIXME: Use the enum directly
            if current_repo.arch.value in [
                "",
                "noarch",
                "src",
            ]:
                results.append(current_repo.to_dict())
            else:
                # some backwards compatibility fuzz
                # repo.arch is mostly a text field
                # distro.arch is i386/x86_64
                if current_repo.arch.value in ["i386", "x86", "i686"]:
                    if distro.arch.value in ["i386", "x86"]:
                        results.append(current_repo.to_dict())
                elif current_repo.arch.value in ["x86_64"]:
                    if distro.arch.value in ["x86_64"]:
                        results.append(current_repo.to_dict())
                else:
                    if distro.arch.value == current_repo.arch.value:
                        results.append(current_repo.to_dict())
        return results

    def find_system_by_dns_name(self, dns_name: str) -> Dict[str, Any]:
        """
        This is used by the puppet external nodes feature.

        :param dns_name: The dns name of the system. This should be the fqdn and not only the hostname.
        :return: All system information or an empty dict.
        """
        # FIXME: expose generic finds for other methods
        # WARNING: this function is /not/ expected to stay in Cobbler long term
        system = self.api.find_system(dns_name=dns_name)
        if system is None or isinstance(system, list):
            return {}
        return self.get_system_as_rendered(system.name)  # type: ignore

    def get_distro_as_rendered(
        self, name: str, token: Optional[str] = None, **rest: Any
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        Get distribution after passing through Cobbler's inheritance engine.

        :param name: distro name
        :param token: authentication token
        :param rest: This is dropped in this method since it is not needed here.
        :return: Get a template rendered as a distribution.
        """

        self._log("get_distro_as_rendered", name=name, token=token)
        obj = self.api.find_distro(name=name)
        if obj is not None and not isinstance(obj, list):
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

    def get_profile_as_rendered(
        self, name: str, token: Optional[str] = None, **rest: Any
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        Get profile after passing through Cobbler's inheritance engine.

        :param name: profile name
        :param token: authentication token
        :param rest: This is dropped in this method since it is not needed here.
        :return: Get a template rendered as a profile.
        """

        self._log("get_profile_as_rendered", name=name, token=token)
        obj = self.api.find_profile(name=name)
        if obj is not None and not isinstance(obj, list):
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

    def get_system_as_rendered(
        self, name: str, token: Optional[str] = None, **rest: Any
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        Get profile after passing through Cobbler's inheritance engine.

        :param name: system name
        :param token: authentication token
        :param rest: This is dropped in this method since it is not needed here.
        :return: Get a template rendered as a system.
        """

        self._log("get_system_as_rendered", name=name, token=token)
        obj = self.api.find_system(name=name)
        if obj is not None and not isinstance(obj, list):
            _dict = utils.blender(self.api, True, obj)
            # Generate a pxelinux.cfg?
            image_based = False
            profile: Optional[Union["Profile", "Image"]] = obj.get_conceptual_parent()  # type: ignore
            if profile is None:
                raise ValueError("Profile not found!")
            distro: Optional["Distro"] = profile.get_conceptual_parent()  # type: ignore

            arch = None
            if distro is None and profile.COLLECTION_TYPE == "image":
                image_based = True
                arch = profile.arch
            else:
                arch = distro.arch  # type: ignore

            if obj.is_management_supported():
                if not image_based:
                    _dict["pxelinux.cfg"] = self.tftpgen.write_pxe_file(
                        None, obj, profile, distro, arch  # type: ignore
                    )
                else:
                    _dict["pxelinux.cfg"] = self.tftpgen.write_pxe_file(
                        None, obj, None, None, arch, image=profile  # type: ignore
                    )

            return self.xmlrpc_hacks(_dict)
        return self.xmlrpc_hacks({})

    def get_repo_as_rendered(
        self, name: str, token: Optional[str] = None, **rest: Any
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        Get repository after passing through Cobbler's inheritance engine.

        :param name: repository name
        :param token: authentication token
        :param rest: This is dropped in this method since it is not needed here.
        :return: Get a template rendered as a repository.
        """

        self._log("get_repo_as_rendered", name=name, token=token)
        obj = self.api.find_repo(name=name)
        if obj is not None and not isinstance(obj, list):
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

    def get_image_as_rendered(
        self, name: str, token: Optional[str] = None, **rest: Any
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        Get repository after passing through Cobbler's inheritance engine.

        :param name: image name
        :param token: authentication token
        :param rest: This is dropped in this method since it is not needed here.
        :return: Get a template rendered as an image.
        """

        self._log("get_image_as_rendered", name=name, token=token)
        obj = self.api.find_image(name=name)
        if obj is not None and not isinstance(obj, list):
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

    def get_menu_as_rendered(
        self, name: str, token: Optional[str] = None, **rest: Any
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        Get menu after passing through Cobbler's inheritance engine

        :param name: Menu name
        :param token: Authentication token
        :param rest: This is dropped in this method since it is not needed here.
        :return: Get a template rendered as a file.
        """

        self._log("get_menu_as_rendered", name=name, token=token)
        obj = self.api.find_menu(name=name)
        if obj is not None and not isinstance(obj, list):
            return self.xmlrpc_hacks(utils.blender(self.api, True, obj))
        return self.xmlrpc_hacks({})

    def get_random_mac(
        self, virt_type: str = "xenpv", token: Optional[str] = None, **rest: Any
    ) -> str:
        """
        Wrapper for ``utils.get_random_mac()``. Used in the webui.

        :param virt_type: The type of the virtual machine.
        :param token: The API-token obtained via the login() method. Auth token to authenticate against the api.
        :param rest: This is dropped in this method since it is not needed here.
        :return: The random mac address which shall be used somewhere else.
        """
        # ToDo: Remove rest param
        self._log("get_random_mac", token=None)
        return utils.get_random_mac(self.api, virt_type)

    def xmlrpc_hacks(
        self, data: Optional[Union[List[Any], Dict[Any, Any], int, str, float]]
    ) -> Union[List[Any], Dict[Any, Any], int, str, float]:
        """
        Convert None in XMLRPC to just '~' to make extra sure a client that can't allow_none can deal with this.

        ALSO: a weird hack ensuring that when dicts with integer keys (or other types) are transmitted with string keys.

        :param data: The data to prepare for the XMLRPC response.
        :return: The converted data.
        """
        return utils.strip_none(data)

    def get_status(
        self, mode: str = "normal", token: Optional[str] = None, **rest: Any
    ) -> Union[Dict[Any, Any], str]:
        """
        Returns the same information as `cobbler status`
        While a read-only operation, this requires a token because it's potentially a fair amount of I/O

        :param mode: How the status should be presented.
        :param token: The API-token obtained via the login() method. Auth token to authenticate against the api.
        :param rest: This parameter is currently unused for this method.
        :return: The human or machine readable status of the status of Cobbler.
        """
        self.check_access(token, "sync")
        return self.api.status(mode=mode)

    def __get_random(self, length: int) -> str:
        """
        Get a random string of a desired length.

        :param length: The length of the
        :return: A random string of the desired length from ``/dev/urandom``.
        """
        b64 = base64.b64encode(os.urandom(length))
        return b64.decode()

    def __make_token(self, user: str) -> str:
        """
        Returns a new random token.

        :param user: The user for which the token should be generated.
        :return: The token which was generated.
        """
        b64 = self.__get_random(25)
        self.token_cache[b64] = (time.time(), user)
        return b64

    @staticmethod
    def __is_token(token: Optional[str]) -> bool:
        """
        Simple check to validate if it is a token.

        __make_token() uses 25 as the length of bytes that means we need to padding bytes to have a 34 character str.
        Because base64 specifies that the number of padding bytes are shown via equal characters, we have a 36 character
        long str in the end in every case.

        :param token: The str which should be checked.
        :return: True in case the validation succeeds, otherwise False.
        """
        return isinstance(token, str) and len(token) == 36

    def __invalidate_expired_tokens(self) -> None:
        """
        Deletes any login tokens that might have expired. Also removes expired events.
        """
        timenow = time.time()
        for token in list(self.token_cache.keys()):
            (tokentime, _) = self.token_cache[token]
            if timenow > tokentime + self.api.settings().auth_token_expiration:
                self._log("expiring token", token=token, debug=True)
                del self.token_cache[token]
        # and also expired objects
        for oid in list(self.unsaved_items.keys()):
            (tokentime, _) = self.unsaved_items[oid]
            if timenow > tokentime + CACHE_TIMEOUT:
                del self.unsaved_items[oid]
        for tid in list(self.events.keys()):
            event = self.events[tid]
            if timenow > event.statetime + float(EVENT_TIMEOUT):
                del self.events[tid]
            # logfile cleanup should be dealt w/ by logrotate

    def __validate_user(self, input_user: str, input_password: str) -> bool:
        """
        Returns whether this user/pass combo should be given access to the Cobbler read-write API.

        For the system user, this answer is always "yes", but it is only valid for the socket interface.

        :param input_user: The user to validate.
        :param input_password: The password to validate.
        :return: If the authentication was successful ``True`` is returned. ``False`` in all other cases.
        """
        return self.api.authenticate(input_user, input_password)

    def __validate_token(self, token: Optional[str]) -> bool:
        """
        Checks to see if an API method can be called when the given token is passed in. Updates the timestamp of the
        token automatically to prevent the need to repeatedly call login(). Any method that needs access control should
        call this before doing anything else.

        :param token: The token to validate.
        :return: True if access is allowed, otherwise False.
        """
        self.__invalidate_expired_tokens()

        if token in self.token_cache:
            user = self.get_user_from_token(token)
            if user == "<system>":
                # system token is only valid over Unix socket
                return False
            self.token_cache[token] = (time.time(), user)  # update to prevent timeout
            return True
        self._log("invalid token", token=token)
        return False

    def __name_to_object(self, resource: str, name: str) -> Optional["ITEM"]:  # type: ignore
        result: Optional["ITEM"] = None
        if resource.find("distro") != -1:
            result = self.api.find_distro(name, return_list=False)  # type: ignore
        if resource.find("profile") != -1:
            result = self.api.find_profile(name, return_list=False)  # type: ignore
        if resource.find("system") != -1:
            result = self.api.find_system(name, return_list=False)  # type: ignore
        if resource.find("repo") != -1:
            result = self.api.find_repo(name, return_list=False)  # type: ignore
        if resource.find("menu") != -1:
            result = self.api.find_menu(name, return_list=False)  # type: ignore
        if isinstance(result, list):
            raise ValueError("Search is not allowed to return list!")
        return result

    def check_access_no_fail(
        self, token: str, resource: str, arg1: Optional[str] = None, arg2: Any = None
    ) -> int:
        """
        This is called by the WUI to decide whether an element is editable or not. It differs form check_access in that
        it is supposed to /not/ log the access checks (TBA) and does not raise exceptions.

        :param token: The token to check access for.
        :param resource: The resource for which access shall be checked.
        :param arg1: Arguments to hand to the authorization provider.
        :param arg2: Arguments to hand to the authorization provider.
        :return: 1 if the object is editable or 0 otherwise.
        """
        need_remap = False
        for item_type in [
            "distro",
            "profile",
            "system",
            "repo",
            "image",
            "menu",
        ]:
            if arg1 is not None and resource.find(item_type) != -1:
                need_remap = True
                break

        if need_remap:
            # we're called with an object name, but need an object
            arg1 = self.__name_to_object(resource, arg1)  # type: ignore

        try:
            self.check_access(token, resource, arg1, arg2)
            return 1
        except Exception:
            utils.log_exc()
            return 0

    def check_access(
        self,
        token: Optional[str],
        resource: str,
        arg1: Optional[str] = None,
        arg2: Any = None,
    ) -> int:
        """
        Check if the token which was provided has access.

        :param token: The token to check access for.
        :param resource: The resource for which access shall be checked.
        :param arg1: Arguments to hand to the authorization provider.
        :param arg2: Arguments to hand to the authorization provider.
        :return: If the operation was successful return ``1``. If unsuccessful then return ``0``. Other codes may be
                 returned if specified by the currently configured authorization module.
        """
        user = self.get_user_from_token(token)
        if user == "<DIRECT>":
            self._log("CLI Authorized", debug=True)
            return 1
        return_code = self.api.authorize(user, resource, arg1, arg2)
        self._log(f"{user} authorization result: {return_code}", debug=True)
        if not return_code:
            raise CX(f"authorization failure for user {user}")
        return return_code

    def get_authn_module_name(self, token: str) -> str:
        """
        Get the name of the currently used authentication module.

        :param token: The API-token obtained via the login() method. Cobbler token, obtained form login()
        :return: The name of the module.
        """
        user = self.get_user_from_token(token)
        if user != "<DIRECT>":
            raise CX(
                f"authorization failure for user {user} attempting to access authn module name"
            )
        return self.api.get_module_name_from_file("authentication", "module")

    def login(self, login_user: str, login_password: str) -> str:
        """
        Takes a username and password, validates it, and if successful returns a random login token which must be used
        on subsequent method calls. The token will time out after a set interval if not used. Re-logging in permitted.

        :param login_user: The username which is used to authenticate at Cobbler.
        :param login_password:  The password which is used to authenticate at Cobbler.
        :return: The token which can be used further on.
        """
        # if shared secret access is requested, don't bother hitting the auth plugin
        if login_user == "":
            if login_password == self.shared_secret:
                return self.__make_token("<DIRECT>")
            raise ValueError("login failed due to missing username!")

        # This should not log to disk OR make events as we're going to call it like crazy in CobblerWeb. Just failed
        # attempts.
        if self.__validate_user(login_user, login_password):
            token = self.__make_token(login_user)
            return token
        raise ValueError(f"login failed ({login_user})")

    def logout(self, token: str) -> bool:
        """
        Retires a token ahead of the timeout.

        :param token: The API-token obtained via the login() method. Cobbler token, obtained form login()
        :return: if operation was successful or not
        """
        self._log("logout", token=token)
        if token in self.token_cache:
            del self.token_cache[token]
            return True
        return False

    def token_check(self, token: str) -> bool:
        """
        Checks to make sure a token is valid or not.

        :param token: The API-token obtained via the login() method. Cobbler token, obtained form login()
        :return: if operation was successful or not
        """
        return self.__validate_token(token)

    def sync_dhcp(self, token: str) -> bool:
        """
        Run sync code, which should complete before XMLRPC timeout. We can't do reposync this way. Would be nice to
        send output over AJAX/other later.

        :param token: The API-token obtained via the login() method. Cobbler token, obtained form login()
        :return: bool if operation was successful
        """
        self._log("sync_dhcp", token=token)
        self.check_access(token, "sync")
        self.api.sync_dhcp()
        return True

    def sync(self, token: str) -> bool:
        """
        Run sync code, which should complete before XMLRPC timeout. We can't do reposync this way. Would be nice to
        send output over AJAX/other later.

        :param token: The API-token obtained via the login() method. Cobbler token, obtained form login()
        :return: bool if operation was successful
        """
        # FIXME: performance
        self._log("sync", token=token)
        self.check_access(token, "sync")
        self.api.sync()
        return True

    def read_autoinstall_template(self, file_path: str, token: str) -> str:
        """
        Read an automatic OS installation template file

        :param file_path: automatic OS installation template file path
        :param token: The API-token obtained via the login() method. Cobbler token, obtained form login()
        :returns: file content
        """
        what = "read_autoinstall_template"
        self._log(what, name=file_path, token=token)
        self.check_access(token, what, file_path, True)

        return self.autoinstall_mgr.read_autoinstall_template(file_path)

    def write_autoinstall_template(self, file_path: str, data: str, token: str) -> bool:
        """
        Write an automatic OS installation template file

        :param file_path: automatic OS installation template file path
        :param data: new file content
        :param token: The API-token obtained via the login() method. Cobbler token, obtained form login()
        :returns: bool if operation was successful
        """

        what = "write_autoinstall_template"
        self._log(what, name=file_path, token=token)
        self.check_access(token, what, file_path, True)

        self.autoinstall_mgr.write_autoinstall_template(file_path, data)

        return True

    def remove_autoinstall_template(self, file_path: str, token: str) -> bool:
        """
        Remove an automatic OS installation template file

        :param file_path: automatic OS installation template file path
        :param token: The API-token obtained via the login() method. Cobbler token, obtained form login()
        :returns: bool if operation was successful
        """
        what = "write_autoinstall_template"
        self._log(what, name=file_path, token=token)
        self.check_access(token, what, file_path, True)

        self.autoinstall_mgr.remove_autoinstall_template(file_path)

        return True

    def read_autoinstall_snippet(self, file_path: str, token: str) -> str:
        """
        Read an automatic OS installation snippet file

        :param file_path: automatic OS installation snippet file path
        :param token: The API-token obtained via the login() method. Cobbler token, obtained form login()
        :returns: file content
        """
        what = "read_autoinstall_snippet"
        self._log(what, name=file_path, token=token)
        self.check_access(token, what, file_path, True)

        return self.autoinstall_mgr.read_autoinstall_snippet(file_path)

    def write_autoinstall_snippet(self, file_path: str, data: str, token: str) -> bool:
        """
        Write an automatic OS installation snippet file

        :param file_path: automatic OS installation snippet file path
        :param data: new file content
        :param token: Cobbler token, obtained form login()
        :return: if operation was successful
        """

        what = "write_autoinstall_snippet"
        self._log(what, name=file_path, token=token)
        self.check_access(token, what, file_path, True)

        self.autoinstall_mgr.write_autoinstall_snippet(file_path, data)

        return True

    def remove_autoinstall_snippet(self, file_path: str, token: str) -> bool:
        """
        Remove an automated OS installation snippet file

        :param file_path: automated OS installation snippet file path
        :param token: Cobbler token, obtained form login()
        :return: bool if operation was successful
        """

        what = "remove_autoinstall_snippet"
        self._log(what, name=file_path, token=token)
        self.check_access(token, what, file_path, True)

        self.autoinstall_mgr.remove_autoinstall_snippet(file_path)

        return True

    def get_config_data(self, hostname: str) -> str:
        """
        Generate configuration data for the system specified by hostname.

        :param hostname: The hostname for what to get the config data of.
        :return: The config data as a json for Koan.
        """
        self._log(f"get_config_data for {hostname}")
        obj = configgen.ConfigGen(self.api, hostname)
        return obj.gen_config_data_for_koan()

    def clear_system_logs(self, object_id: str, token: str) -> bool:
        """
        clears console logs of a system

        :param object_id: The object id of the system to clear the logs of.
        :param token: The API-token obtained via the login() method.
        :return: True if the operation succeeds.
        """
        # We pass return_list=False, thus the return type is Optional[System]
        obj: Optional["system.System"] = self.api.find_system(uid=object_id, return_list=False)  # type: ignore
        self.check_access(
            token, "clear_system_logs", obj.name if obj else "object not found"
        )
        if obj is None:
            return False
        self.api.clear_logs(obj)
        return True

    def input_string_or_list_no_inherit(
        self, options: Optional[Union[str, List[Any]]]
    ) -> List[Any]:
        """
        .. seealso:: :func:`~cobbler.api.CobblerAPI.input_string_or_list_no_inherit`
        """
        return self.api.input_string_or_list_no_inherit(options)

    def input_string_or_list(
        self, options: Optional[Union[str, List[Any]]]
    ) -> Union[List[Any], str]:
        """
        .. seealso:: :func:`~cobbler.api.CobblerAPI.input_string_or_list`
        """
        return self.api.input_string_or_list(options)

    def input_string_or_dict(
        self,
        options: Union[str, List[Any], Dict[Any, Any]],
        allow_multiples: bool = True,
    ) -> Union[str, Dict[Any, Any]]:
        """
        .. seealso:: :func:`~cobbler.api.CobblerAPI.input_string_or_dict`
        """
        return self.api.input_string_or_dict(options, allow_multiples=allow_multiples)

    def input_string_or_dict_no_inherit(
        self,
        options: Union[str, List[Any], Dict[Any, Any]],
        allow_multiples: bool = True,
    ) -> Dict[Any, Any]:
        """
        .. seealso:: :func:`~cobbler.api.CobblerAPI.input_string_or_dict_no_inherit`
        """
        return self.api.input_string_or_dict_no_inherit(
            options, allow_multiples=allow_multiples
        )

    def input_boolean(self, value: Union[str, bool, int]) -> bool:
        """
        .. seealso:: :func:`~cobbler.api.CobblerAPI.input_boolean`
        """
        return self.api.input_boolean(value)

    def input_int(self, value: Union[str, int, float]) -> int:
        """
        .. seealso:: :func:`~cobbler.api.CobblerAPI.input_int`
        """
        return self.api.input_int(value)

    def get_tftp_file(
        self, path: str, offset: int, size: int, token: str
    ) -> Tuple[bytes, int]:
        """
        Generate and return a file for a TFTP client.

        :param path: Path to file
        :param token: The API-token obtained via the login() method
        :param offset: Offset of the requested chunk in the file
        :param size: Size of the requested chunk in the file
        :return: The requested chunk and the length of the whole file
        """
        self._log("get_tftp_file", token=token)
        self.check_access(token, "get_tftp_file")
        return self.api.get_tftp_file(path, offset, size)


# *********************************************************************************


class RequestHandler(SimpleXMLRPCRequestHandler):
    """
    TODO
    """

    def do_OPTIONS(self) -> None:
        """
        TODO
        """
        self.send_response(200)
        self.end_headers()

    # Add these headers to all responses
    def end_headers(self) -> None:
        """
        TODO
        """
        self.send_header(
            "Access-Control-Allow-Headers",
            "Origin, X-Requested-With, Content-Type, Accept",
        )
        self.send_header("Access-Control-Allow-Origin", "*")
        SimpleXMLRPCRequestHandler.end_headers(self)


class CobblerXMLRPCServer(ThreadingMixIn, xmlrpc.server.SimpleXMLRPCServer):
    """
    This is the class for the main Cobbler XMLRPC Server. This class does not directly contain all XMLRPC methods. It
    just starts the server.
    """

    def __init__(self, args: Any) -> None:
        """
        The constructor for the main Cobbler XMLRPC server.

        :param args: Arguments which are handed to the Python XMLRPC server.
        """
        self.allow_reuse_address = True
        xmlrpc.server.SimpleXMLRPCServer.__init__(
            self, args, requestHandler=RequestHandler
        )


# *********************************************************************************


class ProxiedXMLRPCInterface:
    """
    TODO
    """

    def __init__(self, api: "CobblerAPI", proxy_class: Type[Any]) -> None:
        """
        This interface allows proxying request through another class.

        :param api: The api object to resolve information with
        :param proxy_class: The class which proxies the requests.
        """
        self.proxied = proxy_class(api)
        self.logger = self.proxied.api.logger

    def _dispatch(self, method: str, params: Any, **rest: Any) -> Any:
        """
        This method magically registers the methods at the XMLRPC interface.

        :param method: The method to register.
        :param params: The params for the method.
        :param rest: This gets dropped curently.
        :return: The result of the method.
        """
        # ToDo: Drop rest param
        if method.startswith("_"):
            raise CX("forbidden method")

        if not hasattr(self.proxied, method):
            raise CX(f"unknown remote method '{method}'")

        method_handle = getattr(self.proxied, method)

        # FIXME: see if this works without extra boilerplate
        try:
            return method_handle(*params)
        except Exception as exception:
            utils.log_exc()
            raise exception
