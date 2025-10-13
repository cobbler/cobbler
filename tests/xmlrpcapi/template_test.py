"""
Tests that validate the functionality of the module that is responsible for providing XML-RPC calls related to
templates.
"""

from cobbler.remote import CobblerXMLRPCInterface


def test_find_template_without_collection(remote: CobblerXMLRPCInterface, token: str):
    """
    TODO
    """
    # Arrange
    name = "built-in-isolinux_menuentry"

    # Act
    result = remote.find_items("", {"name": name}, "name", False, False, token)

    # Assert
    assert result == [name]


def test_find_template(remote: CobblerXMLRPCInterface, token: str):
    """
    TODO
    """
    # Arrange
    name = "built-in-isolinux_menuentry"

    # Act
    result = remote.find_template({"name": name}, False, False, token)

    # Assert
    assert result == [name]


def test_get_template_content(remote: CobblerXMLRPCInterface, token: str):
    """
    TODO
    """
    # Arrange
    expected_result = """LABEL {{ menu_name }}
{%- if menu_indent %}
  MENU INDENT {{ menu_indent }}
{% endif %}
  MENU LABEL {{ menu_name }}
  KERNEL {{ kernel_path }}
  {{ append_line }}
"""
    template = remote.find_template(
        {"name": "built-in-isolinux_menuentry"}, True, False, token
    )

    # Act
    result = remote.get_template_content(template[0]["uid"], token)

    # Assert
    assert result == expected_result
