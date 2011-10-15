"""
Mod Python service functions for Cobbler's public interface
(aka cool stuff that works with wget)

based on code copyright 2007 Albert P. Tobey <tobert@gmail.com>
additions: 2007-2009 Michael DeHaan <mdehaan@redhat.com>
 
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

import exceptions
import xmlrpclib
import os
import traceback
import string
import sys
import time
import urlgrabber
import yaml # PyYAML

# the following imports are largely for the test code
import remote
import glob
import api as cobbler_api
import utils
import os
import os.path
import simplejson

class CobblerSvc(object):
    """
    Interesting mod python functions are all keyed off the parameter
    mode, which defaults to index.  All options are passed
    as parameters into the function.
    """
    def __init__(self, server=None, req=None):
        self.server = server
        self.remote = None
        self.req    = req

    def __xmlrpc_setup(self):
        """
        Sets up the connection to the Cobbler XMLRPC server. 
        This is the version that does not require logins.
        """
        if self.remote is None:
            self.remote = xmlrpclib.Server(self.server, allow_none=True)

    def index(self,**args):
        return "no mode specified"

    def debug(self,profile=None,**rest):
        # the purpose of this method could change at any time
        # and is intented for temporary test code only, don't rely on it
        self.__xmlrpc_setup()
        return self.remote.get_repos_compatible_with_profile(profile)

    def ks(self,profile=None,system=None,REMOTE_ADDR=None,REMOTE_MAC=None,**rest):
        """
        Generate kickstart files...
        """
        self.__xmlrpc_setup()
        data = self.remote.generate_kickstart(profile,system,REMOTE_ADDR,REMOTE_MAC)
        return u"%s" % data    

    def events(self,user="",**rest):
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

    def template(self,profile=None,system=None,path=None,**rest):
        """
        Generate a templated file for the system
        """
        self.__xmlrpc_setup()
        if path is not None:
            path = path.replace("_","/")
            path = path.replace("//","_")
        else:
            return "# must specify a template path"

        if profile is not None:
            data = self.remote.get_template_file_for_profile(profile,path)
        elif system is not None:
            data = self.remote.get_template_file_for_system(system,path)
        else:
            data = "# must specify profile or system name"
        return data

    def yum(self,profile=None,system=None,**rest):
        self.__xmlrpc_setup()
        if profile is not None:
            data = self.remote.get_repo_config_for_profile(profile)
        elif system is not None:
            data = self.remote.get_repo_config_for_system(system)
        else:
            data = "# must specify profile or system name"
        return data

    def trig(self,mode="?",profile=None,system=None,REMOTE_ADDR=None,**rest):
        """
        Hook to call install triggers.
        """
        self.__xmlrpc_setup()
        ip = REMOTE_ADDR
        if profile:
            rc = self.remote.run_install_triggers(mode,"profile",profile,ip)
        else:
            rc = self.remote.run_install_triggers(mode,"system",system,ip)
        return str(rc)

    def nopxe(self,system=None,**rest):
        self.__xmlrpc_setup()
        return str(self.remote.disable_netboot(system))

    def list(self,what="systems",**rest):
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
           buf = buf + "%s\n" % x["name"]
        return buf

    def autodetect(self,**rest):
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

    def look(self,**rest):
        # debug only
        return repr(rest)

    def findks(self,system=None,profile=None,**rest):
        self.__xmlrpc_setup()

        serverseg = self.server.replace("http://","")
        serverseg = self.server.replace("/cobbler_api","")

        name = "?"    
        type = "system"
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
            return urlgrabber.urlread(url)
        except:
            return "# kickstart retrieval failed (%s)" % url

    def puppet(self,hostname=None,**rest):
        self.__xmlrpc_setup()

        if hostname is None:
           return "hostname is required"
         
        results = self.remote.find_system_by_dns_name(hostname)

        classes = results.get("mgmt_classes", [])
        params = results.get("mgmt_parameters",{})

        newdata = {
           "classes"    : classes,
           "parameters" : params
        }
        
        return yaml.dump(newdata)

def __test_setup():

    # this contains some code from remote.py that has been modified
    # slightly to add in some extra parameters for these checks.
    # it can probably be combined into something like a test_utils
    # module later.

    api = cobbler_api.BootAPI()

    fake = open("/tmp/cobbler.fake","w+")
    fake.write("")
    fake.close()

    distro = api.new_distro()
    distro.set_name("distro0")
    distro.set_kernel("/tmp/cobbler.fake")
    distro.set_initrd("/tmp/cobbler.fake")
    api.add_distro(distro)

    repo = api.new_repo()
    repo.set_name("repo0")

    if not os.path.exists("/tmp/empty"):
       os.mkdir("/tmp/empty",770)
    repo.set_mirror("/tmp/empty")
    files = glob.glob("rpm-build/*.rpm")
    if len(files) == 0:
       raise Exception("Tests must be run from the cobbler checkout directory.")
    rc = utils.subprocess_call(None,"cp rpm-build/*.rpm /tmp/empty",shell=True)
    api.add_repo(repo)

    fd = open("/tmp/cobbler_t1","w+")
    fd.write("$profile_name")
    fd.close()

    fd = open("/tmp/cobbler_t2","w+")
    fd.write("$system_name")
    fd.close()

    profile = api.new_profile()
    profile.set_name("profile0")
    profile.set_distro("distro0")
    profile.set_kickstart("/var/lib/cobbler/kickstarts/sample.ks")
    profile.set_repos(["repo0"])
    profile.set_mgmt_classes(["alpha","beta"])
    profile.set_ksmeta({"tree":"look_for_this1","gamma":3})
    profile.set_template_files("/tmp/cobbler_t1=/tmp/t1-rendered")
    api.add_profile(profile)

    system = api.new_system()
    system.set_name("system0")
    system.set_hostname("hostname0")
    system.set_gateway("192.168.1.1")
    system.set_profile("profile0")
    system.set_dns_name("hostname0","eth0")
    system.set_ksmeta({"tree":"look_for_this2"})
    system.set_template_files({"/tmp/cobbler_t2":"/tmp/t2-rendered"})
    api.add_system(system)

    image = api.new_image()
    image.set_name("image0")
    image.set_file("/tmp/cobbler.fake")
    api.add_image(image)

    # perhaps an artifact of the test process?
    # FIXME: get path (at least webdir) from settings?
    if os.path.exists("/var/www/cobbler/repo_mirror/"):
        utils.os_system("rm -rf /var/www/cobbler/repo_mirror/repo0")
    elif os.path.exists("/srv/www/cobbler/repo_mirror/"):
        utils.os_system("rm -rf /srv/www/cobbler/repo_mirror/repo0")

    api.reposync(name="repo0")

def test_services_access():
    import remote
    remote._test_setup_settings(pxe_once=1)
    remote._test_bootstrap_restart()
    remote._test_remove_objects()
    __test_setup()
    time.sleep(5)
    api = cobbler_api.BootAPI()

    # test mod_python service URLs -- more to be added here

    templates = [ "sample.ks", "sample_end.ks", "legacy.ks" ]

    for template in templates:
        ks = "/var/lib/cobbler/kickstarts/%s" % template
        p = api.find_profile("profile0")
        assert p is not None
        p.set_kickstart(ks)
        api.add_profile(p)

        url = "http://127.0.0.1/cblr/svc/op/ks/profile/profile0"
        data = urlgrabber.urlread(url)
        assert data.find("look_for_this1") != -1

        url = "http://127.0.0.1/cblr/svc/op/ks/system/system0"
        data = urlgrabber.urlread(url)
        assert data.find("look_for_this2") != -1

    # see if we can pull up the yum configs
    url = "http://127.0.0.1/cblr/svc/op/yum/profile/profile0"
    data = urlgrabber.urlread(url)
    print "D1=%s" % data
    assert data.find("repo0") != -1
    
    url = "http://127.0.0.1/cblr/svc/op/yum/system/system0"
    data = urlgrabber.urlread(url)
    print "D2=%s" % data 
    assert data.find("repo0") != -1
  
    for a in [ "pre", "post" ]:
       filename = "/var/lib/cobbler/triggers/install/%s/unit_testing" % a
       fd = open(filename, "w+")
       fd.write("#!/bin/bash\n")
       fd.write("echo \"TESTING %s type ($1) name ($2) ip ($3)\" >> /var/log/cobbler/kicklog/cobbler_trigger_test\n" % a)
       fd.write("exit 0\n")
       fd.close()
       utils.os_system("chmod +x %s" % filename)

    urls = [
        "http://127.0.0.1/cblr/svc/op/trig/mode/pre/profile/profile0"
        "http://127.0.0.1/cblr/svc/op/trig/mode/post/profile/profile0"
        "http://127.0.0.1/cblr/svc/op/trig/mode/pre/system/system0"
        "http://127.0.0.1/cblr/svc/op/trig/mode/post/system/system0"
    ]
    for x in urls:
        print "reading: %s" % url
        data = urlgrabber.urlread(x)
        print "read: %s" % data        
        time.sleep(5) 
        assert os.path.exists("/var/log/cobbler/kicklog/cobbler_trigger_test")
        os.unlink("/var/log/cobbler/kicklog/cobbler_trigger_test")

    os.unlink("/var/lib/cobbler/triggers/install/pre/unit_testing")
    os.unlink("/var/lib/cobbler/triggers/install/post/unit_testing")

    # trigger testing complete

    # now let's test the nopxe URL (Boot loop prevention)

    sys = api.find_system("system0")
    sys.set_netboot_enabled(True)
    api.add_system(sys) # save the system to ensure it's set True

    url = "http://127.0.0.1/cblr/svc/op/nopxe/system/system0"
    data = urlgrabber.urlread(url)
    time.sleep(2)

    sys = api.find_system("system0")
    assert str(sys.netboot_enabled).lower() not in [ "1", "true", "yes" ]
    
    # now let's test the listing URLs since we document
    # them even know I don't know of anything relying on them.

    url = "http://127.0.0.1/cblr/svc/op/list/what/distros"
    assert urlgrabber.urlread(url).find("distro0") != -1

    url = "http://127.0.0.1/cblr/svc/op/list/what/profiles"
    assert urlgrabber.urlread(url).find("profile0") != -1

    url = "http://127.0.0.1/cblr/svc/op/list/what/systems"
    assert urlgrabber.urlread(url).find("system0") != -1

    url = "http://127.0.0.1/cblr/svc/op/list/what/repos"
    assert urlgrabber.urlread(url).find("repo0") != -1

    url = "http://127.0.0.1/cblr/svc/op/list/what/images"
    assert urlgrabber.urlread(url).find("image0") != -1

    # the following modes are implemented by external apps
    # and are not concerned part of cobbler's core, so testing
    # is less of a priority:
    #    autodetect
    #    findks
    # these features may be removed in a later release
    # of cobbler but really aren't hurting anything so there
    # is no pressing need.
  
    # now let's test the puppet external nodes support
    # and just see if we get valid YAML back without
    # doing much more

    url = "http://127.0.0.1/cblr/svc/op/puppet/hostname/hostname0"
    data = urlgrabber.urlread(url)
    assert data.find("alpha") != -1
    assert data.find("beta") != -1
    assert data.find("gamma") != -1
    assert data.find("3") != -1
    
    data = yaml.load(data)
    assert data.has_key("classes")
    assert data.has_key("parameters")
    
    # now let's test the template file serving
    # which is used by the snippet download_config_files
    # and also by koan's --update-files

    url = "http://127.0.0.1/cblr/svc/op/template/profile/profile0/path/_tmp_t1-rendered"
    data = urlgrabber.urlread(url)
    assert data.find("profile0") != -1
    assert data.find("$profile_name") == -1    

    url = "http://127.0.0.1/cblr/svc/op/template/system/system0/path/_tmp_t2-rendered"
    data = urlgrabber.urlread(url)
    assert data.find("system0") != -1
    assert data.find("$system_name") == -1

    os.unlink("/tmp/cobbler_t1")
    os.unlink("/tmp/cobbler_t2") 

    remote._test_remove_objects()

