"""
Tests that validate the functionality of the module that is responsible for managing the genders config file.
"""

import time
from typing import TYPE_CHECKING

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.items.template import Template
from cobbler.modules.managers import genders
from cobbler.settings import Settings
from cobbler.templates import Templar

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="api_genders_mock")
def fixture_api_genders_mock(mocker: "MockerFixture") -> CobblerAPI:
    """
    TODO
    """
    # pylint: disable=protected-access
    settings_mock = mocker.MagicMock(name="genders_setting_mock", spec=Settings)
    settings_mock.server = "127.0.0.1"
    settings_mock.default_template_type = "cheetah"
    settings_mock.cheetah_import_whitelist = ["re"]
    settings_mock.always_write_dhcp_entries = True
    settings_mock.http_port = 80
    settings_mock.next_server_v4 = ""
    settings_mock.next_server_v6 = "127.0.0.1"
    settings_mock.default_ownership = []
    settings_mock.default_virt_bridge = ""
    settings_mock.default_virt_type = "auto"
    settings_mock.default_virt_ram = 64
    settings_mock.genders_settings_file = "/etc/genders"
    settings_mock.restart_dhcp = True
    settings_mock.enable_ipxe = True
    settings_mock.enable_menu = True
    settings_mock.virt_auto_boot = True
    settings_mock.default_name_servers = []
    settings_mock.default_name_servers_search = []
    settings_mock.manage_dhcp_v4 = True
    settings_mock.manage_dhcp_v6 = True
    settings_mock.manage_genders = True
    settings_mock.default_virt_disk_driver = "raw"
    settings_mock.cache_enabled = False
    api_mock = mocker.MagicMock(autospec=True, spec=CobblerAPI)
    api_mock.settings.return_value = settings_mock
    test_distro = Distro(api_mock)
    test_distro.name = "test_distro"
    api_mock.distros.return_value = [test_distro]
    test_profile = Profile(api_mock)
    test_profile.name = "test_profile"
    test_profile._parent = test_distro.name  # type: ignore[reportPrivateUsage]
    api_mock.profiles.return_value = [test_profile]
    test_system = System(api_mock)
    test_system.name = "test_system"
    test_system._parent = test_profile.name  # type: ignore[reportPrivateUsage]
    test_template = Template(
        api_mock, tags={enums.TemplateTag.ACTIVE.value, enums.TemplateTag.GENDERS.value}
    )
    test_template._Template__content = "test"  # type: ignore
    api_mock.find_system.return_value = [test_system]
    api_mock.find_template.return_value = [test_template]
    api_mock.systems.return_value = [test_system]
    api_mock.templar = mocker.MagicMock(autospec=True, spec=Templar)
    return api_mock


def test_register():
    """
    TODO
    """
    # Arrange
    # Act
    result = genders.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/change/*"


def test_write_genders_file(mocker: "MockerFixture", api_genders_mock: CobblerAPI):
    """
    TODO
    """
    # Arrange
    templar_mock = api_genders_mock.templar
    mocker.patch(
        "time.gmtime",
        return_value=time.struct_time((2000, 1, 1, 0, 0, 0, 0, 1, 1)),
    )

    # Act
    genders.write_genders_file(
        api_genders_mock,
        "profiles_genders_value",  # type: ignore[reportArgumentType,arg-type]
        "distros_genders_value",  # type: ignore[reportArgumentType,arg-type]
        "mgmtcls_genders_value",  # type: ignore[reportArgumentType,arg-type]
    )

    # Assert
    assert templar_mock.render.call_count == 1  # type: ignore
    templar_mock.render.assert_called_with(  # type: ignore
        "test",
        {
            "date": "Mon Jan  1 00:00:00 2000",
            "profiles_genders": "profiles_genders_value",
            "distros_genders": "distros_genders_value",
            "mgmtcls_genders": "mgmtcls_genders_value",
        },
        "/etc/genders",
    )


def test_run(mocker: "MockerFixture", api_genders_mock: CobblerAPI):
    """
    TODO
    """
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
        {},
    )
    assert result == 0
