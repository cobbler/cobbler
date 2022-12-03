"""
TODO
"""

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.template import Template


def test_object_creation(cobbler_api: CobblerAPI):
    """
    Test to verify that the Template object is created correctly.
    """
    # Arrange

    # Act
    repo = Template(cobbler_api)

    # Arrange
    assert isinstance(repo, Template)


def test_make_clone(cobbler_api: CobblerAPI):
    """
    Test to verify that cloning the Template object works as expected.
    """
    # Arrange
    test_template = Template(
        cobbler_api,
        template_type="cheetah",
        uri={"schema": enums.TemplateSchema.ENVIRONMENT.value},
    )

    # Act
    result = test_template.make_clone()

    # Assert
    assert result != test_template


def test_to_dict(cobbler_api: CobblerAPI):
    """
    Test to verify that the to_dict method works as expected.
    """
    # Arrange
    test_template = Template(cobbler_api)

    # Act
    result = test_template.to_dict()

    # Assert
    assert isinstance(result, dict)


def test_to_dict_resolved(cobbler_api: CobblerAPI):
    """
    Test to verify that the to_dict method with resolved=True works as expected.
    """
    # Arrange
    test_template = Template(cobbler_api)

    # Act
    result = test_template.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
