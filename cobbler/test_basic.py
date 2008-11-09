# Test cases for Cobbler
#
# Michael DeHaan <mdehaan@redhat.com>

import sys
import unittest
import os
import subprocess
import tempfile
import shutil
import traceback

from cexceptions import *  
import acls

#from cobbler import settings
#from cobbler import collection_distros
#from cobbler import collection_profiles
#from cobbler import collection_systems
#from cobbler import collection_repos
#from cobbler import collection_images
import modules.authz_ownership as authz_module
import api
import config
import utils
utils.TEST_MODE = True

FAKE_INITRD="initrd-2.6.15-1.2054_FAKE.img"
FAKE_INITRD2="initrd-2.5.16-2.2055_FAKE.img"
FAKE_INITRD3="initrd-1.8.18-3.9999_FAKE.img"
FAKE_KERNEL="vmlinuz-2.6.15-1.2054_FAKE"
FAKE_KERNEL2="vmlinuz-2.5.16-2.2055_FAKE"
FAKE_KERNEL3="vmlinuz-1.8.18-3.9999_FAKE"

cleanup_dirs = []

class BootTest(unittest.TestCase):

    def setUp(self):


        # Create temp dir
        self.topdir = "/tmp/cobbler_test"
        try:
            os.makedirs(self.topdir)
        except:
            pass

        self.fk_initrd = os.path.join(self.topdir,  FAKE_INITRD)
        self.fk_initrd2 = os.path.join(self.topdir, FAKE_INITRD2)
        self.fk_initrd3 = os.path.join(self.topdir, FAKE_INITRD3)

        self.fk_kernel = os.path.join(self.topdir,  FAKE_KERNEL)
        self.fk_kernel2 = os.path.join(self.topdir, FAKE_KERNEL2)
        self.fk_kernel3 = os.path.join(self.topdir, FAKE_KERNEL3)

        self.api = api.BootAPI()
        create = [ self.fk_initrd, self.fk_initrd2, self.fk_initrd3,
                self.fk_kernel, self.fk_kernel2, self.fk_kernel3 ]
        for fn in create:
            f = open(fn,"w+")
            f.close()
        self.__make_basic_config()

    def tearDown(self):

        for x in self.api.distros():
            self.api.remove_distro(x,recursive=True)
        for y in self.api.repos():
            self.api.remove_repo(y)
        for z in self.api.images():
            self.api.remove_image(z)
        shutil.rmtree(self.topdir,ignore_errors=True)
        self.api = None

    def __make_basic_config(self):
        distro = self.api.new_distro()
        self.assertTrue(distro.set_name("testdistro0"))
        self.assertTrue(distro.set_kernel(self.fk_kernel))
        self.assertTrue(distro.set_initrd(self.fk_initrd))
        self.assertTrue(self.api.add_distro(distro))
        self.assertTrue(self.api.find_distro(name="testdistro0"))
        
        profile = self.api.new_profile()
        self.assertTrue(profile.set_name("testprofile0"))
        self.assertTrue(profile.set_distro("testdistro0"))
        self.assertTrue(profile.set_kickstart("/etc/cobbler/sample_end.ks"))
        self.assertTrue(self.api.add_profile(profile))
        self.assertTrue(self.api.find_profile(name="testprofile0"))

        system = self.api.new_system()
        self.assertTrue(system.set_name("testsystem0"))
        self.assertTrue(system.set_mac_address("BB:EE:EE:EE:EE:FF","intf0"))
        self.assertTrue(system.set_ip_address("192.51.51.50","intf0"))
        self.assertTrue(system.set_profile("testprofile0"))
        self.assertTrue(self.api.add_system(system))
        self.assertTrue(self.api.find_system(name="testsystem0"))

        repo = self.api.new_repo()
        try:
            os.makedirs("/tmp/test_example_cobbler_repo")
        except:
            pass
        fd = open("/tmp/test_example_cobbler_repo/test.file", "w+")
        fd.write("hello!")
        fd.close()
        self.assertTrue(repo.set_name("testrepo0"))
        self.assertTrue(repo.set_mirror("/tmp/test_example_cobbler_repo"))
        self.assertTrue(self.api.add_repo(repo))

        image = self.api.new_image()
        self.assertTrue(image.set_name("testimage0"))
        self.assertTrue(image.set_file("/etc/hosts")) # meaningless path
        self.assertTrue(self.api.add_image(image))


