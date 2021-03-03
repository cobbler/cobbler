import pytest

from cobbler import remote
from cobbler.api import CobblerAPI
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items.item import Item


@pytest.mark.skip
def test_get_from_cache():
    # Arrange
    # Act
    Item.get_from_cache()
    # Assert
    assert False

@pytest.mark.skip
def test_set_cache():
    # Arrange
    # Act
    Item.set_cache()
    # Assert
    assert False

@pytest.mark.skip
def test_remove_from_cache():
    # Arrange
    # Act
    Item.remove_from_cache()
    # Assert
    assert False

@pytest.mark.skip
def test_item_create():
    # Arrange
    # Act
    titem = Item()
    # Assert
    assert False

@pytest.mark.skip
def test_get_fields():
    # Arrange
    titem = Item()
    
    # Act
    titem.get_fields()
    
    # Assert
    assert False

@pytest.mark.skip
def test_clear():
    # Arrange
    titem = Item()
    
    # Act
    titem.clear()
    # Assert
    assert False

@pytest.mark.skip
def test_make_clone():
    # Arrange
    titem = Item()
    
    # Act
    titem.make_clone()
    # Assert
    assert False

@pytest.mark.skip
def test_from_dict():
    # Arrange
    titem = Item()
    
    # Act
    titem.from_dict()
    # Assert
    assert False

@pytest.mark.skip
def test_to_string():
    # Arrange
    test_api = CobblerAPI()
    test_collection_mgr = CollectionManager(test_api)
    titem = Item(test_collection_mgr)
    
    # Act
    titem.to_string()
    # Assert
    assert False

@pytest.mark.skip
def test_get_setter_methods():
    # Arrange
    titem = Item()
    
    # Act
    titem.get_setter_methods()
    # Assert
    assert False

@pytest.mark.skip
def test_set_uid():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_uid()
    # Assert
    assert False

@pytest.mark.skip
def test_get_children():
    # Arrange
    titem = Item()
    
    # Act
    titem.get_children()
    # Assert
    assert False

@pytest.mark.skip
def test_get_descendatns():
    # Arrange
    titem = Item()
    
    # Act
    titem.get_descendants()
    # Assert
    assert False

@pytest.mark.skip
def test_get_parent():
    # Arrange
    titem = Item()
    
    # Act
    titem.get_parent()
    # Assert
    assert False

@pytest.mark.skip
def test_get_conceptual_parent():
    # Arrange
    titem = Item()
    
    # Act
    titem.get_conceptual_parent()
    # Assert
    assert False

@pytest.mark.skip
def test_set_name():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_name()
    # Assert
    assert False

@pytest.mark.skip
def test_set_comment():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_comment()
    # Assert
    assert False

@pytest.mark.skip
def test_set_owners():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_owners()
    # Assert
    assert False

@pytest.mark.skip
def test_set_kernel_options():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_kernel_options_post()
    # Assert
    assert False

@pytest.mark.skip
def test_set_kernel_options_post():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_kernel_options()
    # Assert
    assert False

@pytest.mark.skip
def test_set_autoinstall_meta():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_autoinstall_meta()
    # Assert
    assert False

@pytest.mark.skip
def test_set_mgmt_classes():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_mgmt_classes()
    # Assert
    assert False

@pytest.mark.skip
def test_set_mgmt_parameters():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_mgmt_parameters()
    # Assert
    assert False

@pytest.mark.skip
def test_set_template_files():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_template_files()
    # Assert
    assert False

@pytest.mark.skip
def test_set_fetchable_files():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_fetchable_files()
    # Assert
    assert False

@pytest.mark.skip
def test_sort_key():
    # Arrange
    titem = Item()
    
    # Act
    titem.sort_key()
    # Assert
    assert False

@pytest.mark.skip
def test_find_match():
    # Arrange
    titem = Item()
    
    # Act
    titem.find_match()
    # Assert
    assert False

@pytest.mark.skip
def test_find_match_signle_key():
    # Arrange
    titem = Item()
    
    # Act
    titem.find_match_single_key()
    # Assert
    assert False

@pytest.mark.skip
def test_dump_vars():
    # Arrange
    titem = Item()
    
    # Act
    titem.dump_vars()
    # Assert
    assert False

@pytest.mark.skip
def test_set_depth():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_depth()
    # Assert
    assert False

@pytest.mark.skip
def test_set_ctime():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_ctime()
    # Assert
    assert False

@pytest.mark.skip
def test_set_mtime():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_mtime()
    # Assert
    assert False

@pytest.mark.skip
def test_set_parent():
    # Arrange
    titem = Item()
    
    # Act
    titem.set_parent()
    # Assert
    assert False

@pytest.mark.skip
def test_check_if_valid():
    # Arrange
    titem = Item()
    
    # Act
    titem.check_if_valid()
    # Assert
    assert False
