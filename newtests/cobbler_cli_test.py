import os
import sys
import unittest

from cobbler import utils

FAKE_INITRD="initrd-2.6.15-1.2054_FAKE.img"
FAKE_INITRD2="initrd-2.5.16-2.2055_FAKE.img"
FAKE_INITRD3="initrd-1.8.18-3.9999_FAKE.img"
FAKE_KERNEL="vmlinuz-2.6.15-1.2054_FAKE"
FAKE_KERNEL2="vmlinuz-2.5.16-2.2055_FAKE"
FAKE_KERNEL3="vmlinuz-1.8.18-3.9999_FAKE"

cleanup_dirs = []

class CobblerCLITest(unittest.TestCase):
   def setUp(self):
      """
      Set up
      """
      return

   def tearDown(self):
      """
      Cleanup here
      """
      return

class Test_A_Direct(CobblerCLITest):
   """
   Tests cobbler direct commands
   """
   def test_00_cobbler_version(self):
      """Runs 'cobbler version'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","version"],shell=False)
      self.assertEqual(rc,0)
   def test_01_cobbler_status(self):
      """Runs 'cobbler status'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","status"],shell=False)
      self.assertEqual(rc,0)

class CobblerImportTest(unittest.TestCase):
   imported_distros = []
   def setUp(self):
      """
      Set up, mounts NFS share
      """
      (data,rc) = utils.subprocess_sp(None,["mount","-t","nfs4","jenkins.sngx.net:/home/shared/distros","/mnt"],shell=False)
      self.assertEqual(rc,0)
   def tearDown(self):
      """
      Cleanup here
      """
      for d in self.imported_distros:
         try:
             (data,rc) = utils.subprocess_sp(None,["cobbler","distro","remove","--name=%s" % d],shell=False)
         except:
             print "Failed to remove distro '%s' during cleanup" % d
      (data,rc) = utils.subprocess_sp(None,["umount","/mnt"],shell=False)
      self.assertEqual(rc,0)

class Test_B_Imports(CobblerImportTest):
   """
   Tests imports of various distros
   """
   def test_A_00_check_mount(self):
      """Validating remote mount location"""
      (data,rc) = utils.subprocess_sp(None,"mount | grep mnt | grep nfs4",shell=True)
      self.assertEqual(rc,0)

