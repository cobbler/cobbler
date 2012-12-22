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
   server = None
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