class RenameTest(BootTest):

    def __tester(self, finder, renamer, name1, name2):

        x = finder(name1)
        assert x is not None

        renamer(x, name2)
        x = finder(name1)
        y = finder(name2)
        assert x is None
        assert y is not None
        
        renamer(y, name1) 
        x = finder(name1)
        y = finder(name2)
        assert x is not None
        assert y is None 

    def test_renames(self):
        self.__tester(self.api.find_distro, self.api.rename_distro, "testdistro0", "testdistro1")
        self.api.update() # unneccessary?
        self.__tester(self.api.find_profile, self.api.rename_profile, "testprofile0", "testprofile1")
        self.api.update() # unneccessary?
        self.__tester(self.api.find_system, self.api.rename_system, "testsystem0", "testsystem1")
        self.api.update() # unneccessary?
        self.__tester(self.api.find_repo, self.api.rename_repo, "testrepo0", "testrepo1")
        self.api.update() # unneccessary?
        self.__tester(self.api.find_image, self.api.rename_image, "testimage0", "testimage1")


class DuplicateNamesAndIpPrevention(BootTest):

    """
    The command line (and WebUI) have checks to prevent new system
    additions from conflicting with existing systems and overwriting
    them inadvertantly. This class tests that code.  NOTE: General API
    users will /not/ encounter these checks.
    """

    def test_duplicate_prevention(self):

        # find things we are going to test with
        distro1 = self.api.find_distro(name="testdistro0")
        profile1 = self.api.find_profile(name="testprofile0")
        system1 = self.api.find_system(name="testsystem0")
        repo1 = self.api.find_repo(name="testrepo0")

        # make sure we can't overwrite a previous distro with
        # the equivalent of an "add" (not an edit) on the
        # command line.
        distro2 = self.api.new_distro()
        self.assertTrue(distro2.set_name("testdistro0"))
        self.assertTrue(distro2.set_kernel(self.fk_kernel))
        self.assertTrue(distro2.set_initrd(self.fk_initrd))
        self.assertTrue(distro2.set_owners("canary"))
        # this should fail
        try:
           self.api.add_distro(distro2,check_for_duplicate_names=True)
           self.assertTrue(1==2,"distro add should fail")
        except CobblerException:
           pass
        except:
           self.assertTrue(1==2,"exception type")
        # we caught the exception but make doubly sure there was no write
        distro_check = self.api.find_distro(name="testdistro0")
        self.assertTrue("canary" not in distro_check.owners)

        # repeat the check for profiles
        profile2 = self.api.new_profile()
        self.assertTrue(profile2.set_name("testprofile0"))
        self.assertTrue(profile2.set_distro("testdistro0"))
        # this should fail
        try:
            self.api.add_profile(profile2,check_for_duplicate_names=True)
            self.assertTrue(1==2,"profile add should fail")
        except CobblerException:
            pass
        except:
            traceback.print_exc()
            self.assertTrue(1==2,"exception type")

        # repeat the check for systems (just names this time)
        system2 = self.api.new_system()
        self.assertTrue(system2.set_name("testsystem0"))
        self.assertTrue(system2.set_profile("testprofile0"))
        # this should fail
        try:
            self.api.add_system(system2,check_for_duplicate_names=True)
            self.assertTrue(1==2,"system add should fail")
        except CobblerException:
            pass
        except:
            traceback.print_exc()
            self.assertTrue(1==2,"exception type")

        # repeat the check for repos
        repo2 = self.api.new_repo()
        self.assertTrue(repo2.set_name("testrepo0"))
        self.assertTrue(repo2.set_mirror("http://imaginary"))
        # self.failUnlessRaises(CobblerException,self.api.add_repo,[repo,check_for_duplicate_names=True])
        try:
            self.api.add_repo(repo2,check_for_duplicate_names=True)
            self.assertTrue(1==2,"repo add should fail")
        except CobblerException:
            pass
        except:
            self.assertTrue(1==2,"exception type")

        # now one more check to verify we can't add a system
        # of a different name but duplicate netinfo.  
        system3 = self.api.new_system()
        self.assertTrue(system3.set_name("unused_name"))
        self.assertTrue(system3.set_profile("testprofile0"))
        # MAC is initially accepted
        self.assertTrue(system3.set_mac_address("BB:EE:EE:EE:EE:FF","intf3"))
        # can't add as this MAC already exists!  

        #self.failUnlessRaises(CobblerException,self.api.add_system,[system3,check_for_duplicate_names=True,check_for_duplicate_netinfo=True)
        try:
           self.api.add_system(system3,check_for_duplicate_names=True,check_for_duplicate_netinfo=True)
        except CobblerException: 
           pass
        except:
           traceback.print_exc()
           self.assertTrue(1==2,"wrong exception type")

        # set the MAC to a different value and try again
        self.assertTrue(system3.set_mac_address("FF:EE:EE:EE:EE:DD","intf3"))
        # it should work
        self.assertTrue(self.api.add_system(system3,check_for_duplicate_names=False,check_for_duplicate_netinfo=True))
        # now set the IP so that collides
        self.assertTrue(system3.set_ip_address("192.51.51.50","intf6"))
        # this should also fail

        # self.failUnlessRaises(CobblerException,self.api.add_system,[system3,check_for_duplicate_names=True,check_for_duplicate_netinfo=True)
        try:
           self.api.add_system(system3,check_for_duplicate_names=True,check_for_duplicate_netinfo=True)
           self.assertTrue(1==2,"system add should fail")
        except CobblerException:
           pass
        except:
           self.assertTrue(1==2,"wrong exception type")

        # fix the IP and Mac back 
        self.assertTrue(system3.set_ip_address("192.86.75.30","intf6"))
        self.assertTrue(system3.set_mac_address("AE:BE:DE:CE:AE:EE","intf3"))
        # now it works again
        # note that we will not check for duplicate names as we want
        # to test this as an 'edit' operation.
        self.assertTrue(self.api.add_system(system3,check_for_duplicate_names=False,check_for_duplicate_netinfo=True))

        # FIXME: note -- how netinfo is handled when doing renames/copies/edits
        # is more involved and we probably should add tests for that also.

