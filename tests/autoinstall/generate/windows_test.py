"""
Test module to verify the functionality of the Kickstart generator.
"""

from typing import Any, Callable

from cobbler.api import CobblerAPI
from cobbler.autoinstall.generate.windows import WindowsGenerator
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System


def test_generate_autoinstall(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Verify that Kickstart files can be successfully generated.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = "built-in-win.xml"  # type: ignore
    test_generator = WindowsGenerator(cobbler_api)

    # Act
    result = test_generator.generate_autoinstall(
        test_system, test_system.autoinstall  # type: ignore
    )

    # Assert
    assert isinstance(result, str)


def test_generate_autoinstall_metatdata(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Verify that metadata for Kickstart can be successfully generated.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_generator = WindowsGenerator(cobbler_api)

    # Act
    # pylint: disable-next= assignment-from-none
    result = test_generator.generate_autoinstall_metadata(test_system, "")  # type: ignore

    # Assert
    assert result is None
