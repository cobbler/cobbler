"""
Test module to verify the functionality of filesystem helper functions.
"""

import os
import pathlib
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.utils import filesystem_helpers

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.parametrize(
    "test_src,is_symlink,test_dst,expected_result",
    [
        # ("", "", False), --> This has a task in utils.py
        ("/tmp/not-safe-file", True, "/tmp/dst", False),
        ("/tmp/safe-file", False, "/tmp/dst", True),
    ],
)
def test_is_safe_to_hardlink(
    cobbler_api: CobblerAPI,
    test_src: str,
    is_symlink: bool,
    test_dst: str,
    expected_result: bool,
):
    """
    Test to verify the behavior of the is_safe_to_hardlink function.
    """
    # Arrange
    if is_symlink and test_src:
        os.symlink("/foobar/test", test_src)
    elif test_src:
        open(test_src, "w", encoding="UTF-8").close()

    # Act
    result = filesystem_helpers.is_safe_to_hardlink(test_src, test_dst, cobbler_api)

    # Cleanup
    os.remove(test_src)

    # Assert
    assert expected_result == result


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_hashfile():
    """
    Test to verify the behavior of the hashfile function.
    """
    # Arrange
    # TODO: Create testfile
    testfilepath = "/dev/shm/bigtestfile"
    expected_hash = ""

    # Act
    result = filesystem_helpers.hashfile(testfilepath)

    # Assert
    assert expected_hash == result


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_cachefile():
    """
    Test to verify the behavior of the cachefile function.
    """
    # Arrange
    cache_src = ""
    cache_dst = ""

    # Act
    filesystem_helpers.cachefile(cache_src, cache_dst)

    # Assert
    # TODO: Check .link_cache folder exists and the link cache file in it
    # TODO: Assert file exists in the cache destination
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_linkfile(cobbler_api: CobblerAPI):
    """
    Test to verify the behavior of the linkfile function.
    """
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    filesystem_helpers.linkfile(cobbler_api, test_source, test_destination)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyfile():
    """
    Test to verify the behavior of the copyfile function.
    """
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    filesystem_helpers.copyfile(test_source, test_destination)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyremotefile():
    """
    Test to verify the behavior of the copyremotefile function.
    """
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    filesystem_helpers.copyremotefile(test_source, test_destination, None)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_mkdirimage():
    """
    Test to verify the behavior of the mkdirimage function.
    """
    # Arrange
    test_path = pathlib.Path("/tmp")
    test_image_location = ""

    # Act
    filesystem_helpers.mkdirimage(test_path, test_image_location)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyfileimage():
    """
    Test to verify the behavior of the copyfileimage function.
    """
    # Arrange
    test_src = ""
    test_image_location = ""
    test_dst = ""

    # Act
    filesystem_helpers.copyfileimage(test_src, test_image_location, test_dst)

    # Assert
    assert False


def test_rmfile(tmp_path: Path):
    """
    Test to verify the behavior of the rmfile function.
    """
    # Arrange
    tfile = tmp_path / "testfile"

    # Act
    filesystem_helpers.rmfile(str(tfile))

    # Assert
    assert not os.path.exists(tfile)


def test_rmglob_files(tmp_path: Path):
    """
    Test to verify the behavior of the rmglob_files function.
    """
    # Arrange
    tfile1 = tmp_path / "file1.tfile"
    tfile2 = tmp_path / "file2.tfile"

    # Act
    filesystem_helpers.rmglob_files(str(tmp_path), "*.tfile")

    # Assert
    assert not os.path.exists(tfile1)
    assert not os.path.exists(tfile2)


def test_rmtree_contents():
    """
    Test to verify the behavior of the rmtree_contents function.
    """
    # Arrange
    testfolder = "/dev/shm/"
    testfiles = ["test1", "blafile", "testremove"]
    for file in testfiles:
        Path(os.path.join(testfolder, file)).touch()

    # Act
    filesystem_helpers.rmtree_contents(testfolder)

    # Assert
    assert len(os.listdir(testfolder)) == 0


def test_rmtree():
    """
    Test to verify the behavior of the rmtree function.
    """
    # Arrange
    testtree = "/dev/shm/testtree"
    os.mkdir(testtree)

    # Pre assert to check the creation succeeded.
    assert os.path.exists(testtree)

    # Act
    filesystem_helpers.rmtree(testtree)

    # Assert
    assert not os.path.exists(testtree)


def test_mkdir():
    """
    Test to verify the behavior of the mkdir function.
    """
    # TODO: Check how already existing folder is handled.
    # Arrange
    testfolder = "/dev/shm/testfoldercreation/testmkdir"
    testmode = 0o600

    try:
        shutil.rmtree(testfolder)
    except OSError:
        pass

    # Pre assert to check that this actually does something
    assert not os.path.exists(testfolder)

    # Act
    filesystem_helpers.mkdir(testfolder, testmode)

    # Assert
    assert os.path.exists(testfolder)


