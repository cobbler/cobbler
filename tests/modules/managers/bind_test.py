import time
from typing import TYPE_CHECKING, Any

import pytest

from cobbler.api import CobblerAPI
from cobbler.modules.managers import bind

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(scope="function")
def named_template() -> str:
    """
    This provides a minmal test templated for named that is close to the real one.
    """
    return """options {
          listen-on port 53 { 127.0.0.1; };
          directory       "@@bind_zonefiles@@";
          dump-file       "@@bind_zonefiles@@/data/cache_dump.db";
          statistics-file "@@bind_zonefiles@@/data/named_stats.txt";
          memstatistics-file "@@bind_zonefiles@@/data/named_mem_stats.txt";
          allow-query     { localhost; };
          recursion yes;
};

#for $zone in $forward_zones
zone "${zone}." {
    type master;
    file "$zone";
};

#end for
#for $zone, $arpa in $reverse_zones
zone "${arpa}." {
    type master;
    file "$zone";
};

#end for
"""


def test_register():
    # Arrange & Act
    result = bind.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    # Arrange & Act & Assert
    assert bind._BindManager.what() == "bind"


def test_get_manager(cobbler_api: CobblerAPI):
    # Arrange & Act
    result = bind.get_manager(cobbler_api)

    # Assert
    isinstance(result, bind._BindManager)


def test_manager_write_configs(mocker: "MockerFixture", cobbler_api: CobblerAPI, named_template: str):
    # Arrange
    open_mock = mocker.mock_open()
    mock_named_template = mocker.mock_open(read_data=named_template)
    mock_secondary_template = mocker.mock_open(read_data="garbage")
    mock_zone_template = mocker.mock_open(read_data="garbage 2")
    mock_bind_serial = mocker.mock_open()
    mock_etc_named_conf = mocker.mock_open()
    mock_etc_secondary_conf = mocker.mock_open()

    def mock_open(*args: Any, **kwargs: Any):
        if args[0] == "/etc/cobbler/named.template":
            return mock_named_template(*args, **kwargs)
        if args[0] == "/etc/cobbler/secondary.template":
            return mock_secondary_template(*args, **kwargs)
        if args[0] == "/etc/cobbler/zone.template":
            return mock_zone_template(*args, **kwargs)
        if args[0] == "/var/lib/cobbler/bind_serial":
            return mock_bind_serial(*args, **kwargs)
        if args[0] == "/etc/named.conf":
            return mock_etc_named_conf(*args, **kwargs)
        if args[0] == "/etc/secondary.conf":
            return mock_etc_secondary_conf(*args, **kwargs)
        return open_mock(*args, **kwargs)

    mocker.patch("builtins.open", mock_open)
    manager = bind.get_manager(cobbler_api)
    # TODO Mock settings for manage_dns and forward/reverse zones

    # Act
    manager.write_configs()

    # Assert
    # TODO: Extend assertions
    mock_bind_serial.assert_any_call(
        "/var/lib/cobbler/bind_serial", "r", encoding="UTF-8"
    )
    mock_bind_serial_handle = mock_bind_serial()
    mock_bind_serial_handle.write.assert_any_call(time.strftime("%Y%m%d00"))
    open_mock.assert_not_called()


def test_manager_restart_service(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    # Arrange
    manager = bind.get_manager(cobbler_api)
    mocked_service_name = mocker.patch(
        "cobbler.utils.named_service_name", autospec=True, return_value="named"
    )
    mock_service_restart = mocker.patch(
        "cobbler.utils.subprocess_call", return_value=0
    )

    # Act
    result = manager.restart_service()

    # Assert
    assert mocked_service_name.call_count == 1
    mock_service_restart.assert_called_with(["service", "named", "restart"], shell=False)
    assert result == 0