class Ownership(BootTest):

    def test_ownership_params(self):
   
        fd = open("/tmp/test_cobbler_kickstart","w+")
        fd.write("")
        fd.close()

        # find things we are going to test with
        distro = self.api.find_distro(name="testdistro0")
        profile = self.api.find_profile(name="testprofile0")
        system = self.api.find_system(name="testsystem0")
        repo = self.api.find_repo(name="testrepo0")

        # as we didn't specify an owner for objects, the default
        # ownership should be as specified in settings
        default_owner = self.api.settings().default_ownership
        for obj in [ distro, profile, system, repo ]:
            self.assertTrue(obj is not None)
            self.assertEquals(obj.owners, default_owner, "default owner for %s" % obj)        

        # verify we can test things
        self.assertTrue(distro.set_owners(["superlab","basement1"]))
        self.assertTrue(profile.set_owners(["superlab","basement1"]))
        self.assertTrue(profile.set_kickstart("/tmp/test_cobbler_kickstart"))
        self.assertTrue(system.set_owners(["superlab","basement1","basement3"]))
        self.assertTrue(repo.set_owners([]))
        self.api.add_distro(distro)
        self.api.add_profile(profile)
        self.api.add_system(system)
        self.api.add_repo(repo)

        # now edit the groups file.  We won't test the full XMLRPC
        # auth stack here, but just the module in question

        acl_engine = acls.AclEngine()
        def authorize(api, user, resource, arg1=None, arg2=None):
            return authz_module.authorize(api, user,resource,arg1,arg2,acl_engine=acl_engine)

        # if the users.conf file exists, back it up for the tests
        if os.path.exists("/etc/cobbler/users.conf"):
           shutil.copyfile("/etc/cobbler/users.conf","/tmp/cobbler_ubak")
         
        fd = open("/etc/cobbler/users.conf","w+")
        fd.write("\n")
        fd.write("[admins]\n")
        fd.write("admin1 = 1\n")
        fd.write("\n")
        fd.write("[superlab]\n")
        fd.write("superlab1 = 1\n")
        fd.write("superlab2 = 1\n")
        fd.write("\n")
        fd.write("[basement]\n") 
        fd.write("basement1 = 1\n")      
        fd.write("basement2 = 1\n")      
        fd.write("basement3 = 1\n")      
        fd.close()


        xo = self.api.find_distro("testdistro0")
        xn = "testdistro0"
        ro = self.api.find_repo("testrepo0")
        rn = "testrepo0"

        # WARNING: complex test explanation follows! 
        # we must ensure those who can edit the kickstart are only those
        # who can edit all objects that depend on the said kickstart
        # in this test, superlab & basement1 can edit test_profile0
        # superlab & basement1/3 can edit test_system0
        # the systems share a common kickstart record (in this case
        # explicitly set, which is a bit arbitrary as they are parent/child
        # nodes, but the concept is not limited to this).  
        # Therefore the correct result is that the following users can edit:
        #    admin1, superlab1, superlab2
        # And these folks can't
        #    basement1, basement2
        # Basement2 is rejected because the kickstart is shared by something
        # basmeent2 can not edit.


        for user in [ "admin1", "superlab1", "superlab2", "basement1" ]:
           self.assertTrue(authorize(self.api, user, "write_kickstart", "/tmp/test_cobbler_kickstart"), "%s can modify_kickstart" % user)

        for user in [ "basement2", "dne" ]:
           self.assertFalse(authorize(self.api, user, "write_kickstart", "/tmp/test_cobbler_kickstart"), "%s can modify_kickstart" % user)

        # ensure admin1 can edit (he's an admin) and do other tasks
        # same applies to basement1 who is explicitly added as a user
        # and superlab1 who is in a group in the ownership list
        for user in ["admin1","superlab1","basement1"]:
           self.assertTrue(authorize(self.api, user, "save_distro", xo),"%s can save_distro" % user)
           self.assertTrue(authorize(self.api, user, "modify_distro", xo),"%s can modify_distro" % user)
           self.assertTrue(authorize(self.api, user, "copy_distro", xo),"%s can copy_distro" % user)
           self.assertTrue(authorize(self.api, user, "remove_distro", xn),"%s can remove_distro" % user)  

        # ensure all users in the file can sync
        for user in [ "admin1", "superlab1", "basement1", "basement2" ]:     
           self.assertTrue(authorize(self.api, user, "sync"))

        # make sure basement2 can't edit (not in group)
        # and same goes for "dne" (does not exist in users.conf)
        
        for user in [ "basement2", "dne" ]:
           self.assertFalse(authorize(self.api, user, "save_distro", xo), "user %s cannot save_distro" % user)
           self.assertFalse(authorize(self.api, user, "modify_distro", xo), "user %s cannot modify_distro" % user)
           self.assertFalse(authorize(self.api, user, "remove_distro", xn), "user %s cannot remove_distro" % user)
 
        # basement2 is in the file so he can still copy
        self.assertTrue(authorize(self.api, "basement2", "copy_distro", xo), "basement2 can copy_distro")

        # dne can not copy or sync either (not in the users.conf)
        self.assertFalse(authorize(self.api, "dne", "copy_distro", xo), "dne cannot copy_distro")
        self.assertFalse(authorize(self.api, "dne", "sync"), "dne cannot sync")

        # unlike the distro testdistro0, testrepo0 is unowned
        # so any user in the file will be able to edit it.
        for user in [ "admin1", "superlab1", "basement1", "basement2" ]:
           self.assertTrue(authorize(self.api, user, "save_repo", ro), "user %s can save_repo" % user)

        # though dne is still not listed and will be denied
        self.assertFalse(authorize(self.api, "dne", "save_repo", ro), "dne cannot save_repo")

        # if we survive, restore the users file as module testing is done
        if os.path.exists("/tmp/cobbler_ubak"):
           shutil.copyfile("/etc/cobbler/users.conf","/tmp/cobbler_ubak")


