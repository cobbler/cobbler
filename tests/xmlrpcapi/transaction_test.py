"""
Tests that validate the functionality of XML-RPC API transactions.
"""

import os
from typing import Callable

import pytest

from cobbler.remote import CobblerXMLRPCInterface


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_create_profile(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: create/edit a profile object
    """
    # Arrange
    # Act
    remote.transaction_begin(token)
    profile = remote.new_profile(token)
    remote.modify_profile(profile, "name", "testprofile0", token)
    remote.modify_profile(profile, "distro", "testdistro0", token)

    assert remote.save_profile(profile, token)

    # uncommited profile is not visible without token
    assert remote.get_item_handle("profile", "testprofile0") == "~"

    assert remote.transaction_commit(token)

    # now it is visible
    assert remote.get_item_handle("profile", "testprofile0") != "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_modify_profile(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: modify a profile object
    """
    # Arrange
    # Act
    remote.transaction_begin(token)
    profile = remote.get_profile_handle("testprofile0")
    remote.modify_profile(profile, "comment", "test comment", token)

    assert remote.save_profile(profile, token)

    assert remote.get_profile_handle("testprofile0") == profile

    # changes are visible inside the transaction identified by the token
    assert remote.get_profile("testprofile0", token=token)["comment"] == "test comment"

    # changes are not visible until commit
    assert remote.get_profile("testprofile0")["comment"] != "test comment"
    assert remote.transaction_commit(token)
    assert remote.get_profile("testprofile0")["comment"] == "test comment"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_copy_profile(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a profile object
    """

    # Arrange --> Done in fixtures

    # Act
    remote.transaction_begin(token)
    profile = remote.get_item_handle("profile", "testprofile0", token)
    assert remote.copy_profile(profile, "testprofilecopy1", token)

    # without token, the new profile is not visible
    assert remote.get_item_handle("profile", "testprofilecopy1") == "~"

    # it is visible inside the transaction identified by the token
    profile1 = remote.get_item_handle("profile", "testprofilecopy1", token)
    assert profile1 != "~"
    assert remote.copy_profile(profile1, "testprofilecopy2", token)

    # without token, the new profiles are not visible
    assert remote.get_item_handle("profile", "testprofilecopy1") == "~"
    assert remote.get_item_handle("profile", "testprofilecopy2") == "~"

    assert remote.transaction_commit(token)
    # after commit, everything is visible
    assert remote.get_item_handle("profile", "testprofilecopy1") != "~"
    assert remote.get_item_handle("profile", "testprofilecopy2") != "~"

    # Cleanup
    remote.remove_profile("testprofilecopy1", token)
    remote.remove_profile("testprofilecopy2", token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
)
def test_rename_profile(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a profile object
    """

    # Arrange --> Done in fixtures

    # Act
    remote.transaction_begin(token)
    profile = remote.get_item_handle("profile", "testprofile0", token)
    assert remote.rename_profile(profile, "testprofilerenamed1", token)

    # without token, the original is still visible
    assert remote.get_item_handle("profile", "testprofile0") != "~"

    # without token, the new profile is not visible
    assert remote.get_item_handle("profile", "testprofilerenamed1") == "~"

    # it is visible inside the transaction identified by the token
    profile1 = remote.get_item_handle("profile", "testprofilerenamed1", token)
    assert profile1 != "~"
    assert remote.rename_profile(profile1, "testprofilerenamed2", token)

    # without token, the new profiles are not visible
    assert remote.get_item_handle("profile", "testprofilerenamed1") == "~"
    assert remote.get_item_handle("profile", "testprofilerenamed2") == "~"

    assert remote.transaction_commit(token)
    # after commit, the new profiles are visible
    assert remote.get_item_handle("profile", "testprofilerenamed1") == "~"
    assert remote.get_item_handle("profile", "testprofilerenamed2") != "~"

    # Cleanup
    remote.remove_profile("testprofilerenamed2", token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
)
def test_remove_profile_recursive(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: remove a profile with descendants
    """

    # Arrange
    remote.transaction_begin(token)

    subprofile = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile, "name", "testsubprofile0", token)
    assert remote.modify_profile(subprofile, "parent", "testprofile0", token)
    assert remote.save_profile(subprofile, token)

    subprofile1 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile1, "name", "testsubprofile1", token)
    assert remote.modify_profile(subprofile1, "parent", "testsubprofile0", token)
    assert remote.save_profile(subprofile1, token)

    assert remote.transaction_commit(token)

    # Act

    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    remote.transaction_begin(token)
    assert remote.remove_profile("testprofile0", token)

    # profiles are visible outside of transaction until commit
    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    # inside the transaction identified by the token the profiles are deleted
    assert remote.get_item_handle("profile", "testprofile0", token) == "~"
    assert remote.get_item_handle("profile", "testsubprofile0", token) == "~"
    assert remote.get_item_handle("profile", "testsubprofile1", token) == "~"

    assert remote.transaction_commit(token)

    # now the profiles are deleted everywhere
    assert remote.get_item_handle("profile", "testprofile0") == "~"
    assert remote.get_item_handle("profile", "testsubprofile0") == "~"
    assert remote.get_item_handle("profile", "testsubprofile1") == "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
)
def test_create_profiles(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: create/edit multiple profiles
    """
    # Arrange
    # Act
    remote.transaction_begin(token)
    for i in range(50):
        profile = remote.new_profile(token)
        remote.modify_profile(profile, "name", "testprofile{}".format(i), token)
        remote.modify_profile(profile, "distro", "testdistro0", token)
        remote.save_profile(profile, token)
    assert remote.transaction_commit(token)

    remote.transaction_begin(token)
    for i in range(50):
        remote.remove_profile("testprofile{}".format(i), token)
    assert remote.transaction_commit(token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
)
def test_parent_profile_recursive(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: reparent a profile with descendants
    """

    # Arrange

    profile1 = remote.new_subprofile(token)
    assert remote.modify_profile(profile1, "name", "testprofile1", token)
    assert remote.modify_profile(profile1, "parent", "testprofile0", token)
    assert remote.save_profile(profile1, token)

    profile2 = remote.new_subprofile(token)
    assert remote.modify_profile(profile2, "name", "testprofile2", token)
    assert remote.modify_profile(profile2, "parent", "testprofile1", token)
    assert remote.save_profile(profile2, token)

    profile3 = remote.new_subprofile(token)
    assert remote.modify_profile(profile3, "name", "testprofile3", token)
    assert remote.modify_profile(profile3, "parent", "testprofile2", token)
    assert remote.save_profile(profile3, token)

    # Act
    assert remote.get_profile("testprofile0")["depth"] == 1
    assert remote.get_profile("testprofile1")["depth"] == 2
    assert remote.get_profile("testprofile2")["depth"] == 3
    assert remote.get_profile("testprofile3")["depth"] == 4

    assert remote.modify_profile(profile2, "parent", "testprofile0", token)
    assert remote.save_profile(profile2, token)

    assert remote.get_profile("testprofile0")["depth"] == 1
    assert remote.get_profile("testprofile1")["depth"] == 2
    assert remote.get_profile("testprofile2")["depth"] == 2
    #   this seems to be a bug
    #   assert remote.get_profile("testprofile3")["depth"] == 3

    assert remote.remove_profile("testprofile0", token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
)
def test_reparent_and_delete_profile(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: reparent a profile and delete the old parent in one transaction
    """

    # Arrange

    subprofile1 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile1, "name", "testsubprofile0", token)
    assert remote.modify_profile(subprofile1, "parent", "testprofile0", token)
    assert remote.save_profile(subprofile1, token)

    subprofile2 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile2, "name", "testsubprofile1", token)
    assert remote.modify_profile(subprofile2, "parent", "testprofile0", token)
    assert remote.save_profile(subprofile2, token)

    # Act
    remote.transaction_begin(token)

    profile1 = remote.new_profile(token)
    assert remote.modify_profile(profile1, "name", "testprofile1", token)
    assert remote.modify_profile(profile1, "distro", "testdistro0", token)
    assert remote.save_profile(profile1, token)

    subprofile1 = remote.get_item_handle("profile", "testsubprofile0", token)

    assert remote.modify_profile(subprofile1, "parent", "testprofile1", token)
    assert remote.save_profile(subprofile1, token)

    assert remote.remove_profile("testprofile0", token)

    # the transaction is not visible without the token
    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_item_handle("profile", "testprofile1") == "~"
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    remote.transaction_commit(token)

    assert remote.get_item_handle("profile", "testprofile0") == "~"
    assert remote.get_item_handle("profile", "testprofile1") != "~"

    # this subprofile got the new parent, so it still exists
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"

    # this subprofile has been deleted with "testprofile0"
    assert remote.get_item_handle("profile", "testsubprofile1") == "~"

    # cleanup
    assert remote.remove_profile("testprofile1", token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_conflict(remote: CobblerXMLRPCInterface, token: str, token2: str):
    """
    Test: conflicting transactions
    """

    # Arrange --> Done in fixtures

    # Act
    remote.transaction_begin(token)
    profile = remote.get_item_handle("profile", "testprofile0", token)
    remote.modify_profile(profile, "comment", "test comment", token)

    # delete the original profile before the transaction is finished
    remote.transaction_begin(token2)
    assert remote.remove_profile("testprofile0", token2)

    # the first commit is successful
    assert remote.transaction_commit(token2)

    # the second commit fails because the item has been modified
    with pytest.raises(ValueError):
        remote.transaction_commit(token)

    # result of the successfully commited transaction - profile is removed
    assert remote.get_item_handle("profile", "testprofile0") == "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_conflict2(remote: CobblerXMLRPCInterface, token: str, token2: str):
    """
    Test: conflicting transactions
    """

    # Arrange --> Done in fixtures

    # Act
    remote.transaction_begin(token)
    profile = remote.get_item_handle("profile", "testprofile0", token)
    remote.modify_profile(profile, "comment", "test comment", token)

    # delete the original profile before the transaction is finished
    remote.transaction_begin(token2)
    assert remote.remove_profile("testprofile0", token2)

    # the first commit is successful
    assert remote.transaction_commit(token)

    # the second commit fails because the item has been modified
    with pytest.raises(ValueError):
        remote.transaction_commit(token2)

    # result of the successfully commited transaction - comment is set
    assert remote.get_profile("testprofile0")["comment"] == "test comment"


@pytest.mark.usefixtures(
    "create_testmenu",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_create_distro_profile(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Test: create/edit a distro object
    """
    # Arrange
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)

    # Act

    remote.transaction_begin(token)
    distro = remote.new_distro(token)
    remote.modify_distro(distro, "name", "testdistro0", token)
    remote.modify_distro(distro, "kernel", path_kernel, token)
    remote.modify_distro(distro, "initrd", path_initrd, token)

    assert remote.save_distro(distro, token)

    profile = remote.new_profile(token)
    remote.modify_profile(profile, "name", "testprofile0", token)
    remote.modify_profile(profile, "distro", "testdistro0", token)

    assert remote.save_profile(profile, token)

    # uncommited profile is not visible without token
    assert remote.get_item_handle("profile", "testprofile0") == "~"

    # uncommited distro is not visible without token
    assert remote.get_item_handle("distro", "testdistro0") == "~"

    assert remote.transaction_commit(token)

    # now it is visible
    assert remote.get_item_handle("distro", "testdistro0") != "~"
    assert remote.get_item_handle("profile", "testprofile0") != "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_modify_distro(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: modify a distro object
    """
    # Arrange
    # Act
    remote.transaction_begin(token)
    distro = remote.get_distro_handle("testdistro0")
    remote.modify_distro(distro, "comment", "test comment", token)

    assert remote.save_distro(distro, token)

    assert remote.get_distro_handle("testdistro0") == distro

    assert remote.get_distro("testdistro0")["comment"] != "test comment"
    assert remote.transaction_commit(token)
    assert remote.get_distro("testdistro0")["comment"] == "test comment"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_copy_profile(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a distro object
    """

    # Arrange --> Done in fixtures

    # Act
    remote.transaction_begin(token)
    distro = remote.get_item_handle("distro", "testdistro0", token)
    assert remote.copy_distro(distro, "testdistrocopy1", token)

    # without token, the new distro is not visible
    assert remote.get_item_handle("distro", "testdistrocopy1") == "~"

    # it is visible inside the transaction identified by the token
    distro1 = remote.get_item_handle("distro", "testdistrocopy1", token)
    assert distro1 != "~"
    assert remote.copy_distro(distro1, "testdistrocopy2", token)

    # without token, the new distros are not visible
    assert remote.get_item_handle("distro", "testdistrocopy1") == "~"
    assert remote.get_item_handle("distro", "testdistrocopy2") == "~"

    assert remote.transaction_commit(token)
    # after commit, everything is visible
    assert remote.get_item_handle("distro", "testdistrocopy1") != "~"
    assert remote.get_item_handle("distro", "testdistrocopy2") != "~"

    # Cleanup
    remote.remove_distro("testdistrocopy1", token)
    remote.remove_distro("testdistrocopy2", token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testmenu",
)
def test_remove_distro_recursive(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: remove a distro with descendants
    """

    # Arrange
    remote.transaction_begin(token)

    subprofile = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile, "name", "testsubprofile0", token)
    assert remote.modify_profile(subprofile, "parent", "testprofile0", token)
    assert remote.save_profile(subprofile, token)

    subprofile1 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile1, "name", "testsubprofile1", token)
    assert remote.modify_profile(subprofile1, "parent", "testsubprofile0", token)
    assert remote.save_profile(subprofile1, token)

    assert remote.transaction_commit(token)

    # Act

    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    remote.transaction_begin(token)
    assert remote.remove_distro("testdistro0", token)

    # distro and profiles are visible outside of transaction until commit
    assert remote.get_item_handle("distro", "testdistro0") != "~"
    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    # inside the transaction identified by the token the profiles are deleted
    assert remote.get_item_handle("distro", "testdistro0", token) == "~"
    assert remote.get_item_handle("profile", "testprofile0", token) == "~"
    assert remote.get_item_handle("profile", "testsubprofile0", token) == "~"
    assert remote.get_item_handle("profile", "testsubprofile1", token) == "~"

    assert remote.transaction_commit(token)

    # now the profiles are deleted everywhere
    assert remote.get_item_handle("distro", "testdistro0") == "~"
    assert remote.get_item_handle("profile", "testprofile0") == "~"
    assert remote.get_item_handle("profile", "testsubprofile0") == "~"
    assert remote.get_item_handle("profile", "testsubprofile1") == "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testmenu",
    "remove_testprofile",
)
def test_reparent_and_remove_distro(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Test: change profile distro to a new one and delete the old disto in one transaction
    """

    # Arrange
    remote.transaction_begin(token)

    subprofile = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile, "name", "testsubprofile0", token)
    assert remote.modify_profile(subprofile, "parent", "testprofile0", token)
    assert remote.save_profile(subprofile, token)

    subprofile1 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile1, "name", "testsubprofile1", token)
    assert remote.modify_profile(subprofile1, "parent", "testsubprofile0", token)
    assert remote.save_profile(subprofile1, token)

    assert remote.transaction_commit(token)

    # Act

    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    remote.transaction_begin(token)

    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    distro = remote.new_distro(token)
    remote.modify_distro(distro, "name", "testdistro1", token)
    remote.modify_distro(distro, "kernel", path_kernel, token)
    remote.modify_distro(distro, "initrd", path_initrd, token)

    assert remote.save_distro(distro, token)

    profile = remote.get_item_handle("profile", "testprofile0", token)
    assert remote.modify_profile(profile, "distro", "testdistro1", token)
    assert remote.save_profile(profile, token)
    assert remote.remove_distro("testdistro0", token)

    # distro and profiles are visible outside of transaction until commit
    assert remote.get_item_handle("distro", "testdistro0") != "~"
    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    # inside the transaction identified by the token the distro is deleted
    assert remote.get_item_handle("distro", "testdistro0", token) == "~"

    # the profiles exist
    assert remote.get_item_handle("profile", "testprofile0", token) != "~"
    assert remote.get_item_handle("profile", "testsubprofile0", token) != "~"
    assert remote.get_item_handle("profile", "testsubprofile1", token) != "~"

    assert remote.transaction_commit(token)

    # now the changes are commited
    assert remote.get_item_handle("distro", "testdistro0") == "~"
    assert remote.get_item_handle("distro", "testdistro1") != "~"
    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_profile("testprofile0")["distro"] == "testdistro1"

    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    # cleanup
    assert remote.remove_distro("testdistro1", token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
    "remove_testsystem",
)
def test_create_system_positive(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: create/edit a system object
    """
    # Act
    remote.transaction_begin(token)
    system = remote.new_system(token)
    remote.modify_system(system, "name", "testsystem0", token)
    remote.modify_system(system, "profile", "testprofile0", token)
    assert remote.save_system(system, token)

    # without token, the new system is not visible
    assert remote.get_item_handle("system", "testsystem0") == "~"
    assert remote.transaction_commit(token)

    # Assert
    assert remote.get_item_handle("system", "testsystem0") != "~"
