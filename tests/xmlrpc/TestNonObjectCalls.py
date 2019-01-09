import time
import re
from xmlrpc.CobblerXmlRpcBaseTest import CobblerXmlRpcBaseTest
from cobbler.remote import EVENT_COMPLETE

FAKE_INITRD = "initrd1.img"
FAKE_INITRD2 = "initrd2.img"
FAKE_INITRD3 = "initrd3.img"
FAKE_KERNEL = "vmlinuz1"
FAKE_KERNEL2 = "vmlinuz2"
FAKE_KERNEL3 = "vmlinuz3"
TEST_POWER_MANAGEMENT = True
TEST_SYSTEM = ""
cleanup_dirs = []


def tprint(call_name):
    """
    Print a remote call debug message

    @param call_name str remote call name
    """

    print("test remote call: %s()" % call_name)


class TestNonObjectCalls(CobblerXmlRpcBaseTest):

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

        assert self.token not in ("", None)

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