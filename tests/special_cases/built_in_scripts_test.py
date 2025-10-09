"""
Test module for built-in scripts in Cobbler.
"""

from typing import Callable

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def test_built_in_preseed_early_default(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in preseed early default script generation.
    """
    # Arrange
    expected_result = [
        "# Start preseed_early_default",
        "# This script is not run in the chroot /target by default",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/pre/profile/test_built_in_preseed_early_default" -O /dev/null',
        "",
        "# End preseed_early_default",
        "",
    ]
    template = "built-in-preseed_early_default"
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)

    # Act
    result = cobbler_api.generate_script(test_profile.name, None, template)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_preseed_late_default(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in preseed late default script generation.
    """
    # Arrange
    expected_result = [
        "# Start preseed_late_default",
        "# This script runs in the chroot /target by default",
        "# Start post_install_network_config generated code",
        "# End post_install_network_config generated code",
        "",
        "# start late_apt_repo_config",
        "cat<<EOF>/etc/apt/sources.list",
        "EOF",
        "# end late_apt_repo_config",
        "",
        "# A general purpose snippet to add late-command actions for preseeds",
        "",
        "# Start download cobbler managed config files (if applicable)",
        "# End download cobbler managed config files (if applicable)",
        "",
        "",
        'wget "http://192.168.1.1/cblr/svc/op/trig/mode/post/profile/test_built_in_preseed_late_default" -O /dev/null',
        "# End preseed_late_default",
        "",
    ]
    template = "built-in-preseed_late_default"
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)

    # Act
    result = cobbler_api.generate_script(test_profile.name, None, template)

    # Assert
    assert result == "\n".join(expected_result)


def test_built_in_preseed_nochroot_late_default(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify the built-in preseed nochroot late default script generation.
    """
    # Arrange
    expected_result = [
        "# Start preseed_nochroot_late_default",
        "# This script runs in the / directory by default",
        "",
        "# End preseed_nochroot_late_default",
        "",
    ]
    template = "built-in-preseed_nochroot_late_default"
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)

    # Act
    result = cobbler_api.generate_script(test_profile.name, None, template)

    # Assert
    assert result == "\n".join(expected_result)