distros = [
 {"name":"rhel58-x86_64", "desc":"RHEL 5.8 x86_64", "path":"/mnt/rhel58_x86_64"},
 {"name":"rhel63-x86_64", "desc":"RHEL 6.3 x86_64", "path":"/mnt/rhel63_x86_64"},
 {"name":"centos63-x86_64", "desc":"CentOS 6.3 x86_64", "path":"/mnt/centos63_x86_64"},
 {"name":"sl62-x86_64", "desc":"Scientific Linux 6.2 x86_64", "path":"/mnt/sl62_x86_64"},
 {"name":"f16-x86_64", "desc":"Fedora 16 x86_64", "path":"/mnt/f16_x86_64"},
 {"name":"f17-x86_64", "desc":"Fedora 17 x86_64", "path":"/mnt/f17_x86_64"},
 {"name":"f18beta-x86_64", "desc":"Fedora 18 BETA(TC6) x86_64", "path":"/mnt/f18_beta_tc6_x86_64"},
 {"name":"ubuntu12.04-server-x86_64", "desc":"Ubuntu Precise (12.04) Server amd64", "path":"/mnt/ubuntu_1204_server_amd64"},
 {"name":"ubuntu12.04.1-server-i386", "desc":"Ubuntu Precise (12.04.1) Server i386", "path":"/mnt/ubuntu_1204_1_server_i386"},
 {"name":"ubuntu12.10-server-x86_64", "desc":"Ubuntu Quantal (12.10) Server amd64", "path":"/mnt/ubuntu_1210_server_amd64"},
 {"name":"ubuntu12.10-server-i386", "desc":"Ubuntu Quantal (12.10) Server i386", "path":"/mnt/ubuntu_1210_server_i386"},
 {"name":"debian_6.0.5-x86_64", "desc":"Debian Sarge (6.0.5) amd64", "path":"/mnt/debian_6.0.5_amd64"},
 {"name":"opensuse11.3-i386", "desc":"OpenSuSE 11.3 i586", "path":"/mnt/opensuse11.3_i586"},
 {"name":"opensuse11.4-x86_64", "desc":"OpenSuSE 11.4 x86_64", "path":"/mnt/opensuse11.4_x86_64"},
 {"name":"opensuse12.1-x86_64", "desc":"OpenSuSE 12.1 x86_64", "path":"/mnt/opensuse12.1_x86_64"},
 {"name":"opensuse12.2-i386", "desc":"OpenSuSE 12.2 i586", "path":"/mnt/opensuse12.2_i586"},
 {"name":"opensuse12.2-x86_64", "desc":"OpenSuSE 12.2 x86_64", "path":"/mnt/opensuse12.2_x86_64"},
 {"name":"sles11_sp2-i386", "desc":"SLES 11 SP2 i586", "path":"/mnt/sles11_sp2_i586"},
 {"name":"sles11_sp2-x86_64", "desc":"SLES 11 SP2 x86_64", "path":"/mnt/sles11_sp2_x86_64"},
 {"name":"sles11_sp2-ppc64", "desc":"SLES 11 SP2 ppc64", "path":"/mnt/sles11_sp2_ppc64"},
 {"name":"vmware_esx_4.0_u1-x86_64", "desc":"VMware ESX 4.0 update1", "path":"/mnt/vmware_esx_4.0_u1_208167_x86_64"},
 {"name":"vmware_esx_4.0_u2-x86_64", "desc":"VMware ESX 4.0 update2", "path":"/mnt/vmware_esx_4.0_u2_261974_x86_64"},
 {"name":"vmware_esxi4.1-x86_64", "desc":"VMware ESXi 4.1", "path":"/mnt/vmware_esxi4.1_348481_x86_64"},
 {"name":"vmware_esxi5.0-x86_64", "desc":"VMware ESXi 5.0", "path":"/mnt/vmware_esxi5.0_469512_x86_64"},
 {"name":"vmware_esxi5.1-x86_64", "desc":"VMware ESXi 5.1", "path":"/mnt/vmware_esxi5.1_799733_x86_64"},
 {"name":"freebsd8.2-x86_64", "desc":"FreeBSD 8.2 amd64", "path":"/mnt/freebsd8.2_amd64"},
 {"name":"freebsd8.3-x86_64", "desc":"FreeBSD 8.3 amd64", "path":"/mnt/freebsd8.3_amd64"},
 {"name":"freebsd9.0-i386", "desc":"FreeBSD 9.0 i386", "path":"/mnt/freebsd9.0_i386"},
 {"name":"freebsd9.0-x86_64", "desc":"FreeBSD 9.0 amd64", "path":"/mnt/freebsd9.0_amd64"},
]

def create_import_func(data):
   name = data["name"]
   desc = data["desc"]
   path = data["path"]
   def do_import(self):
      print "doing import, name=%s, desc=%s, path=%s" % (name,desc,path)
      (data,rc) = utils.subprocess_sp(None,["cobbler","import","--name=test-%s" % name,"--path=%s" % path],shell=False)
      print data
      self.assertEqual(rc,0)
      # TODO: scan output of import to build list of imported distros/profiles
      #       and compare to expected list. Then use that list to run reports 
      #       and for later cleanup
      (data,rc) = utils.subprocess_sp(None,["cobbler","distro","report","--name=test-%s" % name],shell=False)
      print data
      self.assertEqual(rc,0)
      (data,rc) = utils.subprocess_sp(None,["cobbler","profile","report","--name=test-%s" % name],shell=False)
      print data
      self.assertEqual(rc,0)
      (data,rc) = utils.subprocess_sp(None,["cobbler","distro","remove","--name=test-%s" % name],shell=False)
      print data
      self.assertEqual(rc,0)
   return do_import

for i in range(0,len(distros)):
   test_func = create_import_func(distros[i])
   test_func.__name__ = 'test_B_%02d_import_%s' % (i,distros[i]["name"])
   test_func.__doc__ = "Import of %s" % distros[i]["desc"]
   setattr(Test_B_Imports, test_func.__name__, test_func)
   del test_func