class MultiNIC(BootTest):
    
    def test_multi_nic_support(self):


        system = self.api.new_system()
        self.assertTrue(system.set_name("nictest"))
        self.assertTrue(system.set_profile("testprofile0"))
        self.assertTrue(system.set_hostname("zero","intf0"))
        self.assertTrue(system.set_mac_address("EE:FF:DD:CC:DD:CC","intf1"))
        self.assertTrue(system.set_ip_address("127.0.0.5","intf2"))
        self.assertTrue(system.set_dhcp_tag("zero","intf3"))
        self.assertTrue(system.set_virt_bridge("zero","intf4"))
        self.assertTrue(system.set_gateway("192.168.1.25","intf4"))
        self.assertTrue(system.set_mac_address("AA:AA:BB:BB:CC:CC","intf4"))
        self.assertTrue(system.set_hostname("fooserver","intf4"))
        self.assertTrue(system.set_dhcp_tag("red","intf4"))
        self.assertTrue(system.set_ip_address("192.168.1.26","intf4"))
        self.assertTrue(system.set_subnet("255.255.255.0","intf4"))
        self.assertTrue(system.set_dhcp_tag("tag2","intf5"))
        self.assertTrue(self.api.add_system(system))
        self.assertTrue(self.api.find_system(hostname="fooserver"))
        self.assertTrue(self.api.find_system(mac_address="EE:FF:DD:CC:DD:CC"))
        self.assertTrue(self.api.find_system(ip_address="127.0.0.5"))
        self.assertTrue(self.api.find_system(virt_bridge="zero"))
        self.assertTrue(self.api.find_system(gateway="192.168.1.25"))
        self.assertTrue(self.api.find_system(subnet="255.255.255.0"))
        self.assertTrue(self.api.find_system(dhcp_tag="tag2"))
        self.assertTrue(self.api.find_system(dhcp_tag="zero"))

        # verify that systems has exactly 5 interfaces
        self.assertTrue(len(system.interfaces.keys()) == 6)

        # now check one interface to make sure it's exactly right
        # and we didn't accidentally fill in any other fields elsewhere

        self.assertTrue(system.interfaces.has_key("intf4"))
        for (name,intf) in system.interfaces.iteritems():
            if name == "intf4": # xmlrpc dicts must have string keys, so we must also
                self.assertTrue(intf["gateway"] == "192.168.1.25")
                self.assertTrue(intf["virt_bridge"] == "zero")
                self.assertTrue(intf["subnet"] == "255.255.255.0")
                self.assertTrue(intf["mac_address"] == "AA:AA:BB:BB:CC:CC")
                self.assertTrue(intf["ip_address"] == "192.168.1.26")
                self.assertTrue(intf["hostname"] == "fooserver")
                self.assertTrue(intf["dhcp_tag"] == "red")
 
