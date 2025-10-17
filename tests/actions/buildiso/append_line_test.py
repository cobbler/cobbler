"""
Test module to ensure the functionality of the append line builder for the buildiso functionality.
"""

from typing import Any, Callable, Dict

import pytest

from cobbler import utils
from cobbler.actions.buildiso.append_line import AppendLineBuilder
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System


def test_init(cobbler_api: CobblerAPI):
    """
    Test to verify that creating the objects works as expected.
    """
    assert isinstance(AppendLineBuilder(cobbler_api, "", {}), AppendLineBuilder)


@pytest.mark.parametrize(
    "input_kopts_dict,exepcted_output",
    [
        ({}, ""),
        ({"test": 1}, "test=1"),
        ({"test": None}, "test"),
        ({"test": '"test"'}, 'test="test"'),
        ({"test": "test test test"}, 'test="test test test"'),
        ({"test": 'test "test" test'}, 'test="test "test" test"'),
        ({"test": ['"test"']}, 'test="test"'),
        ({"test": ['"test"', "test"]}, 'test="test" test=test'),
    ],
)
def test_add_remaining_kopts(
    cobbler_api: CobblerAPI, input_kopts_dict: Dict[str, Any], exepcted_output: str
):
    """
    Test to verify that the kernel options are correctly formatted and added.
    """
    # Arrange
    test_builder = AppendLineBuilder(cobbler_api, "", {})

    # Act
    test_builder.add_remaining_kopts(input_kopts_dict)
    result = test_builder.append_line.render({})

    # Assert
    assert result == exepcted_output


def test_generate_system(
    request: "pytest.FixtureRequest",
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str, str, str], System],
):
    """
    Test to verify that generating the append line for a System works as expected.
    """
    # Arrange
    autoinstall_scheme = cobbler_api.settings().autoinstall_scheme
    test_distro = create_distro()
    test_distro.breed = "suse"  # type: ignore[method-assign]
    cobbler_api.add_distro(test_distro)
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(profile_uid=test_profile.uid)  # type: ignore
    blendered_data = utils.blender(cobbler_api, False, test_system)  # type: ignore
    blendered_data["autoinstall"] = (
        f"{autoinstall_scheme}://{blendered_data['server']}:{blendered_data['http_port']}/cblr/svc/op/autoinstall/"
        f"profile/{test_system.name}"  # type: ignore
    )
    test_builder = AppendLineBuilder(cobbler_api, test_distro.name, blendered_data)
    originalname = request.node.originalname or request.node.name  # type: ignore

    # Act
    result = test_builder.generate_system(test_distro, test_system, False)  # type: ignore

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert (
        result
        == f"APPEND initrd=/{originalname}.img install=http://192.168.1.1:80/cblr/links/{originalname} "
        "autoyast=http://192.168.1.1:80/cblr/svc/op/autoinstall/profile/test_generate_system"
    )


def test_generate_system_redhat(
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str, str, str], System],
):
    """
    Test to verify that generating the append line for a RedHat Distro works as expected.
    """
    # Arrange
    autoinstall_scheme = cobbler_api.settings().autoinstall_scheme
    test_distro = create_distro()
    test_distro.breed = "redhat"  # type: ignore[method-assign]
    cobbler_api.add_distro(test_distro)
    test_profile = create_profile(test_distro.uid)
    test_system = create_system(profile_uid=test_profile.uid)  # type: ignore
    blendered_data = utils.blender(cobbler_api, False, test_system)  # type: ignore
    blendered_data["autoinstall"] = (
        f"{autoinstall_scheme}://{blendered_data['server']}:{blendered_data['http_port']}/cblr/svc/op/autoinstall/"
        f"profile/{test_system.name}"  # type: ignore
    )
    test_builder = AppendLineBuilder(cobbler_api, test_distro.name, blendered_data)

    # Act
    result = test_builder.generate_system(test_distro, test_system, False)  # type: ignore

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert (
        result == f"APPEND initrd=/{test_distro.name}.img "
        "inst.ks=http://192.168.1.1:80/cblr/svc/op/autoinstall/profile/test_generate_system_redhat"
    )


