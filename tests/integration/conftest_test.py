"""
Tests for helpers defined in the integration test conftest module.
"""

from unittest.mock import Mock

import pytest

from tests.integration.conftest import wait_for_cobblerd


def test_wait_for_cobblerd_returns_once_ping_succeeds() -> None:
    """
    Test that "wait_for_cobblerd" retries through transient connection failures - the state right after a cobblerd
    restart, before it has bound its XML-RPC listener - and returns as soon as a ping succeeds.
    """
    remote = Mock()
    remote.ping.side_effect = [ConnectionRefusedError(), ConnectionRefusedError(), True]

    wait_for_cobblerd(remote, timeout=5, interval=0)

    assert remote.ping.call_count == 3


def test_wait_for_cobblerd_raises_timeout_if_never_reachable() -> None:
    """
    Test that "wait_for_cobblerd" gives up and raises "TimeoutError" if cobblerd never becomes reachable, instead
    of retrying forever.
    """
    remote = Mock()
    remote.ping.side_effect = ConnectionRefusedError("connection refused")

    with pytest.raises(TimeoutError):
        wait_for_cobblerd(remote, timeout=0.05, interval=0.01)
