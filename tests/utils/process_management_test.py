from cobbler.utils import process_management


def test_is_systemd():
    # Arrange

    # Act
    result = process_management.is_systemd()

    # Assert
    assert result


def test_service_restart_no_manager(mocker):
    # Arrange
    mocker.patch(
        "cobbler.utils.process_management.is_supervisord",
        autospec=True,
        return_value=False,
    )
    mocker.patch(
        "cobbler.utils.process_management.is_systemd", autospec=True, return_value=False
    )
    mocker.patch(
        "cobbler.utils.process_management.is_service", autospec=True, return_value=False
    )

    # Act
    result = process_management.service_restart("testservice")

    # Assert
    assert result == 1


def test_service_restart_supervisord(mocker):
    mocker.patch(
        "cobbler.utils.process_management.is_supervisord",
        autospec=True,
        return_value=True,
    )
    # TODO Mock supervisor API and return value

    # Act
    result = process_management.service_restart("dhcpd")

    # Assert
    assert result == 0


def test_service_restart_systemctl(mocker):
    mocker.patch(
        "cobbler.utils.process_management.is_supervisord",
        autospec=True,
        return_value=False,
    )
    mocker.patch(
        "cobbler.utils.process_management.is_systemd", autospec=True, return_value=True
    )
    subprocess_mock = mocker.patch(
        "cobbler.utils.subprocess_call", autospec=True, return_value=0
    )

    # Act
    result = process_management.service_restart("testservice")

    # Assert
    assert result == 0
    subprocess_mock.assert_called_with(
        ["systemctl", "restart", "testservice"], shell=False
    )


def test_service_restart_service(mocker):
    # Arrange
    mocker.patch(
        "cobbler.utils.process_management.is_supervisord",
        autospec=True,
        return_value=False,
    )
    mocker.patch(
        "cobbler.utils.process_management.is_systemd", autospec=True, return_value=False
    )
    mocker.patch(
        "cobbler.utils.process_management.is_service", autospec=True, return_value=True
    )
    subprocess_mock = mocker.patch(
        "cobbler.utils.subprocess_call", autospec=True, return_value=0
    )

    # Act
    result = process_management.service_restart("testservice")

    # Assert
    assert result == 0
    subprocess_mock.assert_called_with(
        ["service", "testservice", "restart"], shell=False
    )
