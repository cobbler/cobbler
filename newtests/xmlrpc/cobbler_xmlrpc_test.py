import logging
import os
import random
import sys
import time
import unittest
import xmlrpclib

from cobbler import utils
from cobbler import item_distro
import cexceptions

FAKE_INITRD="initrd-2.6.15-1.2054_FAKE.img"
FAKE_INITRD2="initrd-2.5.16-2.2055_FAKE.img"
FAKE_INITRD3="initrd-1.8.18-3.9999_FAKE.img"
FAKE_KERNEL="vmlinuz-2.6.15-1.2054_FAKE"
FAKE_KERNEL2="vmlinuz-2.5.16-2.2055_FAKE"
FAKE_KERNEL3="vmlinuz-1.8.18-3.9999_FAKE"

cleanup_dirs = []

class CobblerXMLRPCTest(unittest.TestCase):
   server = None

   def setUp(self):
      """
      Sets up Cobbler API connection and logs in
      """

      logging.basicConfig( stream=sys.stderr )
      self.logger = logging.getLogger( self.__class__.__name__ )
      self.logger.setLevel( logging.DEBUG )

      self.url_api = utils.local_get_cobbler_api_url()
      self.url_xmlrpc = utils.local_get_cobbler_xmlrpc_url()
      self.remote = xmlrpclib.Server(self.url_api)
      self.shared_secret = utils.get_shared_secret()

      self.token  = self.remote.login("", self.shared_secret)
      if not self.token:
         self.server.stop()
         sys.exit(1)

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

      self.redhat_kickstart = os.path.join(self.topdir, "test.ks")
      self.ubuntu_preseed = os.path.join(self.topdir, "test.seed")

      create = [ 
         self.fk_initrd, self.fk_initrd2, self.fk_initrd3,
         self.fk_kernel, self.fk_kernel2, self.fk_kernel3, 
         self.redhat_kickstart, self.ubuntu_preseed,
      ]
      for fn in create:
         f = open(fn,"w+")
         f.close()

      self.distro_fields = [
        # TODO: fetchable files, boot files, etc.
        # field_name, good value(s), bad value(s)
        # ["",["",],["",]],
        ["name",["testdistro0",],[]],
        ["kernel",[self.fk_kernel,],["",]],
        ["initrd",[self.fk_initrd,],["",]],
        ["breed",["generic",],["badversion",]],
        ["os_version",["generic26",],["bados",]],
        ["arch",["i386","x86_64","ppc","ppc64"],["badarch",]],
        ["comment",["test comment",],[]],
        ["owners",["user1 user2 user3",],[]],
        ["kernel_options",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
        ["kernel_options_post",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
        ["ks_meta",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
        ["mgmt_classes",["one two three",],[]],
        ["redhat_management_key",["abcd1234",],[]],
        ["redhat_management_server",["1.1.1.1",],[]],
      ]

      self.profile_fields = [
        # TODO: fetchable files, boot files, etc.
        #       repos, which have to exist
        # field_name, good value(s), bad value(s)
        # ["",["",],["",]],
        ["name",["testprofile0",],[]],
        ["distro",["testdistro0",],["baddistro",]],
        ["enable_gpxe",["yes","YES","1","0","no"],[]],
        ["enable_menu",["yes","YES","1","0","no"],[]],
        ["comment",["test comment",],[]],
        ["owners",["user1 user2 user3",],[]],
        ["kernel_options",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
        ["kernel_options_post",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
        ["ks_meta",["a=1 b=2 c=3 c=4 c=5 d e",],[]],
        ["kickstart",[self.redhat_kickstart,self.ubuntu_preseed],["/path/to/bad/kickstart",]],
        ["proxy",["testproxy",],[]],
        ["virt_auto_boot",["1","0"],["yes","no"]],
        ["virt_cpus",["<<inherit>>","1","2"],["a",]],
        ["virt_file_size",["<<inherit>>","5","10"],["a",]],
        ["virt_disk_driver",["<<inherit>>","raw","qcow2","vmdk"],[]],
        ["virt_ram",["<<inherit>>","256","1024"],["a",]],
        ["virt_type",["<<inherit>>","xenpv","xenfv","qemu","kvm","vmware","openvz"],["bad",]],
        ["virt_bridge",["<<inherit>>","br0","virbr0","xenbr0"],[]],
        ["virt_path",["<<inherit>>","/path/to/test",],[]],
        ["dhcp_tag",["","foo"],[]],
        ["server",["1.1.1.1",],[]],
        ["name_servers",["1.1.1.1 1.1.1.2 1.1.1.3",],[]],
        ["name_servers_search",["example.com foo.bar.com",],[]],
        ["mgmt_classes",["one two three",],[]],
        ["mgmt_parameters",["<<inherit>>",],["badyaml",]], # needs more test cases that are valid yaml
        ["redhat_management_key",["abcd1234",],[]],
        ["redhat_management_server",["1.1.1.1",],[]],
        ["template_remote_kickstarts",["yes","YES","1","0","no"],[]],
      ]
   def tearDown(self):
      """
      Cleanup here
      """
      return

class Test_A_Create(CobblerXMLRPCTest):
   """
   Tests creation of objects
   """
   def test_00_create_distro(self):
      """Tests creation of a distro object"""
      distro = self.remote.new_distro(self.token)
      for field in self.distro_fields:
         (fname,fgood,fbad) = field
         for fb in fbad:
             try:
                self.remote.modify_distro(distro,fname,fb,self.token)
             except:
                pass
             else:
                self.fail("bad field (%s=%s) did not raise an exception" % (fname,fb))
         for fg in fgood:
             try:
                self.assertTrue(self.remote.modify_distro(distro,fname,fg,self.token))
             except:
                self.fail("good field (%s=%s) raised an exception" % (fname,fg))
      self.assertTrue(self.remote.save_distro(distro,self.token))

   def test_01_create_profile(self):
      """Tests creation of a profile object"""
      profile = self.remote.new_profile(self.token)
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
             except:
                self.fail("good field (%s=%s) raised an exception" % (fname,fg))
      self.assertTrue(self.remote.save_profile(profile,self.token))

   def test_02_create_subprofile(self):
      """Tests creation of a subprofile object"""
      subprofile = self.remote.new_subprofile(self.token)
      self.assertTrue(self.remote.modify_profile(subprofile,"name","testsubprofile0",self.token))
      self.assertTrue(self.remote.modify_profile(subprofile,"parent","testprofile0",self.token))
      # test fields
      #for field in item_profile.FIELDS:
      #   (fname,def1,def2,display,editable,tooltip,values,type) = field
      #   if fname not in ["name","distro","parent"] and editable:
      #      if values and isinstance(values,list):
      #         fvalue = random.choice(values)
      #      else:
      #          fvalue = "testing_" + fname
      #      self.assertTrue(self.remote.modify_profile(subprofile,fname,fvalue,self.token))
      self.assertTrue(self.remote.save_profile(subprofile,self.token))

   def test_03_create_system(self):
      """Tests creation of a system object"""
      system = self.remote.new_system(self.token)
      self.assertTrue(self.remote.modify_system(system,"name","testsystem0",self.token))
      self.assertTrue(self.remote.modify_system(system,"profile","testprofile0",self.token))
      # test fields
      #for field in item_system.FIELDS:
      #   (fname,def1,def2,display,editable,tooltip,values,type) = field
      #   if fname not in ["name","profile"] and editable:
      #      if values and isinstance(values,list):
      #         fvalue = random.choice(values)
      #      else:
      #          fvalue = "testing_" + fname
      #      self.assertTrue(self.remote.modify_system(system,fname,fvalue,self.token))
      self.assertTrue(self.remote.save_system(system,self.token))

   def test_04_create_repo(self):
      """Tests creation of a repo object"""
      repo = self.remote.new_repo(self.token)
      self.assertTrue(self.remote.modify_repo(repo,"name","testrepo0",self.token))
      self.assertTrue(self.remote.modify_repo(repo,"mirror","http://www.sample.com/path/to/some/repo",self.token))
      self.assertTrue(self.remote.modify_repo(repo,"mirror_locally","0",self.token))
      # test fields
      #for field in item_repo.FIELDS:
      #   (fname,def1,def2,display,editable,tooltip,values,type) = field
      #   if fname not in ["name",] and editable:
      #      if values and isinstance(values,list):
      #         fvalue = random.choice(values)
      #      else:
      #          fvalue = "testing_" + fname
      #      self.assertTrue(self.remote.modify_repo(repo,fname,fvalue,self.token))
      self.assertTrue(self.remote.save_repo(repo,self.token))

   def test_05_create_mgmtclass(self):
      """Tests creation of a mgmtclass object"""
      mgmtclass = self.remote.new_mgmtclass(self.token)
      self.assertTrue(self.remote.modify_mgmtclass(mgmtclass,"name","testmgmtclass0",self.token))
      # test fields
      #for field in item_mgmtclass.FIELDS:
      #   (fname,def1,def2,display,editable,tooltip,values,type) = field
      #   if fname not in ["name",] and editable:
      #      if values and isinstance(values,list):
      #         fvalue = random.choice(values)
      #      else:
      #          fvalue = "testing_" + fname
      #      self.assertTrue(self.remote.modify_mgmtclass(mgmtclass,fname,fvalue,self.token))
      self.assertTrue(self.remote.save_mgmtclass(mgmtclass,self.token))

   def test_06_create_image(self):
      """Tests creation of an image object"""
      image = self.remote.new_image(self.token)
      self.assertTrue(self.remote.modify_image(image,"name","testimage0",self.token))
      # test fields
      #for field in item_image.FIELDS:
      #   (fname,def1,def2,display,editable,tooltip,values,type) = field
      #   if fname not in ["name",] and editable:
      #      if values and isinstance(values,list):
      #         fvalue = random.choice(values)
      #      else:
      #          fvalue = "testing_" + fname
      #      self.assertTrue(self.remote.modify_image(image,fname,fvalue,self.token))
      self.assertTrue(self.remote.save_image(image,self.token))

   def test_07_create_file(self):
      """Tests creation of a file object"""
      #file = self.remote.new_file(self.token)
      #self.assertTrue(self.remote.modify_file(file,"name","testfile0",self.token))
      # test fields
      #for field in item_file.FIELDS:
      #   (fname,def1,def2,display,editable,tooltip,values,type) = field
      #   if fname not in ["name",] and editable:
      #      if values and isinstance(values,list):
      #         fvalue = random.choice(values)
      #      else:
      #          fvalue = "testing_" + fname
      #      self.assertTrue(self.remote.modify_file(file,fname,fvalue,self.token))
      #self.assertTrue(self.remote.save_file(file,self.token))
      pass

   def test_08_create_package(self):
      """Tests creation of a package object"""
      pass

class Test_B_Get(CobblerXMLRPCTest):
   """
   Tests the get_ calls for various objects
   """
   def test_00_get_distro(self):
      """Get a distro object"""
      pass
   def test_01_get_profile(self):
      """Get a profile object"""
      pass
   def test_02_get_system(self):
      """Get a system object"""
      pass
   def test_03_get_repo(self):
      """Get a repo object"""
      pass
   def test_04_get_mgmtclass(self):
      """Get a mgmtclass object"""
      pass
   def test_05_get_image(self):
      """Get an image object"""
      pass
   def test_06_get_file(self):
      """Get a file object"""
      pass
   def test_07_get_package(self):
      """Get a package object"""
      pass
   def test_08_generic_get(self):
      """Get an object using the generic get_item() call"""
      pass

class Test_C_Find(CobblerXMLRPCTest):
   """
   Tests the remote find_ calls for various objects
   """
   def test_00_find_distro(self):
      """Finding a distro object"""
      self.assertTrue(self.remote.find_distro({"name":"testdistro0"},self.token))
   def test_01_find_profile(self):
      """Finding a profile object"""
      self.assertTrue(self.remote.find_profile({"name":"testprofile0"},self.token))
   def test_02_find_system(self):
      """Finding a system object"""
      self.assertTrue(self.remote.find_system({"name":"testsystem0"},self.token))
   def test_03_find_repo(self):
      """Finding a repo object"""
      self.assertTrue(self.remote.find_repo({"name":"testrepo0"},self.token))
   def test_04_find_mgmtclass(self):
      """Finding a mgmtclass object"""
      self.assertTrue(self.remote.find_mgmtclass({"name":"testmgmtclass0"},self.token))
   def test_05_find_image(self):
      """Finding an image object"""
      self.assertTrue(self.remote.find_image({"name":"testimage0"},self.token))
   def test_06_find_file(self):
      """Finding a file object"""
      #self.assertTrue(self.remote.find_file({"name":"testfile0"},self.token))
      pass
   def test_07_find_package(self):
      """Finding a package object"""
      pass
   def test_08_find_system_by_dnsname(self):
      """Finding a system by its dns name"""
      pass
   def test_09_generic_find(self):
      """Finding items using generic item_find() call"""
      pass


class Test_D_Edit(CobblerXMLRPCTest):
   """
   Tests the remote edit_ and save_ calls for objects
   """
   def test_00_edit_distro(self):
      """Editing a distro object"""
      pass
   def test_01_edit_profile(self):
      """Editing a profile object"""
      pass
   def test_02_edit_system(self):
      """Editing a system object"""
      pass
   def test_03_edit_repo(self):
      """Editing a repo object"""
      pass
   def test_04_edit_mgmtclass(self):
      """Editing a mgmtclass object"""
      pass
   def test_05_edit_image(self):
      """Editing an image object"""
      pass
   def test_06_edit_file(self):
      """Editing a file object"""
      pass
   def test_07_edit_package(self):
      """Editing a package object"""
      pass

class Test_E_Copy(CobblerXMLRPCTest):
   """
   Tests the remote copy_ calls for various objects
   """
   def test_00_copy_distro(self):
      """Copying a distro object"""
      distro = self.remote.get_item_handle("distro","testdistro0",self.token)
      self.assertTrue(self.remote.copy_distro(distro,"testdistrocopy",self.token))
   def test_01_copy_profile(self):
      """Copying a profile object"""
      profile = self.remote.get_item_handle("profile","testprofile0",self.token)
      self.assertTrue(self.remote.copy_profile(profile,"testprofilecopy",self.token))
   def test_02_copy_system(self):
      """Copying a system object"""
      system = self.remote.get_item_handle("system","testsystem0",self.token)
      self.assertTrue(self.remote.copy_system(system,"testsystemcopy",self.token))
   def test_03_copy_repo(self):
      """Copying a repo object"""
      repo = self.remote.get_item_handle("repo","testrepo0",self.token)
      self.assertTrue(self.remote.copy_repo(repo,"testrepocopy",self.token))
   def test_04_copy_mgmtclass(self):
      """Copying a mgmtclass object"""
      mgmtclass = self.remote.get_item_handle("mgmtclass","testmgmtclass0",self.token)
      self.assertTrue(self.remote.copy_mgmtclass(mgmtclass,"testmgmtclasscopy",self.token))
   def test_05_copy_image(self):
      """Copying an image object"""
      image = self.remote.get_item_handle("image","testimage0",self.token)
      self.assertTrue(self.remote.copy_image(image,"testimagecopy",self.token))
   def test_06_copy_file(self):
      """Copying a file object"""
      #testfile = self.remote.get_item_handle("file","testfile0",self.token)
      #self.assertTrue(self.remote.copy_file(testfile,"testfilecopy",self.token))
      pass
   def test_07_copy_package(self):
      """Copying a package object"""
      pass

class Test_F_Rename(CobblerXMLRPCTest):
   """
   Tests the remote rename_ calls for various objects
   """
   def test_00_rename_distro(self):
      """Renaming a distro object"""
      distro = self.remote.get_item_handle("distro","testdistrocopy",self.token)
      self.assertTrue(self.remote.rename_distro(distro,"testdistro1",self.token))
   def test_01_rename_profile(self):
      """Renaming a profile object"""
      profile = self.remote.get_item_handle("profile","testprofilecopy",self.token)
      self.assertTrue(self.remote.rename_profile(profile,"testprofile1",self.token))
   def test_02_rename_system(self):
      """Renaming a system object"""
      system = self.remote.get_item_handle("system","testsystemcopy",self.token)
      self.assertTrue(self.remote.rename_system(system,"testsystem1",self.token))
   def test_03_rename_repo(self):
      """Renaming a repo object"""
      repo = self.remote.get_item_handle("repo","testrepocopy",self.token)
      self.assertTrue(self.remote.rename_repo(repo,"testrepo1",self.token))
   def test_04_rename_mgmtclass(self):
      """Renaming a mgmtclass object"""
      mgmtclass = self.remote.get_item_handle("mgmtclass","testmgmtclasscopy",self.token)
      self.assertTrue(self.remote.rename_mgmtclass(mgmtclass,"testmgmtclass1",self.token))
   def test_05_rename_image(self):
      """Renaming an image object"""
      image = self.remote.get_item_handle("image","testimagecopy",self.token)
      self.assertTrue(self.remote.rename_image(image,"testimage1",self.token))
   def test_06_rename_file(self):
      """Renaming a file object"""
      #testfile = self.remote.get_item_handle("file","testfilecopy",self.token)
      #self.assertTrue(self.remote.rename_file(testfile,"testfile1",self.token))
      pass
   def test_07_rename_package(self):
      """Renaming a package object"""
      pass

class Test_G_Remove(CobblerXMLRPCTest):
   """
   Tests the remote remove_ calls for various objects
   Removals happen backwards, to prevent recurisive deletes
   """
   def test_99_remove_distro(self):
      """Removing a distro object"""
      self.assertTrue(self.remote.remove_distro("testdistro0",self.token))
      self.assertTrue(self.remote.remove_distro("testdistro1",self.token))
   def test_98_remove_profile(self):
      """Removing a profile object"""
      self.assertTrue(self.remote.remove_profile("testsubprofile0",self.token))
      self.assertTrue(self.remote.remove_profile("testprofile0",self.token))
      self.assertTrue(self.remote.remove_profile("testprofile1",self.token))
   def test_97_remove_system(self):
      """Removing a system object"""
      self.assertTrue(self.remote.remove_system("testsystem0",self.token))
      self.assertTrue(self.remote.remove_system("testsystem1",self.token))
   def test_96_remove_image(self):
      """Removing an image object"""
      self.assertTrue(self.remote.remove_image("testimage0",self.token))
      self.assertTrue(self.remote.remove_image("testimage1",self.token))
   def test_95_remove_repo(self):
      """Removing a repo object"""
      self.assertTrue(self.remote.remove_repo("testrepo0",self.token))
      self.assertTrue(self.remote.remove_repo("testrepo1",self.token))
   def test_94_remove_mgmtclass(self):
      """Removing a mgmtclass object"""
      self.assertTrue(self.remote.remove_mgmtclass("testmgmtclass0",self.token))
      self.assertTrue(self.remote.remove_mgmtclass("testmgmtclass1",self.token))
   def test_93_remove_file(self):
      """Removing a file object"""
      #self.assertTrue(self.remote.remove_file("testfile0",self.token))
      #self.assertTrue(self.remote.remove_file("testfile1",self.token))
      pass
   def test_92_remove_package(self):
      """Removing a package object"""
      pass

class Test_H_RegularCalls(CobblerXMLRPCTest):
   def test_00_token(self):
      """
      Check if the authenticated token is valid
      """
      assert self.token not in ("",None)

   def test_01_get_user_from_token(self):
      """
      Gets the associated user from the token
      """
      self.assertTrue(self.remote.get_user_from_token(self.token))

   def test_02_check(self):
      """
      Execute the remote check call
      """
      self.assertTrue(self.remote.check(self.token))

   def test_03_last_modified_time(self):
      """
      Execute the remote last_modified_time call
      """
      # should return a short time, if the setup
      # phase went ok
      assert self.remote.last_modified_time(self.token) != 0

