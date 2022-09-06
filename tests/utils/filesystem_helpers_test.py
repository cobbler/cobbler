import os
import shutil
from pathlib import Path

import pytest

from cobbler.cexceptions import CX
from cobbler.utils import filesystem_helpers
from tests.conftest import does_not_raise


@pytest.mark.parametrize(
    "test_src,test_dst,expected_result",
    [
        # ("", "", False), --> This has a task in utils.py
        ("/usr/bin/os-release", "/tmp", True),
        ("/etc/os-release", "/tmp", False),
    ],
)
def test_is_safe_to_hardlink(cobbler_api, test_src, test_dst, expected_result):
    # Arrange
    # TODO: Generate cases

    # Act
    result = filesystem_helpers.is_safe_to_hardlink(test_src, test_dst, cobbler_api)

    # Assert
    assert expected_result == result


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_hashfile():
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
    # Arrange
    cache_src = ""
    cache_dst = ""
    api = None

    # Act
    filesystem_helpers.cachefile(cache_src, cache_dst)

    # Assert
    # TODO: Check .link_cache folder exists and the link cache file in it
    # TODO: Assert file exists in the cache destination
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_linkfile(cobbler_api):
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    filesystem_helpers.linkfile(test_source, test_destination, api=cobbler_api)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyfile():
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    filesystem_helpers.copyfile(test_source, test_destination)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyremotefile():
    # Arrange
    test_source = ""
    test_destination = ""

    # Act
    filesystem_helpers.copyremotefile(test_source, test_destination, None)

    # Assert
    assert False


@pytest.mark.skip("This calls a lot of os-specific stuff. Let's fix this test later.")
def test_copyfile_pattern():
    # Arrange
    test_pattern = ""
    test_destination = ""

    # Act
    filesystem_helpers.copyfile_pattern(test_pattern, test_destination)

    # Assert
    assert False


def test_rmfile(tmpdir: Path):
    # Arrange
    tfile = tmpdir.join("testfile")

    # Act
    filesystem_helpers.rmfile(tfile)

    # Assert
    assert not os.path.exists(tfile)


def test_rmglob_files(tmpdir: Path):
    # Arrange
    tfile1 = tmpdir.join("file1.tfile")
    tfile2 = tmpdir.join("file2.tfile")

    # Act
    filesystem_helpers.rmglob_files(tmpdir, "*.tfile")

    # Assert
    assert not os.path.exists(tfile1)
    assert not os.path.exists(tfile2)


def test_rmtree_contents():
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
    # TODO: Check how already existing folder is handled.
    # Arrange
    testfolder = "/dev/shm/testfoldercreation"
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
def test_path_tail(test_first_path, test_second_path, expected_result):
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
def test_safe_filter(test_input, expected_exception):
    # Arrange, Act & Assert
    with expected_exception:
        assert filesystem_helpers.safe_filter(test_input) is None
