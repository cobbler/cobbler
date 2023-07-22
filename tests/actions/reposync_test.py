import os

import pytest

from cobbler import cexceptions, enums
from cobbler.actions import reposync
from cobbler.items.repo import Repo

from tests.conftest import does_not_raise


@pytest.fixture(scope="function")
def reposync_object(mocker, cobbler_api):
    settings_mock = mocker.MagicMock()
    settings_mock.webdir = "/srv/www/cobbler"
    settings_mock.server = "localhost"
    settings_mock.http_port = 80
    settings_mock.proxy_url_ext = ""
    settings_mock.yumdownloader_flags = "--testflag"
    settings_mock.reposync_rsync_flags = "--testflag"
    settings_mock.reposync_flags = "--testflag"
    mocker.patch.object(cobbler_api, "settings", return_value=settings_mock)
    test_reposync = reposync.RepoSync(cobbler_api, tries=2, nofail=False)
    return test_reposync


@pytest.fixture
def repo(cobbler_api):
    """
    Creates a Repository "testrepo0" with a keep_updated=True and mirror_locally=True".
    """
    test_repo = Repo(cobbler_api)
    test_repo.name = "testrepo0"
    test_repo.mirror_locally = True
    test_repo.keep_updated = True
    return test_repo


@pytest.fixture
def remove_repo(cobbler_api):
    """
    Removes the Repository "testrepo0" which can be created with repo.
    """
    yield
    test_repo = cobbler_api.find_repo("testrepo0")
    if test_repo is not None:
        cobbler_api.remove_repo(test_repo.name)


@pytest.fixture(scope="function", autouse=True)
def reset_librepo():
    has_librepo = reposync.HAS_LIBREPO
    yield
    reposync.HAS_LIBREPO = has_librepo


def test_repo_walker(mocker, tmp_path):
    # Arrange
    def test_fun(arg, top, names):
        pass

    subdir1 = tmp_path / "sub1"
    subdir2 = tmp_path / "sub2"
    subdir1.mkdir()
    subdir2.mkdir()
    spy = mocker.Mock(wraps=test_fun)

    # Act
    reposync.repo_walker(tmp_path, spy, None)

    # Assert
    assert spy.mock_calls == [
        # settings.yaml is here because of our autouse fixture that we use to restore the settings
        mocker.call(None, tmp_path, ["settings.yaml", "sub1", "sub2"]),
        mocker.call(None, str(subdir1), []),
        mocker.call(None, str(subdir2), []),
    ]


@pytest.mark.parametrize(
    "input_has_librepo,input_path_exists_side_effect,expected_exception,expected_result",
    [
        (True, [True, False], does_not_raise(), ["/usr/bin/dnf", "reposync"]),
        (True, [False, True], does_not_raise(), ["/usr/bin/reposync"]),
        (True, [False, False], pytest.raises(cexceptions.CX), ""),
        (False, [False, True], pytest.raises(cexceptions.CX), ""),
    ],
)
def test_reposync_cmd(
    mocker,
    reposync_object,
    input_has_librepo,
    input_path_exists_side_effect,
    expected_exception,
    expected_result,
):
    # Arrange
    mocker.patch("os.path.exists", side_effect=input_path_exists_side_effect)
    reposync.HAS_LIBREPO = input_has_librepo

    # Act
    with expected_exception:
        result = reposync_object.reposync_cmd()

        # Assert
        assert result == expected_result


def test_run(mocker, reposync_object, repo):
    # Arrange
    env_vars = {}
    mocker.patch("os.makedirs")
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch(
        "os.path.join",
        side_effect=[
            "/srv/www/cobbler/repo_mirror",
            "/srv/www/cobbler/repo_mirror/%s" % repo.name,
        ],
    )
    mocker.patch("os.environ", return_value=env_vars)
    mocker.patch.object(reposync_object, "repos", return_value=[repo])
    mocker.patch.object(reposync_object, "sync")
    mocker.patch.object(reposync_object, "update_permissions")
    reposync_object.repos = [repo]

    # Act
    reposync_object.run()

    # Assert
    # This has to be 0 since all env vars need to be removed after reposync has run.
    assert len(env_vars) == 0


def test_gen_urlgrab_ssl_opts(reposync_object):
    # Arrange
    input_dict = {}

    # Act
    result = reposync_object.gen_urlgrab_ssl_opts(input_dict)

    # Assert
    assert isinstance(result, tuple)
    assert len(result) == 2
    # The data of the first element is kind of flexible let's skip asserting it for now
    assert isinstance(result[1], bool)


