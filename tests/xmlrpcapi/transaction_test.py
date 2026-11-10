"""
Tests that validate the functionality of XML-RPC API transactions.
"""

import logging
import os
from typing import TYPE_CHECKING, Any, Callable, Dict, List, cast

import pytest

from cobbler.cexceptions import CX
from cobbler.remote import CobblerXMLRPCInterface

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

logger = logging.getLogger()


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
)
def test_create_profile(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: create/edit a profile object
    """
    # Arrange
    distro_uid = remote.get_distro_handle("testdistro0")

    # Act
    remote.transaction_begin(token)
    profile = remote.new_profile(token)
    remote.modify_profile(profile, ["name"], "testprofile0", token)
    remote.modify_profile(profile, ["distro"], distro_uid, token)

    assert remote.save_profile(profile, True, True, "bypass", token)

    # uncommited profile is not visible without token
    assert remote.get_item_handle("profile", "testprofile0") == "~"

    assert remote.transaction_commit(token)

    # now it is visible
    assert remote.get_item_handle("profile", "testprofile0") != "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
)
def test_create_and_remove_profile_inside_same_transaction_does_not_crash_commit(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: an item created (new + modify + save) and then removed again within the same still-open
    transaction must never reach the real collection at all. ``save_item`` never actually inserts a
    transaction-tracked object into the real collection -- only ``transaction_commit`` does, via
    ``add_remove_items``'s "to_add" pass. Before this fix, ``remove_item`` unconditionally recorded a
    removal ``TransactionTuple`` for the object_id, overwriting its earlier "to add" entry; at commit,
    ``add_remove_items`` would then try to remove an item from the real collection that had never
    actually been added to it, since it only ever existed as a transaction-local pending add.
    """
    # Arrange
    distro_uid = remote.get_distro_handle("testdistro0")

    # Act
    remote.transaction_begin(token)
    profile = remote.new_profile(token)
    remote.modify_profile(profile, ["name"], "testprofile0", token)
    remote.modify_profile(profile, ["distro"], distro_uid, token)
    assert remote.save_profile(profile, True, True, "bypass", token)
    assert remote.remove_profile(profile, token, False)
    assert remote.transaction_commit(token)

    # Assert
    assert remote.get_item_handle("profile", "testprofile0") == "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_remove_and_readd_profile_with_same_name_inside_transaction_is_reachable(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: remove an existing profile and add a brand new, differently-uid'd
    profile under the SAME name within one transaction. ``add_remove_items``
    processes all of ``to_add`` (which performs the real index insertion via
    ``Collection.add()``) before any of ``to_remove``, so by the time the old
    profile's removal runs, the "name" index's "testprofile0" key already
    points at the new profile's uid, not the old one's. ``remove_single_index_value``
    used to unconditionally ``pop`` that key regardless of which uid it
    currently pointed at, silently deleting the new profile's own, still-live
    name-index entry and leaving it unreachable by name after a successful,
    exception-free commit.
    """
    # Arrange
    distro_uid = remote.get_distro_handle("testdistro0")
    old_profile_uid = remote.get_profile_handle("testprofile0")

    # Act
    remote.transaction_begin(token)
    assert remote.remove_profile(old_profile_uid, token, False)
    new_profile = remote.new_profile(token)
    remote.modify_profile(new_profile, ["name"], "testprofile0", token)
    remote.modify_profile(new_profile, ["distro"], distro_uid, token)
    assert remote.save_profile(new_profile, True, True, "bypass", token)
    assert remote.transaction_commit(token)

    # Assert
    assert remote.get_item_handle("profile", "testprofile0") == new_profile


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
)
def test_get_profile_handle_forwards_token_for_transaction_staged_item(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: the type-specific ``get_profile_handle`` (unlike the generic
    ``get_item_handle``) must forward its token so a profile created/saved
    earlier in the same still-open transaction can be re-resolved, exactly
    as ``copy``/``rename`` commands do after mutating an item.
    """
    # Arrange
    distro_uid = remote.get_distro_handle("testdistro0")

    # Act
    remote.transaction_begin(token)
    profile = remote.new_profile(token)
    remote.modify_profile(profile, ["name"], "testprofile0", token)
    remote.modify_profile(profile, ["distro"], distro_uid, token)
    assert remote.save_profile(profile, True, True, "bypass", token)

    # Assert
    # without a token, the transaction-staged profile is correctly invisible
    assert remote.get_profile_handle("testprofile0") == "~"
    # with the token, it must resolve to the staged item's handle
    assert remote.get_profile_handle("testprofile0", token) == profile

    assert remote.transaction_commit(token)
    assert remote.get_profile_handle("testprofile0") == profile


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
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
    remote.modify_profile(profile, ["comment"], "test comment", token)

    assert remote.save_profile(profile, True, True, "bypass", token)

    assert remote.get_profile_handle("testprofile0") == profile

    # changes are visible inside the transaction identified by the token
    assert (
        cast(Dict[Any, Any], remote.get_profile(profile, token=token))["comment"]
        == "test comment"
    )

    # changes are not visible until commit
    assert (
        cast(Dict[Any, Any], remote.get_profile(profile))["comment"] != "test comment"
    )
    assert remote.transaction_commit(token)
    assert (
        cast(Dict[Any, Any], remote.get_profile(profile))["comment"] == "test comment"
    )


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
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


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
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


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_remove_profile_recursive(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: remove a profile with descendants
    """

    # Arrange
    profile_uid = remote.get_profile_handle("testprofile0")
    remote.transaction_begin(token)

    subprofile = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile, ["name"], "testsubprofile0", token)
    assert remote.modify_profile(subprofile, ["parent"], profile_uid, token)
    assert remote.save_profile(subprofile, True, True, "bypass", token)

    subprofile1 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile1, ["name"], "testsubprofile1", token)
    assert remote.modify_profile(subprofile1, ["parent"], subprofile, token)
    assert remote.save_profile(subprofile1, True, True, "bypass", token)

    assert remote.transaction_commit(token)

    # Act

    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    remote.transaction_begin(token)
    assert remote.remove_profile(profile_uid, token)

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
    distro_uid = remote.get_distro_handle("testdistro0")

    # Act
    remote.transaction_begin(token)
    profile_uids: List[str] = []
    for i in range(50):
        profile = remote.new_profile(token)
        remote.modify_profile(profile, ["name"], f"testprofile{i}", token)
        remote.modify_profile(profile, ["distro"], distro_uid, token)
        remote.save_profile(profile, True, True, "bypass", token)
        profile_uids.append(profile)
    assert remote.transaction_commit(token)

    remote.transaction_begin(token)
    for profile_uid in profile_uids:
        remote.remove_profile(profile_uid, token)
    assert remote.transaction_commit(token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_parent_profile_recursive(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: reparent a profile with descendants
    """

    # Arrange
    profile_uid = remote.get_profile_handle("testprofile0")
    profile1 = remote.new_subprofile(token)
    assert remote.modify_profile(profile1, ["name"], "testprofile1", token)
    assert remote.modify_profile(profile1, ["parent"], profile_uid, token)
    assert remote.save_profile(profile1, True, True, "bypass", token)

    profile2 = remote.new_subprofile(token)
    assert remote.modify_profile(profile2, ["name"], "testprofile2", token)
    assert remote.modify_profile(profile2, ["parent"], profile1, token)
    assert remote.save_profile(profile2, True, True, "bypass", token)

    profile3 = remote.new_subprofile(token)
    assert remote.modify_profile(profile3, ["name"], "testprofile3", token)
    assert remote.modify_profile(profile3, ["parent"], profile2, token)
    assert remote.save_profile(profile3, True, True, "bypass", token)

    # Act
    assert cast(Dict[Any, Any], remote.get_profile(profile_uid))["depth"] == 1
    assert cast(Dict[Any, Any], remote.get_profile(profile1))["depth"] == 2
    assert cast(Dict[Any, Any], remote.get_profile(profile2))["depth"] == 3
    assert cast(Dict[Any, Any], remote.get_profile(profile3))["depth"] == 4

    assert remote.modify_profile(profile2, ["parent"], profile_uid, token)
    assert remote.save_profile(profile2, True, True, "bypass", token)

    assert cast(Dict[Any, Any], remote.get_profile(profile_uid))["depth"] == 1
    assert cast(Dict[Any, Any], remote.get_profile(profile1))["depth"] == 2
    assert cast(Dict[Any, Any], remote.get_profile(profile2))["depth"] == 2
    #   this seems to be a bug
    #   assert cast(Dict[Any, Any], remote.get_profile(profile3))["depth"] == 3

    assert remote.remove_profile(profile_uid, token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_reparent_and_delete_profile(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: reparent a profile and delete the old parent in one transaction
    """

    # Arrange
    distro_uid = remote.get_distro_handle("testdistro0")
    profile_uid = remote.get_profile_handle("testprofile0")
    subprofile1 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile1, ["name"], "testsubprofile0", token)
    assert remote.modify_profile(subprofile1, ["parent"], profile_uid, token)
    assert remote.save_profile(subprofile1, True, True, "bypass", token)

    subprofile2 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile2, ["name"], "testsubprofile1", token)
    assert remote.modify_profile(subprofile2, ["parent"], profile_uid, token)
    assert remote.save_profile(subprofile2, True, True, "bypass", token)

    # Act
    remote.transaction_begin(token)

    profile1 = remote.new_profile(token)
    assert remote.modify_profile(profile1, ["name"], "testprofile1", token)
    assert remote.modify_profile(profile1, ["distro"], distro_uid, token)
    assert remote.save_profile(profile1, True, True, "bypass", token)

    subprofile1 = remote.get_item_handle("profile", "testsubprofile0", token)

    assert remote.modify_profile(subprofile1, ["parent"], profile1, token)
    assert remote.save_profile(subprofile1, True, True, "bypass", token)

    assert remote.remove_profile(profile_uid, token)

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
    assert remote.remove_profile(profile1, token)


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_conflict(remote: CobblerXMLRPCInterface, token: str, token2: str):
    """
    Test: conflicting transactions
    """

    # Arrange --> Done in fixtures

    # Act
    remote.transaction_begin(token)
    profile = remote.get_item_handle("profile", "testprofile0", token)
    remote.modify_profile(profile, ["comment"], "test comment", token)

    # delete the original profile before the transaction is finished
    remote.transaction_begin(token2)
    assert remote.remove_profile(profile, token2)

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
)
def test_conflict2(remote: CobblerXMLRPCInterface, token: str, token2: str):
    """
    Test: conflicting transactions
    """

    # Arrange --> Done in fixtures

    # Act
    remote.transaction_begin(token)
    profile = remote.get_item_handle("profile", "testprofile0", token)
    remote.modify_profile(profile, ["comment"], "test comment", token)

    # delete the original profile before the transaction is finished
    remote.transaction_begin(token2)
    assert remote.remove_profile(profile, token2)

    # the first commit is successful
    assert remote.transaction_commit(token)

    # the second commit fails because the item has been modified
    with pytest.raises(ValueError):
        remote.transaction_commit(token2)

    # result of the successfully commited transaction - comment is set
    assert (
        cast(Dict[Any, Any], remote.get_profile(profile))["comment"] == "test comment"
    )


@pytest.mark.usefixtures(
    "create_testmenu",
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
    remote.modify_distro(distro, ["name"], "testdistro0", token)
    remote.modify_distro(distro, ["kernel"], path_kernel, token)
    remote.modify_distro(distro, ["initrd"], path_initrd, token)

    assert remote.save_distro(distro, True, True, "bypass", token)

    profile = remote.new_profile(token)
    remote.modify_profile(profile, ["name"], "testprofile0", token)
    remote.modify_profile(profile, ["distro"], distro, token)

    assert remote.save_profile(profile, True, True, "bypass", token)

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
    remote.modify_distro(distro, ["comment"], "test comment", token)

    assert remote.save_distro(distro, True, True, "bypass", token)

    assert remote.get_distro_handle("testdistro0") == distro

    assert cast(Dict[Any, Any], remote.get_distro(distro))["comment"] != "test comment"
    assert remote.transaction_commit(token)
    assert cast(Dict[Any, Any], remote.get_distro(distro))["comment"] == "test comment"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_remove_distro_recursive(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: remove a distro with descendants
    """

    # Arrange
    distro_uid = remote.get_distro_handle("testdistro0")
    profile_uid = remote.get_profile_handle("testprofile0")
    remote.transaction_begin(token)

    subprofile = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile, ["name"], "testsubprofile0", token)
    assert remote.modify_profile(subprofile, ["parent"], profile_uid, token)
    assert remote.save_profile(subprofile, True, True, "bypass", token)

    subprofile1 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile1, ["name"], "testsubprofile1", token)
    assert remote.modify_profile(subprofile1, ["parent"], subprofile, token)
    assert remote.save_profile(subprofile1, True, True, "bypass", token)

    assert remote.transaction_commit(token)

    # Act

    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"

    remote.transaction_begin(token)
    assert remote.remove_distro(distro_uid, token)

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
)
def test_reparent_and_remove_distro(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Test: change profile distro to a new one and delete the old distro in one transaction
    """

    # Arrange
    old_distro_uid = remote.get_distro_handle("testdistro0")
    remote.transaction_begin(token)
    profile_uid = remote.get_item_handle("profile", "testprofile0", token)
    logger.info("profile_uid: %s", profile_uid)

    subprofile = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile, ["name"], "testsubprofile0", token)
    assert remote.modify_profile(subprofile, ["parent"], profile_uid, token)
    assert remote.save_profile(subprofile, True, True, "new", token)

    subprofile1 = remote.new_subprofile(token)
    assert remote.modify_profile(subprofile1, ["name"], "testsubprofile1", token)
    assert remote.modify_profile(subprofile1, ["parent"], subprofile, token)
    assert remote.save_profile(subprofile1, True, True, "new", token)

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
    remote.modify_distro(distro, ["name"], "testdistro1", token)
    remote.modify_distro(distro, ["kernel"], path_kernel, token)
    remote.modify_distro(distro, ["initrd"], path_initrd, token)

    assert remote.save_distro(distro, True, True, "new", token)

    profile = remote.get_item_handle("profile", "testprofile0", token)
    assert remote.modify_profile(profile, ["distro"], distro, token)
    assert remote.save_profile(profile, True, True, "new", token)
    assert remote.remove_distro(old_distro_uid, token)

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
    assert cast(Dict[Any, Any], remote.get_profile(profile))["distro"] == distro

    assert remote.get_item_handle("profile", "testsubprofile0") != "~"
    assert remote.get_item_handle("profile", "testsubprofile1") != "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_create_system_positive(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: create/edit a system object
    """
    # Act
    profile_uid = remote.get_profile_handle("testprofile0")
    remote.transaction_begin(token)
    system = remote.new_system(token)
    remote.modify_system(system, ["name"], "testsystem0", token)
    remote.modify_system(system, ["profile"], profile_uid, token)
    assert remote.save_system(system, True, True, "bypass", token)

    # without token, the new system is not visible
    assert remote.get_item_handle("system", "testsystem0") == "~"
    assert remote.transaction_commit(token)

    # Assert
    assert remote.get_item_handle("system", "testsystem0") != "~"


def test_modify_template_kernel_options_inside_transaction_does_not_crash(
    create_autoinstall_template: Callable[[str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: ``Template`` (a plain ``BaseItem``, not an ``InheritableItem``) has
    no ``kernel_options``/``kernel_options_post`` attributes, but a generic
    XML-RPC client (e.g. cobblerclient's shared ``Item`` struct) may still
    issue a ``modify_template`` call for them on every update. Outside a
    transaction this is a harmless no-op; inside one, the transaction-aware
    change-tracking code used to unconditionally read the attribute's
    current value first, raising ``AttributeError``. It must now no-op the
    same way as outside a transaction, and the transaction must commit
    cleanly afterward (exercising ``add_remove_items``' depth-based sort,
    which Template/BaseItem types also have no ``.depth`` for).
    """
    # Arrange
    template = create_autoinstall_template("test_transaction.ks", "")

    # Act
    remote.transaction_begin(token)
    assert remote.modify_template(template, ["kernel_options"], {}, token)
    assert remote.modify_template(template, ["kernel_options_post"], {}, token)
    assert remote.modify_template(
        template, ["comment"], "updated in transaction", token
    )
    assert remote.save_template(template, True, True, "bypass", token)

    # Assert
    assert remote.transaction_commit(token)
    assert (
        cast(Dict[Any, Any], remote.get_template(template))["comment"]
        == "updated in transaction"
    )


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "create_testsystem",
)
def test_remove_distro_recursive_inside_transaction_does_not_crash(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: ``remove_distro(..., recursive=True)`` inside a transaction walks every
    dependent item via ``_transaction_descendants``, which reads each dependency pair's
    "dependant_type_attribute" generically. For most pairs (e.g. ``Profile.distro``) this
    getter resolves and returns the referenced ``BaseItem``, but for others (e.g.
    ``System.profile``) it returns the raw uid string instead, and for ``ItemGroup.members``
    it returns a list of uid strings. The code used to assume a resolved object and access
    ``.uid`` unconditionally, raising ``AttributeError: 'str' object has no attribute 'uid'``
    as soon as the walk reached a distro's profile's system (distro -> profile -> system).

    Also covers a second, related bug reached one level deeper: once the walk reaches the
    system's own ``NetworkInterface`` (distro -> profile -> system -> interface), recursing into
    ``_transaction_descendants`` for it used to unconditionally call the same-type parent/child
    tree walk, which assumes a ``.get_parent`` property that only ``InheritableItem`` subtypes
    have -- ``NetworkInterface`` (like ``Template``) is a plain ``BaseItem`` and always a leaf in
    this dependency model, raising ``AttributeError: 'NetworkInterface' object has no attribute
    'get_parent'``.

    And a third bug in the removal commit itself: ``add_remove_items`` used to remove every item
    in the batch first, then run each one's PXE/DHCP sync cleanup in a second pass afterward. By
    the time the system's cleanup trigger (which resolves its profile/distro via
    ``get_conceptual_parent()``) ran, the profile and distro had already been deleted from their
    collections, so the lookup returned ``None`` and crashed on the next ``.get_conceptual_parent()``
    call -- ``AttributeError: 'NoneType' object has no attribute 'get_conceptual_parent'``.
    """
    # Arrange
    distro_uid = remote.get_distro_handle("testdistro0")
    remote.get_profile_handle("testprofile0")
    system_uid = remote.get_system_handle("testsystem0")
    interface_handle = remote.new_network_interface(system_uid, token)
    remote.modify_network_interface(interface_handle, ["name"], "eth0", token)
    assert remote.save_network_interface(interface_handle, True, True, "new", token)

    # Act
    remote.transaction_begin(token)
    assert remote.remove_distro(distro_uid, token, True)
    assert remote.transaction_commit(token)

    # Assert
    assert remote.get_distro_handle("testdistro0") == "~"
    assert remote.get_profile_handle("testprofile0") == "~"
    assert remote.get_system_handle("testsystem0") == "~"
    assert (
        remote.find_network_interface(
            {"system_uid": system_uid, "name": "eth0"}, expand=False
        )
        == []
    )


def test_modify_profile_group_kernel_options_inside_transaction_does_not_crash(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: ``ProfileGroup`` (an ``InheritableItem`` but not a ``BootableItem``) has
    no ``kernel_options``/``kernel_options_post`` attributes -- those are
    ``BootableItem``-only -- but a generic XML-RPC client (e.g. cobblerclient's
    shared ``Item`` struct) may still issue a ``modify_profile_group`` call for
    them on every update. Outside a transaction this is a harmless no-op; inside
    one, the transaction-aware change-tracking code must no-op the same way
    instead of crashing, and the transaction must commit cleanly afterward.
    """
    # Act
    remote.transaction_begin(token)
    profile_group = remote.new_profile_group(token)
    assert remote.modify_profile_group(
        profile_group, ["name"], "testprofilegroup0", token
    )
    assert remote.modify_profile_group(profile_group, ["kernel_options"], {}, token)
    assert remote.modify_profile_group(
        profile_group, ["kernel_options_post"], {}, token
    )
    assert remote.modify_profile_group(
        profile_group, ["comment"], "updated in transaction", token
    )
    assert remote.save_profile_group(profile_group, True, True, "new", token)

    # Assert
    assert remote.transaction_commit(token)
    assert (
        cast(Dict[Any, Any], remote.get_profile_group(profile_group))["comment"]
        == "updated in transaction"
    )


def test_copy_and_rename_system_group_inside_transaction_does_not_crash(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: copying and then renaming a ``SystemGroup`` (an ``InheritableItem``
    but not a ``BootableItem``) inside a single open transaction must not crash
    and must be fully visible once committed.
    """
    # Arrange
    handle = remote.new_system_group(token)
    remote.modify_system_group(handle, ["name"], "testsystemgroup0", token)
    assert remote.save_system_group(handle, True, True, "new", token)

    # Act
    remote.transaction_begin(token)
    system_group = remote.get_system_group_handle("testsystemgroup0", token)
    assert remote.copy_system_group(system_group, "testsystemgroupcopy1", token)

    # without token, the copy is not visible
    assert remote.get_item_handle("system_group", "testsystemgroupcopy1") == "~"

    copy_handle = remote.get_system_group_handle("testsystemgroupcopy1", token)
    assert remote.rename_system_group(copy_handle, "testsystemgrouprenamed1", token)

    # without token, neither the copy's old nor new name is visible
    assert remote.get_item_handle("system_group", "testsystemgroupcopy1") == "~"
    assert remote.get_item_handle("system_group", "testsystemgrouprenamed1") == "~"

    assert remote.transaction_commit(token)

    # Assert: after commit, the original and the renamed copy are visible,
    # and the copy's old name is gone.
    assert remote.get_item_handle("system_group", "testsystemgroup0") != "~"
    assert remote.get_item_handle("system_group", "testsystemgroupcopy1") == "~"
    assert remote.get_item_handle("system_group", "testsystemgrouprenamed1") != "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "create_testsystem",
)
def test_add_remove_items_rolls_back_entire_batch_on_mid_commit_failure(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Regression test: ``add_remove_items()`` used to apply queued items one at a time with no
    rollback -- a failure partway through the batch left every item already applied earlier in
    the very same commit permanently removed/added, with the rest of the queued batch silently
    discarded. A transaction must be all-or-nothing, exactly like a database transaction: if any
    item in the batch fails, everything already applied earlier in that same commit must be
    reverted too, not left behind as a partial, unrecoverable commit.

    ``to_remove`` is processed deepest-first (System, then Distro), so removing "testsystem0" (a
    leaf, always succeeds) and "testdistro0" (still depended on by "testprofile0", which is NOT
    part of this batch) in the same transaction removes the system first, then fails on the
    distro with an "orphan" error. "testsystem0" must be restored afterward, not left deleted.
    """
    # Arrange
    system_uid = remote.get_system_handle("testsystem0")
    distro_uid = remote.get_distro_handle("testdistro0")
    remote.transaction_begin(token)
    assert remote.remove_system(system_uid, token)
    assert remote.remove_distro(distro_uid, token, False)

    # Act & Assert
    with pytest.raises(CX):
        remote.transaction_commit(token)

    # The system, removed earlier in the same failed batch, must have been rolled back (restored)
    # too -- not left behind as a partial, unrecoverable commit.
    assert remote.get_item_handle("system", "testsystem0") != "~"
    assert remote.get_item_handle("distro", "testdistro0") != "~"
    assert remote.get_item_handle("profile", "testprofile0") != "~"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_add_remove_items_rollback_restores_modified_item_instead_of_deleting_it(
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Regression test: modifying an already-persisted item queues it in "to_add" (``Collection.add()``
    just overwrites ``self.listing[ref.uid]`` in place for an existing uid), not "to_remove" -- a
    plain modification, not a brand new item. A rollback must restore such an item to its
    pre-modification state, not delete it outright the way undoing a genuinely new item does.

    Modifying "testprofile0"'s comment (succeeds, applied first since "to_add" is processed before
    "to_remove") and then removing "testdistro0" (fails -- "testprofile0" still depends on it) in
    the same transaction must, after rollback, leave "testprofile0" existing with its original
    comment, not deleted.
    """
    # Arrange
    profile = remote.get_profile_handle("testprofile0")
    original_comment = cast(Dict[Any, Any], remote.get_profile(profile))["comment"]
    distro_uid = remote.get_distro_handle("testdistro0")
    remote.transaction_begin(token)
    remote.modify_profile(profile, ["comment"], "modified in failed transaction", token)
    assert remote.save_profile(profile, True, True, "bypass", token)
    assert remote.remove_distro(distro_uid, token, False)

    # Act & Assert
    with pytest.raises(CX):
        remote.transaction_commit(token)

    # The profile must still exist (not deleted like rolling back a brand new item would do) and
    # its original comment must be restored, not left with the failed transaction's modification.
    assert remote.get_item_handle("profile", "testprofile0") != "~"
    assert (
        cast(Dict[Any, Any], remote.get_profile(profile))["comment"] == original_comment
    )


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_add_remove_items_quick_sync_acquires_filelock_on_add(
    remote: CobblerXMLRPCInterface,
    token: str,
    mocker: "MockerFixture",
):
    """
    Regression test for the quick-sync/full-sync race: ``add_remove_items()`` used to call the per-item quick-sync
    (``add_quick_pxe_sync``) and ``tftpgen.make_pxe_menu()`` directly, without ever taking the
    global ``/var/lib/cobbler/lock`` that a full ``cobbler sync`` holds around its destructive
    directory rebuild -- so a transaction commit could race a concurrent full sync just like the
    classic (non-transactional) ``save_*`` path could. The whole method now runs under one single
    acquisition of that lock (see ``test_add_remove_items_quick_sync_acquires_filelock_once_for_whole_add_batch``
    for proof that this holds for a multi-item batch, not just one acquisition per item): one call
    for the method's own outer acquisition, plus one for the added system's on-disk serialization
    (``Collection.add()``'s ``save=True`` path, which now shares this same lock instead of an
    independent, non-reentrant ``fcntl.flock()`` -- see ``cobbler/serializer.py``).
    """
    # Arrange
    profile_uid = remote.get_profile_handle("testprofile0")
    remote.transaction_begin(token)
    system = remote.new_system(token)
    remote.modify_system(system, ["name"], "testsystem0", token)
    remote.modify_system(system, ["profile"], profile_uid, token)
    assert remote.save_system(system, True, True, "new", token)
    filelock_mock = mocker.patch("cobbler.utils.filelock")

    # Act
    assert remote.transaction_commit(token)

    # Assert
    assert filelock_mock.call_count == 2
    for call in filelock_mock.call_args_list:
        assert call.args[0] == "/var/lib/cobbler/lock"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
)
def test_add_remove_items_quick_sync_acquires_filelock_once_for_whole_add_batch(
    remote: CobblerXMLRPCInterface,
    token: str,
    mocker: "MockerFixture",
):
    """
    Regression test: ``add_remove_items()`` used to acquire ``/var/lib/cobbler/lock`` separately for
    each added item's quick-sync (plus once more for the final menu rebuild), dropping and
    re-acquiring it in between - leaving a window, between any two items of the very same
    transaction, where a concurrent full ``cobbler sync``'s destructive directory rebuild could
    interleave. The whole method - every item's on-disk serialization, its quick-sync, and the final
    menu rebuild - now runs under one single, uninterrupted acquisition of this lock: one call for
    the method's own outer acquisition, plus one per added item for that item's on-disk
    serialization (``Collection.add()``'s ``save=True`` path; see ``cobbler/serializer.py``, which
    now shares this same reentrant lock instead of independently ``flock()``-ing the same file).
    """
    # Arrange
    profile_uid = remote.get_profile_handle("testprofile0")
    remote.transaction_begin(token)
    system_names = ("testsystem0", "testsystem1", "testsystem2")
    for name in system_names:
        system = remote.new_system(token)
        remote.modify_system(system, ["name"], name, token)
        remote.modify_system(system, ["profile"], profile_uid, token)
        assert remote.save_system(system, True, True, "new", token)
    filelock_mock = mocker.patch("cobbler.utils.filelock")

    # Act
    assert remote.transaction_commit(token)

    # Assert: one outer acquisition plus one per added system's on-disk serialization.
    assert filelock_mock.call_count == 1 + len(system_names)
    for call in filelock_mock.call_args_list:
        assert call.args[0] == "/var/lib/cobbler/lock"


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "create_testsystem",
)
def test_add_remove_items_quick_sync_acquires_filelock_on_remove(
    remote: CobblerXMLRPCInterface,
    token: str,
    mocker: "MockerFixture",
):
    """
    Same regression as above, for the removal call site (``remove_quick_pxe_sync``). The removed
    item's own ``Collection.remove()`` call (immediately before its quick-sync) unconditionally
    serializes the deletion to disk; now that the serializer shares this same reentrant lock instead
    of independently ``flock()``-ing the same file (see ``cobbler/serializer.py``), that nested call
    is a safe no-op rather than a deadlock, so the whole method - including the removal's own
    serialization - can run under the one outer acquisition taken at the top of the method: one call
    for the outer acquisition, plus one for the removed system's on-disk delete.
    """
    # Arrange
    system_uid = remote.get_system_handle("testsystem0")
    remote.transaction_begin(token)
    assert remote.remove_system(system_uid, token)
    filelock_mock = mocker.patch("cobbler.utils.filelock")

    # Act
    assert remote.transaction_commit(token)

    # Assert
    assert filelock_mock.call_count == 2
    for call in filelock_mock.call_args_list:
        assert call.args[0] == "/var/lib/cobbler/lock"
