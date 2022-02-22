import pytest

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
    import_signatures.import_walker("", True, "")

    # Assert
    assert False


def test_get_manager(cobbler_api):
    # Arrange & Act
    result = import_signatures.get_import_manager(cobbler_api)

    # Assert
    isinstance(result, import_signatures._ImportSignatureManager)


def test_manager_what():
    # Arrange & Act & Assert
    assert import_signatures._ImportSignatureManager.what() == "import/signatures"
