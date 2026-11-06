"""
Tests for the replicate action of Cobbler.
"""

from typing import Callable

import pytest
from pytest_mock import MockerFixture

from cobbler.actions import replicate
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro


@pytest.fixture(scope="function")
def replicate_obj(cobbler_api: CobblerAPI) -> replicate.Replicate:
    """
    Creates a blank replicate object for a single test.
    """
    return replicate.Replicate(cobbler_api)


def test_rsync_it(mocker: MockerFixture, replicate_obj: replicate.Replicate):
    """
    Test that asserts that the rsync_it subroutine works as expected.
    """
    # Arrange
    mock_subprocess_call = mocker.patch("cobbler.utils.subprocess_call", return_value=0)
    replicate_obj.master = "cobbler-master"

    # Act
    replicate_obj.rsync_it("/path1", "/path2", "item")

    # Assert
    mock_subprocess_call.assert_called_with(
        ["rsync", "-avzH", "cobbler-master::/path1", "/path2"], shell=False
    )


def test_remove_objects_not_on_master(
    mocker: MockerFixture, replicate_obj: replicate.Replicate
):
    """
    Test that asserts that the remove_objects_not_on_master subroutine works as expected.
    """
    # Arrange
    replicate_obj.local_data["distro"] = []
    replicate_obj.remote_data["distro"] = []
    mocker.patch(
        "cobbler.utils.lod_to_dod",
        side_effect=[{"fake_uid": {"uid": "fake_uid", "name": "test"}}, {}],
    )
    api_mock = mocker.patch.object(replicate_obj, "api")

    # Act
    replicate_obj.remove_objects_not_on_master("distro")

    # Assert
    api_mock.remove_item.assert_called_with("distro", "fake_uid", recursive=True)  # type: ignore


def test_add_objects_not_on_local(
    mocker: MockerFixture, replicate_obj: replicate.Replicate
):
    """
    Test that asserts that the add_objects_not_on_local subroutine works as expected.
    """
    # Arrange
    replicate_obj.local_data["distro"] = []
    replicate_obj.remote_data["distro"] = [{"name": "test", "depth": 0}]
    replicate_obj.must_include["distro"] = ["test"]  # type: ignore
    mocker.patch("cobbler.utils.lod_to_dod", return_value={})
    mocker.patch(
        "cobbler.utils.lod_sort_by_key",
        return_value=[{"uid": "fake_uid", "name": "test"}],
    )
    api_mock = mocker.patch.object(replicate_obj, "api")

    # Act
    replicate_obj.add_objects_not_on_local("distro")

    # Assert
    api_mock.new_distro.assert_called_once()  # type: ignore


def test_add_objects_not_on_local_continues_after_construction_exception(
    mocker: MockerFixture, replicate_obj: replicate.Replicate
):
    """
    Test that asserts that a construction-time exception (raised by the ``new_<type>()`` call,
    e.g. because of invalid data on the remote object) for one object does not abort processing
    of the remaining objects in the same call -- it should be logged and skipped just like an
    ``add_item()`` failure already is.
    """
    # Arrange
    replicate_obj.local_data["distro"] = []
    replicate_obj.remote_data["distro"] = [{"name": "broken", "depth": 0}]
    replicate_obj.must_include["distro"] = ["broken", "ok"]  # type: ignore
    mocker.patch("cobbler.utils.lod_to_dod", return_value={})
    mocker.patch(
        "cobbler.utils.lod_sort_by_key",
        return_value=[
            {"uid": "uid-broken", "name": "broken"},
            {"uid": "uid-ok", "name": "ok"},
        ],
    )
    api_mock = mocker.patch.object(replicate_obj, "api")

    def new_distro_side_effect(**kwargs: object):
        if kwargs.get("name") == "broken":
            raise ValueError("construction failed")
        return mocker.MagicMock()

    api_mock.new_distro.side_effect = new_distro_side_effect  # type: ignore

    # Act
    replicate_obj.add_objects_not_on_local("distro")

    # Assert: the "broken" object's construction exception must not prevent "ok" from being
    # processed (reached by add_item).
    assert api_mock.new_distro.call_count == 2  # type: ignore
    api_mock.add_item.assert_called_once()  # type: ignore
    assert api_mock.add_item.call_args.args[0] == "distro"  # type: ignore