class Utilities(BootTest):

    def _expeq(self, expected, actual):
        try:
            self.failUnlessEqual(expected, actual,
                "Expected: %s; actual: %s" % (expected, actual))
        except:
            self.fail("exception during failUnlessEqual")

    def test_kernel_scan(self):
        self.assertTrue(utils.find_kernel(self.fk_kernel))
        self.assertFalse(utils.find_kernel("filedoesnotexist"))
        self._expeq(self.fk_kernel, utils.find_kernel(self.topdir))

    def test_initrd_scan(self):
        self.assertTrue(utils.find_initrd(self.fk_initrd))
        self.assertFalse(utils.find_initrd("filedoesnotexist"))
        self._expeq(self.fk_initrd, utils.find_initrd(self.topdir))

    def test_kickstart_scan(self):
        # we don't check to see if kickstart files look like anything
        # so this will pass
        self.assertTrue(utils.find_kickstart("filedoesnotexist") is None)
        self.assertTrue(utils.find_kickstart(self.topdir) == None)
        self.assertTrue(utils.find_kickstart("http://bar"))
        self.assertTrue(utils.find_kickstart("ftp://bar"))
        self.assertTrue(utils.find_kickstart("nfs://bar"))
        self.assertFalse(utils.find_kickstart("gopher://bar"))

    def test_matching(self):
        self.assertTrue(utils.is_mac("00:C0:B7:7E:55:50"))
        self.assertTrue(utils.is_mac("00:c0:b7:7E:55:50"))
        self.assertFalse(utils.is_mac("00.D0.B7.7E.55.50"))
        self.assertFalse(utils.is_mac("testsystem0"))
        self.assertTrue(utils.is_ip("127.0.0.1"))
        self.assertTrue(utils.is_ip("192.168.1.1"))
        self.assertFalse(utils.is_ip("00:C0:B7:7E:55:50"))
        self.assertFalse(utils.is_ip("testsystem0"))

    def test_some_random_find_commands(self):
        # initial setup...
        self.test_system_name_is_a_MAC()
        # search for a parameter that isn't real, want an error
        self.failUnlessRaises(CobblerException,self.api.systems().find, pond="mcelligots")

        # verify that even though we have several different NICs search still works
        # FIMXE: temprorarily disabled
        # self.assertTrue(self.api.find_system(name="nictest") is not None)

        # search for a parameter with a bad value, want None
        self.assertFalse(self.api.systems().find(name="horton"))
        # one valid parameter another invalid is still an error
        self.failUnlessRaises(CobblerException,self.api.systems().find, name="onefish",pond="mcelligots")
        # searching with no args is ALSO an error
        self.failUnlessRaises(CobblerException, self.api.systems().find)
        # searching for a list returns a list of correct length
        self.assertTrue(len(self.api.systems().find(mac_address="00:16:41:14:B7:71",return_list=True))==1)
        # make sure we can still search without an explicit keyword arg
        self.assertTrue(len(self.api.systems().find("00:16:41:14:B7:71",return_list=True))==1)
        self.assertTrue(self.api.systems().find("00:16:41:14:B7:71"))

    def test_invalid_distro_non_referenced_kernel(self):
        distro = self.api.new_distro()
        self.assertTrue(distro.set_name("testdistro2"))
        self.failUnlessRaises(CobblerException,distro.set_kernel,"filedoesntexist")
        self.assertTrue(distro.set_initrd(self.fk_initrd))
        self.failUnlessRaises(CobblerException, self.api.add_distro, distro)
        self.assertFalse(self.api.distros().find(name="testdistro2"))

    def test_invalid_distro_non_referenced_initrd(self):
        distro = self.api.new_distro()
        self.assertTrue(distro.set_name("testdistro3"))
        self.assertTrue(distro.set_kernel(self.fk_kernel))
        self.failUnlessRaises(CobblerException, distro.set_initrd, "filedoesntexist")
        self.failUnlessRaises(CobblerException, self.api.add_distro, distro)
        self.assertFalse(self.api.distros().find(name="testdistro3"))

    def test_invalid_profile_non_referenced_distro(self):
        profile = self.api.new_profile()
        self.assertTrue(profile.set_name("testprofile11"))
        self.failUnlessRaises(CobblerException, profile.set_distro, "distrodoesntexist")
        self.assertTrue(profile.set_kickstart("/etc/cobbler/sample.ks"))
        self.failUnlessRaises(CobblerException, self.api.add_profile, profile)
        self.assertFalse(self.api.profiles().find(name="testprofile2"))

    def test_invalid_profile_kickstart_not_url(self):
        profile = self.api.new_profile()
        self.assertTrue(profile.set_name("testprofile12"))
        self.assertTrue(profile.set_distro("testdistro0"))
        self.failUnlessRaises(CobblerException, profile.set_kickstart, "kickstartdoesntexist")
        # since kickstarts are optional, you can still add it
        self.assertTrue(self.api.add_profile(profile))
        self.assertTrue(self.api.profiles().find(name="testprofile12"))
        # now verify the other kickstart forms would still work
        self.assertTrue(profile.set_kickstart("http://bar"))
        self.assertTrue(profile.set_kickstart("ftp://bar"))
        self.assertTrue(profile.set_kickstart("nfs://bar"))

    def test_profile_virt_parameter_checking(self):
        profile = self.api.new_profile()
        self.assertTrue(profile.set_name("testprofile12b"))
        self.assertTrue(profile.set_distro("testdistro0"))
        self.assertTrue(profile.set_kickstart("http://127.0.0.1/foo"))
        self.assertTrue(profile.set_virt_bridge("xenbr1"))
        # sizes must be integers
        self.assertTrue(profile.set_virt_file_size("54321"))
        self.failUnlessRaises(Exception, profile.set_virt_file_size, "huge")
        self.failUnlessRaises(Exception, profile.set_virt_file_size, "54.321")
        # cpus must be integers
        self.assertTrue(profile.set_virt_cpus("2"))
        self.failUnlessRaises(Exception, profile.set_virt_cpus, "3.14")
        self.failUnlessRaises(Exception, profile.set_virt_cpus, "6.02*10^23")
        self.assertTrue(self.api.add_profile(profile))

    def test_inheritance_and_variable_propogation(self):

        # STEP ONE: verify that non-inherited objects behave
        # correctly with ks_meta (we picked this attribute
        # because it's a hash and it's a bit harder to handle
        # than strings).  It should be passed down the render
        # tree to all subnodes

        repo = self.api.new_repo()
        try:
            os.makedirs("/tmp/test_cobbler_repo")
        except:
            pass
        fd = open("/tmp/test_cobbler_repo/test.file", "w+")
        fd.write("hello!")
        fd.close()
        self.assertTrue(repo.set_name("testrepo"))
        self.assertTrue(repo.set_mirror("/tmp/test_cobbler_repo"))
        self.assertTrue(self.api.add_repo(repo))

        profile = self.api.new_profile()
        self.assertTrue(profile.set_name("testprofile12b2"))
        self.assertTrue(profile.set_distro("testdistro0"))
        self.assertTrue(profile.set_kickstart("http://127.0.0.1/foo"))
        self.assertTrue(profile.set_repos(["testrepo"]))
        self.assertTrue(self.api.add_profile(profile))

        # disable this test as it's not a valid repo yet
        # self.api.reposync()

        self.api.sync()
        system = self.api.new_system()
        self.assertTrue(system.set_name("foo"))
        self.assertTrue(system.set_profile("testprofile12b2"))
        self.assertTrue(system.set_ksmeta({"asdf" : "jkl" }))
        self.assertTrue(self.api.add_system(system))
        profile = self.api.profiles().find("testprofile12b2")
        ksmeta = profile.ks_meta
        self.assertFalse(ksmeta.has_key("asdf"))

        # FIXME: do the same for inherited profiles
        # now verify the same for an inherited profile
        # and this time walk up the tree to verify it wasn't
        # applied to any other object except the base.

        profile2 = self.api.new_profile(is_subobject=True)
        profile2.set_name("testprofile12b3")
        profile2.set_parent("testprofile12b2")
        self.api.add_profile(profile2)
        # disable this test as syncing an invalid repo will fail
        # self.api.reposync()
        self.api.sync()

        # FIXME: now add a system to the inherited profile
        # and set a attribute on it that we will later check for

        system2 = self.api.new_system()
        self.assertTrue(system2.set_name("foo2"))
        self.assertTrue(system2.set_profile("testprofile12b3"))
        self.assertTrue(system2.set_ksmeta({"narf" : "troz"}))
        self.assertTrue(self.api.add_system(system2))
        # disable this test as invalid repos don't sync
        # self.api.reposync()
        self.api.sync()

        # FIXME: now evaluate the system object and make sure  
        # that it has inherited the repos value from the superprofile
        # above it's actual profile.  This should NOT be present in the
        # actual object, which we have not modified yet.

        data = utils.blender(self.api, False, system2)
        self.assertTrue(data["repos"] == ["testrepo"])
        self.assertTrue(self.api.profiles().find(system2.profile).repos == "<<inherit>>")

        # now if we set the repos object of the system to an additional
        # repo we should verify it now contains two repos.
        # (FIXME)
        
        repo2 = self.api.new_repo()
        try:
           os.makedirs("/tmp/cobbler_test/repo0")
        except:
           pass
        fd = open("/tmp/cobbler_test/repo0/file.test","w+")
        fd.write("Hi!")
        fd.close()
        self.assertTrue(repo2.set_name("testrepo2"))
        self.assertTrue(repo2.set_mirror("/tmp/cobbler_test/repo0"))
        self.assertTrue(self.api.add_repo(repo2))
        profile2 = self.api.profiles().find("testprofile12b3")
        # note: side check to make sure we can also set to string values
        profile2.set_repos("testrepo2")       
        self.api.add_profile(profile2) # save it 

        # random bug testing: run sync several times and ensure cardinality doesn't change
        #self.api.reposync()
        self.api.sync()
        self.api.sync()
        self.api.sync()

        data = utils.blender(self.api, False, system2)
        self.assertTrue("testrepo" in data["repos"])
        self.assertTrue("testrepo2" in data["repos"])
        self.assertTrue(len(data["repos"]) == 2)
        self.assertTrue(self.api.profiles().find(system2.profile).repos == ["testrepo2"])

        # now double check that the parent profile still only has one repo in it.
        # this is part of our test against upward propogation

        profile = self.api.profiles().find("testprofile12b2")
        self.assertTrue(len(profile.repos) == 1)
        self.assertTrue(profile.repos == ["testrepo"])

        # now see if the subprofile does NOT have the ksmeta attribute
        # this is part of our test against upward propogation

        profile2 = self.api.profiles().find("testprofile12b3")
        self.assertTrue(type(profile2.ks_meta) == type(""))
        self.assertTrue(profile2.ks_meta == "<<inherit>>")

        # now see if the profile above this profile still doesn't have it

        profile = self.api.profiles().find("testprofile12b2")
        self.assertTrue(type(profile.ks_meta) == type({}))
        # self.api.reposync()
        self.api.sync()
        self.assertFalse(profile.ks_meta.has_key("narf"), "profile does not have the system ksmeta")

        #self.api.reposync()
        self.api.sync()

        # verify that the distro did not acquire the property
        # we just set on the leaf system
        distro = self.api.distros().find("testdistro0")
        self.assertTrue(type(distro.ks_meta) == type({}))
        self.assertFalse(distro.ks_meta.has_key("narf"), "distro does not have the system ksmeta")

        # STEP THREE: verify that inheritance appears to work    
        # by setting ks_meta on the subprofile and seeing
        # if it appears on the leaf system ... must use
        # blender functions

        profile2 = self.api.profiles().find("testprofile12b3")
        profile2.set_ksmeta({"canyouseethis" : "yes" })
        self.assertTrue(self.api.add_profile(profile2))
        system2 = self.api.systems().find("foo2")
        data = utils.blender(self.api, False, system2)
        self.assertTrue(data.has_key("ks_meta"))
        self.assertTrue(data["ks_meta"].has_key("canyouseethis"))
        
        # STEP FOUR: do the same on the superprofile and see
        # if that propogates
        
        profile = self.api.profiles().find("testprofile12b2")
        profile.set_ksmeta({"canyouseethisalso" : "yes" })
        self.assertTrue(self.api.add_profile(profile))
        system2 = self.api.systems().find("foo2")
        data = utils.blender(self.api, False, system2)
        self.assertTrue(data.has_key("ks_meta"))
        self.assertTrue(data["ks_meta"].has_key("canyouseethisalso"))

        # STEP FIVE: see if distro attributes propogate

        distro = self.api.distros().find("testdistro0")
        distro.set_ksmeta({"alsoalsowik" : "moose" })
        self.assertTrue(self.api.add_distro(distro))
        system2 = self.api.find_system("foo2")
        data = utils.blender(self.api, False, system2)
        self.assertTrue(data.has_key("ks_meta"))
        self.assertTrue(data["ks_meta"].has_key("alsoalsowik"))
        
        


        # STEP SEVEN:  see if settings changes also propogate
        # TBA 

    def test_system_name_is_a_MAC(self):
        system = self.api.new_system()
        name = "00:16:41:14:B7:71"
        self.assertTrue(system.set_name(name))
        self.assertTrue(system.set_profile("testprofile0"))
        self.assertTrue(self.api.add_system(system))
        self.assertTrue(self.api.find_system(name=name))
        self.assertTrue(self.api.find_system(mac_address="00:16:41:14:B7:71"))
        self.assertFalse(self.api.find_system(mac_address="thisisnotamac"))

    def test_system_name_is_an_IP(self):
        system = self.api.new_system()
        name = "192.168.1.54"
        self.assertTrue(system.set_name(name))
        self.assertTrue(system.set_profile("testprofile0"))
        self.assertTrue(self.api.add_system(system))
        self.assertTrue(self.api.find_system(name=name))

    def test_invalid_system_non_referenced_profile(self):
        system = self.api.new_system()
        self.assertTrue(system.set_name("testsystem0"))
        self.failUnlessRaises(CobblerException, system.set_profile, "profiledoesntexist")
        self.failUnlessRaises(CobblerException, self.api.add_system, system)

