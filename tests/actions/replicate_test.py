import pytest

from cobbler.actions import replicate


@pytest.fixture(scope="function")
def replicate_obj(cobbler_api):
    return replicate.Replicate(cobbler_api)


def test_rsync_it(mocker, replicate_obj):
    # Arrange
    mock_subprocess_call = mocker.patch("cobbler.utils.subprocess_call", return_value=0)
    replicate_obj.master = "cobbler-master"

    # Act
    replicate_obj.rsync_it("/path1", "/path2", "item")

    # Assert
    mock_subprocess_call.assert_called_with(
        "rsync -avzH cobbler-master::/path1 /path2", shell=True
    )


def test_remove_objects_not_on_master(mocker, replicate_obj):
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
    api_mock.remove_item.assert_called_with("distro", "test", recursive=True)


def test_add_objects_not_on_local(mocker, replicate_obj):
    # Arrange
    replicate_obj.local_data["distro"] = []
    replicate_obj.remote_data["distro"] = []
    replicate_obj.must_include["distro"] = ["test"]
    mocker.patch("cobbler.utils.lod_to_dod", return_value={})
    mocker.patch(
        "cobbler.utils.lod_sort_by_key",
        return_value=[{"uid": "fake_uid", "name": "test"}],
    )
    api_mock = mocker.patch.object(replicate_obj, "api")

    # Act
    replicate_obj.add_objects_not_on_local("distro")

    # Assert
    api_mock.new_distro.assert_called_once()


def test_replace_objects_newer_on_remote(mocker, replicate_obj):
    # Arrange
    replicate_obj.local_data["distro"] = []
    replicate_obj.remote_data["distro"] = []
    replicate_obj.must_include["distro"] = ["test"]
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
    api_mock.new_distro.assert_called_once()
    api_mock.add_item.assert_called_once()


def test_replicate_data(mocker, replicate_obj):
    # Arrange
    remote_mock = mocker.MagicMock()
    remote_mock.get_settings.return_value = {"webdir": "/srv/www/cobbler"}
    remote_mock.get_items.return_value = {}
    mocker.patch.object(
        replicate_obj,
        "remote",
        return_value=remote_mock,
    )
    local_mock = mocker.MagicMock(return_value={"webdir": "/srv/www/cobbler"})
    local_mock.get_items.return_value = {}
    mocker.patch.object(
        replicate_obj,
        "local",
        return_value=local_mock,
    )
    rsync_mock = mocker.patch.object(replicate_obj, "rsync_it")
    expected_rsync_it_calls = [
        mocker.call("cobbler-distros/config/", "/var/www/cobbler/distro_mirror/config"),
        mocker.call("cobbler-templates", "/var/lib/cobbler/templates"),
        mocker.call("cobbler-snippets", "/var/lib/cobbler/snippets"),
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


def test_link_distros(mocker, replicate_obj, create_distro):
    # Arrange
    test_distro = create_distro()
    mock_link_distro = mocker.patch.object(test_distro, "link_distro")

    # Act
    replicate_obj.link_distros()

    # Assert
    mock_link_distro.assert_called_once()


def test_generate_include_map(mocker, replicate_obj):
    # Arrange
    mocker.patch("cobbler.utils.lod_to_dod", return_value={"a": {}})
    replicate_obj.sync_all = True
    replicate_obj.remote_data = {
        "distro": [{"a": 1}],
        "profile": [{"a": 1}],
        "system": [{"a": 1}],
        "repo": [{"a": 1}],
        "image": [{"a": 1}],
        "mgmtclass": [{"a": 1}],
        "package": [{"a": 1}],
        "file": [{"a": 1}],
    }
    expected_must_include = {
        "distro": {"a": 1},
        "profile": {"a": 1},
        "system": {"a": 1},
        "repo": {"a": 1},
        "image": {"a": 1},
        "mgmtclass": {"a": 1},
        "package": {"a": 1},
        "file": {"a": 1},
    }

    # Act
    replicate_obj.generate_include_map()

    # Assert
    assert replicate_obj.must_include == expected_must_include


def test_run(mocker, cobbler_api, replicate_obj):
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