def test_replace_objects_newer_on_remote(
    mocker: MockerFixture, replicate_obj: replicate.Replicate
):
    """
    Test that asserts that the replace_objects_newer_on_remote subroutine works as expected.
    """
    # Arrange
    replicate_obj.local_data["distro"] = []
    replicate_obj.remote_data["distro"] = []
    replicate_obj.must_include["distro"] = ["test"]  # type: ignore
    mocker.patch(
        "cobbler.utils.lod_to_dod",
        side_effect=[
            {"fake_uid": {"uid": "fake_uid", "name": "test", "mtime": 4}},
            {"fake_uid": {"uid": "fake_uid", "name": "test", "mtime": 5}},
        ],
    )
    api_mock = mocker.patch.object(replicate_obj, "api")

    # Act
    replicate_obj.replace_objects_newer_on_remote("distro")

    # Assert
    api_mock.new_distro.assert_called_once()  # type: ignore
    api_mock.add_item.assert_called_once()  # type: ignore


def test_replace_objects_newer_on_remote_renamed_removes_old_by_uid(
    mocker: MockerFixture, replicate_obj: replicate.Replicate
):
    """
    When the same uid has a different name remotely (a rename), the stale local object must be
    removed by its uid, not by its (now-superseded) name.
    """
    # Arrange
    replicate_obj.local_data["distro"] = []
    replicate_obj.remote_data["distro"] = []
    replicate_obj.must_include["distro"] = ["new-name"]  # type: ignore
    mocker.patch(
        "cobbler.utils.lod_to_dod",
        side_effect=[
            {"fake_uid": {"uid": "fake_uid", "name": "old-name", "mtime": 4}},
            {"fake_uid": {"uid": "fake_uid", "name": "new-name", "mtime": 5}},
        ],
    )
    api_mock = mocker.patch.object(replicate_obj, "api")

    # Act
    replicate_obj.replace_objects_newer_on_remote("distro")

    # Assert
    api_mock.remove_item.assert_called_with("distro", "fake_uid", recursive=True)  # type: ignore


def test_replace_objects_newer_on_remote_continues_after_construction_exception(
    mocker: MockerFixture, replicate_obj: replicate.Replicate
):
    """
    Test that asserts that a construction-time exception (raised by the ``new_<type>()`` call)
    for one object does not abort processing of the remaining objects in the same call.
    """
    # Arrange
    replicate_obj.local_data["distro"] = []
    replicate_obj.remote_data["distro"] = []
    replicate_obj.must_include["distro"] = ["broken", "ok"]  # type: ignore
    mocker.patch(
        "cobbler.utils.lod_to_dod",
        side_effect=[
            {
                "uid-broken": {"uid": "uid-broken", "name": "broken", "mtime": 4},
                "uid-ok": {"uid": "uid-ok", "name": "ok", "mtime": 4},
            },
            {
                "uid-broken": {"uid": "uid-broken", "name": "broken", "mtime": 5},
                "uid-ok": {"uid": "uid-ok", "name": "ok", "mtime": 5},
            },
        ],
    )
    api_mock = mocker.patch.object(replicate_obj, "api")

    def new_distro_side_effect(**kwargs: object):
        if kwargs.get("name") == "broken":
            raise ValueError("construction failed")
        return mocker.MagicMock()

    api_mock.new_distro.side_effect = new_distro_side_effect  # type: ignore

    # Act
    replicate_obj.replace_objects_newer_on_remote("distro")

    # Assert: the "broken" object's construction exception must not prevent "ok" from being
    # processed (reached by add_item).
    assert api_mock.new_distro.call_count == 2  # type: ignore
    api_mock.add_item.assert_called_once()  # type: ignore


def test_replicate_data(mocker: MockerFixture, replicate_obj: replicate.Replicate):
    """
    Test that asserts that the replicate_data subroutine works as expected.
    """
    # Arrange
    remote_mock = mocker.MagicMock()
    remote_mock.get_settings.return_value = {"webdir": "/srv/www/cobbler"}  # type: ignore
    remote_mock.get_items.return_value = {}  # type: ignore
    replicate_obj.remote = remote_mock
    local_mock = mocker.MagicMock(return_value={"webdir": "/srv/www/cobbler"})
    local_mock.get_items.return_value = {}  # type: ignore
    replicate_obj.local = local_mock
    rsync_mock = mocker.patch.object(replicate_obj, "rsync_it")
    expected_rsync_it_calls = [
        mocker.call("cobbler-distros/config/", "/srv/www/cobbler/distro_mirror/config"),
        mocker.call("cobbler-templates", "/var/lib/cobbler/templates"),
        mocker.call("cobbler-triggers", "/var/lib/cobbler/triggers"),
        mocker.call("cobbler-scripts", "/var/lib/cobbler/scripts"),
    ]
    not_on_local_mock = mocker.patch.object(replicate_obj, "add_objects_not_on_local")
    newer_on_remote_mock = mocker.patch.object(
        replicate_obj, "replace_objects_newer_on_remote"
    )

    # Act
    replicate_obj.replicate_data()

    # Assert
    assert rsync_mock.mock_calls == expected_rsync_it_calls
    assert not_on_local_mock.call_count == len(replicate.OBJ_TYPES)
    assert newer_on_remote_mock.call_count == len(replicate.OBJ_TYPES)


