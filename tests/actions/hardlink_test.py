"""
Module to test the "cobbler hardlink" functionallity.
"""

import os
from pathlib import Path
from typing import List

import pytest
from pytest_mock import MockerFixture

from cobbler.actions import hardlink
from cobbler.api import CobblerAPI


def test_object_creation(cobbler_api: CobblerAPI):
    """
    Assert that the object can be created without failure.
    """
    # Arrange & Act
    result = hardlink.HardLinker(cobbler_api)

    # Assert
    assert isinstance(result, hardlink.HardLinker)
    assert result.hardlink != ""
    assert result.family != ""
    assert result.webdir != ""


def test_constructor_value_error():
    """
    Assert that with missing arguments the creation of the object would fail with a TypeError.
    """
    # pylint: disable=no-value-for-parameter
    # Act & Assert
    with pytest.raises(TypeError):
        hardlink.HardLinker()  # type: ignore


def test_no_hardlink_available(mocker: MockerFixture, cobbler_api: CobblerAPI):
    """
    Assert that an Exception is thrown in case the "hardlink" command is not available.
    """
    # Arrange
    mocker.patch("os.path.exists", return_value=False)
    utils_die_mock = mocker.patch("cobbler.utils.die")

    # Act
    hardlink.HardLinker(api=cobbler_api)

    # Assert
    utils_die_mock.assert_called_once()


@pytest.mark.parametrize(
    "mock_family,expected_hardlink_cmd",
    [
        (
            "debian",
            [
                "/usr/bin/hardlink",
                "-f",
                "-p",
                "-o",
                "-t",
                "-v",
                "/srv/www/cobbler/distro_mirror",
                "/srv/www/cobbler/repo_mirror",
            ],
        ),
        (
            "suse",
            [
                "/usr/bin/hardlink",
                "-f",
                "-v",
                "/srv/www/cobbler/distro_mirror",
                "/srv/www/cobbler/repo_mirror",
            ],
        ),
        (
            "other distros",
            [
                "/usr/bin/hardlink",
                "-c",
                "-v",
                "/srv/www/cobbler/distro_mirror",
                "/srv/www/cobbler/repo_mirror",
            ],
        ),
    ],
)
def test_run(
    mocker: MockerFixture,
    cobbler_api: CobblerAPI,
    mock_family: str,
    expected_hardlink_cmd: List[str],
):
    """
    Assert that the main logic of the module is working as expected.
    """
    # Arrange
    mocker.patch("cobbler.utils.get_family", return_value=mock_family)
    mock_subprocess_call = mocker.patch("cobbler.utils.subprocess_call", return_value=0)
    mock_break_repodata_hardlinks = mocker.patch.object(
        hardlink.HardLinker, "_break_repodata_hardlinks", autospec=True
    )
    mock_manager = mocker.Mock()
    mock_manager.attach_mock(mock_subprocess_call, "subprocess_call")
    mock_manager.attach_mock(
        mock_break_repodata_hardlinks, "break_repodata_hardlinks"
    )
    hardlink_obj = hardlink.HardLinker(cobbler_api)
    hardlink_obj.webdir = "/srv/www/cobbler"
    expected_calls = [
        mocker.call(expected_hardlink_cmd, shell=False),
        mocker.call(
            [
                "/usr/bin/hardlink",
                "-c",
                "-v",
                "/srv/www/cobbler/distro_mirror",
                "/srv/www/cobbler/repo_mirror",
            ],
            shell=False,
        ),
    ]
    expected_manager_calls = [
        mocker.call.subprocess_call(expected_hardlink_cmd, shell=False),
        mocker.call.subprocess_call(
            [
                "/usr/bin/hardlink",
                "-c",
                "-v",
                "/srv/www/cobbler/distro_mirror",
                "/srv/www/cobbler/repo_mirror",
            ],
            shell=False,
        ),
        mocker.call.break_repodata_hardlinks(hardlink_obj),
    ]

    # Act
    hardlink_obj.run()

    # Assert
    assert mock_subprocess_call.mock_calls == expected_calls
    assert mock_manager.mock_calls == expected_manager_calls


def test_break_repodata_hardlinks_replaces_repodata_files(tmp_path: Path):
    """
    Assert that hardlinked files inside repodata directories get private inodes.
    """
    # Arrange
    repo1_repodata = tmp_path / "repo_mirror" / "repo1" / "repodata"
    repo2_repodata = tmp_path / "repo_mirror" / "repo2" / "repodata"
    repo1_repodata.mkdir(parents=True)
    repo2_repodata.mkdir(parents=True)
    repo1_file = repo1_repodata / "repomd.xml"
    repo2_file = repo2_repodata / "repomd.xml"
    repo1_file.write_text("<repomd />")
    os.link(repo1_file, repo2_file)
    hardlink_obj = hardlink.HardLinker.__new__(hardlink.HardLinker)
    hardlink_obj.webdir = str(tmp_path)

    # Act
    hardlink_obj._break_repodata_hardlinks()

    # Assert
    repo1_stat = repo1_file.stat()
    repo2_stat = repo2_file.stat()
    assert repo1_stat.st_ino != repo2_stat.st_ino
    assert repo1_stat.st_nlink == 1
    assert repo2_stat.st_nlink == 1
    assert repo1_file.read_text() == repo2_file.read_text()


def test_break_repodata_hardlinks_leaves_other_hardlinks(tmp_path: Path):
    """
    Assert that hardlinked files outside repodata directories stay hardlinked.
    """
    # Arrange
    repo1_packages = tmp_path / "repo_mirror" / "repo1" / "Packages"
    repo2_packages = tmp_path / "repo_mirror" / "repo2" / "Packages"
    repo1_packages.mkdir(parents=True)
    repo2_packages.mkdir(parents=True)
    repo1_file = repo1_packages / "package.rpm"
    repo2_file = repo2_packages / "package.rpm"
    repo1_file.write_text("rpm")
    os.link(repo1_file, repo2_file)
    hardlink_obj = hardlink.HardLinker.__new__(hardlink.HardLinker)
    hardlink_obj.webdir = str(tmp_path)

    # Act
    hardlink_obj._break_repodata_hardlinks()

    # Assert
    repo1_stat = repo1_file.stat()
    repo2_stat = repo2_file.stat()
    assert repo1_stat.st_ino == repo2_stat.st_ino
    assert repo1_stat.st_nlink == 2
    assert repo2_stat.st_nlink == 2
