"""
Test module to verify the functionality of the legacy generator.
"""

from typing import Any, Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.autoinstall.generate.legacy import LegacyGenerator
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
    Verify that legacy autoinstall files can be successfully generated.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = "built-in-default.ks"  # type: ignore
    test_generator = LegacyGenerator(cobbler_api)

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
    Verify that metadata for legacy autoinstall can be successfully generated.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_generator = LegacyGenerator(cobbler_api)

    # Act
    # pylint: disable-next= assignment-from-none
    result = test_generator.generate_autoinstall_metadata(test_system, "")  # type: ignore

    # Assert
    assert result is None


@pytest.mark.parametrize(
    "key",
    ["yum_repo_stanza", "yum_config_stanza"],
)
def test_generate_autoinstall_metadata_resolves_conceptual_parent_for_profile(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    key: str,
):
    """
    Regression test: ``generate_autoinstall_metadata`` used to pass an inverted ``is_profile`` argument to the
    repo/config stanza helpers, which made a profile resolve its conceptual parent as if it were a system (i.e. one
    ``get_conceptual_parent()`` call too many), raising an ``AttributeError`` since a distro has no further
    conceptual parent to look up ``source_repos``/the Red Hat breed check on.
    """
    # Arrange
    test_distro = create_distro()
    test_distro.breed = "redhat"  # type: ignore
    test_profile = create_profile(test_distro.uid)
    test_generator = LegacyGenerator(cobbler_api)

    # Act
    result = test_generator.generate_autoinstall_metadata(test_profile, key)  # type: ignore

    # Assert
    assert isinstance(result, str)


@pytest.mark.parametrize(
    "key",
    ["yum_repo_stanza", "yum_config_stanza"],
)
def test_generate_autoinstall_metadata_resolves_conceptual_parent_for_system(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
    key: str,
):
    """
    Regression test: the same inverted ``is_profile`` argument made a system resolve its conceptual parent as if it
    were a profile (i.e. one ``get_conceptual_parent()`` call too few), raising an ``AttributeError`` since a
    profile has no ``source_repos`` attribute (only a distro does).
    """
    # Arrange
    test_distro = create_distro()
    test_distro.breed = "redhat"  # type: ignore
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_generator = LegacyGenerator(cobbler_api)

    # Act
    result = test_generator.generate_autoinstall_metadata(test_system, key)  # type: ignore

    # Assert
    assert isinstance(result, str)
