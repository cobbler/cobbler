import os
import re
import shlex
import unittest

from cobbler import utils


def run_cmd(cmd):
    '''
    Run a command

    @param string cmd command
    @return tuple(string, int) output and return code
    '''

    args = shlex.split(cmd)
    return utils.subprocess_sp(None, args, shell=False)

def get_last_line(lines):

    i = len(lines)-1
    while lines[i] == '' and i > 0:
        i -= 1

    return lines[i]

class CobblerCLITest_Direct(unittest.TestCase):
   """
   Tests Cobbler CLI direct commands
   """

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

   def test_00_cobbler_version(self):
      """Runs 'cobbler version'"""
      (output, rc) = run_cmd("cobbler version")
      self.assertEqual(rc, 0)
      line = output.split("\n")[0]
      match_obj = re.match("Cobbler \d+\.\d+\.\d+", line)
      self.assertTrue(match_obj is not None)

   def test_01_cobbler_status(self):
      """Runs 'cobbler status'"""
      (output, rc) = run_cmd("cobbler status")
      self.assertEqual(rc, 0)
      lines = output.split("\n")
      match_obj = re.match("ip\s+|target\s+|start\s+|state\s+", lines[0])
      self.assertTrue(match_obj is not None)

   def test_02_cobbler_sync(self):
      """Runs 'cobbler sync'"""
      (output, rc) = run_cmd("cobbler sync")
      self.assertEqual(rc, 0)
      lines = output.split("\n")
      self.assertEqual("*** TASK COMPLETE ***", get_last_line(lines))

   def test_03_cobbler_signature_report(self):
      """Runs 'cobbler signature report'"""
      (output, rc) = run_cmd("cobbler signature report")
      self.assertEqual(rc, 0)
      lines = output.split("\n")
      self.assertTrue("Currently loaded signatures:" == lines[0])
      expected_output = "\d+ breeds with \d+ total signatures loaded"
      match_obj = re.match(expected_output, get_last_line(lines))
      self.assertTrue(match_obj is not None)

   def test_04_cobbler_signature_update(self):
      """Runs 'cobbler signature update'"""
      (output, rc) = run_cmd("cobbler signature update")
      lines = output.split("\n")
      self.assertEqual(rc,0)
      self.assertEqual("*** TASK COMPLETE ***", get_last_line(lines))

   def test_05_cobbler_acl_adduser(self):
      """Runs 'cobbler aclsetup --adduser'"""
      (output, rc) = run_cmd("cobbler aclsetup --adduser=cobbler")
      self.assertEqual(rc, 0)
      # TODO: verify user acl exists on directories

   def test_06_cobbler_acl_addgroup(self):
      """Runs 'cobbler aclsetup --addgroup'"""
      (output, rc) = run_cmd("cobbler aclsetup --addgroup=cobbler")
      self.assertEqual(rc, 0)
      # TODO: verify group acl exists on directories

   def test_07_cobbler_acl_removeuser(self):
      """Runs 'cobbler aclsetup --removeuser'"""
      (output, rc) = run_cmd("cobbler aclsetup --removeuser=cobbler")
      self.assertEqual(rc, 0)
      # TODO: verify user acl no longer exists on directories

   def test_08_cobbler_acl_removegroup(self):
      """Runs 'cobbler aclsetup --removegroup'"""
      (output, rc) = run_cmd("cobbler aclsetup --removegroup=cobbler")
      self.assertEqual(rc,0)
      # TODO: verify group acl no longer exists on directories

   def test_09_cobbler_reposync(self):
      """Runs 'cobbler reposync'"""
      (output, rc) = run_cmd("cobbler reposync")
      self.assertEqual(rc,0)
      (output, rc) = run_cmd("cobbler reposync --tries=3")
      self.assertEqual(rc,0)
      (output, rc) = run_cmd("cobbler reposync --no-fail")
      self.assertEqual(rc,0)

def test_10_cobbler_buildiso(self):
      """Runs 'cobbler buildiso'"""

      (output, rc) = run_cmd("cobbler buildiso")
      self.assertEqual(rc,0)
      lines = output.split("\n")
      self.assertEqual("*** TASK COMPLETE ***", get_last_line(lines))
      self.assertTrue(os.path.isfile("/root/generated.iso"))

   def _assert_list_section(self, lines, start_line, section_name):

      i = start_line
      self.assertEqual(lines[i], "%s:" % section_name)
      i += 1
      while lines[i] != "":
         i += 1
      i += 1

      return i

   def test_11_cobbler_list(self):

      (output, rc) = run_cmd("cobbler list")
      self.assertEqual(rc,0)
      lines = output.split("\n")
      i = 0
      i = self._assert_list_section(lines, i, "distros")
      i = self._assert_list_section(lines, i, "profiles")
      i = self._assert_list_section(lines, i, "systems")
      i = self._assert_list_section(lines, i, "repos")
      i = self._assert_list_section(lines, i, "images")
      i = self._assert_list_section(lines, i, "mgmtclasses")
      i = self._assert_list_section(lines, i, "packages")
      i = self._assert_list_section(lines, i, "files")

   def _assert_report_section(self, lines, start_line, section_name):

      i = start_line
      self.assertEqual(lines[i], "%s:" % section_name)
      i += 1
      match_obj = re.match("=+$", lines[i].strip())
      self.assertTrue(match_obj is not None)
      i += 1
      while i < len(lines)-1 and re.match("=+$", lines[i+1]) is None:
          while i < len(lines) and lines[i] != "":
             i += 1
          while i < len(lines) and lines[i] == "":
             i += 1

      return i

   def test_12_cobbler_report(self):
      (output, rc) = run_cmd("cobbler report")
      self.assertEqual(rc,0)
      lines = output.split("\n")
      i = 0
      i = self._assert_report_section(lines, i, "distros")
      i = self._assert_report_section(lines, i, "profiles")
      i = self._assert_report_section(lines, i, "systems")
      i = self._assert_report_section(lines, i, "repos")
      i = self._assert_report_section(lines, i, "images")
      i = self._assert_report_section(lines, i, "mgmtclasses")
      i = self._assert_report_section(lines, i, "packages")
      i = self._assert_report_section(lines, i, "files")

   def test_13_cobbler_getloaders(self):
      (output, rc) = run_cmd("cobbler get-loaders")
      lines = output.split("\n")
      self.assertEqual(rc,0)
      self.assertEqual("*** TASK COMPLETE ***", get_last_line(lines))

   # @IMPROVEMENT test cobbler validateks
   # @IMPROVEMENT test cobbler hardlink
   # @IMPROVEMENT test cobbler replicate. Requires 2 test cobbler servers
