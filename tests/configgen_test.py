"""
Tests that validate the functionality of the module that is responsible for generating configuration data.
"""

import os
from typing import Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.configgen import ConfigGen

# TODO: If the action items of the configgen class are done then the tests need to test the robustness of the class.


@pytest.fixture(name="create_testbed")
def fixture_create_testbed(
    create_kernel_initrd: Callable[[str, str], str],
    cobbler_api: CobblerAPI,
):
    """
    Fixture to create a set of distro, profile and system that can be used during the configgen tests.
    """

    def _create_testbed() -> CobblerAPI:
        folder = create_kernel_initrd("vmlinux", "initrd.img")
        test_distro = cobbler_api.new_distro(
            name="test_configgen_distro",
            kernel=os.path.join(folder, "vmlinux"),
            initrd=os.path.join(folder, "initrd.img"),
        )
        cobbler_api.add_distro(test_distro)
        test_profile = cobbler_api.new_profile(
            name="test_configgen_profile", distro=test_distro.uid
        )
        cobbler_api.add_profile(test_profile)
        test_system = cobbler_api.new_system(
            name="test_configgen_system",
            profile=test_profile.uid,
            hostname="testhost.test.de",
            autoinstall_meta={"test": "teststring"},
        )
        cobbler_api.add_system(test_system)

        return cobbler_api

    return _create_testbed


def test_object_value_error(cobbler_api: CobblerAPI):
    """
    Test to verify that creating a ConfigGen object with a non-existant item fails with a ValueError.
    """
    # Arrange

    # Act & Assert
    with pytest.raises(ValueError):
        ConfigGen(cobbler_api, "nonexistant")


def test_object_creation(create_testbed: Callable[[], CobblerAPI]):
    """
    Test to verify that creating a ConfigGen object with an existing object works.
    """
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system

    # Act
    test_configgen = ConfigGen(test_api, "testhost.test.de")

    # Assert
    assert isinstance(test_configgen, ConfigGen)


def test_resolve_resource_var(create_testbed: Callable[[], CobblerAPI]):
    """
    Test to verify that resolving variables is working as expected.
    """
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system
    config_gen = ConfigGen(test_api, "testhost.test.de")

    # Act
    result = config_gen.resolve_resource_var("Hello $test !")

    # Assert
    assert isinstance(result, str)
    assert result == "Hello teststring !"


def test_get_cobbler_resource(create_testbed: Callable[[], CobblerAPI]):
    """
    Test to verify that wrapping utils.belnder works as desired.
    """
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system
    config_gen = ConfigGen(test_api, "testhost.test.de")

    # Act
    result = config_gen.get_cobbler_resource("")

    # Assert
    assert isinstance(result, (list, str, dict))


def test_get_config_data(create_testbed: Callable[[], CobblerAPI]):
    """
    Test to verify that all configuration data can be retrieved from Cobbler.
    """
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system
    config_gen = ConfigGen(test_api, "testhost.test.de")

    # Act
    result = config_gen.gen_config_data()

    # Assert
    assert isinstance(result, dict)


def test_get_config_data_for_koan(create_testbed: Callable[[], CobblerAPI]):
    """
    Test to verify that getting all configuration data in the Koan-specific format works as expected.
    """
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system
    config_gen = ConfigGen(test_api, "testhost.test.de")

    # Act
    result = config_gen.gen_config_data_for_koan()

    # Assert
    assert isinstance(result, str)
