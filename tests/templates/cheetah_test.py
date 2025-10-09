"""
Test module for verifying Cheetah template functionalities in Cobbler.
"""

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
