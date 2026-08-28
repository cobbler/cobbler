"""
Tests that validate the functionality of the module that serves TFTP content dynamically (e.g. via cobbler-tftp)
instead of copying it into the TFTP root.
"""

from typing import TYPE_CHECKING, Any, Generator

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.system import System
from cobbler.modules.managers import dynamic_tftp
from cobbler.settings import Settings
from cobbler.tftpgen import TFTPGen

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="api_mock_dynamic_tftp")
def fixture_api_mock_dynamic_tftp(mocker: "MockerFixture") -> CobblerAPI:
    """
    Fixture to provide a mocked CobblerAPI instance with necessary attributes for testing the dynamic_tftp manager.
    """
    api_mock_dynamic_tftp = mocker.MagicMock(spec=CobblerAPI)
    settings_mock = mocker.MagicMock(
        name="dynamic_tftp_setting_mock", spec=Settings, autospec=True
    )
    settings_mock.tftpboot_location = "/var/lib/tftpboot"
    settings_mock.webdir = "/srv/www/cobbler"
    api_mock_dynamic_tftp.settings.return_value = settings_mock
    api_mock_dynamic_tftp.distros = mocker.MagicMock(return_value=[])
    api_mock_dynamic_tftp.profiles = mocker.MagicMock(return_value=[])
    api_mock_dynamic_tftp.systems = mocker.MagicMock(return_value=[])
    api_mock_dynamic_tftp.repos = mocker.MagicMock(return_value=[])
    api_mock_dynamic_tftp.tftpgen = mocker.MagicMock(spec=TFTPGen, autospec=True)
    return api_mock_dynamic_tftp


@pytest.fixture(name="reset_singleton", scope="function", autouse=True)
def fixture_reset_singleton() -> Generator[Any, Any, Any]:
    """
    Fixture to reset the singleton instance of _DynamicTftpManager before and after each test.
    """
    dynamic_tftp.MANAGER = None
    yield
    dynamic_tftp.MANAGER = None


def test_register():
    """
    Test the register function to ensure it returns the expected string.
    """
    # Arrange & Act
    result = dynamic_tftp.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    """
    Test the what method of the _DynamicTftpManager class to ensure it returns the expected string.
    """
    # pylint: disable=protected-access
    # Arrange & Act & Assert
    assert dynamic_tftp._DynamicTftpManager.what() == "dynamic_tftp"  # type: ignore[reportPrivateUsage]


def test_dynamic_tftp_singleton(mocker: "MockerFixture"):
    """
    Test to ensure that the _DynamicTftpManager class implements the singleton pattern correctly.
    """
    # Arrange
    mcollection = mocker.Mock()

    # Act
    manager_1 = dynamic_tftp.get_manager(mcollection)
    manager_2 = dynamic_tftp.get_manager(mcollection)

    # Assert
    assert manager_1 == manager_2


def test_manager_write_boot_files(api_mock_dynamic_tftp: CobblerAPI):
    """
    Test that write_boot_files is a no-op that doesn't touch tftpgen.
    """
    # Arrange
    manager_obj = dynamic_tftp.get_manager(api_mock_dynamic_tftp)
    tftpgen_mock = api_mock_dynamic_tftp.tftpgen

    # Act
    result = manager_obj.write_boot_files()

    # Assert
    assert result == 0
    assert tftpgen_mock.method_calls == []  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]


def test_manager_sync_single_system(api_mock_dynamic_tftp: CobblerAPI):
    """
    Test that sync_single_system is a no-op that doesn't touch tftpgen.
    """
    # Arrange
    manager_obj = dynamic_tftp.get_manager(api_mock_dynamic_tftp)
    tftpgen_mock = api_mock_dynamic_tftp.tftpgen

    # Act
    result = manager_obj.sync_single_system(None, None)  # type: ignore[reportArgumentType,arg-type]

    # Assert
    assert result == 0
    assert tftpgen_mock.method_calls == []  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]


def test_manager_add_single_distro(api_mock_dynamic_tftp: CobblerAPI):
    """
    Test that add_single_distro is a no-op that doesn't touch tftpgen.
    """
    # Arrange
    manager_obj = dynamic_tftp.get_manager(api_mock_dynamic_tftp)
    tftpgen_mock = api_mock_dynamic_tftp.tftpgen

    # Act
    manager_obj.add_single_distro(None)  # type: ignore[reportArgumentType,arg-type]

    # Assert
    assert tftpgen_mock.method_calls == []  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]


def test_manager_add_single_image(api_mock_dynamic_tftp: CobblerAPI):
    """
    Test that add_single_image is a no-op that doesn't touch tftpgen.
    """
    # Arrange
    manager_obj = dynamic_tftp.get_manager(api_mock_dynamic_tftp)
    tftpgen_mock = api_mock_dynamic_tftp.tftpgen

    # Act
    manager_obj.add_single_image(None)  # type: ignore[reportArgumentType,arg-type]

    # Assert
    assert tftpgen_mock.method_calls == []  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]


def test_manager_sync_systems(api_mock_dynamic_tftp: CobblerAPI):
    """
    Test that sync_systems is a no-op that doesn't touch tftpgen.
    """
    # Arrange
    manager_obj = dynamic_tftp.get_manager(api_mock_dynamic_tftp)
    tftpgen_mock = api_mock_dynamic_tftp.tftpgen

    # Act
    manager_obj.sync_systems([System(api_mock_dynamic_tftp)], True)

    # Assert
    assert tftpgen_mock.method_calls == []  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]


def test_manager_sync(api_mock_dynamic_tftp: CobblerAPI):
    """
    Test that sync is a no-op that doesn't touch tftpgen.
    """
    # Arrange
    manager_obj = dynamic_tftp.get_manager(api_mock_dynamic_tftp)
    tftpgen_mock = api_mock_dynamic_tftp.tftpgen

    # Act
    result = manager_obj.sync()

    # Assert
    assert result == 0
    assert tftpgen_mock.method_calls == []  # type: ignore[reportUnknownMemberType,reportAttributeAccessIssue]