@pytest.mark.usefixtures("remove_repo")
@pytest.mark.parametrize(
    "input_mirror_type,input_mirror,expected_exception",
    [
        (
            enums.MirrorType.BASEURL,
            "http://download.fedoraproject.org/pub/fedora/linux/development/rawhide/Everything/x86_64/os",
            does_not_raise(),
        ),
        (
            enums.MirrorType.MIRRORLIST,
            "https://mirrors.fedoraproject.org/mirrorlist?repo=rawhide&arch=x86_64",
            does_not_raise(),
        ),
        (
            enums.MirrorType.METALINK,
            "https://mirrors.fedoraproject.org/metalink?repo=rawhide&arch=x86_64",
            does_not_raise(),
        ),
    ],
)
def test_reposync_yum(
    mocker,
    input_mirror_type,
    input_mirror,
    expected_exception,
    cobbler_api,
    repo,
    reposync_object,
):
    # Arrange
    test_repo = repo
    test_repo.breed = enums.RepoBreeds.YUM
    test_repo.mirror = input_mirror
    test_repo.mirror_type = input_mirror_type
    test_repo.rpm_list = "fedora-gpg-keys"
    test_settings = cobbler_api.settings()
    repo_path = os.path.join(test_settings.webdir, "repo_mirror", test_repo.name)
    mocked_subprocess = mocker.patch(
        "cobbler.utils.subprocess_call", autospec=True, return_value=0
    )
    mocker.patch.object(
        reposync_object, "create_local_file", return_value="/create/local/file"
    )
    mocker.patch.object(
        reposync_object, "reposync_cmd", return_value=["/my/fake/dnf", "reposync"]
    )
    mocker.patch.object(reposync_object, "rflags", return_value="--fake-r-flakg")
    mocker.patch.object(
        reposync_object,
        "gen_urlgrab_ssl_opts",
        return_value=(("TODO", "TODO", "TODO"), False),
    )
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("shutil.rmtree")
    mocker.patch("os.makedirs")
    mocked_repo_walker = mocker.patch("cobbler.actions.reposync.repo_walker")
    handle_mock = mocker.MagicMock()
    result_mock = mocker.MagicMock()
    mocker.patch("librepo.Handle", return_value=handle_mock)
    mocker.patch("librepo.Result", return_value=result_mock)

    # Act & Assert
    with expected_exception:
        reposync_object.yum_sync(repo)

        mocked_subprocess.assert_called_with(
            [
                "/usr/bin/dnf",
                "download",
                "--testflag",
                "--disablerepo=*",
                f"--enablerepo={repo.name}",
                "-c=/create/local/file",
                f"--destdir={repo_path}",
                "fedora-gpg-keys",
            ],
            shell=False,
        )
        handle_mock.perform.assert_called_with(result_mock)
        assert mocked_repo_walker.call_count == 1


@pytest.mark.usefixtures("remove_repo")
@pytest.mark.parametrize(
    "input_mirror_type,input_mirror,input_arch,input_rpm_list,expected_exception",
    [
        (
            enums.MirrorType.BASEURL,
            "http://ftp.debian.org/debian",
            enums.RepoArchs.X86_64,
            "",
            does_not_raise(),
        ),
        (
            enums.MirrorType.MIRRORLIST,
            "http://ftp.debian.org/debian",
            enums.RepoArchs.X86_64,
            "",
            pytest.raises(cexceptions.CX),
        ),
        (
            enums.MirrorType.METALINK,
            "http://ftp.debian.org/debian",
            enums.RepoArchs.X86_64,
            "",
            pytest.raises(cexceptions.CX),
        ),
        (
            enums.MirrorType.BASEURL,
            "http://ftp.debian.org/debian",
            enums.RepoArchs.NONE,
            "",
            pytest.raises(cexceptions.CX),
        ),
        (
            enums.MirrorType.BASEURL,
            "http://ftp.debian.org/debian",
            enums.RepoArchs.X86_64,
            "dpkg",
            pytest.raises(cexceptions.CX),
        ),
    ],
)
def test_reposync_apt(
    mocker,
    input_mirror_type,
    input_mirror,
    input_arch,
    input_rpm_list,
    expected_exception,
    cobbler_api,
    repo,
    reposync_object,
):
    # Arrange
    test_repo = repo
    test_repo.breed = enums.RepoBreeds.APT
    test_repo.arch = input_arch
    test_repo.apt_components = "main"
    test_repo.apt_dists = "stable"
    test_repo.mirror = input_mirror
    test_repo.mirror_type = input_mirror_type
    test_repo.rpm_list = input_rpm_list
    test_settings = cobbler_api.settings()
    repo_path = os.path.join(test_settings.webdir, "repo_mirror", test_repo.name)
    mocked_subprocess = mocker.patch(
        "cobbler.utils.subprocess_call", autospec=True, return_value=0
    )
    mocker.patch("os.path.exists", return_value=True)

    # Act
    with expected_exception:
        reposync_object.apt_sync(repo)

        # Assert
        mocked_subprocess.assert_called_with(
            [
                "/usr/bin/debmirror",
                "--nocleanup",
                "--method=http",
                "--host=ftp.debian.org",
                "--root=/debian",
                "--dist=stable",
                "--section=main",
                repo_path,
                "--nosource",
                "-a=amd64",
            ],
            shell=False,
        )


