"""
TODO
"""

from typing import Any, Dict, Optional

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.abstract.item_bootable import BootableItem

from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "input_kernel_options,expected_exception,expected_result",
    [
        ("", does_not_raise(), {}),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_kernel_options(
    cobbler_api: CobblerAPI,
    input_kernel_options: Any,
    expected_exception: Any,
    expected_result: Optional[Dict[Any, Any]],
):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the kernel_options property correctly.
    """
    # Arrange
    titem = BootableItem(cobbler_api)

    # Act
    with expected_exception:
        titem.kernel_options = input_kernel_options

        # Assert
        assert titem.kernel_options == expected_result


@pytest.mark.parametrize(
    "input_kernel_options,expected_exception,expected_result",
    [
        ("", does_not_raise(), {}),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_kernel_options_post(
    cobbler_api: CobblerAPI,
    input_kernel_options: Any,
    expected_exception: Any,
    expected_result: Optional[Dict[Any, Any]],
):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the kernel_options_post property correctly.
    """
    # Arrange
    titem = BootableItem(cobbler_api)

    # Act
    with expected_exception:
        titem.kernel_options_post = input_kernel_options

        # Assert
        assert titem.kernel_options_post == expected_result


@pytest.mark.parametrize(
    "input_autoinstall_meta,expected_exception,expected_result",
    [
        ("", does_not_raise(), {}),
        (False, pytest.raises(TypeError), None),
    ],
)
def test_autoinstall_meta(
    cobbler_api: CobblerAPI,
    input_autoinstall_meta: Any,
    expected_exception: Any,
    expected_result: Optional[Dict[Any, Any]],
):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the autoinstall_meta property correctly.
    """
    # Arrange
    titem = BootableItem(cobbler_api)

    # Act
    with expected_exception:
        titem.autoinstall_meta = input_autoinstall_meta

        # Assert
        assert titem.autoinstall_meta == expected_result


def test_template_files(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the template_files property correctly.
    """
    # pylint: disable=use-implicit-booleaness-not-comparison
    # Arrange
    titem = BootableItem(cobbler_api)

    # Act
    titem.template_files = {}

    # Assert
    assert titem.template_files == {}


def test_boot_files(cobbler_api: CobblerAPI):
    """
    Assert that an abstract Cobbler Item can use the Getter and Setter of the boot_files property correctly.
    """
    # pylint: disable=use-implicit-booleaness-not-comparison
    # Arrange
    titem = BootableItem(cobbler_api)

    # Act
    titem.boot_files = {}

    # Assert
    assert titem.boot_files == {}