class SyncContents(BootTest):

    def test_blender_cache_works(self):

        # this is just a file that exists that we don't have to create
        fake_file = "/etc/hosts"

        distro = self.api.new_distro()
        self.assertTrue(distro.set_name("D1"))
        self.assertTrue(distro.set_kernel(fake_file))
        self.assertTrue(distro.set_initrd(fake_file))
        self.assertTrue(self.api.add_distro(distro))
        self.assertTrue(self.api.find_distro(name="D1"))

        profile = self.api.new_profile()
        self.assertTrue(profile.set_name("P1"))
        self.assertTrue(profile.set_distro("D1"))
        self.assertTrue(profile.set_kickstart(fake_file))
        self.assertTrue(self.api.add_profile(profile))
        assert self.api.find_profile(name="P1") != None

        system = self.api.new_system()
        self.assertTrue(system.set_name("S1"))
        self.assertTrue(system.set_mac_address("BB:EE:EE:EE:EE:FF","intf0"))
        self.assertTrue(system.set_profile("P1"))
        self.assertTrue(self.api.add_system(system))
        assert self.api.find_system(name="S1") != None

        # ensure that the system after being added has the right template data
        # in /tftpboot

        converted="01-bb-ee-ee-ee-ee-ff"

        if os.path.exists("/var/lib/tftpboot"):
            fh = open("/var/lib/tftpboot/pxelinux.cfg/%s" % converted)
        else:
            fh = open("/tftpboot/pxelinux.cfg/%s" % converted)

        data = fh.read()
        self.assertTrue(data.find("/op/ks/") != -1)
        fh.close()

        # ensure that after sync is applied, the blender cache still allows
        # the system data to persist over the profile data in /tftpboot
        # (which was an error we had in 0.6.3)

        self.api.sync()
        if os.path.exists("/var/lib/tftpboot"):
            fh = open("/var/lib/tftpboot/pxelinux.cfg/%s" % converted)
        else:
            fh = open("/tftpboot/pxelinux.cfg/%s" % converted)
        data = fh.read()
        print "DEBUG DATA: %s" % data
        self.assertTrue(data.find("/op/ks/") != -1)
        fh.close()


