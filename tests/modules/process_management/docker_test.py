"""
Tests that validate the functionality of the Docker label-based process management module. These tests mock the
Docker SDK client directly on the module under test, so they do not require a real Docker daemon, nor even the
``docker`` Python package, to be installed.
"""

from typing import TYPE_CHECKING, Dict, Optional
from unittest.mock import MagicMock

import pytest

from cobbler.modules.process_management import docker as docker_module
from cobbler.settings import Settings

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


class FakeDockerException(Exception):
    """
    Stand-in for ``docker.errors.DockerException``, used regardless of whether the real SDK happens to be
    installed in the test environment.
    """


@pytest.fixture(autouse=True)
def docker_sdk_loaded(mocker: "MockerFixture"):
    """
    Force the module under test to behave as if the optional ``docker`` SDK is installed, and give it a fake
    exception type to catch, regardless of whether the real package is actually importable here.
    """
    mocker.patch.object(docker_module, "DOCKER_SDK_LOADED", True)
    mocker.patch.object(docker_module, "DockerException", FakeDockerException)


def _make_api_handle(
    socket_path: str = "/var/run/docker.sock",
    docker_service_labels: Optional[Dict[str, str]] = None,
) -> MagicMock:
    if docker_service_labels is None:
        docker_service_labels = {
            "dhcpd": "dhcp",
            "dhcpd4": "dhcp",
            "dhcpd6": "dhcp",
            "named": "dns",
            "dnsmasq": "dnsmasq",
        }
    api_handle = MagicMock()
    api_handle.settings.return_value.modules = {
        "process_management": {
            "docker_socket_path": socket_path,
            "docker_service_labels": docker_service_labels,
        }
    }
    return api_handle


def _make_fake_docker_sdk(fake_client: MagicMock) -> MagicMock:
    fake_docker_sdk = MagicMock()
    fake_docker_sdk.DockerClient.return_value = fake_client
    return fake_docker_sdk


def test_default_docker_service_labels_matches_settings_default():
    """
    Drift guard: DEFAULT_DOCKER_SERVICE_LABELS is a duplicated literal (docker.py can't cleanly import
    cobbler.settings' default without instantiating the whole Settings object at import time), so make sure it
    stays byte-for-byte in sync with the real default in cobbler.settings.Settings.__init__().
    """
    # Arrange & Act
    real_default = Settings().modules["process_management"]["docker_service_labels"]

    # Assert
    assert docker_module.DEFAULT_DOCKER_SERVICE_LABELS == real_default


def test_register_returns_process_management_when_sdk_present(
    mocker: "MockerFixture",
):
    # Arrange
    mocker.patch.object(docker_module, "DOCKER_SDK_LOADED", True)

    # Act
    result = docker_module.register()

    # Assert
    assert result == "process_management"


def test_register_returns_empty_string_when_sdk_missing(mocker: "MockerFixture"):
    # Arrange
    mocker.patch.object(docker_module, "DOCKER_SDK_LOADED", False)

    # Act
    result = docker_module.register()

    # Assert
    assert result == ""


def test_restart_service_single_match_restarts_container(mocker: "MockerFixture"):
    # Arrange
    api_handle = _make_api_handle()
    container = MagicMock(name="matched_container")
    fake_client = MagicMock()
    fake_client.containers.list.return_value = [container]
    fake_docker_sdk = _make_fake_docker_sdk(fake_client)
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)

    # Act
    result = docker_module.restart_service(api_handle, "dhcpd")

    # Assert
    fake_docker_sdk.DockerClient.assert_called_once_with(
        base_url="unix:///var/run/docker.sock"
    )
    fake_client.containers.list.assert_called_once_with(
        all=True, filters={"label": "cobbler.io/managed-service=dhcp"}
    )
    container.restart.assert_called_once_with()
    fake_client.close.assert_called_once_with()
    assert result == 0


def test_restart_service_unmapped_service_name_falls_back_to_raw_name(
    mocker: "MockerFixture",
):
    # Arrange
    api_handle = _make_api_handle(docker_service_labels={})
    container = MagicMock()
    fake_client = MagicMock()
    fake_client.containers.list.return_value = [container]
    fake_docker_sdk = _make_fake_docker_sdk(fake_client)
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)

    # Act
    result = docker_module.restart_service(api_handle, "some-unmapped-service")

    # Assert
    fake_client.containers.list.assert_called_once_with(
        all=True,
        filters={"label": "cobbler.io/managed-service=some-unmapped-service"},
    )
    container.restart.assert_called_once_with()
    assert result == 0


def test_restart_service_zero_matches_is_a_hard_error(mocker: "MockerFixture"):
    # Arrange
    api_handle = _make_api_handle()
    fake_client = MagicMock()
    fake_client.containers.list.return_value = []
    fake_docker_sdk = _make_fake_docker_sdk(fake_client)
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)
    mocked_logger = mocker.patch.object(docker_module, "logger")

    # Act
    result = docker_module.restart_service(api_handle, "dhcpd")

    # Assert
    assert result != 0
    mocked_logger.error.assert_called_once()
    fake_client.close.assert_called_once_with()


def test_restart_service_multiple_matches_is_a_hard_error(mocker: "MockerFixture"):
    # Arrange
    api_handle = _make_api_handle()
    container_a = MagicMock()
    container_b = MagicMock()
    fake_client = MagicMock()
    fake_client.containers.list.return_value = [container_a, container_b]
    fake_docker_sdk = _make_fake_docker_sdk(fake_client)
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)
    mocked_logger = mocker.patch.object(docker_module, "logger")

    # Act
    result = docker_module.restart_service(api_handle, "dhcpd")

    # Assert
    assert result != 0
    mocked_logger.error.assert_called_once()
    container_a.restart.assert_not_called()
    container_b.restart.assert_not_called()
    fake_client.close.assert_called_once_with()


