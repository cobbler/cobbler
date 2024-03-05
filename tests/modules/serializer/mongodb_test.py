"""
TODO
"""

import copy
import pytest
from cobbler.cexceptions import CX
from cobbler.modules.serializers import mongodb

from tests.conftest import does_not_raise

@pytest.mark.parametrize(
    "item_name,expected_exception",
    [
        (
            "testitem",
            does_not_raise(),
        ),
        (
            None,
            pytest.raises(CX),
        ),
    ],
)
def test_deserialize_item(item_name: str, expected_exception):
    """
    TODO
    """
    # Arrange
    collection_type = "distro"
    input_value = {"name": item_name, "arch": "x86_64"}
    test_item = copy.deepcopy(input_value)
    if item_name is not None:
        mongodb.__connect()
        mongodb.mongodb[collection_type].insert_one(test_item)

    expected_value = input_value.copy()
    expected_value["inmemory"] = True

    # Act
    with expected_exception:
        result = mongodb.deserialize_item(collection_type, item_name)
        print(result)

        # Assert
        assert result in (expected_value, {"inmemory": True})