@pytest.mark.usefixtures("remove_repo")
@pytest.mark.parametrize(
    "input_mirror_type,input_mirror,expected_exception",
    [
        (
            enums.MirrorType.BASEURL,
            "http://download.fedoraproject.org/pub/fedora/linux/development/rawhide/Everything/x86_64/os/Packages/2",
            does_not_raise(),
        ),
        (
            enums.MirrorType.MIRRORLIST,
            "http://download.fedoraproject.org/pub/fedora/linux/development/rawhide/Everything/x86_64/os/Packages/2",
            pytest.raises(cexceptions.CX),
        ),
        (
            enums.MirrorType.METALINK,
            "http://download.fedoraproject.org/pub/fedora/linux/development/rawhide/Everything/x86_64/os/Packages/2",
            pytest.raises(cexceptions.CX),
        ),
    ],
)
def test_reposync_wget(
    mocker,
    input_mirror_type,
    input_mirror,
    expected_exception,
    cobbler_api,
    repo,
    reposync_object,
):
    # Arrange
    test_repo = repo
    test_repo.breed = enums.RepoBreeds.WGET
    test_repo.mirror = input_mirror
    test_repo.mirror_type = input_mirror_type
    repo_path = os.path.join(
        reposync_object.settings.webdir, "repo_mirror", test_repo.name
    )
    mocked_subprocess = mocker.patch(
        "cobbler.utils.subprocess_call", autospec=True, return_value=0
    )
    mocker.patch("cobbler.actions.reposync.repo_walker")
    mocker.patch.object(reposync_object, "create_local_file")

    # Act
    with expected_exception:
        reposync_object.wget_sync(test_repo)

        # Assert
        mocked_subprocess.assert_called_with(
            [
                "wget",
                "-N",
                "-np",
                "-r",
                "-l",
                "inf",
                "-nd",
                "-P",
                repo_path,
                input_mirror,
            ],
            shell=False,
        )


def test_reposync_rhn(mocker, reposync_object, repo):
    # Arrange
    repo.mirror = "rhn://%s" % repo.name
    mocked_subprocess = mocker.patch(
        "cobbler.utils.subprocess_call", autospec=True, return_value=0
    )
    mocker.patch("os.path.isdir", return_value=True)
    mocker.patch("os.makedirs")
    mocker.patch("cobbler.actions.reposync.repo_walker")
    mocker.patch.object(reposync_object, "create_local_file")
    mocker.patch.object(
        reposync_object, "reposync_cmd", return_value=["/my/fake/reposync"]
    )

    # Act
    reposync_object.rhn_sync(repo)

    # Assert
    # TODO: Check this more and document how its actually working
    mocked_subprocess.assert_called_with(
        [
            "/my/fake/reposync",
            "--testflag",
            "--repo=testrepo0",
            "--download-path=/srv/www/cobbler/repo_mirror",
        ],
        shell=False,
    )


def test_reposync_rsync(mocker, reposync_object, repo):
    # Arrange
    mocked_subprocess = mocker.patch("cobbler.utils.subprocess_call", return_value=0)
    mocker.patch("cobbler.actions.reposync.repo_walker")
    mocker.patch.object(reposync_object, "create_local_file")
    repo_path = os.path.join(reposync_object.settings.webdir, "repo_mirror", repo.name)

    # Act
    reposync_object.rsync_sync(repo)

    # Assert
    mocked_subprocess.assert_called_with(
        [
            "rsync",
            "--testflag",
            "--delete-after",
            "-e ssh",
            "--delete",
            "--exclude-from=/etc/cobbler/rsync.exclude",
            "/",
            repo_path,
        ],
        shell=False,
    )


