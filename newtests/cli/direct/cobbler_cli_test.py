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

class Test_Direct(CobblerCLITest):
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
   def test_02_cobbler_sync(self):
      """Runs 'cobbler sync'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","sync"],shell=False)
      self.assertEqual(rc,0)
   def test_03_cobbler_signature_report(self):
      """Runs 'cobbler signature report'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","signature","report"],shell=False)
      self.assertEqual(rc,0)
   def test_04_cobbler_signature_update(self):
      """Runs 'cobbler signature update'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","signature","update"],shell=False)
      self.assertEqual(rc,0)
   def test_05_cobbler_acl_adduser(self):
      """Runs 'cobbler aclsetup --adduser'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","aclsetup","--adduser=cobbler"],shell=False)
      self.assertEqual(rc,0)
      # TODO: verify user acl exists on directories
   def test_06_cobbler_acl_addgroup(self):
      """Runs 'cobbler aclsetup --addgroup'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","aclsetup","--addgroup=cobbler"],shell=False)
      self.assertEqual(rc,0)
      # TODO: verify group acl exists on directories
   def test_07_cobbler_acl_removeuser(self):
      """Runs 'cobbler aclsetup --removeuser'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","aclsetup","--removeuser=cobbler"],shell=False)
      self.assertEqual(rc,0)
      # TODO: verify user acl no longer exists on directories
   def test_08_cobbler_acl_removegroup(self):
      """Runs 'cobbler aclsetup --removegroup'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","aclsetup","--removegroup=cobbler"],shell=False)
      self.assertEqual(rc,0)
      # TODO: verify group acl no longer exists on directories
   def test_09_cobbler_reposync(self):
      """Runs 'cobbler reposync'"""
      (data,rc) = utils.subprocess_sp(None,["cobbler","reposync"],shell=False)
      self.assertEqual(rc,0)
      (data,rc) = utils.subprocess_sp(None,["cobbler","reposync","--tries=3"],shell=False)
      self.assertEqual(rc,0)
      (data,rc) = utils.subprocess_sp(None,["cobbler","reposync","--no-fail"],shell=False)
      self.assertEqual(rc,0)

