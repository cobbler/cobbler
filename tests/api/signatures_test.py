"""
Tests that validate the functionality of the CobblerAPI methods that expose the distro signatures data.
"""

from typing import TYPE_CHECKING, List

from cobbler.api import CobblerAPI

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_get_valid_breeds(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "cobbler.api.signatures.get_valid_breeds",
        return_value=["redhat", "debian"],
    )

    # Act
    result = CobblerAPI.get_valid_breeds()

    # Assert
    assert result == ["debian", "redhat"]


def test_get_valid_os_versions_for_breed(mocker: "MockerFixture"):
    # Arrange
    mock = mocker.patch(
        "cobbler.api.signatures.get_valid_os_versions_for_breed",
        return_value=["rhel9", "rhel8"],
    )

    # Act
    result = CobblerAPI.get_valid_os_versions_for_breed("redhat")

    # Assert
    mock.assert_called_once_with("redhat")
    assert result == ["rhel8", "rhel9"]


def test_get_valid_os_versions(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "cobbler.api.signatures.get_valid_os_versions",
        return_value=["rhel9", "rhel8"],
    )

    # Act
    result = CobblerAPI.get_valid_os_versions()

    # Assert
    assert result == ["rhel8", "rhel9"]


def test_get_valid_archs(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "cobbler.api.signatures.get_valid_archs",
        return_value=["x86_64", "aarch64"],
    )

    # Act
    result: List[str] = CobblerAPI.get_valid_archs()

    # Assert
    assert result == ["aarch64", "x86_64"]