def test_link_distros(
    mocker: MockerFixture,
    replicate_obj: replicate.Replicate,
    create_distro: Callable[[], Distro],
):
    """
    Test that asserts that the link_distros subroutine works as expected.
    """
    # Arrange
    test_distro = create_distro()
    mock_link_distro = mocker.patch.object(test_distro, "link_distro")

    # Act
    replicate_obj.link_distros()

    # Assert
    mock_link_distro.assert_called_once()


def test_generate_include_map(
    mocker: MockerFixture, replicate_obj: replicate.Replicate
):
    """
    Test that asserts that the generate_include_map subroutine works as expected.
    """
    # Arrange
    mocker.patch("cobbler.utils.lod_to_dod", return_value={"a": {}})
    replicate_obj.sync_all = True
    replicate_obj.remote_data = {
        "distro": [{"a": 1}],
        "profile": [{"a": 1}],
        "system": [{"a": 1}],
        "repo": [{"a": 1}],
        "image": [{"a": 1}],
        "menu": [{"a": 1}],
        "template": [{"a": 1}],
        "network_interface": [{"a": 1}],
        "distro_group": [{"a": 1}],
        "profile_group": [{"a": 1}],
        "system_group": [{"a": 1}],
    }
    expected_must_include = {
        "distro": {"a": 1},
        "profile": {"a": 1},
        "system": {"a": 1},
        "repo": {"a": 1},
        "image": {"a": 1},
        "menu": {"a": 1},
        "template": {"a": 1},
        "network_interface": {"a": 1},
        "distro_group": {"a": 1},
        "profile_group": {"a": 1},
        "system_group": {"a": 1},
    }

    # Act
    replicate_obj.generate_include_map()

    # Assert
    assert replicate_obj.must_include == expected_must_include


def test_generate_include_map_subprofile_parent_not_pre_included(
    replicate_obj: replicate.Replicate,
):
    """
    Test that asserts that generate_include_map() can pull in a matched subprofile's parent
    profile -- which is not itself matched by any pattern -- without raising
    ``RuntimeError: dictionary changed size during iteration``. This is an ordinary setup (a
    shared base profile plus per-arch/variant subprofiles), not an edge case.
    """
    # Arrange
    replicate_obj.sync_all = False
    replicate_obj.distro_patterns = []
    replicate_obj.profile_patterns = ["leap161-sub*"]
    replicate_obj.system_patterns = []
    replicate_obj.repo_patterns = []
    replicate_obj.image_patterns = []
    replicate_obj.remote_data = {
        "distro": [],
        "profile": [
            {
                "name": "leap161-base",
                "parent": "",
                "distro": "<<inherit>>",
                "repos": [],
            },
            {
                "name": "leap161-sub1",
                "parent": "leap161-base",
                "distro": "<<inherit>>",
                "repos": [],
            },
        ],
        "system": [],
        "repo": [],
        "image": [],
        "menu": [],
        "template": [],
        "network_interface": [],
        "distro_group": [],
        "profile_group": [],
        "system_group": [],
    }

    # Act
    replicate_obj.generate_include_map()

    # Assert: both the explicitly-matched subprofile and its pulled-in, unmatched parent are
    # included.
    assert replicate_obj.must_include["profile"] == {
        "leap161-sub1": 1,
        "leap161-base": 1,
    }


def test_run(
    mocker: MockerFixture, cobbler_api: CobblerAPI, replicate_obj: replicate.Replicate
):
    """
    Test that asserts that the replicate algorithm works as intended as a whole.
    """
    # Arrange
    mocker.patch("xmlrpc.client.Server")
    api_sync_mock = mocker.patch.object(cobbler_api, "sync")
    replicate_data_mock = mocker.patch.object(replicate_obj, "replicate_data")
    link_distros_mock = mocker.patch.object(replicate_obj, "link_distros")

    # Act
    replicate_obj.run("fake.test")

    # Assert
    api_sync_mock.assert_called_once()
    replicate_data_mock.assert_called_once()
    link_distros_mock.assert_called_once()