class Deletions(BootTest):

    def test_invalid_delete_profile_doesnt_exist(self):
        self.failUnlessRaises(CobblerException, self.api.profiles().remove, "doesnotexist")

    def test_invalid_delete_profile_would_orphan_systems(self):
        self.failUnlessRaises(CobblerException, self.api.profiles().remove, "testprofile0")

    def test_invalid_delete_system_doesnt_exist(self):
        self.failUnlessRaises(CobblerException, self.api.systems().remove, "doesnotexist")

    def test_invalid_delete_distro_doesnt_exist(self):
        self.failUnlessRaises(CobblerException, self.api.distros().remove, "doesnotexist")

    def test_invalid_delete_distro_would_orphan_profile(self):
        self.failUnlessRaises(CobblerException, self.api.distros().remove, "testdistro0")

    #def test_working_deletes(self):
    #    self.api.clear()
    #    # self.make_basic_config()
    #    #self.assertTrue(self.api.systems().remove("testsystem0"))
    #    self.api.serialize()
    #    self.assertTrue(self.api.remove_profile("testprofile0"))
    #    self.assertTrue(self.api.remove_distro("testdistro0"))
    #    #self.assertFalse(self.api.find_system(name="testsystem0"))
    #    self.assertFalse(self.api.find_profile(name="testprofile0"))
    #    self.assertFalse(self.api.find_distro(name="testdistro0"))

