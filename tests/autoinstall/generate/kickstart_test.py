"""
Test module to verify the functionality of the Kickstart generator.
"""

from typing import Any, Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.autoinstall.generate.kickstart import KickstartGenerator
from cobbler.items.distro import Distro
from cobbler.items.image import Image
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
    test_system.autoinstall = "built-in-default.ks"  # type: ignore
    test_generator = KickstartGenerator(cobbler_api)

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
    test_generator = KickstartGenerator(cobbler_api)

    # Act
    # pylint: disable-next= assignment-from-none
    result = test_generator.generate_autoinstall_metadata(test_system, "")  # type: ignore

    # Assert
    assert result is None


@pytest.mark.parametrize(
    "key",
    ["yum_repo_stanza", "yum_config_stanza"],
)
def test_generate_autoinstall_metadata_for_image_attached_system(
    cobbler_api: CobblerAPI,
    create_image: Callable[[], Image],
    create_system: Any,
    key: str,
):
    """
    Regression test: a system attached to an image (not a profile) has no profile/distro in its
    conceptual-parent chain, so ``generate_repo_stanza`` used to raise ``KeyError: 'repos'`` (no
    "repos" key in the blended dict) and would then have hit ``AttributeError`` resolving the
    distro.
    """
    # Arrange
    test_image = create_image()
    test_system: System = create_system(image_uid=test_image.uid)
    test_generator = KickstartGenerator(cobbler_api)

    # Act
    result = test_generator.generate_autoinstall_metadata(test_system, key)  # type: ignore

    # Assert
    assert isinstance(result, str)
