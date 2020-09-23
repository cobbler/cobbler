"""
Mod Python service functions for Cobbler's public interface
(aka cool stuff that works with wget/curl)

based on code copyright 2007 Albert P. Tobey <tobert@gmail.com>
additions: 2007-2009 Michael DeHaan <michael.dehaan AT gmail>

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

from builtins import str
from builtins import object
import simplejson
import time
import xmlrpc.client
import yaml
from cobbler.cobbler_collections import manager
from cobbler import download_manager


class CobblerSvc(object):
    """
    Interesting mod python functions are all keyed off the parameter mode, which defaults to index. All options are
    passed as parameters into the function.
    """
    def __init__(self, server=None, req=None):
        """
        Default constructor which sets up everything to be ready.

        :param server: The domain to run at.
        :param req: This parameter is unused.
        """
        # ToDo: Remove req attribute.
        self.server = server
        self.remote = None
        self.req = req
        self.collection_mgr = manager.CollectionManager(self)
        self.logger = None
        self.dlmgr = download_manager.DownloadManager(self.collection_mgr, self.logger)

    def __xmlrpc_setup(self):
        """
        Sets up the connection to the Cobbler XMLRPC server. This is the version that does not require a login.
        """
        if self.remote is None:
            self.remote = xmlrpc.client.Server(self.server, allow_none=True)

    def index(self, **args):
        """
        Just a placeholder method as an entry point.

        :param args: This parameter is unused.
        :return: "no mode specified"
        :rtype: str
        """
        return "no mode specified"

    def debug(self, profile=None, **rest):
        # The purpose of this method could change at any time and is intented for temporary test code only, don't rely
        # on it.
        self.__xmlrpc_setup()
        return self.remote.get_repos_compatible_with_profile(profile)

    def autoinstall(self, profile=None, system=None, REMOTE_ADDR=None, REMOTE_MAC=None, **rest):
        """
        Generate automatic installation files.

        :param profile:
        :param system:
        :param REMOTE_ADDR:
        :param REMOTE_MAC:
        :param rest: This parameter is unused.
        :return:
        """
        self.__xmlrpc_setup()
        data = self.remote.generate_autoinstall(profile, system, REMOTE_ADDR, REMOTE_MAC)
        return "%s" % data

    def ks(self, profile=None, system=None, REMOTE_ADDR=None, REMOTE_MAC=None, **rest):
        """
        Generate automatic installation files. This is a legacy function for part backward compability to 2.6.6
        releases.

        :param profile:
        :param system:
        :param REMOTE_ADDR:
        :param REMOTE_MAC:
        :param rest: This parameter is unused.
        :return:
        """
        self.__xmlrpc_setup()
        data = self.remote.generate_autoinstall(profile, system, REMOTE_ADDR, REMOTE_MAC)
        return "%s" % data

    def gpxe(self, profile=None, system=None, mac=None, **rest):
        """
        Generate a gPXE config

        :param profile:
        :param system:
        :param mac:
        :param rest: This parameter is unused.
        :return:
        """
        self.__xmlrpc_setup()
        if not system and mac:
            query = {"mac_address": mac}
            if profile:
                query["profile"] = profile
            found = self.remote.find_system(query)
            if found:
                system = found[0]

        data = self.remote.generate_gpxe(profile, system)
        return "%s" % data

    def bootcfg(self, profile=None, system=None, **rest):
        """
        Generate a boot.cfg config file. Used primarily for VMware ESXi.

        :param profile:
        :param system:
        :param rest: This parameter is unused.
        :return:
        """
        self.__xmlrpc_setup()
        data = self.remote.generate_bootcfg(profile, system)
        return "%s" % data

    def script(self, profile=None, system=None, **rest):
        """
        Generate a script based on snippets. Useful for post or late-action scripts where it's difficult to embed the
        script in the response file.

        :param profile: The profile to generate the script for.
        :param system: The system to generate the script for.
        :param rest: This may contain a parameter with the key "query_string" which has a key "script" which may be an
                     array. The element from position zero is taken.
        :return: The generated script.
        :rtype: str
        """
        self.__xmlrpc_setup()
        data = self.remote.generate_script(profile, system, rest['query_string']['script'][0])
        return "%s" % data

    def events(self, user="", **rest):
        """
        If no user is given then all events are returned. Otherwise only event associated to a user are returned.

        :param user: Filter the events for a given user.
        :param rest: This parameter is unused.
        :return: A JSON object which contains all events.
        :rtype: str
        """
        self.__xmlrpc_setup()
        if user == "":
            data = self.remote.get_events("")
        else:
            data = self.remote.get_events(user)

        # sort it... it looks like { timestamp : [ array of details ] }
        keylist = list(data.keys())
        keylist.sort()
        results = []
        for k in keylist:
            etime = int(data[k][0])
            nowtime = time.time()
            if ((nowtime - etime) < 30):
                results.append([k, data[k][0], data[k][1], data[k][2]])
        return simplejson.dumps(results)

    def template(self, profile=None, system=None, path=None, **rest):
        """
        Generate a templated file for the system. Either specify a profile OR a system.

        :param profile: The profile to provide for the generation of the template.
        :param system: The system to provide for the generation of the template.
        :param path: The path to the template.
        :param rest: This parameter is unused.
        :return: The rendered template.
        :rtype: str
        """
        self.__xmlrpc_setup()
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
        return data

    def yum(self, profile=None, system=None, **rest):
        """
        Generate a repo config. Either specify a profile OR a system.

        :param profile: The profile to provide for the generation of the template.
        :param system: The system to provide for the generation of the template.
        :param rest: This parameter is unused.
        :return: The generated repository config.
        :rtype: str
        """
        self.__xmlrpc_setup()
        if profile is not None:
            data = self.remote.get_repo_config_for_profile(profile)
        elif system is not None:
            data = self.remote.get_repo_config_for_system(system)
        else:
            data = "# must specify profile or system name"
        return data

    def trig(self, mode="?", profile=None, system=None, REMOTE_ADDR=None, **rest):
        """
        Hook to call install triggers. Only valid for a profile OR a system.

        :param mode: Can be "pre", "post" or "firstboot". Everything else is invalid.
        :type mode: str
        :param profile: The profile object to run triggers for.
        :param system: The system object to run triggers for.
        :param REMOTE_ADDR: The ip if the remote system/profile.
        :param rest: This parameter is unused.
        :return: The return code of the action.
        :rtype: str
        """
        self.__xmlrpc_setup()
        ip = REMOTE_ADDR
        if profile:
            rc = self.remote.run_install_triggers(mode, "profile", profile, ip)
        else:
            rc = self.remote.run_install_triggers(mode, "system", system, ip)
        return str(rc)

    def nopxe(self, system=None, **rest):
        """
        Disables the network boot for the given system.

        :param system: The system to disable netboot for.
        :param rest: This parameter is unused.
        :return: A boolean status if the action succeed or not.
        :rtype: str
        """
        self.__xmlrpc_setup()
        return str(self.remote.disable_netboot(system))

    def list(self, what="systems", **rest):
        """
        Return a list of objects of a desired category. Defaults to "systems".

        :param what: May be "systems", "profiles", "distros", "images", "repos", "mgmtclasses", "packages" or "files"
        :param rest: This parameter is unused.
        :return: The list of object names.
        :rtype: str
        """
        self.__xmlrpc_setup()
        buf = ""
        if what == "systems":
            listing = self.remote.get_systems()
        elif what == "profiles":
            listing = self.remote.get_profiles()
        elif what == "distros":
            listing = self.remote.get_distros()
        elif what == "images":
            listing = self.remote.get_images()
        elif what == "repos":
            listing = self.remote.get_repos()
        elif what == "mgmtclasses":
            listing = self.remote.get_mgmtclasses()
        elif what == "packages":
            listing = self.remote.get_packages()
        elif what == "files":
            listing = self.remote.get_files()
        else:
            return "?"
        for x in listing:
            buf += "%s\n" % x["name"]
        return buf

    def autodetect(self, **rest):
        """
        This tries to autodect the system with the given information. If more than one candidate is found an error
        message is returned.

        :param rest: The keys "REMOTE_MACS", "REMOTE_ADDR" or "interfaces".
        :return: The name of the possible object or an error message.
        :rtype: str
        """
        self.__xmlrpc_setup()
        systems = self.remote.get_systems()

        # If kssendmac was in the kernel options line, see if a system can be found matching the MAC address. This is
        # more specific than an IP match.

        macinput = [mac.split(' ').lower() for mac in rest["REMOTE_MACS"]]

        ip = rest["REMOTE_ADDR"]

        candidates = []

        for x in systems:
            for y in x["interfaces"]:
                if x["interfaces"][y]["mac_address"].lower() in macinput:
                    candidates.append(x)

        if len(candidates) == 0:
            for x in systems:
                for y in x["interfaces"]:
                    if x["interfaces"][y]["ip_address"] == ip:
                        candidates.append(x)

        if len(candidates) == 0:
            return "FAILED: no match (%s,%s)" % (ip, macinput)
        elif len(candidates) > 1:
            return "FAILED: multiple matches"
        elif len(candidates) == 1:
            return candidates[0]["name"]

    def look(self, **rest):
        """
        Debug only: Show the handed dict via repr to the requester.
        :param rest: The dict to represent.
        :return: The dict reformated with repr()
        :rtype; str
        """

        return repr(rest)

    def find_autoinstall(self, system=None, profile=None, **rest):
        """
        Find an autoinstallation for a system or a profile. If this is not known different parameters can be passed to
        rest to find it automatically. See "autodetect".

        :param system: The system to find the autoinstallation for,
        :param profile: The profile to find the autoinstallation for.
        :param rest: The metadata to find the autoinstallation automatically.
        :return: The autoinstall script or error message.
        """
        self.__xmlrpc_setup()

        serverseg = "http://%s" % self.collection_mgr._settings.server

        name = "?"
        if system is not None:
            url = "%s/cblr/svc/op/autoinstall/system/%s" % (serverseg, name)
        elif profile is not None:
            url = "%s/cblr/svc/op/autoinstall/profile/%s" % (serverseg, name)
        else:
            name = self.autodetect(**rest)
            if name.startswith("FAILED"):
                return "# autodetection %s" % name
            url = "%s/cblr/svc/op/autoinstall/system/%s" % (serverseg, name)

        try:
            return self.dlmgr.urlread(url)
        except:
            return "# automatic installation file retrieval failed (%s)" % url

    def findks(self, system=None, profile=None, **rest):
        """
        This is a legacy function which enabled Cobbler partly to be backward compatible to 2.6.6 releases.

        It should be only be used if you must. Please use find_autoinstall if possible!
        :param system: If you wish to find a system please set this parameter to not null. Hand over the name of it.
        :param profile: If you wish to find a system please set this parameter to not null. Hand over the name of it.
        :param rest: If you wish you can try to let Cobbler autodetect the system with the MAC address.
        :return: Returns the autoinstall/kickstart profile.
        """
        self.__xmlrpc_setup()

        serverseg = "http://%s" % self.collection_mgr._settings.server

        name = "?"
        if system is not None:
            url = "%s/cblr/svc/op/ks/system/%s" % (serverseg, name)
        elif profile is not None:
            url = "%s/cblr/svc/op/ks/profile/%s" % (serverseg, name)
        else:
            name = self.autodetect(**rest)
            if name.startswith("FAILED"):
                return "# autodetection %s" % name
            url = "%s/cblr/svc/op/ks/system/%s" % (serverseg, name)

        try:
            return self.dlmgr.urlread(url)
        except:
            return "# kickstart retrieval failed (%s)" % url

    def puppet(self, hostname=None, **rest):
        """
        Dump the puppet data which is available for Cobbler.

        :param hostname: The hostname for the system which should the puppet data be dumped for.
        :param rest: This parameter is unused.
        :return: The yaml for the host.
        :rtype: str
        """
        self.__xmlrpc_setup()

        if hostname is None:
            return "hostname is required"

        settings = self.remote.get_settings()
        results = self.remote.find_system_by_dns_name(hostname)

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
