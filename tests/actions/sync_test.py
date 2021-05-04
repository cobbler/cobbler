from unittest.mock import Mock

import pytest

from cobbler.actions import sync


@pytest.mark.skip("TODO")
def test_run_sync_systems():
    # Arrange
    mcollection = Mock()
    # mock os.path.exists()
    # mock file access (run_triggers)
    # mock collections (distro, profile, etc.)
    # mock tftpd module
    # mock dns module
    # mock dhcp module
    test_sync = sync.CobblerSync()

    # Act
    test_sync.run_sync_systems(["t1.systems.de"])
    # Assert
    # correct order with correct parameters
    assert False


@pytest.mark.skip("TODO")
def test_clean_link_cache():
    # Arrange
    # Act
    # Assert
    assert False


@pytest.mark.skip("TODO")
def test_rsync_gen():
    # Arrange
    # Act
    # Assert
    assert False
