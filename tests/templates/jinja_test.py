"""
Test module for verifying Jinja template functionalities in Cobbler.
"""

import pytest

from cobbler.api import CobblerAPI
from cobbler.templates.jinja import JinjaTemplateProvider


@pytest.fixture(name="test_provider", scope="function")
def fixture_test_provider(cobbler_api: CobblerAPI):
    """
    Fixture to provide a JinjaTemplateProvider instance for testing.
    """
    return JinjaTemplateProvider(cobbler_api)


def test_provider_creation(cobbler_api: CobblerAPI):
    """
    Test to verify the creation of a JinjaTemplateProvider instance.
    """
    # Arrange & Act
    result = JinjaTemplateProvider(cobbler_api)

    # Assert
    assert isinstance(result, JinjaTemplateProvider)


def test_template_type_available(test_provider: JinjaTemplateProvider):
    """
    Test to verify if the Jinja template type is available.
    """
    # Arrange & Act
    result = test_provider.template_type_available

    # Assert - We have installed jinja2 inside the test container
    assert result


def test_template_file_extension(test_provider: JinjaTemplateProvider):
    """
    Test to verify the file extension used by Jinja templates.
    """
    # Arrange & Act
    result = test_provider.template_file_extension

    # Assert - We have installed jinja2 inside the test container
    assert result == "jinja"


def test_render(test_provider: JinjaTemplateProvider):
    """
    Test to verify the rendering of a Jinja template with provided context.
    """
    # Arrange
    test_template = '{% include "built-in-isolinux_menuentry" %}'
    test_search_table = {
        "menu_name": "test",
        "kernel_path": "/test",
        "append_line": "APPEND: test=true",
    }
    expected_result = f"""LABEL {test_search_table['menu_name']}
  MENU LABEL {test_search_table['menu_name']}
  KERNEL {test_search_table['kernel_path']}
  {test_search_table['append_line']}"""

    # Act
    result = test_provider.render(test_template, test_search_table)

    # Assert
    assert result == expected_result


def test_render_toyaml(test_provider: JinjaTemplateProvider):
    """
    Test to verify the custom Jinja filter "toyaml" is working as expected.
    """
    test_template = "{{ context | toyaml }}"
    test_search_table = {
        "context": [
            {
                "my": "custom",
                "mapping": True,
                "with": 5,
                "complex": ["data", 5, {"test": True}],
            }
        ]
    }
    expected_result = "- complex:\n  - data\n  - 5\n  - test: true\n  mapping: true\n  my: custom\n  with: 5"

    # Act
    result = test_provider.render(test_template, test_search_table)

    # Assert
    assert result == expected_result
