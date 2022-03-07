from cobbler.items.mgmtclass import Mgmtclass


def test_object_creation(cobbler_api):
    # Arrange

    # Act
    mgmtclass = Mgmtclass(cobbler_api)

    # Arrange
    assert isinstance(mgmtclass, Mgmtclass)


def test_make_clone(cobbler_api):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    result = mgmtclass.make_clone()

    # Arrange
    assert result != mgmtclass


def test_check_if_valid(cobbler_api):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)
    mgmtclass.name = "unittest_mgmtclass"

    # Act
    mgmtclass.check_if_valid()

    # Assert
    assert True


def test_packages(cobbler_api):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.packages = ""

    # Assert
    assert mgmtclass.packages == []


def test_files(cobbler_api):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.files = ""

    # Assert
    assert mgmtclass.files == []


def test_params(cobbler_api):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.params = ""

    # Assert
    assert mgmtclass.params == {}


def test_is_definition(cobbler_api):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.is_definition = False

    # Assert
    assert not mgmtclass.is_definition


def test_class_name(cobbler_api):
    # Arrange
    mgmtclass = Mgmtclass(cobbler_api)

    # Act
    mgmtclass.class_name = ""

    # Assert
    assert mgmtclass.class_name == ""
