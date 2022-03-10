from unittest.mock import MagicMock

from cobbler.api import CobblerAPI
from cobbler.modules.installation import pre_puppet


def test_register():
    # Arrange & Act
    result = pre_puppet.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/install/pre/*"


def test_run():
    # Arrange
    api = MagicMock(spec=CobblerAPI)
    args = ["test_objtype", "test_name"]

    # Act
    result = pre_puppet.run(api, args)

    # Assert
    # FIXME improve assert
    assert result == 0
