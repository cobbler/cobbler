import pytest

from cobbler.actions import hardlink


def test_object_creation(cobbler_api):
    # Arrange & Act
    result = hardlink.HardLinker(cobbler_api)

    # Assert
    assert isinstance(result, hardlink.HardLinker)
    assert result.hardlink != ""
    assert result.family != ""
    assert result.webdir != ""


def test_constructor_value_error():
    # Act & Assert
    with pytest.raises(ValueError):
        hardlink.HardLinker()


def test_no_hardlink_available(mocker, cobbler_api):
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
            "/usr/bin/hardlink -f -p -o -t -v  /srv/www/cobbler/distro_mirror /srv/www/cobbler/repo_mirror",
        ),
        (
            "suse",
            "/usr/bin/hardlink -f -v  /srv/www/cobbler/distro_mirror /srv/www/cobbler/repo_mirror",
        ),
        (
            "other distros",
            "/usr/bin/hardlink -c -v  /srv/www/cobbler/distro_mirror /srv/www/cobbler/repo_mirror",
        ),
    ],
)
def test_hardlink_cmd(mocker, cobbler_api, mock_family, expected_hardlink_cmd):
    # Arrange
    mocker.patch("cobbler.utils.get_family", return_value=mock_family)

    # Act
    hardlink_obj = hardlink.HardLinker(api=cobbler_api)

    # Assert
    assert expected_hardlink_cmd == hardlink_obj.hardlink_cmd


def test_run(mocker, cobbler_api):
    # Arrange
    hardlink_obj = hardlink.HardLinker(cobbler_api)
    mock_subprocess_call = mocker.patch("cobbler.utils.subprocess_call", return_value=0)
    expected_call = "/usr/bin/hardlink -f -v  /srv/www/cobbler/distro_mirror /srv/www/cobbler/repo_mirror"

    # Act
    hardlink_obj.run()

    # Assert
    mock_subprocess_call.assert_any_call(expected_call, shell=True)
    assert mock_subprocess_call.call_count == 2
