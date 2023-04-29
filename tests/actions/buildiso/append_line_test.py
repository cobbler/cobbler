"""
TODO
"""

from typing import Callable

import pytest

from cobbler import utils
from cobbler.actions.buildiso.netboot import AppendLineBuilder
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System


def test_init():
    """
    TODO
    """
    assert isinstance(AppendLineBuilder("", {}), AppendLineBuilder)


def test_generate_system(
    request: "pytest.FixtureRequest",
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str, str, str], System],
):
    """
    TODO
    """
    # Arrange
    test_distro = create_distro()
    test_distro.breed = "suse"
    cobbler_api.add_distro(test_distro)
    test_profile = create_profile(test_distro.name)
    test_system = create_system(profile_name=test_profile.name)  # type: ignore
    blendered_data = utils.blender(cobbler_api, False, test_system)  # type: ignore
    test_builder = AppendLineBuilder(test_distro.name, blendered_data)
    originalname = request.node.originalname or request.node.name  # type: ignore

    # Act
    result = test_builder.generate_system(test_distro, test_system, False)  # type: ignore

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert (
        result
        == "  APPEND initrd=/%s.img install=http://192.168.1.1:80/cblr/links/%s autoyast=default.ks"
        % (originalname, originalname)
    )


def test_generate_system_redhat(
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str, str, str], System],
):
    """
    TODO
    """
    # Arrange
    test_distro = create_distro()
    test_distro.breed = "redhat"
    cobbler_api.add_distro(test_distro)
    test_profile = create_profile(test_distro.name)
    test_system = create_system(profile_name=test_profile.name)  # type: ignore
    blendered_data = utils.blender(cobbler_api, False, test_system)  # type: ignore
    test_builder = AppendLineBuilder(test_distro.name, blendered_data)

    # Act
    result = test_builder.generate_system(test_distro, test_system, False)  # type: ignore

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert result == f"  APPEND initrd=/{test_distro.name}.img inst.ks=default.ks"


def test_generate_profile(
    request: "pytest.FixtureRequest",
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    TODO
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    blendered_data = utils.blender(cobbler_api, False, test_profile)
    test_builder = AppendLineBuilder(test_distro.name, blendered_data)
    originalname = request.node.originalname or request.node.name  # type: ignore

    # Act
    result = test_builder.generate_profile("suse", "opensuse15generic")

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert (
        result
        == " append initrd=/%s.img install=http://192.168.1.1:80/cblr/links/%s autoyast=default.ks"
        % (originalname, originalname)
    )


def test_generate_profile_install(
    request: "pytest.FixtureRequest",
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    TODO
    """
    # Arrange
    test_distro = create_distro()
    originalname = request.node.originalname or request.node.name  # type: ignore

    test_distro.kernel_options = (
        "install=http://192.168.40.1:80/cblr/links/%s" % originalname  # type: ignore
    )
    test_profile = create_profile(test_distro.name)
    blendered_data = utils.blender(cobbler_api, False, test_profile)
    test_builder = AppendLineBuilder(test_distro.name, blendered_data)

    # Act
    result = test_builder.generate_profile("suse", "opensuse15generic")

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert (
        result
        == " append initrd=/%s.img install=http://192.168.40.1:80/cblr/links/%s autoyast=default.ks"
        % (originalname, originalname)
    )


def test_generate_profile_rhel7(
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    TODO
    """
    # Arrange
    test_distro = create_distro()
    test_distro.breed = "redhat"
    cobbler_api.add_distro(test_distro)
    test_profile = create_profile(test_distro.name)
    blendered_data = utils.blender(cobbler_api, False, test_profile)
    test_builder = AppendLineBuilder(test_distro.name, blendered_data)

    # Act
    result = test_builder.generate_profile("redhat", "rhel7")

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert result == f" append initrd=/{test_distro.name}.img inst.ks=default.ks"


def test_generate_profile_rhel6(
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    TODO
    """
    # Arrange
    test_distro = create_distro()
    test_distro.breed = "redhat"
    cobbler_api.add_distro(test_distro)
    test_profile = create_profile(test_distro.name)
    blendered_data = utils.blender(cobbler_api, False, test_profile)
    test_builder = AppendLineBuilder(test_distro.name, blendered_data)

    # Act
    result = test_builder.generate_profile("redhat", "rhel6")

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert result == f" append initrd=/{test_distro.name}.img ks=default.ks"
