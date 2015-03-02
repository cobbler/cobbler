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

import simplejson
import time
import urlgrabber
import xmlrpclib
import yaml
import collection_manager


class CobblerSvc(object):
    """
    Interesting mod python functions are all keyed off the parameter
    mode, which defaults to index.  All options are passed
    as parameters into the function.
    """
    def __init__(self, server=None, req=None):
        self.server = server
        self.remote = None
        self.req = req
        self.collection_mgr = collection_manager.CollectionManager(self)

    def __xmlrpc_setup(self):
        """
        Sets up the connection to the Cobbler XMLRPC server.
        This is the version that does not require logins.
        """
        if self.remote is None:
            self.remote = xmlrpclib.Server(self.server, allow_none=True)

    def index(self, **args):
        return "no mode specified"

    def debug(self, profile=None, **rest):
        # the purpose of this method could change at any time
        # and is intented for temporary test code only, don't rely on it
        self.__xmlrpc_setup()
        return self.remote.get_repos_compatible_with_profile(profile)

    def autoinstall(self, profile=None, system=None, REMOTE_ADDR=None, REMOTE_MAC=None, **rest):
        """
        Generate automatic installation files
        """
        self.__xmlrpc_setup()
        data = self.remote.generate_autoinstall(profile, system, REMOTE_ADDR, REMOTE_MAC)
        return u"%s" % data

    def gpxe(self, profile=None, system=None, mac=None, **rest):
        """
        Generate a gPXE config
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
        return u"%s" % data

    def bootcfg(self, profile=None, system=None, **rest):
        """
        Generate a boot.cfg config file. Used primarily
        for VMware ESXi.
        """
        self.__xmlrpc_setup()
        data = self.remote.generate_bootcfg(profile, system)
        return u"%s" % data

    def script(self, profile=None, system=None, **rest):
        """
        Generate a script based on snippets. Useful for post
        or late-action scripts where it's difficult to embed
        the script in the response file.
        """
        self.__xmlrpc_setup()
        data = self.remote.generate_script(profile, system, rest['query_string']['script'][0])
        return u"%s" % data

    def events(self, user="", **rest):
        self.__xmlrpc_setup()
        if user == "":
            data = self.remote.get_events("")
        else:
            data = self.remote.get_events(user)

        # sort it... it looks like { timestamp : [ array of details ] }
        keylist = data.keys()
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
        Generate a templated file for the system
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
        Hook to call install triggers.
        """
        self.__xmlrpc_setup()
        ip = REMOTE_ADDR
        if profile:
            rc = self.remote.run_install_triggers(mode, "profile", profile, ip)
        else:
            rc = self.remote.run_install_triggers(mode, "system", system, ip)
        return str(rc)

    def nopxe(self, system=None, **rest):
        self.__xmlrpc_setup()
        return str(self.remote.disable_netboot(system))

    def list(self, what="systems", **rest):
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
        self.__xmlrpc_setup()
        systems = self.remote.get_systems()

        # if kssendmac was in the kernel options line, see
        # if a system can be found matching the MAC address.  This
        # is more specific than an IP match.

        macinput = rest["REMOTE_MAC"]
        if macinput is not None:
            # FIXME: will not key off other NICs, problem?
            mac = macinput.split()[1].strip()
        else:
            mac = "None"

        ip = rest["REMOTE_ADDR"]

        candidates = []

        for x in systems:
            for y in x["interfaces"]:
                if x["interfaces"][y]["mac_address"].lower() == mac.lower():
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
        # debug only
        return repr(rest)

    def find_autoinstall(self, system=None, profile=None, **rest):
        self.__xmlrpc_setup()

        serverseg = "http//%s" % self.collection_mgr._settings.server

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
            return urlgrabber.urlread(url)
        except:
            return "# automatic installation file retrieval failed (%s)" % url

    def puppet(self, hostname=None, **rest):
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
            for ckey in classes.keys():
                tmp = {}
                class_name = classes[ckey].get("class_name", "")
                if class_name in (None, ""):
                    class_name = ckey
                if classes[ckey].get("is_definition", False):
                    def_tmp = {}
                    def_name = classes[ckey]["params"].get("name", "")
                    del classes[ckey]["params"]["name"]
                    if def_name != "":
                        for pkey in classes[ckey]["params"].keys():
                            def_tmp[pkey] = classes[ckey]["params"][pkey]
                        tmp["instances"] = {def_name: def_tmp}
                    else:
                        # FIXME: log an error here?
                        # skip silently...
                        continue
                else:
                    for pkey in classes[ckey]["params"].keys():
                        tmp[pkey] = classes[ckey]["params"][pkey]
                del classes[ckey]
                classes[class_name] = tmp
        else:
            classes = classes.keys()

        return yaml.dump(data, default_flow_style=False)
