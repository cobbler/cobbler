"""
Tests that are ensuring the correct functionality of the CobblerAPI in regard to adding items via it.
"""

from pathlib import Path
import pathlib
from typing import Callable
from cobbler.api import CobblerAPI

from cobbler.items.image import Image


def test_image_add(cobbler_api: CobblerAPI):
    # Arrange
    test_image = Image(cobbler_api)
    test_image.name = "test_cobbler_api_add_image"
    expected_result = Path(
        "/var/lib/cobbler/collections/images/test_cobbler_api_add_image.json"
    )

    # Act
    cobbler_api.add_image(test_image)

    # Assert
    assert expected_result.exists()


def test_case_sensitive_add(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Test that two items with the same characters in different casing can be successfully added and edited.
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    name = "TestName"
    item1 = cobbler_api.new_distro()
    item1.name = name
    item1.kernel = str(pathlib.Path(folder) / fk_kernel)
    item1.initrd = str(pathlib.Path(folder) / fk_initrd)
    cobbler_api.add_distro(item1)
    item2 = cobbler_api.new_distro()
    item2.name = name.lower()
    item2.kernel = str(pathlib.Path(folder) / fk_kernel)
    item2.initrd = str(pathlib.Path(folder) / fk_initrd)

    # Act
    cobbler_api.add_distro(item2)
    cobbler_api.remove_distro(item1.name)
    result_item = cobbler_api.get_item("distro", item2.name)

    # Assert
    assert result_item is not None
    assert result_item.uid == item2.uid
    assert cobbler_api.get_item("distro", item1.name) is None
