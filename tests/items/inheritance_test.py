"""
Test that verifies that the inheritance concept in Cobbler works for all data types.
"""

from typing import Callable

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile

# pylint: disable=protected-access


def test_resolved_dict_deduplication(
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test that verifies if properties with dictionaries correctly deduplicate.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_distro.kernel_options = {"a": True, "b": 5}
    expected_result_raw = {"b": 6, "c": "test"}
    expected_result_resolved = {"a": True, "b": 6, "c": "test"}
    expected_result_distro = {"a": True, "b": 5}

    # Act
    test_profile.kernel_options = {"a": True, "b": 6, "c": "test"}

    # Assert
    assert test_profile._kernel_options == expected_result_raw  # type: ignore
    assert test_profile.kernel_options == expected_result_resolved
    assert test_distro.kernel_options == expected_result_distro


def test_resolved_list_deduplication(
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test that verifies if properties with lists correctly resolve.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_distro.owners = ["owner1"]
    expected_result_raw = ["owner2"]
    expected_result_resolved = ["owner2"]
    expected_result_distro = ["owner1"]

    # Act
    test_profile.owners = ["owner2"]

    # Assert
    assert test_profile._owners == expected_result_raw  # type: ignore
    assert test_profile.owners == expected_result_resolved
    assert test_distro.owners == expected_result_distro


def test_to_dict_filter_resolved(
    cobbler_api: CobblerAPI, create_distro: Callable[[], Distro]
):
    """
    Test that verifies if properties with dictionaries correctly resolve.
    """
    # Arrange
    test_distro = create_distro()
    test_distro.kernel_options = {"test": True}
    test_distro.autoinstall_meta = {"tree": "http://test/url"}
    cobbler_api.add_distro(test_distro)

    titem = Profile(cobbler_api)
    titem.name = "to_dict_filter_resolved_profile"
    titem.distro = test_distro.name
    new_kernel_options = titem.kernel_options
    new_autoinstall_meta = titem.autoinstall_meta
    new_kernel_options["test"] = False
    new_autoinstall_meta["tree"] = "http://newtest/url"
    titem.kernel_options = new_kernel_options
    titem.autoinstall_meta = new_autoinstall_meta
    cobbler_api.add_profile(titem)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("kernel_options") == {"test": False}
    assert result.get("autoinstall_meta") == {"tree": "http://newtest/url"}
