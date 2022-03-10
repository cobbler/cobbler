from unittest.mock import MagicMock

import pytest

from cobbler.api import CobblerAPI
from cobbler.modules.installation import post_report


def test_register():
    # Arrange & Act
    result = post_report.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/install/post/*"


@pytest.mark.skip("Runs endlessly")
def test_run():
    # Arrange
    api = MagicMock(spec=CobblerAPI)
    args = ["system", "test_name", "?"]

    # Act
    result = post_report.run(api, args)

    # Assert
    # FIXME improve assert
    assert result == 0
