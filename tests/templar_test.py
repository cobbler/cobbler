import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.templar import Templar


@pytest.fixture(scope="function")
def setup_cheetah_macros_file():
    with open("/etc/cobbler/cheetah_macros", "w") as f:
        f.writelines(["## define Cheetah functions here and reuse them throughout your templates\n",
                      "\n",
                      "#def $myMethodInMacros($a)\n",
                      "Text in method: $a\n",
                      "#end def\n"])
    yield
    with open("/etc/cobbler/cheetah_macros", "w") as f:
        f.writelines(["## define Cheetah functions here and reuse them throughout your templates\n",
                      "\n",
                      "\n"])


def test_check_for_invalid_imports():
    # Arrange
    test_api = CobblerAPI()
    test_collection_mgr = CollectionManager(test_api)
    test_templar = Templar(test_collection_mgr)
    testdata = "#import json"

    # Act & Assert
    with pytest.raises(CX):
        test_templar.check_for_invalid_imports(testdata)


def test_render():
    # Arrange
    test_api = CobblerAPI()
    test_collection_mgr = CollectionManager(test_api)
    test_templar = Templar(test_collection_mgr)

    # Act
    result = test_templar.render("", {}, None, template_type="cheetah")

    # Assert
    assert result == ""


def test_render_cheetah():
    # Arrange
    test_api = CobblerAPI()
    test_collection_mgr = CollectionManager(test_api)
    test_templar = Templar(test_collection_mgr)

    # Act
    result = test_templar.render_cheetah("$test", {"test": 5})

    # Assert
    assert result == '5'


@pytest.mark.usefixtures("setup_cheetah_macros_file")
@pytest.mark.skip("Macros only work if we restart cobblerd")
def test_cheetah_macros():
    # Arrange
    test_api = CobblerAPI()
    test_collection_mgr = CollectionManager(test_api)
    templar = Templar(test_collection_mgr)

    # Act
    result = templar.render_cheetah("$myMethodInMacros(5)", {})

    # Assert
    assert result == "Text in method: 5\n"


def test_render_jinja2():
    # Arrange
    test_api = CobblerAPI()
    test_collection_mgr = CollectionManager(test_api)
    test_templar = Templar(test_collection_mgr)

    # Act
    result = test_templar.render_jinja2("{{ foo }}", {"foo": "Test successful"})

    # Assert
    assert result == "Test successful"