def test_restart_service_container_restart_raises_docker_exception(
    mocker: "MockerFixture",
):
    # Arrange
    api_handle = _make_api_handle()
    container = MagicMock()
    container.restart.side_effect = FakeDockerException("boom")
    fake_client = MagicMock()
    fake_client.containers.list.return_value = [container]
    fake_docker_sdk = _make_fake_docker_sdk(fake_client)
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)
    mocked_logger = mocker.patch.object(docker_module, "logger")

    # Act
    result = docker_module.restart_service(api_handle, "dhcpd")

    # Assert
    assert result != 0
    mocked_logger.error.assert_called_once()
    fake_client.close.assert_called_once_with()


def test_restart_service_daemon_unreachable_during_client_construction(
    mocker: "MockerFixture",
):
    # Arrange
    api_handle = _make_api_handle()
    fake_docker_sdk = MagicMock()
    fake_docker_sdk.DockerClient.side_effect = ConnectionError(
        "no such file or directory"
    )
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)
    mocked_logger = mocker.patch.object(docker_module, "logger")

    # Act
    result = docker_module.restart_service(api_handle, "dhcpd")

    # Assert
    assert result != 0
    mocked_logger.error.assert_called_once()


def test_restart_service_daemon_unreachable_during_listing(mocker: "MockerFixture"):
    # Arrange
    api_handle = _make_api_handle()
    fake_client = MagicMock()
    fake_client.containers.list.side_effect = ConnectionError("no route to host")
    fake_docker_sdk = _make_fake_docker_sdk(fake_client)
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)
    mocked_logger = mocker.patch.object(docker_module, "logger")

    # Act
    result = docker_module.restart_service(api_handle, "dhcpd")

    # Assert
    assert result != 0
    mocked_logger.error.assert_called_once()
    fake_client.close.assert_called_once_with()


def test_restart_service_returns_error_without_touching_docker_when_sdk_missing(
    mocker: "MockerFixture",
):
    # Arrange
    mocker.patch.object(docker_module, "DOCKER_SDK_LOADED", False)
    api_handle = _make_api_handle()
    fake_docker_sdk = MagicMock()
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)
    mocked_logger = mocker.patch.object(docker_module, "logger")

    # Act
    result = docker_module.restart_service(api_handle, "dhcpd")

    # Assert
    assert result != 0
    mocked_logger.error.assert_called_once()
    fake_docker_sdk.DockerClient.assert_not_called()


def test_restart_service_falls_back_to_defaults_when_both_settings_keys_missing(
    mocker: "MockerFixture",
):
    """
    Regression test: docker_socket_path and docker_service_labels are Optional in the settings schema, so a
    hand-edited settings.yaml could select this module without including either companion key. That must not
    raise a KeyError - it should fall back to the same defaults as the Task 3 settings scaffold, including the
    real default label mapping (not an empty mapping, which would silently search for the wrong, unmapped label).
    """
    # Arrange
    api_handle = MagicMock()
    api_handle.settings.return_value.modules = {"process_management": {}}
    container = MagicMock()
    fake_client = MagicMock()
    fake_client.containers.list.return_value = [container]
    fake_docker_sdk = _make_fake_docker_sdk(fake_client)
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)

    # Act
    result = docker_module.restart_service(api_handle, "dhcpd")

    # Assert
    fake_docker_sdk.DockerClient.assert_called_once_with(
        base_url="unix:///var/run/docker.sock"
    )
    fake_client.containers.list.assert_called_once_with(
        all=True, filters={"label": "cobbler.io/managed-service=dhcp"}
    )
    container.restart.assert_called_once_with()
    assert result == 0


def test_restart_service_falls_back_to_defaults_when_process_management_settings_missing(
    mocker: "MockerFixture",
):
    """
    Regression test: even the "process_management" key itself being absent from settings().modules must not raise
    a KeyError, and must still use the real default label mapping (not an empty one).
    """
    # Arrange
    api_handle = MagicMock()
    api_handle.settings.return_value.modules = {}
    container = MagicMock()
    fake_client = MagicMock()
    fake_client.containers.list.return_value = [container]
    fake_docker_sdk = _make_fake_docker_sdk(fake_client)
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)

    # Act
    result = docker_module.restart_service(api_handle, "named")

    # Assert
    fake_docker_sdk.DockerClient.assert_called_once_with(
        base_url="unix:///var/run/docker.sock"
    )
    fake_client.containers.list.assert_called_once_with(
        all=True, filters={"label": "cobbler.io/managed-service=dns"}
    )
    assert result == 0


def test_restart_service_falls_back_to_default_socket_path_only(
    mocker: "MockerFixture",
):
    """
    Regression test: docker_service_labels present but docker_socket_path missing must still fall back cleanly.
    """
    # Arrange
    api_handle = MagicMock()
    api_handle.settings.return_value.modules = {
        "process_management": {"docker_service_labels": {"dhcpd": "dhcp"}}
    }
    container = MagicMock()
    fake_client = MagicMock()
    fake_client.containers.list.return_value = [container]
    fake_docker_sdk = _make_fake_docker_sdk(fake_client)
    mocker.patch.object(docker_module, "docker", fake_docker_sdk)

    # Act
    result = docker_module.restart_service(api_handle, "dhcpd")

    # Assert
    fake_docker_sdk.DockerClient.assert_called_once_with(
        base_url="unix:///var/run/docker.sock"
    )
    fake_client.containers.list.assert_called_once_with(
        all=True, filters={"label": "cobbler.io/managed-service=dhcp"}
    )
    assert result == 0
