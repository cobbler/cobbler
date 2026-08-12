"""
Tests that validate the functionality of the low-level OS/environment detection helpers used to select a
process-management backend.
"""

from typing import TYPE_CHECKING

from cobbler.modules.process_management import detection

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_is_systemd():
    # Arrange

    # Act
    result = detection.is_systemd()

    # Assert
    assert result


def test_is_containerized_dockerenv_present(mocker: "MockerFixture"):
    # Arrange
    mocker.patch(
        "os.path.exists",
        side_effect=lambda path: path == "/.dockerenv",  # type: ignore[reportUnknownLambdaType]
    )
    mocker.patch.dict("os.environ", {}, clear=True)

    # Act
    result = detection.is_containerized()

    # Assert
    assert result is True


def test_is_containerized_container_env_var(mocker: "MockerFixture"):
    # Arrange
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch.dict("os.environ", {"container": "docker"}, clear=True)

    # Act
    result = detection.is_containerized()

    # Assert
    assert result is True


def test_is_containerized_cgroup_docker(mocker: "MockerFixture"):
    # Arrange
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch.dict("os.environ", {}, clear=True)
    mocker.patch(
        "builtins.open",
        mocker.mock_open(
            read_data="12:pids:/docker/abcdef1234567890\n11:cpu:/docker/abcdef1234567890\n"
        ),
    )

    # Act
    result = detection.is_containerized()

    # Assert
    assert result is True


def test_is_containerized_cgroup_containerd(mocker: "MockerFixture"):
    # Arrange
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch.dict("os.environ", {}, clear=True)
    mocker.patch(
        "builtins.open",
        mocker.mock_open(read_data="12:pids:/system.slice/containerd.service\n"),
    )

    # Act
    result = detection.is_containerized()

    # Assert
    assert result is True


def test_is_containerized_no_signals_present(mocker: "MockerFixture"):
    # Arrange
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch.dict("os.environ", {}, clear=True)
    mocker.patch(
        "builtins.open",
        mocker.mock_open(read_data="12:pids:/\n11:cpu:/\n"),
    )

    # Act
    result = detection.is_containerized()

    # Assert
    assert result is False


def test_is_containerized_cgroup_unreadable(mocker: "MockerFixture"):
    """
    A host without /proc/1/cgroup at all (e.g. missing procfs) must not raise - just fall through to False if
    no other signal fired either.
    """
    # Arrange
    mocker.patch("os.path.exists", return_value=False)
    mocker.patch.dict("os.environ", {}, clear=True)
    mocker.patch("builtins.open", side_effect=OSError("No such file or directory"))

    # Act
    result = detection.is_containerized()

    # Assert
    assert result is False
