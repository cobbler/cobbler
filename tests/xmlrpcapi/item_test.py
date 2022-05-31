import pytest


@pytest.mark.usefixtures("create_testdistro", "remove_testdistro")
def test_get_item_resolved(remote, fk_initrd, fk_kernel):
    """
    Test: get an item object (in this case distro) which is resolved
    """
    # Arrange --> Done in fixture

    # Act
    distro = remote.get_item("distro", "testdistro0", resolved=True)

    # Assert
    assert distro.get("name") == "testdistro0"
    assert distro.get("redhat_management_key") == ""
    assert fk_initrd in distro.get("initrd")
    assert fk_kernel in distro.get("kernel")
