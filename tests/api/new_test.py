"""
Tests that are ensuring the ``CobblerAPI.new_*()`` methods do not leak sensitive field
values (e.g. passwords) into the application log.
"""

import logging

import pytest

from cobbler.api import CobblerAPI


def test_new_system_does_not_leak_sensitive_kwargs_to_log(
    cobbler_api: CobblerAPI,
    caplog: pytest.LogCaptureFixture,
):
    """
    ``new_system()`` used to log the raw ``kwargs`` dict at INFO level, which meant any
    sensitive field (e.g. ``redhat_management_password``) ended up in ``cobbler.log`` in
    plaintext. It must now only log the item type and the newly created object's uid.
    """
    # Arrange
    caplog.set_level(logging.INFO)
    secret_value = "TopSecretRedHatPassword12345"

    # Act
    new_system = cobbler_api.new_system(
        name="test_new_system_sensitive_kwargs",
        redhat_management_password=secret_value,
    )

    # Assert
    assert secret_value not in caplog.text
    assert "new_system" in caplog.text
    assert new_system.uid in caplog.text


def test_new_distro_does_not_leak_kwargs_to_log(
    cobbler_api: CobblerAPI,
    caplog: pytest.LogCaptureFixture,
):
    """
    ``new_distro()`` used to log the raw ``kwargs`` dict at INFO level. It must now only
    log the item type and the newly created object's uid, never arbitrary field values.
    """
    # Arrange
    caplog.set_level(logging.INFO)
    sentinel_comment = "sentinel-value-that-must-not-be-logged"

    # Act
    new_distro = cobbler_api.new_distro(comment=sentinel_comment)

    # Assert
    assert sentinel_comment not in caplog.text
    assert "new_distro" in caplog.text
    assert new_distro.uid in caplog.text
