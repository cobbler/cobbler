import unittest
from .cobbler_xmlrpc_base_test import CobblerXmlRpcBaseTest


class TestMiscellaneous(CobblerXmlRpcBaseTest):
    """
    Class to test remote calls to cobbler which do not belong into a specific category.
    """

    def test_clear_system_logs(self):
        # TODO: test remote.clear_system_logs()
        raise NotImplementedError()

    def test_disable_netboot(self):
        # TODO: test remote.disable_netboot()
        raise NotImplementedError()

    def test_extended_version(self):
        # TODO: test remote.extended_version()
        raise NotImplementedError()

    def test_find_items_paged(self):
        # TODO: test remote.find_items_paged()
        raise NotImplementedError()

    def test_find_system_by_dns_name(self):
        # TODO: test remote.find_system_by_dns_name()
        raise NotImplementedError()

    def test_generatescript(self):
        # TODO: test remote.generatescript()
        raise NotImplementedError()

    def test_get_item_as_rendered(self):
        # TODO: test remote.get_<item>_as_rendered()
        raise NotImplementedError()

    def test_get_s_since(self):
        # TODO: test remote.get_<item>s_since()
        raise NotImplementedError()

    def test_get_authn_module_name(self):
        # TODO: test remote.get_authn_module_name()
        raise NotImplementedError()

    def test_get_blended_data(self):
        # TODO: test remote.get_blended_data()
        raise NotImplementedError()

    def test_get_config_data(self):
        # TODO: test remote.get_config_dataa()
        raise NotImplementedError()

    def test_get_repos_compatible_with_profile(self):
        # TODO: test remote.get_repos_compatible_with_profile()
        raise NotImplementedError()

    def test_get_status(self):
        # TODO: test remote.get_status()
        raise NotImplementedError()

    def test_get_template_file_for_profile(self):
        # TODO: test remote.get_template_file_for_profile()
        raise NotImplementedError()

    def test_get_template_file_for_system(self):
        # TODO: test remote.get_template_file_for_system()
        raise NotImplementedError()

    def test_is_kickstart_in_use(self):
        # TODO: test remote.is_kickstart_in_use()
        raise NotImplementedError()

    def test_logout(self):
        # TODO: test remote.logout()
        raise NotImplementedError()

    def test_modify_setting(self):
        # TODO: test remote.modify_setting()
        raise NotImplementedError()

    def test_read_or_write_kickstart_template(self):
        # TODO: test remote.read_or_write_kickstart_template()
        raise NotImplementedError()

    def test_read_or_write_snippet(self):
        # TODO: test remote.read_or_write_snippet()
        raise NotImplementedError()

    def test_run_install_triggers(self):
        # TODO: test remote.run_install_triggers()
        raise NotImplementedError()

    def test_version(self):
        # TODO: test remote.version()
        raise NotImplementedError()

    def test_xapi_object_edit(self):
        # TODO: test remote.xapi_object_edit()
        raise NotImplementedError()


if __name__ == '__main__':
    unittest.main()
