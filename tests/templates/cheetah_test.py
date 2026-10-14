"""
Test module for verifying Cheetah template functionalities in Cobbler.
"""

from types import SimpleNamespace
from typing import Any, Dict, List, Set, Tuple
from unittest.mock import patch

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.templates.cheetah import CheetahTemplateProvider, CobblerCheetahTemplate


def test_check_for_invalid_imports(cobbler_api: CobblerAPI):
    """
    Test to verify that invalid imports in Cheetah templates are correctly identified and raise an exception.
    """
    # Arrange
    test_templar = CheetahTemplateProvider(cobbler_api)
    testdata = "#import json"

    # Act & Assert
    with pytest.raises(CX):
        test_templar.check_for_invalid_imports(testdata)  # type: ignore


def test_compile(cobbler_api: CobblerAPI):
    """
    Test to verify that a simple Cheetah template can be compiled and rendered correctly.
    """
    # Arrange

    # Act
    compiled_template = CobblerCheetahTemplate(cobbler_api=cobbler_api).compile(
        source="$test"
    )
    result = str(compiled_template(namespaces={"test": 5}))  # type: ignore

    # Assert
    assert result == "5"


def test_read_snippet_none(cobbler_api: CobblerAPI):
    """
    Test to verify that attempting to read a non-existing snippet returns None.
    """
    # Arrange
    test_template = CobblerCheetahTemplate(cobbler_api=cobbler_api)

    # Act
    result = test_template.read_snippet("nonexistingsnippet")

    # Assert
    assert result is None


def test_read_snippet(cobbler_api: CobblerAPI):
    """
    Test to verify that a known built-in snippet can be read correctly.
    """
    # Arrange
    test_template = CobblerCheetahTemplate(cobbler_api=cobbler_api)
    expected = (
        "#errorCatcher ListErrors\n" + "set -x -v\n" + "exec 1>/root/ks-post.log 2>&1\n"
    )

    # Act
    print([obj.name for obj in test_template.cobbler_api.templates()])
    result = test_template.read_snippet("built-in-log_ks_post")

    # Assert
    assert result == expected


def test_nonexisting_snippet(cobbler_api: CobblerAPI):
    """
    Test to verify that requesting a non-existing snippet returns the appropriate error message.
    """
    # Arrange
    test_template = CobblerCheetahTemplate(cobbler_api=cobbler_api)

    # Act
    result = test_template.SNIPPET("preseed_early_default")

    # Assert
    assert result == "# Error: no snippet data for preseed_early_default\n"


def test_snippet(cobbler_api: CobblerAPI):
    """
    Test to verify that a known built-in snippet can be retrieved correctly.
    """
    # Arrange
    test_template = CobblerCheetahTemplate(
        cobbler_api=cobbler_api,
    )

    # Act
    result = test_template.SNIPPET("built-in-post_run_deb")

    # Assert
    assert (
        result
        == "# A general purpose snippet to add late-command actions for preseeds\n"
    )


def test_sedesc(cobbler_api: CobblerAPI):
    """
    Test to verify that special characters in a string are correctly escaped.
    """
    # Arrange
    test_input = "This () needs [] to ^ be * escaped {}."
    expected = "This \\(\\) needs \\[\\] to \\^ be \\* escaped \\{\\}\\."
    test_template = CobblerCheetahTemplate(cobbler_api=cobbler_api)

    # Act
    result = test_template.sedesc(test_input)

    # Assert
    assert result == expected


def test_system_snippet_missing_variable(cobbler_api: CobblerAPI):
    """
    Test that an unresolved variable preserves the per-system snippet and its placeholder.
    """
    # Arrange
    snippet = SimpleNamespace(uid="system-snippet", content="url=$solo_name\n")
    provider = CheetahTemplateProvider(cobbler_api)

    # Act
    with patch.object(cobbler_api, "find_template", return_value=snippet):
        result = provider.render("$SNIPPET('chef_solo')", {"system_name": "node1"})

    # Assert
    assert result == "url=$solo_name\n"


OVERRIDE_PRIORITY_CASES: List[Tuple[Set[str], Dict[str, str], str]] = [
    # All overrides exist: the highest-priority one (system) must win.
    (
        {"per_system", "per_profile", "per_distro"},
        {
            "system_name": "node1",
            "profile_name": "profile1",
            "distro_name": "distro1",
        },
        "system content\n",
    ),
    # No per-system override: falls back to the per-profile override.
    (
        {"per_profile", "per_distro"},
        {
            "system_name": "node1",
            "profile_name": "profile1",
            "distro_name": "distro1",
        },
        "profile content\n",
    ),
    # Only a per-distro override exists: falls back all the way to it.
    (
        {"per_distro"},
        {
            "system_name": "node1",
            "profile_name": "profile1",
            "distro_name": "distro1",
        },
        "distro content\n",
    ),
    # Variables exist but none of the overrides do: falls back to the general snippet.
    (
        set(),
        {
            "system_name": "node1",
            "profile_name": "profile1",
            "distro_name": "distro1",
        },
        "general content\n",
    ),
    # None of the system/profile/distro variables exist: the general snippet is used
    # even though overrides for all three are available.
    (
        {"per_system", "per_profile", "per_distro"},
        {},
        "general content\n",
    ),
]


@pytest.mark.parametrize(
    "available_overrides,context,expected",
    OVERRIDE_PRIORITY_CASES,
)
def test_snippet_override_priority(
    cobbler_api: CobblerAPI,
    available_overrides: Set[str],
    context: Dict[str, str],
    expected: str,
):
    """
    Test that the per-system, per-profile, and per-distro overrides are selected in priority
    order, and that the lookup correctly falls through to the next class (and ultimately to the
    general snippet) whenever a higher-priority override does not exist.
    """
    # Arrange
    override_content = {
        "per_system": "system content\n",
        "per_profile": "profile content\n",
        "per_distro": "distro content\n",
    }

    def fake_find_template(*_args: Any, **kwargs: Any) -> Any:
        tags = kwargs.get("tags")
        if tags is None:
            return SimpleNamespace(uid="general-snippet", content="general content\n")
        if tags in available_overrides:
            return SimpleNamespace(
                uid=f"{tags}-snippet", content=override_content[tags]
            )
        return None

    provider = CheetahTemplateProvider(cobbler_api)

    # Act
    with patch.object(cobbler_api, "find_template", side_effect=fake_find_template):
        result = provider.render("$SNIPPET('chef_solo')", context)

    # Assert
    assert result == expected
