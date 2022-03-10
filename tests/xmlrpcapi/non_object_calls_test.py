import pytest
import time
import re

TEST_POWER_MANAGEMENT = True
TEST_SYSTEM = ""


class TestNonObjectCalls:

    # TODO: Obsolete this method via a unittest method
    def _wait_task_end(self, tid, remote):
        """
        Wait until a task is finished
        """
        timeout = 0
        # "complete" is the constant: EVENT_COMPLETE from cobbler.remote
        while remote.get_task_status(tid)[2] != "complete":
            if remote.get_task_status(tid)[2] == "failed":
                pytest.fail("Task failed")
            print("task %s status: %s" % (tid, remote.get_task_status(tid)))
            time.sleep(5)
            timeout += 5
            if timeout == 60:
                raise Exception

    def test_token(self, token):
        """
        Test: authentication token validation
        """

        assert token not in ("", None)

    def test_get_user_from_token(self, remote, token):
        """
        Test: get user data from authentication token
        """

        assert remote.get_user_from_token(token)

    def test_check(self, remote, token):
        """
        Test: check Cobbler status
        """

        assert remote.check(token)

    def test_last_modified_time(self, remote, token):
        """
        Test: get last modification time
        """

        assert remote.last_modified_time(token) != 0

    def test_power_system(self, remote, token):
        """
        Test: reboot a system
        """

        if TEST_SYSTEM and TEST_POWER_MANAGEMENT:
            tid = remote.background_power_system({"systems": [TEST_SYSTEM], "power": "reboot"}, token)
            self._wait_task_end(tid, remote)

    def test_sync(self, remote, token):
        """
        Test: synchronize Cobbler internal data with managed services
        (dhcp, tftp, dns)
        """

        tid = remote.background_sync({}, token)
        events = remote.get_events(token)

        assert len(events) > 0

        self._wait_task_end(tid, remote)

        event_log = remote.get_event_log(tid)

    def test_get_autoinstall_templates(self, remote, token):
        """
        Test: get autoinstall templates
        """

        result = remote.get_autoinstall_templates(token)
        assert len(result) > 0

    def test_get_autoinstall_snippets(self, remote, token):
        """
        Test: get autoinstall snippets
        """

        result = remote.get_autoinstall_snippets(token)
        assert len(result) > 0

    def test_generate_autoinstall(self, remote):
        """
        Test: generate autoinstall content
        """

        if TEST_SYSTEM:
            remote.generate_autoinstall(None, TEST_SYSTEM)

    def test_generate_ipxe(self, remote):
        """
        Test: generate iPXE file content
        """

        if TEST_SYSTEM:
            remote.generate_ipxe(None, TEST_SYSTEM)

    def test_generate_bootcfg(self, remote):
        """
        Test: generate boot loader configuration file content
        """

        if TEST_SYSTEM:
            remote.generate_bootcfg(None, TEST_SYSTEM)

    def test_get_settings(self, remote, token):
        """
        Test: get settings
        """

        remote.get_settings(token)

    def test_get_signatures(self, remote, token):
        """
        Test: get distro signatures
        """

        remote.get_signatures(token)

    def test_get_valid_breeds(self, remote, token):
        """
        Test: get valid OS breeds
        """

        breeds = remote.get_valid_breeds(token)
        assert len(breeds) > 0

    def test_get_valid_os_versions_for_breed(self, remote, token):
        """
        Test: get valid OS versions for a OS breed
        """

        versions = remote.get_valid_os_versions_for_breed("generic", token)
        assert len(versions) > 0

    def test_get_valid_os_versions(self, remote, token):
        """
        Test: get valid OS versions
        """

        versions = remote.get_valid_os_versions(token)
        assert len(versions) > 0

    def test_get_random_mac(self, remote, token):
        """
        Test: get a random mac for a virtual network interface
        """

        mac = remote.get_random_mac("xen", token)
        hexa = "[0-9A-Fa-f]{2}"
        match_obj = re.match("%s:%s:%s:%s:%s:%s" % (hexa, hexa, hexa, hexa, hexa, hexa), mac)
        assert match_obj
