import pytest

from cobbler.templates import Templar


@pytest.fixture(scope="function")
def setup_cheetah_macros_file():
    with open("/etc/cobbler/cheetah_macros", "w") as f:
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
    with open("/etc/cobbler/cheetah_macros", "w") as f:
        f.writelines(
            [
                "## define Cheetah functions here and reuse them throughout your templates\n",
                "\n",
                "\n",
            ]
        )


def test_render(cobbler_api):
    # Arrange
    test_templar = Templar(cobbler_api)

    # Act
    result = test_templar.render("", {}, None, template_type="cheetah")

    # Assert
    assert result == ""


def test_render_cheetah(cobbler_api):
    # Arrange
    test_templar = Templar(cobbler_api)

    # Act
    result = test_templar.render("$test", {"test": 5}, None, "cheetah")

    # Assert
    assert result == "5"


@pytest.mark.usefixtures("setup_cheetah_macros_file")
@pytest.mark.skip("Macros only work if we restart cobblerd")
def test_cheetah_macros(cobbler_api):
    # Arrange
    templar = Templar(cobbler_api)

    # Act
    result = templar.render("$myMethodInMacros(5)", {}, None, "cheetah")

    # Assert
    assert result == "Text in method: 5\n"


def test_render_jinja2(cobbler_api):
    # Arrange
    test_templar = Templar(cobbler_api)

    # Act
    result = test_templar.render("{{ foo }}", {"foo": "Test successful"}, None, "jinja")

    # Assert
    assert result == "Test successful"