def test_generate_profile(
    request: "pytest.FixtureRequest",
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that generating the append line for a Profile works as expected.
    """
    # Arrange
    autoinstall_scheme = cobbler_api.settings().autoinstall_scheme
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    blendered_data = utils.blender(cobbler_api, False, test_profile)
    blendered_data["autoinstall"] = (
        f"{autoinstall_scheme}://{blendered_data['server']}:{blendered_data['http_port']}/cblr/svc/op/autoinstall/"
        f"profile/{test_profile.name}"  # type: ignore
    )
    test_builder = AppendLineBuilder(cobbler_api, test_distro.name, blendered_data)
    originalname = request.node.originalname or request.node.name  # type: ignore

    # Act
    result = test_builder.generate_profile("suse", "opensuse15generic")

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert (
        result
        == f"append initrd=/{originalname}.img install=http://192.168.1.1:80/cblr/links/{originalname} "
        "autoyast=http://192.168.1.1:80/cblr/svc/op/autoinstall/profile/test_generate_profile"
    )


def test_generate_profile_install(
    request: "pytest.FixtureRequest",
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that generating the append line for a Profile with an install option works as expected.
    """
    # Arrange
    autoinstall_scheme = cobbler_api.settings().autoinstall_scheme
    test_distro = create_distro()
    originalname = request.node.originalname or request.node.name  # type: ignore
    test_distro.kernel_options = (  # type: ignore[method-assign]
        f"install=http://192.168.40.1:80/cblr/links/{originalname}"  # type: ignore
    )
    test_profile = create_profile(test_distro.uid)
    blendered_data = utils.blender(cobbler_api, False, test_profile)
    blendered_data["autoinstall"] = (
        f"{autoinstall_scheme}://{blendered_data['server']}:{blendered_data['http_port']}/cblr/svc/op/autoinstall/"
        f"profile/{test_profile.name}"  # type: ignore
    )
    test_builder = AppendLineBuilder(cobbler_api, test_distro.name, blendered_data)

    # Act
    result = test_builder.generate_profile("suse", "opensuse15generic")

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert (
        result
        == f"append initrd=/{originalname}.img install=http://192.168.40.1:80/cblr/links/{originalname} "
        "autoyast=http://192.168.1.1:80/cblr/svc/op/autoinstall/profile/test_generate_profile_install"
    )


def test_generate_profile_rhel7(
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that generating the append line for a RedHat 7 Profile works as expected.
    """
    # Arrange
    autoinstall_scheme = cobbler_api.settings().autoinstall_scheme
    test_distro = create_distro()
    test_distro.breed = "redhat"  # type: ignore[method-assign]
    cobbler_api.add_distro(test_distro)
    test_profile = create_profile(test_distro.uid)
    blendered_data = utils.blender(cobbler_api, False, test_profile)
    blendered_data["autoinstall"] = (
        f"{autoinstall_scheme}://{blendered_data['server']}:{blendered_data['http_port']}/cblr/svc/op/autoinstall/"
        f"profile/{test_profile.name}"  # type: ignore
    )
    test_builder = AppendLineBuilder(cobbler_api, test_distro.name, blendered_data)

    # Act
    result = test_builder.generate_profile("redhat", "rhel7")

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert (
        result == f"append initrd=/{test_distro.name}.img "
        "inst.ks=http://192.168.1.1:80/cblr/svc/op/autoinstall/profile/test_generate_profile_rhel7"
    )


def test_generate_profile_rhel6(
    cobbler_api: "CobblerAPI",
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that generating the append line for a RedHat 6 Profile works as expected.
    """
    # Arrange
    autoinstall_scheme = cobbler_api.settings().autoinstall_scheme
    test_distro = create_distro()
    test_distro.breed = "redhat"  # type: ignore[method-assign]
    cobbler_api.add_distro(test_distro)
    test_profile = create_profile(test_distro.uid)
    blendered_data = utils.blender(cobbler_api, False, test_profile)
    blendered_data["autoinstall"] = (
        f"{autoinstall_scheme}://{blendered_data['server']}:{blendered_data['http_port']}/cblr/svc/op/autoinstall/"
        f"profile/{test_profile.name}"  # type: ignore
    )
    test_builder = AppendLineBuilder(cobbler_api, test_distro.name, blendered_data)

    # Act
    result = test_builder.generate_profile("redhat", "rhel6")

    # Assert
    # Very basic test yes but this is the expected result atm
    # TODO: Make tests more sophisticated
    assert (
        result == f"append initrd=/{test_distro.name}.img "
        "ks=http://192.168.1.1:80/cblr/svc/op/autoinstall/profile/test_generate_profile_rhel6"
    )
