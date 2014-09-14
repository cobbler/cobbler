import logging
import os
import random
import re
import sys
import time
import unittest
import xmlrpclib

from cobbler.remote import EVENT_COMPLETE
from cobbler.utils import local_get_cobbler_api_url, get_shared_secret

FAKE_INITRD="initrd1.img"
FAKE_INITRD2="initrd2.img"
FAKE_INITRD3="initrd3.img"
FAKE_KERNEL="vmlinuz1"
FAKE_KERNEL2="vmlinuz2"
FAKE_KERNEL3="vmlinuz3"
TEST_POWER_MANAGEMENT = True
TEST_SYSTEM = ""
cleanup_dirs = []

def tprint(call_name):
    """
    Print a remote call debug message

    @param str call_name remote call name
    """

    print("test remote call: %s()" % call_name)

# TODO: test remote.background_aclsetup()
# TODO: test remote.background_buildiso()
# TODO: test remote.background_dlcontent()
# TODO: test remote.background_hardlink()
# TODO: test remote.background_import()
# TODO: test remote.background_replicate()
# TODO: test remote.background_reposync()
# TODO: test remote.background_validateks()
# TODO: test remote.clear_system_logs()
# TODO: test remote.disable_netboot()
# TODO: test remote.extended_version()
# TODO: test remote.find_items_paged()
# TODO: test remote.find_system_by_dns_name()
# TODO: test remote.generatescript()
# TODO: test remote.get_<item>_as_rendered()
# TODO: test remote.get_<item>s_since()
# TODO: test remote.get_authn_module_name()
# TODO: test remote.get_blended_data()
# TODO: test remote.get_config_dataa()
# TODO: test remote.get_repos_compatible_with_profile()
# TODO: test remote.get_status()
# TODO: test remote.get_template_file_for_profile()
# TODO: test remote.get_template_file_for_system()
# TODO: test remote.is_kickstart_in_use()
# TODO: test remote.logout()
# TODO: test remote.modify_setting()
# TODO: test remote.read_or_write_kickstart_template()
# TODO: test remote.read_or_write_snippet()
# TODO: test remote.run_install_triggers()
# TODO: test remote.version()
# TODO: test remote.xapi_object_edit()


class CobblerXmlRpcTest(unittest.TestCase):

    def setUp(self):
        """
        Setup Cobbler XML-RPC connection and login
        """

        # create logger
        logging.basicConfig( stream=sys.stderr )
        self.logger = logging.getLogger( self.__class__.__name__ )
        self.logger.setLevel( logging.DEBUG )

        # create XML-RPC client and connect to server
        api_url = local_get_cobbler_api_url()
        self.remote = xmlrpclib.Server(api_url, allow_none=True)
        shared_secret = get_shared_secret()
        self.token  = self.remote.login("", shared_secret)
        if not self.token:
            sys.exit(1)

    def tearDown(self):
        """
        Cleanup here
        """
        return


