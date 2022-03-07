import os

import pytest

from cobbler.configgen import ConfigGen
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System


# TODO: If the action items of the configgen class are done then the tests need to test the robustness of the class.


@pytest.fixture
def create_testbed(create_kernel_initrd, cobbler_api, cleanup_testbed):
    def _create_testbed():
        folder = create_kernel_initrd("vmlinux", "initrd.img")
        test_distro = Distro(cobbler_api)
        test_distro.name = "test_configgen_distro"
        test_distro.kernel = os.path.join(folder, "vmlinux")
        test_distro.initrd = os.path.join(folder, "initrd.img")
        cobbler_api.add_distro(test_distro)
        test_profile = Profile(cobbler_api)
        test_profile.name = "test_configgen_profile"
        test_profile.distro = "test_configgen_distro"
        cobbler_api.add_profile(test_profile)
        test_system = System(cobbler_api)
        test_system.name = "test_configgen_system"
        test_system.profile = "test_configgen_profile"
        test_system.hostname = "testhost.test.de"
        test_system.autoinstall_meta = {"test": "teststring"}
        cobbler_api.add_system(test_system)

        return cobbler_api
    return _create_testbed


@pytest.fixture(autouse=True)
def cleanup_testbed(cobbler_api):
    yield
    cobbler_api.remove_system("test_configgen_system")
    cobbler_api.remove_profile("test_configgen_profile")
    cobbler_api.remove_distro("test_configgen_distro")


def test_object_value_error(cobbler_api):
    # Arrange

    # Act & Assert
    with pytest.raises(ValueError):
        ConfigGen(cobbler_api, "nonexistant")


def test_object_creation(create_testbed):
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system

    # Act
    test_configgen = ConfigGen(test_api, "testhost.test.de")

    # Assert
    assert isinstance(test_configgen, ConfigGen)


def test_resolve_resource_var(create_testbed):
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system, package and file
    config_gen = ConfigGen(test_api, "testhost.test.de")

    # Act
    result = config_gen.resolve_resource_var("Hello $test !")

    # Assert
    assert isinstance(result, str)
    assert result == "Hello teststring !"


def test_get_cobbler_resource(create_testbed):
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system, package and file
    config_gen = ConfigGen(test_api, "testhost.test.de")

    # Act
    result = config_gen.get_cobbler_resource("")

    # Assert
    assert isinstance(result, (list, str, dict))


def test_get_config_data(create_testbed):
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system, package and file
    config_gen = ConfigGen(test_api, "testhost.test.de")

    # Act
    result = config_gen.gen_config_data()

    # Assert
    assert isinstance(result, dict)


def test_get_config_data_for_koan(create_testbed):
    # Arrange
    test_api = create_testbed()
    # FIXME: Arrange distro, profile and system, package and file
    config_gen = ConfigGen(test_api, "testhost.test.de")

    # Act
    result = config_gen.gen_config_data_for_koan()

    # Assert
    assert isinstance(result, str)
