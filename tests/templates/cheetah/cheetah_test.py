import pytest

from cobbler.cexceptions import CX
from cobbler.templates.cheetah import CobblerCheetahTemplate


def test_check_for_invalid_imports(cobbler_api):
    # Arrange
    test_templar = CobblerCheetahTemplate()
    testdata = "#import json"

    # Act & Assert
    with pytest.raises(CX):
        test_templar.check_for_invalid_imports(testdata)


def test_compile():
    # Arrange

    # Act
    compiled_template = CobblerCheetahTemplate(
        searchList=[{"autoinstall_snippets_dir": "/var/lib/cobbler/snippets"}]
    ).compile(source="$test")
    result = str(compiled_template(namespaces={"test": 5}))

    # Assert
    assert result == "5"


def test_no_snippets_dir():
    # Arrange
    test_template = CobblerCheetahTemplate()

    # Act & Assert
    with pytest.raises(AttributeError):
        test_template.read_snippet("nonexistingsnippet")


def test_read_snippet_none():
    # Arrange
    test_template = CobblerCheetahTemplate(
        searchList=[{"autoinstall_snippets_dir": "/var/lib/cobbler/snippets"}]
    )

    # Act
    result = test_template.read_snippet("nonexistingsnippet")

    # Assert
    assert result is None


def test_read_snippet():
    # Arrange
    test_template = CobblerCheetahTemplate(
        searchList=[{"autoinstall_snippets_dir": "/var/lib/cobbler/snippets"}]
    )
    expected = (
        "#errorCatcher ListErrors\n" + "set -x -v\n" + "exec 1>/root/ks-post.log 2>&1\n"
    )

    # Act
    result = test_template.read_snippet("log_ks_post")

    # Assert
    assert result == expected


def test_nonexisting_snippet():
    # Arrange
    test_template = CobblerCheetahTemplate(
        searchList=[{"autoinstall_snippets_dir": "/var/lib/cobbler/snippets"}]
    )

    # Act
    result = test_template.SNIPPET("preseed_early_default")

    # Assert
    assert result == "# Error: no snippet data for preseed_early_default\n"


def test_snippet():
    # Arrange
    test_template = CobblerCheetahTemplate(
        searchList=[{"autoinstall_snippets_dir": "/var/lib/cobbler/snippets"}]
    )

    # Act
    result = test_template.SNIPPET("post_run_deb")

    # Assert
    assert (
        result
        == "# A general purpose snippet to add late-command actions for preseeds\n"
    )


def test_sedesc():
    # Arrange
    test_input = "This () needs [] to ^ be * escaped {}."
    expected = "This \\(\\) needs \\[\\] to \\^ be \\* escaped \\{\\}\\."
    test_template = CobblerCheetahTemplate()

    # Act
    result = test_template.sedesc(test_input)

    # Assert
    assert result == expected