def test_createrepo_walker(mocker, reposync_object, repo):
    # Arrange
    input_repo = repo
    input_repo.breed = enums.RepoBreeds.RSYNC
    input_dirname = ""
    input_fnames = []
    expected_call = ["createrepo", "--testflags", f"'{input_dirname}'"]
    mocked_subprocess = mocker.patch(
        "cobbler.utils.subprocess_call", autospec=True, return_value=0
    )
    mocker.patch(
        "cobbler.utils.blender",
        autospec=True,
        return_value={"createrepo_flags": "--testflags"},
    )
    mocker.patch("cobbler.utils.remove_yum_olddata")
    mocker.patch("cobbler.utils.subprocess_get", return_value="5")
    mocker.patch("cobbler.utils.get_family", return_value="TODO")
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("os.path.isfile", return_value=True)
    mocker.patch.object(reposync_object, "librepo_getinfo", return_value={})

    # Act
    reposync_object.createrepo_walker(input_repo, input_dirname, input_fnames)

    # Assert
    # TODO: Improve coverage over different cases in method
    mocked_subprocess.assert_called_with(expected_call, shell=False)


@pytest.mark.parametrize(
    "input_repotype,expected_exception",
    [
        (enums.RepoBreeds.YUM, does_not_raise()),
        (enums.RepoBreeds.RHN, does_not_raise()),
        (enums.RepoBreeds.APT, does_not_raise()),
        (enums.RepoBreeds.RSYNC, does_not_raise()),
        (enums.RepoBreeds.WGET, does_not_raise()),
        (enums.RepoBreeds.NONE, pytest.raises(cexceptions.CX)),
    ],
)
def test_sync(mocker, cobbler_api, reposync_object, input_repotype, expected_exception):
    # Arrange
    test_repo = Repo(cobbler_api)
    test_repo.breed = input_repotype
    rhn_sync_mock = mocker.patch.object(reposync_object, "rhn_sync")
    yum_sync_mock = mocker.patch.object(reposync_object, "yum_sync")
    apt_sync_mock = mocker.patch.object(reposync_object, "apt_sync")
    rsync_sync_mock = mocker.patch.object(reposync_object, "rsync_sync")
    wget_sync_mock = mocker.patch.object(reposync_object, "wget_sync")

    # Act
    with expected_exception:
        reposync_object.sync(test_repo)

        # Assert
        call_count = sum(
            (
                rhn_sync_mock.call_count,
                yum_sync_mock.call_count,
                apt_sync_mock.call_count,
                rsync_sync_mock.call_count,
                wget_sync_mock.call_count,
            )
        )
        assert call_count == 1


def test_librepo_getinfo(mocker, reposync_object, tmp_path):
    # Arrange
    handle_mock = mocker.MagicMock()
    result_mock = mocker.MagicMock()
    mocker.patch("librepo.Handle", return_value=handle_mock)
    mocker.patch("librepo.Result", return_value=result_mock)

    # Act
    reposync_object.librepo_getinfo(str(tmp_path))

    # Assert
    handle_mock.perform.assert_called_with(result_mock)
    result_mock.getinfo.assert_called()


def test_create_local_file(mocker, reposync_object, repo):
    # Arrange
    mocker.patch("cobbler.utils.filesystem_helpers.mkdir", autospec=True)
    mock_open = mocker.patch("builtins.open", mocker.mock_open())
    input_dest_path = ""
    input_repo = repo
    input_output = True

    # Act
    reposync_object.create_local_file(input_dest_path, input_repo, output=input_output)

    # Assert
    # TODO: Extend checks
    assert mock_open.call_count == 1
    assert mock_open.mock_calls[0] == mocker.call("config.repo", "w+", encoding="UTF-8")
    mock_open_handle = mock_open()
    assert mock_open_handle.write.mock_calls[0] == mocker.call("[testrepo0]\n")
    assert mock_open_handle.write.mock_calls[1] == mocker.call("name=testrepo0\n")


def test_update_permissions(mocker, reposync_object):
    # Arrange
    mocked_subprocess = mocker.patch(
        "cobbler.utils.subprocess_call", autospec=True, return_value=0
    )
    path_to_update = "/my/fake/path"
    expected_calls = [
        mocker.call(["chown", "-R", "root:www", path_to_update], shell=False),
        mocker.call(["chmod", "-R", "755", path_to_update], shell=False),
    ]

    # Act
    reposync_object.update_permissions(path_to_update)

    # Assert
    assert mocked_subprocess.mock_calls == expected_calls
