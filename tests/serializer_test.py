"""
TODO
"""

from cobbler import serializer

def test_deserialize_item(mocker):
    """
    TODO
    """
    # Arrange
    module_mock = mocker.MagicMock()
    storage_mock = mocker.patch("cobbler.serializer.__get_storage_module", return_value=module_mock)
    input_collection_type = "test"
    input_name = "testitem"

    # Act
    serializer.deserialize_item(input_collection_type, input_name)

    # Assert
    module_mock.deserialize_item.assert_called_with(
        input_collection_type, input_name
    )