class Test_DistroProfileSystem(CobblerXmlRpcTest):
    """
    Test remote calls related to distros, profiles and systems
    These item types are tested together because they have inter-dependencies
    """

    def setUp(self):

        super(Test_DistroProfileSystem, self).setUp()

        # Create temp dir
        self.topdir = "/tmp/cobbler_test"
        try:
            os.makedirs(self.topdir)
        except:
            pass

        # create temp files
        self.fk_initrd = os.path.join(self.topdir,  FAKE_INITRD)
        self.fk_initrd2 = os.path.join(self.topdir, FAKE_INITRD2)
        self.fk_initrd3 = os.path.join(self.topdir, FAKE_INITRD3)
        self.fk_kernel = os.path.join(self.topdir,  FAKE_KERNEL)
        self.fk_kernel2 = os.path.join(self.topdir, FAKE_KERNEL2)
        self.fk_kernel3 = os.path.join(self.topdir, FAKE_KERNEL3)
        self.redhat_kickstart = os.path.join(self.topdir, "test.ks")
        self.suse_autoyast = os.path.join(self.topdir, "test.xml")
        self.ubuntu_preseed = os.path.join(self.topdir, "test.seed")
        self.files_create = [
            self.fk_initrd, self.fk_initrd2, self.fk_initrd3,
            self.fk_kernel, self.fk_kernel2, self.fk_kernel3,
            self.redhat_kickstart, self.suse_autoyast, self.ubuntu_preseed
        ]
        for fn in self.files_create:
            f = open(fn,"w+")
            f.close()

        self.distro_fields = [
          # field format: field_name, good value(s), bad value(s)
          # field order is the order in which they will be set
          # TODO: include fields with dependencies: fetchable files, boot files, etc.
          ["arch",["i386","x86_64","ppc","ppc64"],["badarch"]],
          # generic must be last breed to be set so os_version test below will work
          ["breed",["debian","freebsd","redhat","suse","ubuntu","unix","vmware","windows","xen", "generic"],["badbreed"]],
          ["comment",["test comment",],[]],
          ["initrd",[self.fk_initrd,],["",]],
          ["name",["testdistro0"],[]],
          ["kernel",[self.fk_kernel,],["",]],
          ["kernel_options",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
          ["kernel_options_post",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
          ["ks_meta",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
          ["mgmt_classes",["one two three",],[]],
          ["os_version",["generic26",],["bados",]],
          ["owners",["user1 user2 user3",],[]],
        ]

        self.profile_fields = [
          # field format: field_name, good value(s), bad value(s)
          # TODO: include fields with dependencies: fetchable files, boot files,
          #         template files, repos
          ["comment",["test comment"],[]],
          ["dhcp_tag",["","foo"],[]],
          ["distro",["testdistro0"],["baddistro",]],
          ["enable_gpxe",["yes","YES","1","0","no"],[]],
          ["enable_menu",["yes","YES","1","0","no"],[]],
          ["kernel_options",["a=1 b=2 c=3 c=4 c=5 d e"],[]],
          ["kernel_options_post",["a=1 b=2 c=3 c=4 c=5 d e"],[]],
          ["kickstart",[self.redhat_kickstart,self.suse_autoyast,self.ubuntu_preseed],["/path/to/bad/kickstart",]],
          ["ks_meta",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
          ["mgmt_classes",["one two three",],[]],
          ["mgmt_parameters",["<<inherit>>"],["badyaml"]], # needs more test cases that are valid yaml
          ["name",["testprofile0"],[]],
          ["name_servers",["1.1.1.1 1.1.1.2 1.1.1.3"],[]],
          ["name_servers_search",["example.com foo.bar.com"],[]],
          ["owners",["user1 user2 user3"],[]],
          ["proxy",["testproxy"],[]],
          ["server",["1.1.1.1"],[]],
          ["virt_auto_boot",["1","0"],["yes","no"]],
          ["virt_bridge",["<<inherit>>","br0","virbr0","xenbr0"],[]],
          ["virt_cpus",["<<inherit>>","1","2"],["a"]],
          ["virt_disk_driver",["<<inherit>>","raw","qcow2","vmdk"],[]],
          ["virt_file_size",["<<inherit>>","5","10"],["a"]],
          ["virt_path",["<<inherit>>","/path/to/test",],[]],
          ["virt_ram",["<<inherit>>","256","1024"],["a",]],
          ["virt_type",["<<inherit>>","xenpv","xenfv","qemu","kvm","vmware","openvz"],["bad",]],
        ]

        self.system_fields = [
          # field format: field_name, good value(s), bad value(s)
          # TODO: include fields with dependencies: fetchable files, boot files,
          #         template files, images
          ["comment",["test comment"],[]],
          ["enable_gpxe",["yes","YES","1","0","no"],[]],
          ["kernel_options",["a=1 b=2 c=3 c=4 c=5 d e"],[]],
          ["kernel_options_post",["a=1 b=2 c=3 c=4 c=5 d e"],[]],
          ["kickstart",[self.redhat_kickstart,self.suse_autoyast,self.ubuntu_preseed],["/path/to/bad/kickstart",]],
          ["ks_meta",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
          ["mgmt_classes",["one two three",],[]],
          ["mgmt_parameters",["<<inherit>>"],["badyaml"]], # needs more test cases that are valid yaml
          ["name",["testsystem0"],[]],
          ["netboot_enabled",["yes","YES","1","0","no"],[]],
          ["owners",["user1 user2 user3"],[]],
          ["profile",["testprofile0"],["badprofile",]],
          ["repos_enabled", [], []],
          ["status",["development","testing","acceptance","production"],[]],
          ["proxy",["testproxy"],[]],
          ["server",["1.1.1.1"],[]],
          ["virt_auto_boot",["1","0"],["yes","no"]],
          ["virt_cpus",["<<inherit>>","1","2"],["a"]],
          ["virt_file_size",["<<inherit>>","5","10"],["a"]],
          ["virt_disk_driver",["<<inherit>>","raw","qcow2","vmdk"],[]],
          ["virt_ram",["<<inherit>>","256","1024"],["a",]],
          ["virt_type",["<<inherit>>","xenpv","xenfv","qemu","kvm","vmware","openvz"],["bad",]],
          ["virt_path",["<<inherit>>","/path/to/test",],[]],
          ["virt_pxe_boot",["1", "0"],[]],

          # network
          ["gateway", [], []],
          ["hostname", ["test"], []],
          ["ipv6_autoconfiguration", [], []],
          ["ipv6_default_device", [], []],
          ["name_servers", ["9.1.1.3"], []],
          ["name_servers_search", [], []],

          # network - network interface specific
          # TODO: test these fields
          ["bonding_opts-eth0", [], []],
          ["bridge_opts-eth0", [], []],
          ["cnames-eth0", [], []],
          ["dhcp_tag-eth0", [], []],
          ["dns_name-eth0", [], []],
          ["if_gateway-eth0", [], []],
          ["interface_type-eth0", [], []],
          ["interface_master-eth0", [], []],
          ["ip_address-eth0", [], []],
          ["ipv6_address-eth0", [], []],
          ["ipv6_secondaries-eth0", [], []],
          ["ipv6_mtu-eth0", [], []],
          ["ipv6_static_routes-eth0", [], []],
          ["ipv6_default_gateway-eth0", [], []],
          ["mac_address-eth0", [], []],
          ["mtu-eth0", [], []],
          ["management-eth0", [], []],
          ["netmask-eth0", [], []],
          ["static-eth0", [], []],
          ["static_routes-eth0", [], []],
          ["virt_bridge-eth0", [], []],

          # power management
          ["power_type", ["lpar"], ["bla"]],
          ["power_address", ["127.0.0.1"], []],
          ["power_id", ["pmachine:lpar1"], []],
          ["power_pass", ["pass"], []],
          ["power_user", ["user"], []]

        ]

    def tearDown(self):

        super(Test_DistroProfileSystem, self).tearDown()

        for fn in self.files_create:
            os.remove(fn)

    def _get_distros(self):
        """
        Test: get distros
        """

        tprint("get_distros")
        self.remote.get_distros(self.token)

    def _get_profiles(self):
        """
        Test: get profiles
        """

        tprint("get_profiles")
        self.remote.get_profiles(self.token)

    def _get_systems(self):
        """
        Test: get systems
        """

        tprint("get_systems")
        self.remote.get_systems(self.token)

    def _create_distro(self):
        """
        Test: create/edit a distro
        """

        distros = self.remote.get_distros(self.token)

        tprint("new_distro")
        distro = self.remote.new_distro(self.token)

        tprint("modify_distro")
        for field in self.distro_fields:
            (fname, fgood, fbad) = field
            for fb in fbad:
                 try:
                     self.remote.modify_distro(distro, fname, fb, self.token)
                 except:
                     pass
                 else:
                     self.fail("bad field (%s=%s) did not raise an exception" % (fname,fb))
            for fg in fgood:
                 try:
                     result = self.remote.modify_distro(distro, fname, fg, self.token)
                     self.assertTrue(result)
                 except Exception as e:
                     self.fail("good field (%s=%s) raised exception: %s" % (fname,fg, str(e)))

        tprint("save_distro")
        self.assertTrue(self.remote.save_distro(distro, self.token))

        # FIXME: if field in item_<type>.FIELDS defines possible values,
        # test all of them. This is valid for all item types
        # for field in item_system.FIELDS:
        #    (fname,def1,def2,display,editable,tooltip,values,type) = field
        #    if fname not in ["name","distro","parent"] and editable:
        #        if values and isinstance(values,list):
        #            fvalue = random.choice(values)
        #        else:
        #             fvalue = "testing_" + fname
        #        self.assertTrue(self.remote.modify_profile(subprofile,fname,fvalue,self.token))

        new_distros = self.remote.get_distros(self.token)
        self.assertTrue(len(new_distros) == len(distros) + 1)

    def _create_profile(self):
        """
        Test: create/edit a profile object"""

        profiles = self.remote.get_profiles(self.token)

        tprint("new_profile")
        profile = self.remote.new_profile(self.token)

        tprint("modify_profile")
        for field in self.profile_fields:
            (fname,fgood,fbad) = field
            for fb in fbad:
                 try:
                     self.remote.modify_profile(profile,fname,fb,self.token)
                 except:
                     pass
                 else:
                     self.fail("bad field (%s=%s) did not raise an exception" % (fname,fb))
            for fg in fgood:
                 try:
                     self.assertTrue(self.remote.modify_profile(profile,fname,fg,self.token))
                 except Exception as e:
                     self.fail("good field (%s=%s) raised exception: %s" % (fname,fg, str(e)))

        tprint("save_profile")
        self.assertTrue(self.remote.save_profile(profile,self.token))

        new_profiles = self.remote.get_profiles(self.token)
        self.assertTrue(len(new_profiles) == len(profiles) + 1)

    def _create_subprofile(self):
        """
        Test: create/edit a subprofile object"""

        profiles = self.remote.get_profiles(self.token)

        tprint("new_subprofile")
        subprofile = self.remote.new_subprofile(self.token)

        tprint("modify_profile")
        self.assertTrue(self.remote.modify_profile(subprofile,"name","testsubprofile0",self.token))
        self.assertTrue(self.remote.modify_profile(subprofile,"parent","testprofile0",self.token))

        tprint("save_profile")
        self.assertTrue(self.remote.save_profile(subprofile,self.token))

        new_profiles = self.remote.get_profiles(self.token)
        self.assertTrue(len(new_profiles) == len(profiles) + 1)

    def _create_system(self):
        """
        Test: create/edit a system object
        """

        systems = self.remote.get_systems(self.token)

        tprint("new_system")
        system = self.remote.new_system(self.token)

        tprint("modify_system")
        self.assertTrue(self.remote.modify_system(system,"name","testsystem0",self.token))
        self.assertTrue(self.remote.modify_system(system,"profile","testprofile0",self.token))
        for field in self.system_fields:
            (fname,fgood,fbad) = field
            for fb in fbad:
                 try:
                     self.remote.modify_system(system,fname,fb,self.token)
                 except:
                     pass
                 else:
                     self.fail("bad field (%s=%s) did not raise an exception" % (fname,fb))
            for fg in fgood:
                 try:
                     self.assertTrue(self.remote.modify_system(system,fname,fg,self.token))
                 except Exception as e:
                     self.fail("good field (%s=%s) raised exception: %s" % (fname,fg, str(e)))

        tprint("save_system")
        self.assertTrue(self.remote.save_system(system,self.token))

        new_systems = self.remote.get_systems(self.token)
        self.assertTrue(len(new_systems) == len(systems) + 1)

    def _get_distro(self):
        """
        Test: get a distro object"""

        tprint("get_distro")
        distro = self.remote.get_distro("testdistro0")

    def _get_profile(self):
        """
        Test: get a profile object"""

        tprint("get_profile")
        profile = self.remote.get_profile("testprofile0")

    def _get_system(self):
        """
        Test: get a system object"""

        tprint("get_system")
        system = self.remote.get_system("testsystem0")

    def _find_distro(self):
        """
        Test: find a distro object
        """

        tprint("find_distro")
        result = self.remote.find_distro({"name":"testdistro0"}, self.token)
        self.assertTrue(result)

    def _find_profile(self):
        """
        Test: find a profile object
        """

        tprint("find_profile")
        result = self.remote.find_profile({"name":"testprofile0"}, self.token)
        self.assertTrue(result)

    def _find_system(self):
        """
        Test: find a system object
        """

        tprint("find_system")
        result = self.remote.find_system({"name":"testsystem0"}, self.token)
        self.assertTrue(result)

    def _copy_distro(self):
        """
        Test: copy a distro object
        """

        tprint("copy_distro")
        distro = self.remote.get_item_handle("distro","testdistro0",self.token)
        self.assertTrue(self.remote.copy_distro(distro,"testdistrocopy",self.token))

    def _copy_profile(self):
        """
        Test: copy a profile object
        """

        tprint("copy_profile")
        profile = self.remote.get_item_handle("profile","testprofile0",self.token)
        self.assertTrue(self.remote.copy_profile(profile,"testprofilecopy",self.token))

    def _copy_system(self):
        """
        Test: copy a system object
        """

        tprint("copy_system")
        system = self.remote.get_item_handle("system","testsystem0",self.token)
        self.assertTrue(self.remote.copy_system(system,"testsystemcopy",self.token))

    def _rename_distro(self):
        """
        Test: rename a distro object
        """

        tprint("rename_distro")
        distro = self.remote.get_item_handle("distro","testdistrocopy",self.token)
        self.assertTrue(self.remote.rename_distro(distro,"testdistro1",self.token))

    def _rename_profile(self):
        """
        Test: rename a profile object
        """

        tprint("rename_profile")
        profile = self.remote.get_item_handle("profile","testprofilecopy",self.token)
        self.assertTrue(self.remote.rename_profile(profile,"testprofile1",self.token))

    def _rename_system(self):
        """
        Test: rename a system object
        """

        tprint("rename_system")
        system = self.remote.get_item_handle("system","testsystemcopy",self.token)
        self.assertTrue(self.remote.rename_system(system,"testsystem1",self.token))

    def _remove_distro(self):
        """
        Test: remove a distro object
        """

        tprint("remove_distro")
        self.assertTrue(self.remote.remove_distro("testdistro0",self.token))
        self.assertTrue(self.remote.remove_distro("testdistro1",self.token))

    def _remove_profile(self):
        """
        Test: remove a profile object
        """

        tprint("remove_profile")
        self.assertTrue(self.remote.remove_profile("testsubprofile0",self.token))
        self.assertTrue(self.remote.remove_profile("testprofile0",self.token))
        self.assertTrue(self.remote.remove_profile("testprofile1",self.token))

    def _remove_system(self):
        """
        Test: remove a system object
        """

        tprint("remove_system")
        self.assertTrue(self.remote.remove_system("testsystem0",self.token))
        self.assertTrue(self.remote.remove_system("testsystem1",self.token))

    def _get_repo_config_for_profile(self):
        """
        Test: get repository configuration of a profile
        """

        self.remote.get_repo_config_for_profile("testprofile0")

    def _get_repo_config_for_system(self):
        """
        Test: get repository configuration of a system
        """

        self.remote.get_repo_config_for_system("testprofile0")

    def test_distro_profile_system(self):
        """
        Test remote calls related to distro, profile and system
        """

        self._get_distros()
        self._create_distro()
        self._get_distro()
        self._find_distro()
        self._copy_distro()
        self._rename_distro()

        self._get_profiles()
        self._create_profile()
        self._create_subprofile()
        self._get_profile()
        self._find_profile()
        self._copy_profile()
        self._rename_profile()
        self._get_repo_config_for_profile()

        self._get_systems()
        self._create_system()
        self._get_system()
        self._find_system()
        self._copy_system()
        self._rename_system()
        self._get_repo_config_for_system()

        self._remove_system()
        self._remove_profile()
        self._remove_distro()

class Test_Repo(CobblerXmlRpcTest):

    def _create_repo(self):
        """
        Test: create/edit a repo object
        """

        repos = self.remote.get_repos(self.token)

        tprint("new_repo")
        repo = self.remote.new_repo(self.token)

        tprint("modify_repo")
        self.assertTrue(self.remote.modify_repo(repo, "name", "testrepo0", self.token))
        self.assertTrue(self.remote.modify_repo(repo, "mirror", "http://www.sample.com/path/to/some/repo", self.token))
        self.assertTrue(self.remote.modify_repo(repo, "mirror_locally", "0", self.token))

        tprint("save_repo")
        self.assertTrue(self.remote.save_repo(repo, self.token))

        new_repos = self.remote.get_repos(self.token)
        self.assertTrue(len(new_repos) == len(repos) + 1)

    def _get_repos(self):
        """
        Test: Get repos
        """

        tprint("get_repos")
        self.remote.get_repos()

    def _get_repo(self):
        """
        Test: Get a repo object
        """

        tprint("get_repo")
        repo = self.remote.get_repo("testrepo0")

    def _find_repo(self):
        """
        Test: find a repo object
        """

        tprint("find_repo")
        result = self.remote.find_repo({"name":"testrepo0"}, self.token)
        self.assertTrue(result)

    def _copy_repo(self):
        """
        Test: copy a repo object
        """

        tprint("copy_repo")
        repo = self.remote.get_item_handle("repo","testrepo0",self.token)
        self.assertTrue(self.remote.copy_repo(repo,"testrepocopy",self.token))

    def _rename_repo(self):
        """
        Test: rename a repo object
        """

        tprint("rename_repo")
        repo = self.remote.get_item_handle("repo","testrepocopy",self.token)
        self.assertTrue(self.remote.rename_repo(repo,"testrepo1",self.token))

    def _remove_repo(self):
        """
        Test: remove a repo object
        """

        tprint("remove_repo")
        self.assertTrue(self.remote.remove_repo("testrepo0",self.token))
        self.assertTrue(self.remote.remove_repo("testrepo1",self.token))

    def test_repo(self):

        self._get_repos()
        self._create_repo()
        self._get_repo()
        self._find_repo()
        self._copy_repo()
        self._rename_repo()
        self._remove_repo()

class Test_MgmtClass(CobblerXmlRpcTest):

    def _create_mgmtclass(self):
        """
        Test: create/edit a mgmtclass object
        """

        mgmtclasses = self.remote.get_mgmtclasses(self.token)

        tprint("new_mgmtclass")
        mgmtclass = self.remote.new_mgmtclass(self.token)

        tprint("modify_mgmtclass")
        self.assertTrue(self.remote.modify_mgmtclass(mgmtclass,"name","testmgmtclass0",self.token))

        tprint("save_mgmtclass")
        self.assertTrue(self.remote.save_mgmtclass(mgmtclass,self.token))

        new_mgmtclasses = self.remote.get_mgmtclasses(self.token)
        self.assertTrue(len(new_mgmtclasses) == len(mgmtclasses) + 1)

    def _get_mgmtclasses(self):
        """
        Test: Get mgmtclasses objects
        """

        tprint("get_mgmtclasses")
        self.remote.get_mgmtclasses()

    def _get_mgmtclass(self):
        """
        Test: get a mgmtclass object
        """

        tprint("get_mgmtclass")
        mgmtclass = self.remote.get_mgmtclass("testmgmtclass0")

    def _find_mgmtclass(self):
        """
        Test: find a mgmtclass object
        """

        tprint("find_mgmtclass")
        result = self.remote.find_mgmtclass({"name":"testmgmtclass0"}, self.token)
        self.assertTrue(result)

    def _copy_mgmtclass(self):
        """
        Test: copy a mgmtclass object
        """

        tprint("copy_mgmtclass")
        mgmtclass = self.remote.get_item_handle("mgmtclass","testmgmtclass0",self.token)
        self.assertTrue(self.remote.copy_mgmtclass(mgmtclass,"testmgmtclasscopy",self.token))

    def _rename_mgmtclass(self):
        """
        Test: rename a mgmtclass object
        """

        tprint("rename_mgmtclass")
        mgmtclass = self.remote.get_item_handle("mgmtclass","testmgmtclasscopy",self.token)
        self.assertTrue(self.remote.rename_mgmtclass(mgmtclass,"testmgmtclass1",self.token))

    def _remove_mgmtclass(self):
        """
        Test: remove a mgmtclass object
        """

        tprint("remove_mgmtclass")
        self.assertTrue(self.remote.remove_mgmtclass("testmgmtclass0",self.token))
        self.assertTrue(self.remote.remove_mgmtclass("testmgmtclass1",self.token))

    def test_mgmtclass(self):

        self._get_mgmtclasses()
        self._create_mgmtclass()
        self._get_mgmtclass()
        self._find_mgmtclass()
        self._copy_mgmtclass()
        self._rename_mgmtclass()
        self._remove_mgmtclass()


class Test_Image(CobblerXmlRpcTest):

    def _create_image(self):
        """
        Test: create/edit of an image object"""

        images = self.remote.get_images(self.token)

        tprint("new_image")
        image = self.remote.new_image(self.token)

        tprint("modify_image")
        self.assertTrue(self.remote.modify_image(image,"name","testimage0",self.token))

        tprint("save_image")
        self.assertTrue(self.remote.save_image(image,self.token))

        new_images = self.remote.get_images(self.token)
        self.assertTrue(len(new_images) == len(images) + 1)

    def _get_images(self):
        """
        Test: get images
        """
        tprint("get_images")
        self.remote.get_images()

    def _get_image(self):
        """
        Test: Get an image object
        """

        tprint("get_image")
        image = self.remote.get_image("testimage0")

    def _find_image(self):
        """
        Test: Find an image object
        """

        tprint("find_image")
        result = self.remote.find_image({"name":"testimage0"}, self.token)
        self.assertTrue(result)

    def _copy_image(self):
        """
        Test: Copy an image object
        """

        tprint("find_image")
        image = self.remote.get_item_handle("image","testimage0",self.token)
        self.assertTrue(self.remote.copy_image(image,"testimagecopy",self.token))

    def  _rename_image(self):
        """
        Test: Rename an image object
        """

        tprint("rename_image")
        image = self.remote.get_item_handle("image","testimagecopy",self.token)
        self.assertTrue(self.remote.rename_image(image,"testimage1",self.token))

    def _remove_image(self):
        """
        Test: remove an image object
        """

        tprint("remove_image")
        self.assertTrue(self.remote.remove_image("testimage0",self.token))
        self.assertTrue(self.remote.remove_image("testimage1",self.token))

    def test_image(self):

        self._get_images()
        self._create_image()
        self._get_image()
        self._find_image()
        self._copy_image()
        self._rename_image()
        self._remove_image()


class Test_Package(CobblerXmlRpcTest):

    def _create_package(self):
        """
        Test: create/edit a package object
        """

        packages = self.remote.get_packages(self.token)

        tprint("get_packages")
        packages = self.remote.get_packages(self.token)

        tprint("new_package")
        package = self.remote.new_package(self.token)

        tprint("modify_package")
        self.assertTrue(self.remote.modify_package(package,"name","testpackage0",self.token))

        tprint("save_package")
        self.assertTrue(self.remote.save_package(package, self.token))

        new_packages = self.remote.get_packages(self.token)
        self.assertTrue(len(new_packages) == len(packages) + 1)

    def _get_packages(self):
        """
        Test: Get packages
        """
        tprint("get_package")
        package = self.remote.get_packages()

    def _get_package(self):
        """
        Test: Get a package object
        """

        tprint("get_package")
        package = self.remote.get_package("testpackage0")

    def _find_package(self):
        """
        Test: find a package object
        """

        tprint("find_package")
        result = self.remote.find_package({"name":"testpackage0"}, self.token)
        self.assertTrue(result)

    def _copy_package(self):
        """
        Test: copy a package object
        """

        tprint("copy_package")
        package = self.remote.get_item_handle("package","testpackage0",self.token)
        self.assertTrue(self.remote.copy_package(package,"testpackagecopy",self.token))

    def _rename_package(self):
        """
        Test: rename a package object
        """

        tprint("rename_package")
        package = self.remote.get_item_handle("package","testpackagecopy",self.token)
        self.assertTrue(self.remote.rename_package(package,"testpackage1",self.token))

    def _remove_package(self):
        """
        Test: remove a package object
        """

        tprint("remove_package")
        self.assertTrue(self.remote.remove_package("testpackage0",self.token))
        self.assertTrue(self.remote.remove_package("testpackage1",self.token))

    def test_package(self):

        self._get_packages()
        self._create_package()
        self._get_package()
        self._find_package()
        self._copy_package()
        self._rename_package()
        self._remove_package()


class Test_File(CobblerXmlRpcTest):
    """
    Test remote calls related to files
    """

    def _create_file(self):

        files = self.remote.get_files(self.token)

        tprint("new_file")
        file_id = self.remote.new_file(self.token)

        tprint("modify_file")
        self.remote.modify_file(file_id, "name", "testfile0", self.token)
        self.remote.modify_file(file_id, "is_directory", "False", self.token)
        self.remote.modify_file(file_id, "action", "create", self.token)
        self.remote.modify_file(file_id, "group", "root", self.token)
        self.remote.modify_file(file_id, "mode", "0644", self.token)
        self.remote.modify_file(file_id, "owner", "root", self.token)
        self.remote.modify_file(file_id, "path", "/root/testfile0", self.token)
        self.remote.modify_file(file_id, "template", "testtemplate0", self.token)

        tprint("save_file")
        self.remote.save_file(file_id, self.token)

        new_files = self.remote.get_files(self.token)
        self.assertTrue(len(new_files) == len(files) + 1)

    def _get_files(self):
        """
        Test: get files
        """

        tprint("get_files")
        self.remote.get_files(self.token)

    def _get_file(self):
        """
        Test: Get a file object
        """

        tprint("get_file")
        file = self.remote.get_file("testfile0")

    def _find_file(self):
        """
        Test: find a file object
        """

        tprint("find_file")
        result = self.remote.find_file({"name":"testfile0"}, self.token)
        self.assertTrue(result)

    def _copy_file(self):
        """
        Test: copy a file object
        """

        tprint("copy_file")
        file = self.remote.get_item_handle("file", "testfile0", self.token)
        self.assertTrue(self.remote.copy_file(file, "testfilecopy", self.token))

    def _rename_file(self):
        """
        Test: rename a file object
        """

        tprint("rename_file")
        file = self.remote.get_item_handle("file","testfilecopy",self.token)
        self.assertTrue(self.remote.rename_file(file,"testfile1",self.token))

    def _remove_file(self):
        """
        Test: remove a file object
        """

        tprint("remove_file")
        self.assertTrue(self.remote.remove_file("testfile0",self.token))
        self.assertTrue(self.remote.remove_file("testfile1",self.token))

    def test_file(self):

        self._get_files()
        self._create_file()
        self._get_file()
        self._find_file()
        self._copy_file()
        self._rename_file()
        self._remove_file()


class Test_Item(CobblerXmlRpcTest):
    """
    Test item
    """

    def _get_item(self, type):
        """
        Test: get a generic item

        @param str type item type
        """

        tprint("get_item")
        item = self.remote.get_item(type, "test%s2" % type)

    def _find_item(self, type):
        """
        Test: find a generic item

        @param str type item type
        """

        tprint("find_items")
        result = self.remote.find_items(type, {"name":"test%s2" % type}, None, False)
        self.assertTrue(len(result) > 0)

    def _copy_item(self, type):
        """
        Test: copy a generic item

        @param str type item type
        """

        tprint("copy_item")
        item_id = self.remote.get_item_handle(type, "test%s2" % type, self.token)
        result = self.remote.copy_item(type, item_id, "test%scopy" % type, self.token)
        self.assertTrue(result)

    def _has_item(self, type):
        """
        Test: check if an item is in a item collection

        @param str type item type
        """

        tprint("has_item")
        result = self.remote.has_item(type, "test%s2" % type, self.token)
        self.assertTrue(result)

    def _rename_item(self, type):
        """
        Test: rename a generic item

        @param str type item type
        """

        tprint("rename_item")
        item_id = self.remote.get_item_handle(type, "test%scopy" % type, self.token)
        result = self.remote.rename_item(type, item_id, "test%s3" % type, self.token)
        self.assertTrue(result)

    def _remove_item(self, type):
        """
        Test: remove a generic item

        @param str type item type
        """

        tprint("remove_item")
        self.assertTrue(self.remote.remove_item(type, "test%s2" % type, self.token))
        self.assertTrue(self.remote.remove_item(type, "test%s3" % type, self.token))

    def test_item(self):

        type = "mgmtclass"

        tprint("get_item_names")
        items_names = self.remote.get_item_names(type)

        # create an item of the type defined above
        item_id = self.remote.new_mgmtclass(self.token)

        self.remote.modify_item(type, item_id, "name", "test%s2" % type, self.token)
        result = self.remote.save_item(type, item_id, self.token)
        self.assertTrue(result)

        new_items_names = self.remote.get_item_names(type)
        self.assertTrue(len(new_items_names) == len(items_names) + 1)

        self._get_item(type)
        self._find_item(type)
        self._copy_item(type)
        self._rename_item(type)
        self._remove_item(type)

        new_items_names = self.remote.get_item_names(type)
        self.assertTrue(len(new_items_names) == len(items_names))

class Test_NonObjectCalls(CobblerXmlRpcTest):

    def _wait_task_end(self, tid):
        """
        Wait until a task is finished
        """

        timeout = 0
        while self.remote.get_task_status(tid)[2] != EVENT_COMPLETE:
            print("task %s status: %s" % (tid, self.remote.get_task_status(tid)))
            time.sleep(5)
            timeout += 5
            if timeout == 60:
                raise Exception

    def test_token(self):
        """
        Test: authentication token validation
        """

        assert self.token not in ("",None)

    def test_get_user_from_token(self):
        """
        Test: get user data from authentication token
        """

        tprint("get_user_from_token")
        self.assertTrue(self.remote.get_user_from_token(self.token))

    def test_check(self):
        """
        Test: check Cobbler status
        """

        tprint("check")
        self.assertTrue(self.remote.check(self.token))

    def test_last_modified_time(self):
        """
        Test: get last modification time
        """

        tprint("last_modified_time")
        assert self.remote.last_modified_time(self.token) != 0

    def test_power_system(self):
        """
        Test: reboot a system
        """

        if TEST_SYSTEM and TEST_POWER_MANAGEMENT:
            tprint("background_power_system")
            tid = self.remote.background_power_system({"systems": [TEST_SYSTEM],
                                                       "power": "reboot"},
                                                      self.token)
            self._wait_task_end(tid)

    def test_sync(self):
        """
        Test: synchronize Cobbler internal data with managed services
        (dhcp, tftp, dns)
        """

        tprint("background_sync")
        tid = self.remote.background_sync({}, self.token)

        tprint("get_events")
        events = self.remote.get_events(self.token)
        self.assertTrue(len(events) > 0)

        self._wait_task_end(tid)

        tprint("get_event_log")
        event_log = self.remote.get_event_log(tid)

    def test_get_kickstart_templates(self):
        """
        Test: get kickstart templates
        """

        tprint("get_kickstart_templates")
        result = self.remote.get_kickstart_templates()
        self.assertTrue(len(result) > 0)

    def test_get_snippets(self):
        """
        Test: get snippets
        """

        tprint("get_snippets")
        result = self.remote.get_snippets(self.token)
        self.assertTrue(len(result) > 0)

    def test_generate_kickstart(self):
        """
        Test: generate kickstart content
        """

        if TEST_SYSTEM:
            tprint("generate_kickstart")
            self.remote.generate_kickstart(None, TEST_SYSTEM)

    def test_generate_gpxe(self):
        """
        Test: generate GPXE file content
        """

        if TEST_SYSTEM:
            tprint("generate_gpxe")
            self.remote.generate_gpxe(None, TEST_SYSTEM)

    def test_generate_bootcfg(self):
        """
        Test: generate boot loader configuration file content
        """

        if TEST_SYSTEM:
            tprint("generate_bootcfg")
            self.remote.generate_bootcfg(None, TEST_SYSTEM)

    def test_get_settings(self):
        """
        Test: get settings
        """

        tprint("get_settings")
        self.remote.get_settings(self.token)

    def test_get_signatures(self):
        """
        Test: get distro signatures
        """

        tprint("get_signatures")
        self.remote.get_signatures(self.token)

    def test_get_valid_breeds(self):
        """
        Test: get valid OS breeds
        """

        tprint("get_valid_breeds")
        breeds = self.remote.get_valid_breeds(self.token)
        self.assertTrue(len(breeds) > 0)

    def test_get_valid_os_versions_for_breed(self):
        """
        Test: get valid OS versions for a OS breed
        """

        tprint("get_valid_os_versions_for_breeds")
        versions = self.remote.get_valid_os_versions_for_breed("generic", self.token)
        self.assertTrue(len(versions) > 0)

    def test_get_valid_os_versions(self):
        """
        Test: get valid OS versions
        """

        tprint("get_valid_os_versions")
        versions = self.remote.get_valid_os_versions(self.token)
        self.assertTrue(len(versions) > 0)

    def test_get_random_mac(self):
        """
        Test: get a random mac for a virtual network interface
        """

        tprint("get_random_mac")
        mac = self.remote.get_random_mac("xen", self.token)
        hexa = "[0-9A-Fa-f]{2}"
        match_obj = re.match("%s:%s:%s:%s:%s:%s" % (hexa, hexa, hexa, hexa, hexa, hexa), mac)
        self.assertTrue(match_obj)


if __name__ == '__main__':
    unittest.main()
