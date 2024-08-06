"""
Tests that validate the functionality of the module that is responsible for managing imported distribution trees.
"""

import pytest

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
