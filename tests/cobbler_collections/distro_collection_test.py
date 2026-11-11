"""
Tests that validate the functionality of the module that is responsible for managing the list of distros.
"""

import os.path
from pathlib import Path
from typing import TYPE_CHECKING, Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.cobbler_collections import distros
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items import distro
from cobbler.utils import filesystem_helpers

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="distro_collection")
def fixture_distro_collection(cobbler_api: CobblerAPI):
    """
    Fixture to provide a concrete implementation (Distros) of a generic collection.
    """
    return cobbler_api.distros()


def test_obj_create(collection_mgr: CollectionManager):
    """
    Test to verify that a collection object can be created.
    """
    # Arrange & Act
    distro_collection = distros.Distros(collection_mgr)

    # Assert
    assert isinstance(distro_collection, distros.Distros)


def test_factory_produce(cobbler_api: CobblerAPI, distro_collection: distros.Distros):
    """
    Test to verify that a distro object can be created by the factory method of the collection.
    """
    # Arrange & Act
    result_distro = distro_collection.factory_produce(cobbler_api, {})

    # Assert
    assert isinstance(result_distro, distro.Distro)


def test_get(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that a distro can be retrieved from the collection by name.
    """
    # Arrange
    name = "test_get"
    create_distro(name)

    # Act
    item = distro_collection.get(name)
    fake_item = distro_collection.get("fake_name")

    # Assert
    assert isinstance(item, distro.Distro)
    assert item.name == name
    assert fake_item is None


def test_find(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that a distro can be found inside the collection.
    """
    # Arrange
    name = "test_find"
    create_distro(name)

    # Act
    result = distro_collection.find(True, True, name=name)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0].name == name


