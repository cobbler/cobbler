import os
import time

import pytest

from cobbler import settings


@pytest.mark.skip("This breaks a lot of tests if we don't insert the full settings here.")
def test_update_settings_file():
    # Arrange
    settings_data = None
    time_before_write = time.time()

    # Act
    result = settings.update_settings_file(settings_data)

    # Assert
    assert result
    # This should work the following: The time of modifying the settings file should be greater then the time taken
    # before modifying it. Thus the value of the subtraction of both should be greater than zero. If writing to the
    # files does not work, this is smaller then 0. The content is a yaml file thus we don't want to test if writing a
    # YAML file is logically correct. This is the matter of the library we are using.
    assert os.path.getmtime("/etc/cobbler/settings.yaml") - time_before_write > 0
