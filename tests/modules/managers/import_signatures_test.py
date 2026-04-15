"""
Tests that validate the functionality of the module that is responsible for managing imported distribution trees.
"""

import os

import pytest
from pytest_mock import MockerFixture

from cobbler.api import CobblerAPI
from cobbler.modules.managers import import_signatures


def test_register():
    # Arrange
    # Act
    result = import_signatures.register()

    # Assert
    assert result == "manage/import"


@pytest.mark.skip("too lazy to implement")
def test_import_walker():
    # Arrange
    # Act
    import_signatures.import_walker("", True, "")  # type: ignore

    # Assert
    assert False


def test_get_manager(cobbler_api: CobblerAPI):
    # Arrange & Act
    result = import_signatures.get_import_manager(cobbler_api)

    # Assert
    # pylint: disable-next=protected-access
    isinstance(result, import_signatures._ImportSignatureManager)  # type: ignore


def test_manager_what():
    # Arrange & Act & Assert
    # pylint: disable-next=protected-access
    assert import_signatures._ImportSignatureManager.what() == "import/signatures"  # type: ignore


def test_arch_walker_matches_kernel_arch_regex_from_bytes(
    cobbler_api: CobblerAPI, mocker: MockerFixture
):
    # Arrange
    manager = import_signatures.get_import_manager(cobbler_api)
    manager.signature = {
        "kernel_arch": "tools\\.t00",
        "kernel_arch_regex": "^.*(x86_64).*$",
        "supported_arches": ["x86_64"],
    }
    get_file_lines = mocker.patch.object(
        manager, "get_file_lines", return_value=[b"architecture=x86_64\n"]
    )
    result = {}

    # Act
    manager.arch_walker(result, "/tmp/esxi", ["tools.t00"])

    # Assert
    assert result == {"x86_64": 1}
    get_file_lines.assert_called_once_with(os.path.join("/tmp/esxi", "tools.t00"))
