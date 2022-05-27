from unittest.mock import MagicMock

import pytest

from cobbler.api import CobblerAPI
from cobbler.settings import Settings
from cobbler import autoinstall_manager
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System


@pytest.fixture
def api_mock():
    api_mock = MagicMock(spec=CobblerAPI)
    settings_mock = MagicMock(name="autoinstall_setting_mock", spec=Settings)
    settings_mock.autoinstall_snippets_dir = "/var/lib/cobbler/snippets"
    settings_mock.autoinstall_templates_dir = "/var/lib/cobbler/templates"
    settings_mock.next_server_v4 = ""
    settings_mock.next_server_v6 = ""
    settings_mock.default_virt_bridge = ""
    settings_mock.default_virt_type = "auto"
    settings_mock.default_virt_ram = 64
    settings_mock.run_install_triggers = True
    settings_mock.yum_post_install_mirror = True
    settings_mock.enable_ipxe = True
    settings_mock.enable_menu = True
    settings_mock.virt_auto_boot = True
    settings_mock.default_ownership = []
    settings_mock.default_name_servers = []
    settings_mock.default_name_servers_search = []
    settings_mock.default_virt_disk_driver = "raw"
    api_mock.settings.return_value = settings_mock
    test_distro = Distro(api_mock)
    test_distro.name = "test"
    api_mock.distros.return_value = MagicMock(return_value=[test_distro])
    test_profile = Profile(api_mock)
    test_profile.name = "test"
    api_mock.profiles.return_value = MagicMock(return_value=[test_profile])
    test_system = System(api_mock)
    test_system.name = "test"
    return api_mock


# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - DEBUG | running python triggers from /var/lib/cobbler/triggers/task/validate_autoinstall_files/pre/*
# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - DEBUG | running shell triggers from /var/lib/cobbler/triggers/task/validate_autoinstall_files/pre/*
# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - DEBUG | shell triggers finished successfully
# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - INFO | validate_autoinstall_files
# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - INFO | ----------------------------
# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - DEBUG | osversion:
# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - INFO | Exception occurred: <class 'TypeError'>
# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - INFO | Exception value: unhashable type: 'Profile'
# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - INFO | Exception Info:
#   File "/usr/lib/python3.6/site-packages/cobbler/remote.py", line 99, in run
#     rc = self._run(self)
#
#   File "/usr/lib/python3.6/site-packages/cobbler/remote.py", line 260, in runner
#     return self.remote.api.validate_autoinstall_files()
#
#   File "/usr/lib/python3.6/site-packages/cobbler/api.py", line 1372, in validate_autoinstall_files
#     autoinstall_mgr.validate_autoinstall_files()
#
#   File "/usr/lib/python3.6/site-packages/cobbler/autoinstall_manager.py", line 329, in validate_autoinstall_files
#     (success, errors_type, errors) = self.validate_autoinstall_file(x, True)
#
#   File "/usr/lib/python3.6/site-packages/cobbler/autoinstall_manager.py", line 309, in validate_autoinstall_file
#     self.generate_autoinstall(profile=obj)
#
#   File "/usr/lib/python3.6/site-packages/cobbler/autoinstall_manager.py", line 268, in generate_autoinstall
#     return self.autoinstallgen.generate_autoinstall_for_profile(profile)
#
#   File "/usr/lib/python3.6/site-packages/cobbler/autoinstallgen.py", line 347, in generate_autoinstall_for_profile
#     g = self.api.find_profile(name=g)
#
#   File "/usr/lib/python3.6/site-packages/cobbler/api.py", line 931, in find_profile
#     return self._collection_mgr.profiles().find(name=name, return_list=return_list, no_errors=no_errors, **kargs)
#
#   File "/usr/lib/python3.6/site-packages/cobbler/cobbler_collections/collection.py", line 127, in find
#     return self.listing.get(kargs["name"], None)
#
# [2022-02-28_093028_validate_autoinstall_files] 2022-02-28T09:30:29 - ERROR | ### TASK FAILED ###


def test_create_autoinstallation_manager(api_mock):
    # Arrange
    # TODO

    # Act
    result = autoinstall_manager.AutoInstallationManager(api_mock)

    # Assert
    isinstance(result, autoinstall_manager.AutoInstallationManager)
