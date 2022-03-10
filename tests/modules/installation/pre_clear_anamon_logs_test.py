from unittest.mock import MagicMock

from cobbler.api import CobblerAPI
from cobbler.modules.installation import pre_clear_anamon_logs


def test_register():
    # Arrange & Act
    result = pre_clear_anamon_logs.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/install/pre/*"


def test_run():
    # Arrange
    api = MagicMock(spec=CobblerAPI)
    args = ["test1", "test2", "test3"]

    # Act
    result = pre_clear_anamon_logs.run(api, args)

    # Assert
    # FIXME improve assert
    assert result == 0
