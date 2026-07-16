"""
Test module to verify the functionality of the Template item class.
"""

import pathlib

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


def test_content_setter_writes_under_autoinstall_templates_dir(
    cobbler_api: CobblerAPI, tmp_path: pathlib.Path
):
    """
    Test that setting the content of a FILE schema template writes to the file resolved against
    ``autoinstall_templates_dir``, the same location ``refresh_content()`` reads back from.
    """
    # Arrange
    relative_path = "test_content_setter.j2"
    cobbler_api.settings().autoinstall_templates_dir = str(tmp_path)
    (tmp_path / relative_path).touch()
    test_template = Template(
        cobbler_api,
        uri={"schema": enums.TemplateSchema.FILE.value, "path": relative_path},
    )

    # Act
    test_template.content = "# test content\n"

    # Assert
    assert (tmp_path / relative_path).read_text(encoding="UTF-8") == "# test content\n"
    assert test_template.content == "# test content\n"
