import os
import re

import pytest

dummy_file_path = "/root/dummy"


@pytest.fixture(scope="function")
def get_last_line():
    def _get_last_line(lines):
        i = len(lines) - 1
        while lines[i] == '' and i > 0:
            i -= 1
        return lines[i]
    return _get_last_line


@pytest.fixture(scope="function")
def assert_list_section():
    def _assert_list_section(lines, start_line, section_name):
        i = start_line
        assert lines[i] == "%s:" % section_name
        i += 1
        while lines[i] != "":
            i += 1
        i += 1
        return i
    return _assert_list_section


@pytest.fixture(scope="function")
def assert_report_section():
    def _assert_report_section(lines, start_line, section_name):
        i = start_line
        assert lines[i] == "%s:" % section_name
        i += 1
        match_obj = re.match(r"=+$", lines[i].strip())
        assert match_obj is not None
        i += 1
        while i < len(lines) - 1 and re.match(r"=+$", lines[i + 1]) is None:
            while i < len(lines) and lines[i] != "":
                i += 1
            while i < len(lines) and lines[i] == "":
                i += 1
        return i
    return _assert_report_section


class TestCobblerCliTestDirect:
    """
    Tests Cobbler CLI direct commands
    """

    def test_cobbler_version(self, run_cmd):
        """Runs 'cobbler version'"""
        (outputstd, outputerr) = run_cmd(cmd=["version"])
        line = outputstd.split("\n")[0]
        match_obj = re.match(r"Cobbler \d+\.\d+\.\d+", line)
        assert match_obj is not None

    def test_cobbler_status(self, run_cmd):
        """Runs 'cobbler status'"""
        (outputstd, outputerr) = run_cmd(cmd=["status"])
        lines = outputstd.split("\n")
        match_obj = re.match(r"ip\s+|target\s+|start\s+|state\s+", lines[0])
        assert match_obj is not None

    def test_cobbler_sync(self, run_cmd, get_last_line):
        """Runs 'cobbler sync'"""
        (outputstd, outputerr) = run_cmd(cmd=["sync"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)

    def test_cobbler_sync_dns(self, run_cmd, get_last_line):
        """Runs 'cobbler sync --dns'"""
        (outputstd, outputerr) = run_cmd(cmd=["sync", "--dns"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)

    def test_cobbler_sync_dhcp(self, run_cmd, get_last_line):
        """Runs 'cobbler sync --dhcp'"""
        (outputstd, outputerr) = run_cmd(cmd=["sync", "--dhcp"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)

    def test_cobbler_sync_dhcp_dns(self, run_cmd, get_last_line):
        """Runs 'cobbler sync --dhcp --dns'"""
        (outputstd, outputerr) = run_cmd(cmd=["sync", "--dhcp", "--dns"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)

    def test_cobbler_sync_systems(self, run_cmd, get_last_line):
        """Runs 'cobbler sync'"""
        (outputstd, outputerr) = run_cmd(cmd=["sync", "--systems=a.b.c,a.d.c"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)

    def test_cobbler_signature_report(self, run_cmd, get_last_line):
        """Runs 'cobbler signature report'"""
        (outputstd, outputerr) = run_cmd(cmd=["signature", "report"])
        lines = outputstd.split("\n")
        assert "Currently loaded signatures:" == lines[0]
        expected_output = r"\d+ breeds with \d+ total signatures loaded"
        match_obj = re.match(expected_output, get_last_line(lines))
        assert match_obj is not None

    def test_cobbler_signature_update(self, run_cmd, get_last_line):
        """Runs 'cobbler signature update'"""
        (outputstd, outputerr) = run_cmd(cmd=["signature", "update"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)

    def test_cobbler_acl_adduser(self, run_cmd):
        """Runs 'cobbler aclsetup --adduser'"""
        (outputstd, outputerr) = run_cmd(cmd=["aclsetup", "--adduser=cobbler"])
        # TODO: verify user acl exists on directories

    def test_cobbler_acl_addgroup(self, run_cmd):
        """Runs 'cobbler aclsetup --addgroup'"""
        (outputstd, outputerr) = run_cmd(cmd=["aclsetup", "--addgroup=cobbler"])
        # TODO: verify group acl exists on directories

    def test_cobbler_acl_removeuser(self, run_cmd):
        """Runs 'cobbler aclsetup --removeuser'"""
        (outputstd, outputerr) = run_cmd(cmd=["aclsetup", "--removeuser=cobbler"])
        # TODO: verify user acl no longer exists on directories

    def test_cobbler_acl_removegroup(self, run_cmd):
        """Runs 'cobbler aclsetup --removegroup'"""
        (outputstd, outputerr) = run_cmd(cmd=["aclsetup", "--removegroup=cobbler"])
        # TODO: verify group acl no longer exists on directories

    def test_cobbler_reposync(self, run_cmd):
        """Runs 'cobbler reposync'"""
        (outputstd, outputerr) = run_cmd(cmd=["reposync"])
        (outputstd, outputerr) = run_cmd(cmd=["reposync", "--tries=3"])
        (outputstd, outputerr) = run_cmd(cmd=["reposync", "--no-fail"])

    @pytest.mark.skip("Currently the setup of this test is too complicated")
    def test_cobbler_buildiso(self, run_cmd, get_last_line):
        """Runs 'cobbler buildiso'"""

        (outputstd, outputerr) = run_cmd(cmd=["buildiso"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)
        assert os.path.isfile("/root/generated.iso")

    def test_11_cobbler_list(self, run_cmd, assert_list_section):
        (outputstd, outputerr) = run_cmd(cmd=["list"])
        lines = outputstd.split("\n")
        i = 0
        i = assert_list_section(lines, i, "distros")
        i = assert_list_section(lines, i, "profiles")
        i = assert_list_section(lines, i, "systems")
        i = assert_list_section(lines, i, "repos")
        i = assert_list_section(lines, i, "images")
        i = assert_list_section(lines, i, "mgmtclasses")
        i = assert_list_section(lines, i, "packages")
        i = assert_list_section(lines, i, "files")
        i = assert_list_section(lines, i, "menus")

    def test_cobbler_report(self, run_cmd, assert_report_section):
        (outputstd, outputerr) = run_cmd(cmd=["report"])
        lines = outputstd.split("\n")
        i = 0
        i = assert_report_section(lines, i, "distros")
        i = assert_report_section(lines, i, "profiles")
        i = assert_report_section(lines, i, "systems")
        i = assert_report_section(lines, i, "repos")
        i = assert_report_section(lines, i, "images")
        i = assert_report_section(lines, i, "mgmtclasses")
        i = assert_report_section(lines, i, "packages")
        i = assert_report_section(lines, i, "files")
        i = assert_report_section(lines, i, "menus")

    def test_cobbler_hardlink(self, run_cmd, get_last_line):
        (outputstd, outputerr) = run_cmd(cmd=["hardlink"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)

    @pytest.mark.skip("Currently the setup of this test is too complicated")
    def test_cobbler_replicate(self, run_cmd, get_last_line):
        (outputstd, outputerr) = run_cmd(cmd=["replicate"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)

    def test_cobbler_validate_autoinstalls(self, run_cmd, get_last_line):
        (outputstd, outputerr) = run_cmd(cmd=["validate-autoinstalls"])
        lines = outputstd.split("\n")
        assert "*** TASK COMPLETE ***" == get_last_line(lines)
