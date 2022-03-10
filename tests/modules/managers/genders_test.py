import time
from unittest.mock import MagicMock

import pytest

from cobbler.api import CobblerAPI
from cobbler.modules.managers import genders
from cobbler.settings import Settings
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.items.mgmtclass import Mgmtclass


@pytest.fixture
def api_genders_mock():
    settings_mock = MagicMock(name="genders_setting_mock", spec=Settings)
    settings_mock.server = "127.0.0.1"
    settings_mock.default_template_type = "cheetah"
    settings_mock.cheetah_import_whitelist = ["re"]
    settings_mock.always_write_dhcp_entries = True
    settings_mock.http_port = 80
    settings_mock.next_server_v4 = ""
    settings_mock.next_server_v6 = "127.0.0.1"
    settings_mock.default_ownership = ""
    settings_mock.default_virt_bridge = ""
    settings_mock.default_virt_type = "auto"
    settings_mock.default_virt_ram = 64
    settings_mock.restart_dhcp = True
    settings_mock.enable_ipxe = True
    settings_mock.enable_menu = True
    settings_mock.virt_auto_boot = True
    settings_mock.default_name_servers = []
    settings_mock.default_name_servers_search = []
    settings_mock.manage_dhcp_v4 = True
    settings_mock.manage_dhcp_v6 = True
    settings_mock.manage_genders = True
    settings_mock.jinja2_includedir = ""
    settings_mock.default_virt_disk_driver = "raw"
    api_mock = MagicMock(autospec=True, spec=CobblerAPI)
    api_mock.settings.return_value = settings_mock
    test_distro = Distro(api_mock)
    test_distro.name = "test_distro"
    api_mock.distros.return_value = [test_distro]
    test_profile = Profile(api_mock)
    test_profile.name = "test_profile"
    test_profile._parent = test_distro.name
    api_mock.profiles.return_value = [test_profile]
    test_system = System(api_mock)
    test_system.name = "test_system"
    test_system._parent = test_profile.name
    api_mock.find_system.return_value = [test_system]
    api_mock.systems.return_value = [test_system]
    test_mgmtclass = Mgmtclass(api_mock)
    test_mgmtclass.name = "test_mgmtclass"
    api_mock.mgmtclasses.return_value = [test_mgmtclass]
    return api_mock


def test_register():
    # Arrange
    # Act
    result = genders.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/change/*"


def test_write_genders_file(mocker, api_genders_mock):
    # Arrange
    templar_mock = mocker.patch(
        "cobbler.modules.managers.genders.Templar", autospec=True
    )
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )

    # Act
    genders.write_genders_file(
        api_genders_mock,
        "profiles_genders_value",
        "distros_genders_value",
        "mgmtcls_genders_value",
    )

    # Assert
    assert templar_mock.return_value.render.call_count == 1
    templar_mock.return_value.render.assert_called_with(
        "test",
        {
            "date": "Mon Jan  1 00:00:00 2000",
            "profiles_genders": "profiles_genders_value",
            "distros_genders": "distros_genders_value",
            "mgmtcls_genders": "mgmtcls_genders_value",
        },
        "/etc/genders",
    )


def test_run(mocker, api_genders_mock):
    # Arrange
    genders_mock = mocker.patch(
        "cobbler.modules.managers.genders.write_genders_file", autospec=True
    )

    # Act
    result = genders.run(api_genders_mock, [])

    # Assert
    genders_mock.assert_called_with(
        api_genders_mock,
        {"test_profile": "test_system"},
        {"test_distro": "test_system"},
        {"test_mgmtclass": "test_system"},
    )
    assert result == 0
