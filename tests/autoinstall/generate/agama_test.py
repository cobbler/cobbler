"""
Test module to verify the functionality of the Agama autoinstall generator.
"""

import json
from typing import Any, Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.autoinstall.generate.agama import AgamaGenerator
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System


def test_agama_generate_autoinstall(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test to verify that the built-in template renderes with the Agama generator.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-autoinst.json"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = target_template
    test_generator = AgamaGenerator(cobbler_api)

    # Act
    result = test_generator.generate_autoinstall(test_system, target_template)

    # Assert
    parsed = json.loads(result)
    post_scripts = parsed["scripts"]["post"]
    expected_url = (
        f"http://{cobbler_api.settings().server}"
        f"/cblr/svc/op/nopxe/system/{test_system.name}"
    )
    assert any(expected_url in script["content"] for script in post_scripts)


def test_agama_generate_autoinstall_merges_nopxe_with_custom_scripts(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test that an admin-configured ``agama_scripts``/``post`` entry and the automatically injected ``nopxe`` script
    both end up in the same single ``scripts`` key, instead of the built-in nopxe script producing a second,
    JSON-breaking top-level ``scripts`` key.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-autoinst.json"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_system.autoinstall = target_template
    test_system.autoinstall_meta = {
        "agama_modules": ["scripts"],
        "agama_scripts": {"post": ["my-custom-script"]},
    }
    test_generator = AgamaGenerator(cobbler_api)

    # Act
    result = test_generator.generate_autoinstall(test_system, target_template)

    # Assert
    parsed = json.loads(result)
    assert isinstance(parsed["scripts"], dict)
    post_scripts = parsed["scripts"]["post"]
    names = [script.get("name") for script in post_scripts]
    assert names.count("nopxe") == 1
    assert "my-custom-script" in names


def test_agama_generate_autoinstall_nopxe_does_not_leak_across_systems(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test that injecting the ``nopxe`` post-script does not mutate the shared Profile's own persisted
    ``autoinstall_meta``, and that two Systems inheriting the same Profile each get their own correctly-targeted
    ``nopxe`` URL rather than leaking one System's URL into the other's rendered profile.
    """
    # Arrange
    target_template = cobbler_api.find_template(
        False, False, name="built-in-autoinst.json"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Target template not found!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall_meta = {
        "agama_modules": ["scripts"],
        "agama_scripts": {"post": ["my-custom-script"]},
    }
    system_a: System = create_system(
        profile_uid=test_profile.uid, name="agama-system-a"
    )
    system_b: System = create_system(
        profile_uid=test_profile.uid, name="agama-system-b"
    )
    system_a.autoinstall = target_template
    system_b.autoinstall = target_template
    test_generator = AgamaGenerator(cobbler_api)

    # Act
    result_a = test_generator.generate_autoinstall(system_a, target_template)
    result_b = test_generator.generate_autoinstall(system_b, target_template)

    # Assert - each system's rendered profile points nopxe at itself, not the other system
    for system, result in ((system_a, result_a), (system_b, result_b)):
        expected_url = (
            f"http://{cobbler_api.settings().server}"
            f"/cblr/svc/op/nopxe/system/{system.name}"
        )
        post_scripts = json.loads(result)["scripts"]["post"]
        nopxe_entries = [s for s in post_scripts if s.get("name") == "nopxe"]
        assert len(nopxe_entries) == 1
        assert expected_url in nopxe_entries[0]["content"]

    # Assert - the shared Profile's own persisted autoinstall_meta was never mutated
    assert test_profile.autoinstall_meta["agama_scripts"]["post"] == [
        "my-custom-script"
    ]


def test_agama_generate_autoinstall_metatdata(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
):
    """
    Test to verify that the generator can successfully generate the metadata for Agama.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system: System = create_system(profile_uid=test_profile.uid)
    test_generator = AgamaGenerator(cobbler_api)

    # Act
    test_generator.generate_autoinstall_metadata(test_system, "")

    # Assert - no exception is good enough for now
    assert True