def test_to_list(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that the collection can be converted to a list of dictionaries.
    """
    # Arrange
    name = "test_to_list"
    create_distro(name)

    # Act
    result = distro_collection.to_list()

    # Assert
    assert len(result) == 1
    assert result[0].get("name") == name


def test_from_list(
    distro_collection: distros.Distros,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    """
    Test to verify that the collection can be populated from a list of dictionaries.
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    test_kernel = os.path.join(folder, fk_kernel)
    item_list = [{"name": "test_from_list", "kernel": test_kernel}]

    # Act
    distro_collection.from_list(item_list)

    # Assert
    assert len(distro_collection.listing) == 1
    assert len(distro_collection.indexes["name"]) == 1
    assert len(distro_collection.indexes["arch"]) == 1


def test_from_list_item_failure_is_logged_with_identifying_details(
    distro_collection: distros.Distros,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
    caplog: pytest.LogCaptureFixture,
):
    """
    Regression test for the "vanishing items" bug: when a single item in a collection fails to load from disk
    (e.g. because a validation rule, such as the valid os_versions for a breed, changed since the item was last
    saved), ``from_list()`` must not silently drop it with only a generic, unidentifiable message that reads as
    if the whole collection failed to load. The failure must be logged with the offending item's own uid/name so
    an operator can actually tell which item "vanished" (and that its on-disk JSON file was untouched) instead
    of discovering it only indirectly (e.g. via a missing entry in ``cobbler distro report``).
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    test_kernel = os.path.join(folder, fk_kernel)
    valid_item = {"name": "test_from_list_valid", "kernel": test_kernel}
    invalid_item = {
        "uid": "deadbeefdeadbeefdeadbeefdeadbeef",
        "name": "test_from_list_invalid",
        "kernel": test_kernel,
        "breed": "suse",
        "os_version": "this-os-version-does-not-exist",
    }
    item_list = [valid_item, invalid_item]

    # Act
    with caplog.at_level("ERROR"):
        distro_collection.from_list(item_list)

    # Assert - the valid item still loaded despite the other item in the same collection failing
    assert len(distro_collection.listing) == 1
    assert distro_collection.get("test_from_list_valid") is not None
    # Assert - the invalid item never made it into the live collection
    assert distro_collection.get("test_from_list_invalid") is None
    # Assert - the failure was logged with enough detail to identify the specific offending item, not a generic
    # message that could be mistaken for the entire collection having failed to load
    assert len(caplog.records) == 1
    logged_message = caplog.records[0].getMessage()
    assert invalid_item["uid"] in logged_message
    assert invalid_item["name"] in logged_message
    # Assert - the failure is also surfaced beyond the log, via load_errors(), so it is actionable
    # (e.g. through "cobbler check") rather than only visible to whoever reads cobbler.log
    assert len(distro_collection.load_errors) == 1
    recorded_error = distro_collection.load_errors[0]
    assert recorded_error["uid"] == invalid_item["uid"]
    assert recorded_error["name"] == invalid_item["name"]
    assert recorded_error["collection_type"] == "distro"


def test_copy(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that a distro can be copied inside the collection.
    """
    # Arrange
    name = "test_copy"
    item1 = create_distro(name)

    # Act
    new_item_name = "test_copy_new"
    distro_collection.copy(item1, new_item_name)
    item2: distro.Distro = distro_collection.find(False, name=new_item_name)  # type: ignore

    # Assert
    assert len(distro_collection.listing) == 2
    assert item1.uid in distro_collection.listing
    assert item2.uid in distro_collection.listing
    assert len(distro_collection.indexes["name"]) == 2
    assert (distro_collection.indexes["name"])[item1.name] == item1.uid
    assert (distro_collection.indexes["name"])[item2.name] == item2.uid
    assert (distro_collection.indexes["arch"])[item2.arch.value] == {
        item1.uid,
        item2.uid,
    }


@pytest.mark.parametrize(
    "input_new_name",
    [
        ("to_be_renamed"),
        ("UpperCase"),
    ],
)
def test_rename(
    create_distro: Callable[[], distro.Distro],
    distro_collection: distros.Distros,
    input_new_name: str,
):
    """
    Test to verify that a distro can be renamed inside the collection.
    """
    # Arrange
    item1 = create_distro()
    distro_collection.add(item1)

    # Act
    distro_collection.rename(item1, input_new_name)

    # Assert
    assert distro_collection.listing[item1.uid].name == input_new_name
    assert (distro_collection.indexes["name"])[input_new_name] == item1.uid
    assert (distro_collection.indexes["arch"])[item1.arch.value] == {item1.uid}


def test_collection_add(
    cobbler_api: CobblerAPI,
    distro_collection: distros.Distros,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    """
    Test to verify that a distro can be added to the collection.
    """
    # Arrange
    name = "test_collection_add"
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item1 = distro.Distro(cobbler_api)
    item1.name = name  # type: ignore[method-assign]
    item1.initrd = os.path.join(folder, fk_initrd)  # type: ignore
    item1.kernel = os.path.join(folder, fk_kernel)  # type: ignore
    distro_collection.add(item1)

    # Act
    distro_collection.add(item1)

    # Assert
    assert item1.uid in distro_collection.listing
    assert name in distro_collection.indexes["name"]
    assert item1.arch.value in distro_collection.indexes["arch"]


def test_duplicate_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    """
    Test to verify that adding a duplicate distro raises an exception.
    """
    # Arrange
    name = "test_duplicate_add"
    create_distro(name)
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item2 = distro.Distro(cobbler_api)
    item2.name = name  # type: ignore[method-assign]
    item2.initrd = os.path.join(folder, fk_initrd)  # type: ignore
    item2.kernel = os.path.join(folder, fk_kernel)  # type: ignore

    # Act & Assert
    with pytest.raises(CX):
        distro_collection.add(item2, check_for_duplicate_names=True)


def test_remove(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that a distro can be removed from the collection.
    """
    # Arrange
    name = "test_remove"
    item1 = create_distro(name)
    assert item1.uid in distro_collection.listing
    assert len(distro_collection.indexes["name"]) == 1
    assert (distro_collection.indexes["name"])[name] == item1.uid
    assert (distro_collection.indexes["arch"])[item1.arch.value] == {item1.uid}

    # Act
    distro_collection.remove(item1)

    # Assert
    assert item1.uid not in distro_collection.listing
    assert len(distro_collection.indexes["name"]) == 0
    assert len(distro_collection.indexes["arch"]) == 0


def test_remove_cleans_up_direct_source_overlay_dir(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
    tmp_path: Path,
    mocker: "MockerFixture",
):
    """
    Removing a direct_source distro (one with ``source_tree_path`` set) must also remove its
    overlay directory, once no other distro still references the same ``source_tree_path``.
    """
    # Arrange
    overlay_root = tmp_path / "distro_overlay"
    mocker.patch(
        "cobbler.utils.filesystem_helpers.DISTRO_OVERLAY_DIR", str(overlay_root)
    )
    source_tree_path = tmp_path / "source"
    source_tree_path.mkdir()
    item1 = create_distro("test_remove_cleans_up_direct_source_overlay_dir")
    item1.source_tree_path = str(source_tree_path)
    overlay_file = filesystem_helpers.get_distro_overlay_write_path(
        str(source_tree_path), "boot/winpe.wim"
    )
    Path(overlay_file).write_bytes(b"content")
    overlay_dir = filesystem_helpers.get_distro_overlay_dir(str(source_tree_path))
    assert os.path.isdir(overlay_dir)

    # Act
    distro_collection.remove(item1)

    # Assert
    assert not os.path.exists(overlay_dir)


def test_remove_cleans_up_webdir_links_symlink(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
    cobbler_api: CobblerAPI,
    tmp_path: Path,
):
    """
    Removing a distro must also remove its ``webdir/links/<name>`` symlink, whether it came from a
    classic import or (Windows-specific) direct_source import -- otherwise it is left dangling,
    pointing at content that may no longer exist.
    """
    # Arrange
    webdir = tmp_path / "webdir"
    links_dir = webdir / "links"
    links_dir.mkdir(parents=True)
    cobbler_api.settings().webdir = str(webdir)
    name = "test_remove_cleans_up_webdir_links_symlink"
    item1 = create_distro(name)
    dest_link = links_dir / name
    dest_link.symlink_to(tmp_path)
    assert os.path.islink(dest_link)

    # Act
    distro_collection.remove(item1)

    # Assert
    assert not os.path.lexists(dest_link)


def test_remove_without_source_tree_path_does_not_touch_overlay(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
    mocker: "MockerFixture",
):
    """
    For a classic distro (``source_tree_path`` at its default, empty value), removal must not
    even look up an overlay directory.
    """
    # Arrange
    item1 = create_distro("test_remove_without_source_tree_path_does_not_touch_overlay")
    assert item1.source_tree_path == ""
    overlay_dir_spy = mocker.patch(
        "cobbler.cobbler_collections.distros.filesystem_helpers.get_distro_overlay_dir"
    )

    # Act
    distro_collection.remove(item1)

    # Assert
    overlay_dir_spy.assert_not_called()


def test_remove_keeps_overlay_dir_while_another_distro_shares_same_source_tree_path(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
    tmp_path: Path,
    mocker: "MockerFixture",
):
    """
    If another distro still references the same ``source_tree_path``, removing one of them must
    not delete the shared overlay directory.
    """
    # Arrange
    overlay_root = tmp_path / "distro_overlay"
    mocker.patch(
        "cobbler.utils.filesystem_helpers.DISTRO_OVERLAY_DIR", str(overlay_root)
    )
    source_tree_path = tmp_path / "source"
    source_tree_path.mkdir()
    item1 = create_distro(
        "test_remove_keeps_overlay_dir_while_another_distro_shares_same_source_tree_path_1"
    )
    item1.source_tree_path = str(source_tree_path)
    item2 = create_distro(
        "test_remove_keeps_overlay_dir_while_another_distro_shares_same_source_tree_path_2"
    )
    item2.source_tree_path = str(source_tree_path)
    overlay_file = filesystem_helpers.get_distro_overlay_write_path(
        str(source_tree_path), "boot/winpe.wim"
    )
    Path(overlay_file).write_bytes(b"content")
    overlay_dir = filesystem_helpers.get_distro_overlay_dir(str(source_tree_path))

    # Act
    distro_collection.remove(item1)

    # Assert
    assert os.path.isdir(overlay_dir)


def test_indexes(
    distro_collection: distros.Distros,
):
    """
    Test to verify that the collection's indexes are initialized correctly.
    """
    # Arrange

    # Assert
    assert len(distro_collection.indexes) == 2
    assert len(distro_collection.indexes["name"]) == 0
    assert len(distro_collection.indexes["arch"]) == 0


def test_add_to_indexes(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that an item can be added to the collection's indexes.
    """
    # Arrange
    name = "test_add_to_indexes"
    item1 = create_distro(name)

    # Act
    del (distro_collection.indexes["name"])[name]
    del (distro_collection.indexes["arch"])[item1.arch.value]
    distro_collection.add_to_indexes(item1)

    # Assert
    assert name in distro_collection.indexes["name"]
    assert item1.arch.value in distro_collection.indexes["arch"]


def test_remove_from_indexes(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that an item can be removed from the collection's indexes.
    """
    # Arrange
    name = "test_remove_from_indexes"
    item1 = create_distro(name)

    # Act
    distro_collection.remove_from_indexes(item1)

    # Assert
    assert name not in distro_collection.indexes["name"]
    assert item1.arch.value not in distro_collection.indexes["arch"]


def test_update_indexes(
    create_distro: Callable[[], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that the collection's indexes are updated correctly after modifying an item's attributes.
    """
    # Arrange
    item1 = create_distro()
    new_name = "test_update_indicies_post"

    # Act
    item1.name = new_name  # type: ignore[method-assign]
    item1.arch = enums.Archs.I386  # type: ignore[method-assign]

    # Assert
    assert distro_collection.indexes["name"][new_name] == item1.uid
    assert distro_collection.indexes["arch"][enums.Archs.I386.value] == {item1.uid}


def test_find_by_indexes(
    create_distro: Callable[[], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Test to verify that items can be found by various indexes.
    """
    # Arrange
    item1 = create_distro()
    kwargs1 = {"name": item1.name}
    kwargs2 = {"name": "fake_name"}
    kwargs3 = {"fake_index": item1.uid}
    kwargs4 = {"arch": item1.arch.value}
    kwargs5 = {"arch": "fake_arch"}

    # Act
    result1 = distro_collection.find_by_indexes(kwargs1)
    result2 = distro_collection.find_by_indexes(kwargs2)
    result3 = distro_collection.find_by_indexes(kwargs3)
    result4 = distro_collection.find_by_indexes(kwargs4)
    result5 = distro_collection.find_by_indexes(kwargs5)

    # Assert
    assert isinstance(result1, list)
    assert len(result1) == 1
    assert result1[0] == item1
    assert len(kwargs1) == 0
    assert result2 is None
    assert len(kwargs2) == 0
    assert result3 is None
    assert len(kwargs3) == 1
    assert result4 is not None
    assert len(result4) == 1
    assert len(kwargs4) == 0
    assert result5 is None
    assert len(kwargs5) == 0


def test_add_with_sync_acquires_filelock(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
    distro_collection: distros.Distros,
    mocker: "MockerFixture",
):
    """
    Test that saving a distro with sync enabled takes the global sync lock.
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    item1 = distro.Distro(cobbler_api)
    item1.name = "test_add_with_sync_acquires_filelock"  # type: ignore[method-assign]
    item1.initrd = os.path.join(folder, fk_initrd)  # type: ignore
    item1.kernel = os.path.join(folder, fk_kernel)  # type: ignore
    filelock_mock = mocker.patch("cobbler.utils.filelock")

    # Act
    distro_collection.add(item1, save=True, with_sync=True)

    # Assert
    # Once for the serializer's own on-disk write (save=True) and once for the quick-sync
    # (with_sync=True) - both now route through the same lock primitive.
    assert filelock_mock.call_count == 2
    for call in filelock_mock.call_args_list:
        assert call.args[0] == "/var/lib/cobbler/lock"


def test_remove_with_sync_acquires_filelock(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
    mocker: "MockerFixture",
):
    """
    Test that removing a distro with sync enabled takes the global sync lock.
    """
    # Arrange
    item1 = create_distro("test_remove_with_sync_acquires_filelock")
    filelock_mock = mocker.patch("cobbler.utils.filelock")

    # Act
    distro_collection.remove(item1, with_sync=True)

    # Assert
    # Once for the serializer's own on-disk delete (always runs) and once for the quick-sync
    # (with_delete defaults to True, with_sync=True) - both now route through the same lock.
    assert filelock_mock.call_count == 2
    for call in filelock_mock.call_args_list:
        assert call.args[0] == "/var/lib/cobbler/lock"


def test_add_accepts_matching_expected_mtime(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Classic-edit lost-update race regression test: Collection.add() must allow the write through when
    the caller-supplied expected_mtime still matches the live item's current mtime. Uses a clone of the
    live item (not the live item itself) to mirror how the classic edit path actually calls add() - with
    a private, edited clone, distinct from whatever object is currently sitting in ``self.listing``.
    """
    # Arrange
    item1 = create_distro("test_add_accepts_matching_expected_mtime")
    current_mtime = distro_collection.listing[item1.uid].mtime
    clone = item1.make_clone()
    clone.uid = item1.uid
    clone.comment = "accepted"  # type: ignore

    # Act
    distro_collection.add(clone, save=True, expected_mtime=current_mtime)

    # Assert
    assert distro_collection.listing[item1.uid].comment == "accepted"


def test_add_rejects_stale_expected_mtime(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Classic-edit lost-update race regression test: Collection.add() must reject an add whose
    caller-supplied expected_mtime no longer matches the live item's mtime - closing the
    classic-edit-path lost update race (and, via the same mechanism, the transaction-commit
    apply loop's TOCTOU).
    """
    # Arrange
    item1 = create_distro("test_add_rejects_stale_expected_mtime")
    stale_mtime = item1.mtime
    concurrent_clone = item1.make_clone()
    concurrent_clone.uid = item1.uid
    concurrent_clone.comment = "someone else's concurrent edit"  # type: ignore
    distro_collection.add(concurrent_clone, save=True)
    assert distro_collection.listing[item1.uid].mtime != stale_mtime

    my_stale_clone = item1.make_clone()
    my_stale_clone.uid = item1.uid
    my_stale_clone.comment = "my stale edit"  # type: ignore

    # Act & Assert
    with pytest.raises(ValueError):
        distro_collection.add(my_stale_clone, save=True, expected_mtime=stale_mtime)


def test_add_rejects_expected_mtime_for_removed_item(
    create_distro: Callable[[str], distro.Distro],
    distro_collection: distros.Distros,
):
    """
    Classic-edit lost-update race regression test: an add carrying an expected_mtime must also be
    rejected if the item was removed from the collection in the meantime, not just if it was modified.
    """
    # Arrange
    item1 = create_distro("test_add_rejects_expected_mtime_for_removed_item")
    stale_mtime = item1.mtime
    clone = item1.make_clone()
    clone.uid = item1.uid
    distro_collection.remove(item1)

    # Act & Assert
    with pytest.raises(ValueError):
        distro_collection.add(clone, save=True, expected_mtime=stale_mtime)
