import os
import re
import shlex
import unittest
from cobbler import utils

dummy_file_path = "/root/dummy"


def run_cmd(cmd):
    """
    Run a command

    @param cmd str command
    @return str output
    @raise Exception if return code is not 0
    """

    print("run cmd: %s" % cmd)
    args = shlex.split(cmd)
    (output, rc) = utils.subprocess_sp(None, args, shell=False)
    if rc != 0:
        raise Exception
    return output


def get_last_line(lines):
    i = len(lines) - 1
    while lines[i] == '' and i > 0:
        i -= 1

    return lines[i]


class CobblerCliTestDirect(unittest.TestCase):
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

    def test_cobbler_version(self):
        """Runs 'cobbler version'"""
        output = run_cmd("cobbler version")
        line = output.split("\n")[0]
        match_obj = re.match(r"Cobbler \d+\.\d+\.\d+", line)
        self.assertTrue(match_obj is not None)

    def test_cobbler_status(self):
        """Runs 'cobbler status'"""
        output = run_cmd("cobbler status")
        lines = output.split("\n")
        match_obj = re.match(r"ip\s+|target\s+|start\s+|state\s+", lines[0])
        self.assertTrue(match_obj is not None)

    def test_cobbler_sync(self):
        """Runs 'cobbler sync'"""
        output = run_cmd("cobbler sync")
        lines = output.split("\n")
        self.assertEqual("*** TASK COMPLETE ***", get_last_line(lines))

    def test_cobbler_signature_report(self):
        """Runs 'cobbler signature report'"""
        output = run_cmd("cobbler signature report")
        lines = output.split("\n")
        self.assertTrue("Currently loaded signatures:" == lines[0])
        expected_output = r"\d+ breeds with \d+ total signatures loaded"
        match_obj = re.match(expected_output, get_last_line(lines))
        self.assertTrue(match_obj is not None)

    def test_cobbler_signature_update(self):
        """Runs 'cobbler signature update'"""
        output = run_cmd("cobbler signature update")
        lines = output.split("\n")
        self.assertEqual("*** TASK COMPLETE ***", get_last_line(lines))

    def test_cobbler_acl_adduser(self):
        """Runs 'cobbler aclsetup --adduser'"""
        output = run_cmd("cobbler aclsetup --adduser=cobbler")
        # TODO: verify user acl exists on directories

    def test_cobbler_acl_addgroup(self):
        """Runs 'cobbler aclsetup --addgroup'"""
        output = run_cmd("cobbler aclsetup --addgroup=cobbler")
        # TODO: verify group acl exists on directories

    def test_cobbler_acl_removeuser(self):
        """Runs 'cobbler aclsetup --removeuser'"""
        output = run_cmd("cobbler aclsetup --removeuser=cobbler")
        # TODO: verify user acl no longer exists on directories

    def test_cobbler_acl_removegroup(self):
        """Runs 'cobbler aclsetup --removegroup'"""
        output = run_cmd("cobbler aclsetup --removegroup=cobbler")
        # TODO: verify group acl no longer exists on directories

    def test_cobbler_reposync(self):
        """Runs 'cobbler reposync'"""
        output = run_cmd("cobbler reposync")
        output = run_cmd("cobbler reposync --tries=3")
        output = run_cmd("cobbler reposync --no-fail")

    def test_cobbler_buildiso(self):
        """Runs 'cobbler buildiso'"""

        output = run_cmd("cobbler buildiso")
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

        output = run_cmd("cobbler list")
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
        match_obj = re.match(r"=+$", lines[i].strip())
        self.assertTrue(match_obj is not None)
        i += 1
        while i < len(lines) - 1 and re.match(r"=+$", lines[i + 1]) is None:
            while i < len(lines) and lines[i] != "":
                i += 1
            while i < len(lines) and lines[i] == "":
                i += 1

        return i

    def test_cobbler_report(self):
        output = run_cmd("cobbler report")
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

    def test_cobbler_getloaders(self):
        output = run_cmd("cobbler get-loaders")
        lines = output.split("\n")
        self.assertEqual("*** TASK COMPLETE ***", get_last_line(lines))

    def test_cobbler_hardlink(self):
        # TODO: test cobbler hardlink
        raise NotImplementedError()

    def test_cobbler_replicate(self):
        # TODO: test cobbler replicate. Requires 2 test cobbler servers
        raise NotImplementedError()

    def test_cobbler_validate_autoinstalls(self):
        # TODO: test cobbler validateks
        raise NotImplementedError()


if __name__ == '__main__':
    unittest.main()
