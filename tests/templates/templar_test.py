"""
Tests that validate the functionality of the module that is responsible for abstracting access to the different
template rendering engines that Cobbler supports.
"""

import pytest

from cobbler.api import CobblerAPI
from cobbler.templates import Templar


@pytest.fixture(scope="function")
def setup_cheetah_macros_file():
    """
    TODO
    """
    with open("/etc/cobbler/cheetah_macros", "w", encoding="UTF-8") as f:
        f.writelines(
            [
                "## define Cheetah functions here and reuse them throughout your templates\n",
                "\n",
                "#def $myMethodInMacros($a)\n",
                "Text in method: $a\n",
                "#end def\n",
            ]
        )
    yield
    with open("/etc/cobbler/cheetah_macros", "w", encoding="UTF-8") as f:
        f.writelines(
            [
                "## define Cheetah functions here and reuse them throughout your templates\n",
                "\n",
                "\n",
            ]
        )


def test_render(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    test_templar = Templar(cobbler_api)
    test_templar.load_template_providers()

    # Act
    result = test_templar.render("", {}, None, template_type="cheetah")

    # Assert
    assert result == ""


def test_render_cheetah(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    test_templar = Templar(cobbler_api)
    test_templar.load_template_providers()

    # Act
    result = test_templar.render("$test", {"test": 5}, None, "cheetah")

    # Assert
    assert result == "5"


@pytest.mark.usefixtures("setup_cheetah_macros_file")
@pytest.mark.skip("Macros only work if we restart cobblerd")
def test_cheetah_macros(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    test_templar = Templar(cobbler_api)
    test_templar.load_template_providers()

    # Act
    result = test_templar.render("$myMethodInMacros(5)", {}, None, "cheetah")

    # Assert
    assert result == "Text in method: 5\n"


def test_render_jinja2(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    test_templar = Templar(cobbler_api)
    test_templar.load_template_providers()

    # Act
    result = test_templar.render("{{ foo }}", {"foo": "Test successful"}, None, "jinja")

    # Assert
    assert result == "Test successful"


def test_load_template_providers(cobbler_api: CobblerAPI):
    """
    TODO
    """
    # Arrange
    test_templar = Templar(cobbler_api)
    test_templar.load_template_providers()

    # Act
    test_templar.load_template_providers()

    # Act
    assert list(
        test_templar.__dict__.get("_Templar__loaded_template_providers", {}).keys()
    ) == ["cheetah", "jinja"]