class TestCheck(BootTest):

   def test_check(self):
       # we can't know if it's supposed to fail in advance
       # (ain't that the halting problem), but it shouldn't ever
       # throw exceptions.
       self.api.check()

class TestSync(BootTest):

   def test_real_run(self):
       # syncing a real test run in an automated environment would
       # break a valid cobbler configuration, so we're not going to
       # test this here.
       pass

class TestListings(BootTest):

   def test_listings(self):
       # check to see if the collection listings output something.
       # this is a minimal check, mainly for coverage, not validity
       # self.make_basic_config()
       self.assertTrue(len(self.api.systems().printable()) > 0)
       self.assertTrue(len(self.api.profiles().printable()) > 0)
       self.assertTrue(len(self.api.distros().printable()) > 0)

#class TestCLIBasic(BootTest):
#
#   def test_cli(self):
#       # just invoke the CLI to increase coverage and ensure
#       # nothing major is broke at top level.  Full CLI command testing
#       # is not included (yet) since the API tests hit that fairly throughly
#       # and it would easily double the length of the tests.
#       app = "/usr/bin/python"
#       self.assertTrue(subprocess.call([app,"cobbler/cobbler.py","list"]) == 0)

if __name__ == "__main__":
    if not os.path.exists("setup.py"):
        print "tests: must invoke from top level directory"
        sys.exit(1)
    loader = unittest.defaultTestLoader
    test_module = __import__("tests")  # self import considered harmful?
    tests = loader.loadTestsFromModule(test_module)
    runner = unittest.TextTestRunner()
    runner.run(tests)
    sys.exit(0)
 