@pytest.mark.parametrize(
    "test_first_path,test_second_path,expected_result",
    [("/tmp/test/a", "/tmp/test/a/b/c", "/b/c"), ("/tmp/test/a", "/opt/test/a", "")],
)
def test_path_tail(test_first_path: str, test_second_path: str, expected_result: str):
    """
    Test to verify the behavior of the path_tail function.
    """
    # Arrange
    # TODO: Check if this actually makes sense...

    # Act
    result = filesystem_helpers.path_tail(test_first_path, test_second_path)

    # Assert
    assert expected_result == result


@pytest.mark.parametrize(
    "test_input,expected_exception",
    [
        ("Test", does_not_raise()),
        ("Test;Test", pytest.raises(CX)),
        ("Test..Test", pytest.raises(CX)),
    ],
)
def test_safe_filter(test_input: str, expected_exception: Any):
    """
    Test to verify the behavior of the safe_filter function.
    """
    # Arrange, Act & Assert
    with expected_exception:
        filesystem_helpers.safe_filter(test_input)


def test_create_web_dirs(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test to verify the behavior of the create_web_dirs function.
    """
    # Arrange
    settings_mock = mocker.MagicMock()
    settings_mock.webdir = "/my/custom/webdir"
    mocker.patch.object(cobbler_api, "settings", return_value=settings_mock)

    mock_mkdir = mocker.patch("cobbler.utils.filesystem_helpers.mkdir")
    mock_copyfile = mocker.patch("cobbler.utils.filesystem_helpers.copyfile")

    # Act
    filesystem_helpers.create_web_dirs(cobbler_api)

    # Assert
    assert mock_mkdir.call_count == 9
    assert mock_copyfile.call_count == 2


def test_create_tftpboot_dirs(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test to verify the behavior of the create_tftpboot_dirs function.
    """
    # Arrange
    settings_mock = mocker.MagicMock()
    settings_mock.tftpboot_location = "/srv/tftpboot"
    mocker.patch.object(cobbler_api, "settings", return_value=settings_mock)

    mock_mkdir = mocker.patch("cobbler.utils.filesystem_helpers.mkdir")
    mock_path_symlink_to = mocker.patch("pathlib.Path.symlink_to")
    mocker.patch("pathlib.Path.exists", return_value=False)

    # Act
    filesystem_helpers.create_tftpboot_dirs(cobbler_api)

    # Assert
    assert mock_mkdir.call_count == 12
    assert mock_path_symlink_to.call_count == 4


def test_create_trigger_dirs(mocker: "MockerFixture"):
    """
    Test to verify the behavior of the create_trigger_dirs function.
    """
    # Arrange
    mock_mkdir = mocker.patch("cobbler.utils.filesystem_helpers.mkdir")
    mocker.patch("pathlib.Path.exists", return_value=False)

    # Act
    filesystem_helpers.create_trigger_dirs(pathlib.Path("/var/lib/cobbler"))

    # Assert
    assert mock_mkdir.call_count == 102


def test_create_json_database_dirs(mocker: "MockerFixture"):
    """
    Test to verify the behavior of the create_json_database_dirs function.
    """
    # Arrange
    mock_mkdir = mocker.patch("cobbler.utils.filesystem_helpers.mkdir")
    mocker.patch("pathlib.Path.exists", return_value=False)

    # Act
    filesystem_helpers.create_json_database_dirs(pathlib.Path("/var/lib/cobbler"))

    # Assert
    mock_mkdir.assert_any_call("/var/lib/cobbler/collections")
    # 1 collections parent directory + (1 child directory per item type * 11 item types atm)
    assert mock_mkdir.call_count == 12


# --------------------------------------------------------------------------------------------
# Distro overlay helpers
# --------------------------------------------------------------------------------------------


@pytest.fixture(name="overlay_root")
def fixture_overlay_root(tmp_path: Path, mocker: "MockerFixture") -> Path:
    """
    Redirect ``DISTRO_OVERLAY_DIR`` to a ``tmp_path`` subdirectory for every overlay test, so
    nothing touches the real ``/var/lib/cobbler/distro_overlay``.
    """
    overlay_root = tmp_path / "distro_overlay"
    mocker.patch(
        "cobbler.utils.filesystem_helpers.DISTRO_OVERLAY_DIR", str(overlay_root)
    )
    return overlay_root


def test_get_distro_overlay_dir_is_deterministic_and_distinct_per_source_root(
    overlay_root: Path,
):
    """
    The same ``source_root`` must always map to the same overlay directory, and different
    ``source_root``s must map to different ones.
    """
    # Arrange
    source_a = "/mnt/rocky10"
    source_b = "/mnt/debian13"

    # Act
    dir_a_first = filesystem_helpers.get_distro_overlay_dir(source_a)
    dir_a_second = filesystem_helpers.get_distro_overlay_dir(source_a)
    dir_b = filesystem_helpers.get_distro_overlay_dir(source_b)

    # Assert
    assert dir_a_first == dir_a_second
    assert dir_a_first != dir_b
    assert dir_a_first.startswith(str(overlay_root))


def test_get_distro_overlay_write_path_creates_parent_dir_and_returns_path_under_overlay_root(
    overlay_root: Path,
):
    """
    ``get_distro_overlay_write_path()`` must create the parent directory of the returned path
    (not the file itself), and the returned path must live under the overlay root.
    """
    # Arrange
    source_root = "/mnt/rocky10"

    # Act
    result = filesystem_helpers.get_distro_overlay_write_path(
        source_root, os.path.join("boot", "winpe.wim")
    )

    # Assert
    assert result.startswith(str(overlay_root))
    assert result.endswith(os.path.join("boot", "winpe.wim"))
    assert os.path.isdir(os.path.dirname(result))
    assert not os.path.exists(result)


def test_get_distro_overlay_write_path_rejects_path_traversal(overlay_root: Path):
    """
    A ``relative_path`` that would escape the overlay directory must be rejected.
    """
    # Arrange
    source_root = "/mnt/rocky10"

    # Act & Assert
    with pytest.raises(CX):
        filesystem_helpers.get_distro_overlay_write_path(
            source_root, "../../etc/passwd"
        )


def test_get_distro_overlay_write_dir_creates_and_returns_directory_itself(
    overlay_root: Path,
):
    """
    Unlike ``get_distro_overlay_write_path()``, ``get_distro_overlay_write_dir()`` must create and
    return the directory itself (e.g. for ``createrepo --outputdir``).
    """
    # Arrange
    source_root = "/mnt/rocky10"

    # Act
    result = filesystem_helpers.get_distro_overlay_write_dir(
        source_root, "repodata"
    )

    # Assert
    assert result.startswith(str(overlay_root))
    assert os.path.isdir(result)


def test_get_distro_overlay_write_dir_rejects_path_traversal(overlay_root: Path):
    # Arrange
    source_root = "/mnt/rocky10"

    # Act & Assert
    with pytest.raises(CX):
        filesystem_helpers.get_distro_overlay_write_dir(source_root, "../../etc")


def test_resolve_distro_overlay_root_prefers_overlay_dir_when_file_present(
    overlay_root: Path,
):
    """
    If the overlay directory already contains the requested file, it must win over the original
    source root.
    """
    # Arrange
    source_root = "/mnt/rocky10"
    relative_path = os.path.join("boot", "winpe.wim")
    overlay_file = filesystem_helpers.get_distro_overlay_write_path(
        source_root, relative_path
    )
    Path(overlay_file).write_bytes(b"overlay content")

    # Act
    result = filesystem_helpers.resolve_distro_overlay_root(source_root, relative_path)

    # Assert
    assert result == filesystem_helpers.get_distro_overlay_dir(source_root)


def test_resolve_distro_overlay_root_falls_back_to_source_root_when_absent(
    overlay_root: Path,
):
    """
    If the overlay directory has no such file, the original source root must be returned.
    """
    # Arrange
    source_root = "/mnt/rocky10"
    relative_path = os.path.join("boot", "winpe.wim")

    # Act
    result = filesystem_helpers.resolve_distro_overlay_root(source_root, relative_path)

    # Assert
    assert result == source_root


def test_resolve_distro_overlay_read_path_prefers_overlay_when_present(
    overlay_root: Path, tmp_path: Path
):
    # Arrange
    source_root = str(tmp_path / "source")
    relative_path = os.path.join("boot", "winpe.wim")
    overlay_file = filesystem_helpers.get_distro_overlay_write_path(
        source_root, relative_path
    )
    Path(overlay_file).write_bytes(b"overlay content")

    # Act
    result = filesystem_helpers.resolve_distro_overlay_read_path(
        source_root, relative_path
    )

    # Assert
    assert result == overlay_file


def test_resolve_distro_overlay_read_path_falls_back_to_source_root_when_absent(
    overlay_root: Path, tmp_path: Path
):
    # Arrange
    source_root = str(tmp_path / "source")
    relative_path = os.path.join("boot", "winpe.wim")

    # Act
    result = filesystem_helpers.resolve_distro_overlay_read_path(
        source_root, relative_path
    )

    # Assert
    assert result == os.path.join(source_root, relative_path)


def test_remove_distro_overlay_dir_is_noop_when_absent(overlay_root: Path):
    # Arrange
    source_root = "/mnt/rocky10"

    # Act & Assert (must not raise)
    filesystem_helpers.remove_distro_overlay_dir(source_root)


def test_remove_distro_overlay_dir_removes_existing_overlay(overlay_root: Path):
    # Arrange
    source_root = "/mnt/rocky10"
    overlay_file = filesystem_helpers.get_distro_overlay_write_path(
        source_root, os.path.join("boot", "winpe.wim")
    )
    Path(overlay_file).write_bytes(b"overlay content")
    overlay_dir = filesystem_helpers.get_distro_overlay_dir(source_root)
    assert os.path.isdir(overlay_dir)

    # Act
    filesystem_helpers.remove_distro_overlay_dir(source_root)

    # Assert
    assert not os.path.exists(overlay_dir)
