import pytest

from cobbler.api import CobblerAPI
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items.distro import Distro


def test_to_dict():
    # Arrange
    test_api = CobblerAPI()
    test_collection_mgr = CollectionManager(test_api)
    titem = Distro(test_collection_mgr)
    
    # Act
    result = titem.to_dict()
    
    # Assert
    assert isinstance(result, dict)
    assert "autoinstall_meta" in result
    assert "ks_meta" in result
    # TODO check more fields
