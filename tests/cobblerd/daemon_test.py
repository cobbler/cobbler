"""
Testmodule to verify the functionality of the "cobbler.cobblerd.daemon" module.
"""

from typing import TYPE_CHECKING

from cobbler.cobblerd import daemon

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_regen_ss_file_chowns_when_http_user_exists(mocker: "MockerFixture") -> None:
    """
    ``regen_ss_file()`` must still chown the Kerberos-auth socket file to the detected http user when that
    user actually exists on the system (RPM/DEB/dev-stack deployments running Apache). This is the existing
    behavior and must not change.
    """
    mocker.patch("cobbler.cobblerd.daemon.utils.get_family", return_value="redhat")
    mock_getpwnam = mocker.patch("cobbler.cobblerd.daemon.pwd.getpwnam")
    mock_getpwnam.return_value = (
        "apache",
        "x",
        48,
        48,
        "Apache",
        "/srv/www",
        "/sbin/nologin",
    )
    mock_lchown = mocker.patch("cobbler.cobblerd.daemon.os.lchown")
    mocker.patch("builtins.open", mocker.mock_open())

    daemon.regen_ss_file()

    mock_getpwnam.assert_called_once_with("apache")
    mock_lchown.assert_called_once_with("/var/lib/cobbler/web.ss", 48, -1)


def test_regen_ss_file_tolerates_missing_http_user(mocker: "MockerFixture") -> None:
    """
    In the minimal, Apache-less container image none of "wwwrun"/"apache"/"www-data" exist.
    ``regen_ss_file()`` must not crash the daemon at startup with the ``KeyError`` that
    ``pwd.getpwnam()`` raises for an unknown user -- it must skip the chown (and log about it) instead.
    """
    mocker.patch("cobbler.cobblerd.daemon.utils.get_family", return_value="suse")
    mock_getpwnam = mocker.patch(
        "cobbler.cobblerd.daemon.pwd.getpwnam", side_effect=KeyError("wwwrun")
    )
    mock_lchown = mocker.patch("cobbler.cobblerd.daemon.os.lchown")
    mocker.patch("builtins.open", mocker.mock_open())

    # Must not raise.
    daemon.regen_ss_file()

    mock_getpwnam.assert_called_once_with("wwwrun")
    mock_lchown.assert_not_called()
