from cobbler.api import CobblerAPI
from cobbler.items.mgmtclass import Mgmtclass


def test_object_creation():
    # Arrange
    test_api = CobblerAPI()

    # Act
    mgmtclass = Mgmtclass(test_api)

    # Arrange
    assert isinstance(mgmtclass, Mgmtclass)


def test_make_clone():
    # Arrange
    test_api = CobblerAPI()
    mgmtclass = Mgmtclass(test_api)

    # Act
    result = mgmtclass.make_clone()

    # Arrange
    assert result != mgmtclass


def test_check_if_valid():
    # Arrange
    test_api = CobblerAPI()
    mgmtclass = Mgmtclass(test_api)
    mgmtclass.name = "unittest_mgmtclass"

    # Act
    mgmtclass.check_if_valid()

    # Assert
    assert True


def test_packages():
    # Arrange
    test_api = CobblerAPI()
    mgmtclass = Mgmtclass(test_api)

    # Act
    mgmtclass.packages = ""

    # Assert
    assert mgmtclass.packages == []


def test_files():
    # Arrange
    test_api = CobblerAPI()
    mgmtclass = Mgmtclass(test_api)

    # Act
    mgmtclass.files = ""

    # Assert
    assert mgmtclass.files == []


def test_params():
    # Arrange
    test_api = CobblerAPI()
    mgmtclass = Mgmtclass(test_api)

    # Act
    mgmtclass.params = ""

    # Assert
    assert mgmtclass.params == {}


def test_is_definition():
    # Arrange
    test_api = CobblerAPI()
    mgmtclass = Mgmtclass(test_api)

    # Act
    mgmtclass.is_definition = False

    # Assert
    assert not mgmtclass.is_definition


def test_class_name():
    # Arrange
    test_api = CobblerAPI()
    mgmtclass = Mgmtclass(test_api)

    # Act
    mgmtclass.class_name = ""

    # Assert
    assert mgmtclass.class_name == ""
