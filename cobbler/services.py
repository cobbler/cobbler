"""
Mod Python service functions for Cobbler's public interface (aka cool stuff that works with wget/curl)

Changelog:

Schema: From -> To

Current Schema: Please refer to the documentation visible of the individual methods.

V3.4.0 (unreleased)
    * No changes

V3.3.4 (unreleased)
    * No changes

V3.3.3
    * Removed:
        * ``look``

V3.3.2
    * No changes

V3.3.1
    * No changes

V3.3.0
    * Added:
        * ``settings``
    * Changed:
        * ``gpxe``: Renamed to ``ipxe``

V3.2.2
    * No changes

V3.2.1
    * No changes

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
        * ``autoinstall``
        * ``find_autoinstall``

V2.8.5
    * Inital tracking of changes.

"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: based on code copyright 2007 Albert P. Tobey <tobert@gmail.com>
# SPDX-FileCopyrightText: additions: 2007-2009 Michael DeHaan <michael.dehaan AT gmail>

import json
import time
import xmlrpc.client
from typing import Any, Callable, Dict, List, Optional, Union
from urllib import parse

import yaml

from cobbler import download_manager


class CobblerSvc:
    """
    Interesting mod python functions are all keyed off the parameter mode, which defaults to index. All options are
    passed as parameters into the function.
    """

    def __init__(self, server: str = "") -> None:
        """
        Default constructor which sets up everything to be ready.

        :param server: The domain to run at.
        :param req: This parameter is unused.
        """
        self.server = server
        self.__remote: Optional[xmlrpc.client.Server] = None
        self.dlmgr = download_manager.DownloadManager()

    @property
    def remote(self) -> xmlrpc.client.ServerProxy:
        """
        Sets up the connection to the Cobbler XMLRPC server. This is the version that does not require a login.
        """
        if self.__remote is None:
            self.__remote = xmlrpc.client.Server(self.server, allow_none=True)
        return self.__remote

    def settings(self, **kwargs: Any) -> str:
        """
        Get the application configuration.

        :return: Settings object.
        """
        return json.dumps(self.remote.get_settings(), indent=4)

    def index(self, **args: Any) -> str:
        """
        Just a placeholder method as an entry point.

        :param args: This parameter is unused.
        :return: "no mode specified"
        """
        return "no mode specified"

    def autoinstall(
        self,
        profile: Optional[str] = None,
        system: Optional[str] = None,
        REMOTE_ADDR: Optional[str] = None,
        REMOTE_MAC: Optional[str] = None,
        **rest: Any,
    ) -> str:
        """
        Generate automatic installation files.

        :param profile:
        :param system:
        :param REMOTE_ADDR:
        :param REMOTE_MAC:
        :param rest: This parameter is unused.
        :return:
        """
        data = self.remote.generate_autoinstall(
            profile, system, REMOTE_ADDR, REMOTE_MAC
        )
        if isinstance(data, str):
            return data
        return "ERROR: Server returned unexpected data!"

    def ks(
        self,
        profile: Optional[str] = None,
        system: Optional[str] = None,
        REMOTE_ADDR: Optional[str] = None,
        REMOTE_MAC: Optional[str] = None,
        **rest: Any,
    ) -> str:
        """
        Generate automatic installation files. This is a legacy function for part backward compatibility to 2.6.6
        releases.

        :param profile:
        :param system:
        :param REMOTE_ADDR:
        :param REMOTE_MAC:
        :param rest: This parameter is unused.
        :return:
        """
        data = self.remote.generate_autoinstall(
            profile, system, REMOTE_ADDR, REMOTE_MAC
        )
        if isinstance(data, str):
            return data
        return "ERROR: Server returned unexpected data!"

    def ipxe(
        self,
        profile: Optional[str] = None,
        image: Optional[str] = None,
        system: Optional[str] = None,
        mac: Optional[str] = None,
        **rest: Any,
    ) -> str:
        """
        Generates an iPXE configuration.

        :param profile: A profile.
        :param image: An image.
        :param system: A system.
        :param mac: A MAC address.
        :param rest: This parameter is unused.
        """
        if not system and mac:
            query = {"mac_address": mac}
            if profile:
                query["profile"] = profile
            elif image:
                query["image"] = image
            # mypy and xmlrpc don't play well together
            found: List[Any] = self.remote.find_system(query)  # type: ignore
            if found:
                system = found[0]

        data = self.remote.generate_ipxe(profile, image, system)
        if isinstance(data, str):
            return data
        return "ERROR: Server returned unexpected data!"

    def bootcfg(
        self, profile: Optional[str] = None, system: Optional[str] = None, **rest: Any
    ) -> str:
        """
        Generate a boot.cfg config file. Used primarily for VMware ESXi.

        :param profile:
        :param system:
        :param rest: This parameter is unused.
        :return:
        """
        data = self.remote.generate_bootcfg(profile, system)
        if isinstance(data, str):
            return data
        return "ERROR: Server returned unexpected data!"

    def script(
        self, profile: Optional[str] = None, system: Optional[str] = None, **rest: Any
    ) -> str:
        """
        Generate a script based on snippets. Useful for post or late-action scripts where it's difficult to embed the
        script in the response file.

        :param profile: The profile to generate the script for.
        :param system: The system to generate the script for.
        :param rest: This may contain a parameter with the key "query_string" which has a key "script" which may be an
                     array. The element from position zero is taken.
        :return: The generated script.
        """
        data = self.remote.generate_script(
            profile, system, rest["query_string"]["script"][0]
        )
        if isinstance(data, str):
            return data
        return "ERROR: Server returned unexpected data!"

    def events(self, user: str = "", **rest: Any) -> str:
        """
        If no user is given then all events are returned. Otherwise only event associated to a user are returned.

        :param user: Filter the events for a given user.
        :param rest: This parameter is unused.
        :return: A JSON object which contains all events.
        """
        if user == "":
            data = self.remote.get_events("")
        else:
            data = self.remote.get_events(user)

        if not isinstance(data, dict):
            raise ValueError("Server returned incorrect data!")

        # sort it... it looks like { timestamp : [ array of details ] }
        keylist = list(data.keys())
        keylist.sort()
        results: List[List[Union[str, float]]] = []
        for k in keylist:
            etime = int(data[k][0])
            nowtime = time.time()
            if (nowtime - etime) < 30:
                results.append([k, data[k][0], data[k][1], data[k][2]])
        return json.dumps(results)

    def template(
        self,
        profile: Optional[str] = None,
        system: Optional[str] = None,
        path: Optional[str] = None,
        **rest: Any,
    ) -> str:
        """
        Generate a templated file for the system. Either specify a profile OR a system.

        :param profile: The profile to provide for the generation of the template.
        :param system: The system to provide for the generation of the template.
        :param path: The path to the template.
        :param rest: This parameter is unused.
        :return: The rendered template.
        """
        if path is not None:
            path = path.replace("_", "/")
            path = path.replace("//", "_")
        else:
            return "# must specify a template path"

        if profile is not None:
            data = self.remote.get_template_file_for_profile(profile, path)
        elif system is not None:
            data = self.remote.get_template_file_for_system(system, path)
        else:
            data = "# must specify profile or system name"
        if not isinstance(data, str):
            raise ValueError("Server returned an unexpected data type!")
        return data

    def yum(
        self, profile: Optional[str] = None, system: Optional[str] = None, **rest: Any
    ) -> str:
        """
        Generate a repo config. Either specify a profile OR a system.

        :param profile: The profile to provide for the generation of the template.
        :param system: The system to provide for the generation of the template.
        :param rest: This parameter is unused.
        :return: The generated repository config.
        """
        if profile is not None:
            data = self.remote.get_repo_config_for_profile(profile)
        elif system is not None:
            data = self.remote.get_repo_config_for_system(system)
        else:
            data = "# must specify profile or system name"
        if not isinstance(data, str):
            raise ValueError("Server returned an unexpected data type!")
        return data

    def trig(
        self,
        mode: str = "?",
        profile: Optional[str] = None,
        system: Optional[str] = None,
        REMOTE_ADDR: Optional[str] = None,
        **rest: Any,
    ) -> str:
        """
        Hook to call install triggers. Only valid for a profile OR a system.

        :param mode: Can be "pre", "post" or "firstboot". Everything else is invalid.
        :param profile: The profile object to run triggers for.
        :param system: The system object to run triggers for.
        :param REMOTE_ADDR: The ip if the remote system/profile.
        :param rest: This parameter is unused.
        :return: The return code of the action.
        """
        ip_address = REMOTE_ADDR
        if profile:
            return_code = self.remote.run_install_triggers(
                mode, "profile", profile, ip_address
            )
        else:
            return_code = self.remote.run_install_triggers(
                mode, "system", system, ip_address
            )
        return str(return_code)

    def nopxe(self, system: Optional[str] = None, **rest: Any) -> str:
        """
        Disables the network boot for the given system.

        :param system: The system to disable netboot for.
        :param rest: This parameter is unused.
        :return: A boolean status if the action succeed or not.
        """
        return str(self.remote.disable_netboot(system))

    def list(self, what: str = "systems", **rest: Any) -> str:
        """
        Return a list of objects of a desired category. Defaults to "systems".

        :param what: May be "systems", "profiles", "distros", "images", "repos", "mgmtclasses", "packages",
                            "files" or "menus"
        :param rest: This parameter is unused.
        :return: The list of object names.
        """
        # mypy and xmlrpc don't play well together
        listing: List[Dict[str, Any]]
        if what == "systems":
            listing = self.remote.get_systems()  # type: ignore
        elif what == "profiles":
            listing = self.remote.get_profiles()  # type: ignore
        elif what == "distros":
            listing = self.remote.get_distros()  # type: ignore
        elif what == "images":
            listing = self.remote.get_images()  # type: ignore
        elif what == "repos":
            listing = self.remote.get_repos()  # type: ignore
        elif what == "mgmtclasses":
            listing = self.remote.get_mgmtclasses()  # type: ignore
        elif what == "packages":
            listing = self.remote.get_packages()  # type: ignore
        elif what == "files":
            listing = self.remote.get_files()  # type: ignore
        elif what == "menus":
            listing = self.remote.get_menus()  # type: ignore
        else:
            return "?"
        names = [x["name"] for x in listing]
        if len(names) > 0:
            return "\n".join(names) + "\n"
        return ""

    def autodetect(self, **rest: Union[str, int, List[str]]) -> str:
        """
        This tries to autodect the system with the given information. If more than one candidate is found an error
        message is returned.

        :param rest: The keys "REMOTE_MACS", "REMOTE_ADDR" or "interfaces".
        :return: The name of the possible object or an error message.
        """
        # mypy and xmlrpc don't play well together
        systems: List[Dict[str, Any]] = self.remote.get_systems()  # type: ignore

        # If kssendmac was in the kernel options line, see if a system can be found matching the MAC address. This is
        # more specific than an IP match.

        # We cannot be certain that this header is included, thus we can't add a type check (potential breaking change).
        mac_addresses: List[str] = rest["REMOTE_MACS"]  # type: ignore
        macinput: List[str] = []
        for mac in mac_addresses:
            macinput.extend(mac.lower().split(" "))

        ip_address = rest["REMOTE_ADDR"]

        candidates: List[Dict[str, Any]] = []

        for system in systems:
            for interface in system["interfaces"]:
                if system["interfaces"][interface]["mac_address"].lower() in macinput:
                    candidates.append(system)

        if len(candidates) == 0:
            for system in systems:
                for interface in system["interfaces"]:
                    if system["interfaces"][interface]["ip_address"] == ip_address:
                        candidates.append(system)

        if len(candidates) == 0:
            return f"FAILED: no match ({ip_address},{macinput})"
        if len(candidates) > 1:
            return "FAILED: multiple matches"
        if len(candidates) == 1:
            return candidates[0]["name"]
        return "FAILED: Negative amount of matches!"

    def find_autoinstall(
        self,
        system: Optional[str] = None,
        profile: Optional[str] = None,
        **rest: Union[str, int],
    ) -> str:
        """
        Find an autoinstallation for a system or a profile. If this is not known different parameters can be passed to
        rest to find it automatically. See "autodetect".

        :param system: The system to find the autoinstallation for,
        :param profile: The profile to find the autoinstallation for.
        :param rest: The metadata to find the autoinstallation automatically.
        :return: The autoinstall script or error message.
        """
        name = "?"
        if system is not None:
            url = f"{self.server}/cblr/svc/op/autoinstall/system/{name}"
        elif profile is not None:
            url = f"{self.server}/cblr/svc/op/autoinstall/profile/{name}"
        else:
            name = self.autodetect(**rest)
            if name.startswith("FAILED"):
                return f"# autodetection {name}"
            url = f"{self.server}/cblr/svc/op/autoinstall/system/{name}"

        try:
            return self.dlmgr.urlread(url).content.decode("UTF-8")
        except Exception:
            return f"# automatic installation file retrieval failed ({url})"

    def findks(
        self,
        system: Optional[str] = None,
        profile: Optional[str] = None,
        **rest: Union[str, int],
    ) -> str:
        """
        This is a legacy function which enabled Cobbler partly to be backward compatible to 2.6.6 releases.

        It should be only be used if you must. Please use find_autoinstall if possible!
        :param system: If you wish to find a system please set this parameter to not null. Hand over the name of it.
        :param profile: If you wish to find a system please set this parameter to not null. Hand over the name of it.
        :param rest: If you wish you can try to let Cobbler autodetect the system with the MAC address.
        :return: Returns the autoinstall/kickstart profile.
        """
        name = "?"
        if system is not None:
            url = f"{self.server}/cblr/svc/op/ks/system/{name}"
        elif profile is not None:
            url = f"{self.server}/cblr/svc/op/ks/profile/{name}"
        else:
            name = self.autodetect(**rest)
            if name.startswith("FAILED"):
                return f"# autodetection {name}"
            url = f"{self.server}/cblr/svc/op/ks/system/{name}"

        try:
            return self.dlmgr.urlread(url).content.decode("UTF-8")
        except Exception:
            return f"# kickstart retrieval failed ({url})"

    def puppet(self, hostname: Optional[str] = None, **rest: Union[str, int]) -> str:
        """
        Dump the puppet data which is available for Cobbler.

        :param hostname: The hostname for the system which should the puppet data be dumped for.
        :param rest: This parameter is unused.
        :return: The yaml for the host.
        """
        if hostname is None:
            return "hostname is required"

        settings = self.remote.get_settings()
        if not isinstance(settings, dict):
            raise ValueError("Server returned an unexpected data type!")
        results = self.remote.find_system_by_dns_name(hostname)
        if not isinstance(results, dict):
            raise ValueError("Server returned an unexpected data type!")

        classes = results.get("mgmt_classes", {})
        params = results.get("mgmt_parameters", {})
        environ = results.get("status", "")

        data = {
            "classes": classes,
            "parameters": params,
            "environment": environ,
        }

        if environ == "":
            data.pop("environment", None)

        if settings.get("puppet_parameterized_classes", False):
            for ckey in list(classes.keys()):
                tmp = {}
                class_name = classes[ckey].get("class_name", "")
                if class_name in (None, ""):
                    class_name = ckey
                if classes[ckey].get("is_definition", False):
                    def_tmp = {}
                    def_name = classes[ckey]["params"].get("name", "")
                    del classes[ckey]["params"]["name"]
                    if def_name != "":
                        for pkey in list(classes[ckey]["params"].keys()):
                            def_tmp[pkey] = classes[ckey]["params"][pkey]
                        tmp["instances"] = {def_name: def_tmp}
                    else:
                        # FIXME: log an error here?
                        # skip silently...
                        continue
                else:
                    for pkey in list(classes[ckey]["params"].keys()):
                        tmp[pkey] = classes[ckey]["params"][pkey]
                del classes[ckey]
                classes[class_name] = tmp
        else:
            classes = list(classes.keys())

        return yaml.dump(data, default_flow_style=False)


def __fillup_form_dict(form: Dict[Any, Any], my_uri: str) -> str:
    """
    Helper function to fillup the form dict with required mode information.

    :param form: The form dict to manipulate
    :param my_uri: The URI to work with.
    :return: The normalized URI.
    """
    my_uri = parse.unquote(my_uri)

    tokens = my_uri.split("/")
    tokens = tokens[1:]
    label = True
    field = ""
    for token in tokens:
        if label:
            field = token
        else:
            form[field] = token
        label = not label
    return my_uri


def __generate_remote_mac_list(environ: Dict[str, Any]) -> List[Any]:
    # This MAC header is set by anaconda during a kickstart booted with the
    # kssendmac kernel option. The field will appear here as something
    # like: eth0 XX:XX:XX:XX:XX:XX
    mac_counter = 0
    remote_macs: List[Any] = []
    mac_header = f"HTTP_X_RHN_PROVISIONING_MAC_{mac_counter:d}"
    while environ.get(mac_header, None):
        remote_macs.append(environ[mac_header])
        mac_counter = mac_counter + 1
        mac_header = f"HTTP_X_RHN_PROVISIONING_MAC_{mac_counter:d}"
    return remote_macs


def application(
    environ: Dict[str, Any], start_response: Callable[[str, List[Any]], None]
) -> List[bytes]:
    """
    UWSGI entrypoint for Gunicorn

    :param environ:
    :param start_response:
    :return:
    """

    form: Dict[str, Any] = {}
    my_uri = __fillup_form_dict(form, environ["RAW_URI"])
    form["query_string"] = parse.parse_qs(environ["QUERY_STRING"])
    form["REMOTE_MACS"] = __generate_remote_mac_list(environ)

    # REMOTE_ADDR isn't a required wsgi attribute so it may be naive to assume it's always present in this context.
    form["REMOTE_ADDR"] = environ.get("REMOTE_ADDR", None)

    # Read config for the XMLRPC port to connect to:
    with open("/etc/cobbler/settings.yaml", encoding="UTF-8") as main_settingsfile:
        ydata = yaml.safe_load(main_settingsfile)

    # Instantiate a CobblerWeb object
    http_api = CobblerSvc(server=f'http://127.0.0.1:{ydata.get("xmlrpc_port", 25151)}')

    # Check for a valid path/mode; handle invalid paths gracefully
    mode = form.get("op", "index")

    # TODO: We could do proper exception handling here and return
    # Corresponding HTTP status codes:

    status = "200 OK"
    # Execute corresponding operation on the CobblerSvc object:
    func = getattr(http_api, mode)
    try:
        content = func(**form)

        if content.find("# *** ERROR ***") != -1:
            status = "500 SERVER ERROR"
            print("possible cheetah template error")

        # TODO: Not sure these strings are the right ones to look for...
        elif (
            content.find("# profile not found") != -1
            or content.find("# system not found") != -1
            or content.find("# object not found") != -1
        ):
            print(f"content not found: {my_uri}")
            status = "404 NOT FOUND"
    except xmlrpc.client.Fault as err:
        status = "500 SERVER ERROR"
        content = err.faultString

    content = content.encode("utf-8")

    response_headers = [
        ("Content-type", "text/plain;charset=utf-8"),
        ("Content-Length", str(len(content))),
    ]
    start_response(status, response_headers)

    return [content]
