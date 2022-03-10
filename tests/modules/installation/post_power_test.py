from unittest.mock import MagicMock

from cobbler.api import CobblerAPI
from cobbler.modules.installation import post_power


def test_register():
    # Arrange & Act
    result = post_power.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/install/post/*"


def test_run():
    # Arrange
    api = MagicMock(spec=CobblerAPI)
    args = ["test_objtype", "test_name"]

    # Act
    result = post_power.run(api, args)

    # Assert
    # FIXME improve assert
    assert result == 0
