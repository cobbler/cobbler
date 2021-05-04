from unittest.mock import Mock

import pytest

from cobbler.modules.managers import in_tftpd


def test_tftpd_singleton():
    # Arrange
    mcollection = Mock()

    # Act
    manager_1 = in_tftpd.get_manager(mcollection)
    manager_2 = in_tftpd.get_manager(mcollection)

    # Assert
    assert manager_1 == manager_2


@pytest.mark.skip("TODO")
@pytest.mark.parametrize("input_systems, input_verbose, expected_output", [
    ("t1.example.org", True, "t1.example.org")
])
def test_sync_systems(input_systems, input_verbose, expected_output):
    # Arrange
    mcollection = Mock()
    manager_obj = in_tftpd.get_manager(mcollection)
    # mock tftpgen

    # Act
    # .sync_systems(input_systems, input_verbose)

    # Assert
    assert False
