"""
Test to verify the functionallity of the isc bind module.
"""

from fnmatch import fnmatch
import pathlib
import time
from typing import TYPE_CHECKING, Any, Dict, List, TextIO

import pytest

from cobbler.api import CobblerAPI
from cobbler.modules.managers import bind

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _get_file_and_mode(file, mode='r', *args, **kwargs):
    """
    Helper to extract the file and mode arguments from a call to open(),
    Because it is an actual callable function, it can handle the exact
    same combinations of positional and keyword arguments as open().
    """
    return (file, mode)


class MockFiles:
    """
    Implements a mock filesystem using MockerFixture.
    """

    def __init__(self, mocker: "MockerFixture", files: Dict[str, str]):
        self.mocker = mocker
        self.files = files
        self.real_patterns: List[str] = list()
        self.open_unknown = mocker.mock_open()
        self._real_open = open
        self.patch = mocker.patch("builtins.open", self.open)

    def _is_real(self, path: str) -> bool:
        for pat in self.real_patterns:
            if fnmatch(path, pat):
                return True
        return False

    def open(self, *args: Any, **kwargs: Any) -> TextIO:
        """
        Open a mock file.
        """
        path, mode = _get_file_and_mode(*args, **kwargs)
        if 'r' not in mode:
            return self._real_open(*args, **kwargs)
        open_data = self.files.get(path, self.open_unknown)
        if isinstance(open_data, str):
            open_data = self.mocker.mock_open(read_data=open_data)
            self.files[path] = open_data
        elif open_data == self.open_unknown and self._is_real(path):
            return self._real_open(*args, **kwargs)
        return open_data(*args, **kwargs)


@pytest.fixture(scope="function")
def mock_config_files(mocker: "MockerFixture") -> MockFiles:
    """
    Provide BIND config files for testing.
    """

    files = {
        "/etc/cobbler/named.template":
        """options {
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
""",
        "/etc/cobbler/secondary.template": "garbage",
        "/etc/cobbler/zone.template":
        """\\$TTL 3600
@                       IN      SOA     $cobbler_server. nobody.example.com. (
                                        $serial      ; Serial
                                        86400        ; Refresh (1 day)
                                        7200         ; Retry   (2 hours)
                                        604800       ; Expire  (1 week)
                                        3600         ; TTL     (1 hour)
                                        )

@                       IN      NS      $cobbler_server.

;; CNAMEs
$cname_record

;; Hosts
$host_record
""",
    }
    mock_files = MockFiles(mocker, files)
    mock_files.real_patterns.append("/etc/cobbler/*")
    return mock_files


@pytest.fixture(scope="function", autouse=True)
def reset_singleton():
    """
    Helper fixture to reset the isc singleton before and after a test.
    """
    bind.MANAGER = None
    yield
    bind.MANAGER = None


def test_register():
    """
    Test if the manager registers with the correct ID.
    """
    # Arrange & Act
    result = bind.register()

    # Assert
    assert result == "manage"


def test_manager_what():
    """
    Test if the manager identifies itself correctly.
    """
    # pylint: disable=protected-access
    # Arrange & Act & Assert
    assert bind._BindManager.what() == "bind"  # type: ignore


def test_get_manager(cobbler_api: CobblerAPI):
    """
    Test if the singleton is correctly initialized.
    """
    # pylint: disable=protected-access
    # Arrange & Act
    result = bind.get_manager(cobbler_api)

    # Assert
    isinstance(result, bind._BindManager)  # type: ignore


def test_write_configs(
    mocker: "MockerFixture", cobbler_api: CobblerAPI,
    mock_config_files: MockFiles
):
    """
    Test if the manager is able to correctly write the configuration files.
    """
    # Arrange
    settings = cobbler_api.settings()
    settings.from_dict({
        "server": "cobbler.example.com",
        "manage_dns": True,
        "manage_forward_zones": [ "example.com" ],
        "manage_reverse_zones": [ "192.168.1", "2001:db8:0:1" ],
    })

    manager = bind.get_manager(cobbler_api)

    # Act
    manager.write_configs()

    # Assert
    # TODO: Extend assertions
    mocker.stopall()

    assert open("/var/lib/cobbler/bind_serial").read() == time.strftime("%Y%m%d00")

    def assert_zone_has(path: str, *expect: List[str]) -> None:
        parsed = list(map(
            lambda line: line[:line.find(';')].split(),
            open(path).readlines()))
        for line in expect:
            assert line in parsed

    assert_zone_has(
        "/var/lib/named/example.com",
        ["@", "IN", "SOA", "cobbler.example.com.", "nobody.example.com.", "("],
        ["IN", "NS", "cobbler.example.com."],
    )
    assert_zone_has(
        "/var/lib/named/192.168.1",
        ["@", "IN", "SOA", "cobbler.example.com.", "nobody.example.com.", "("],
        ["IN", "NS", "cobbler.example.com."],
    )
    assert_zone_has(
        "/var/lib/named/2001:0db8:0000:0001",
        ["@", "IN", "SOA", "cobbler.example.com.", "nobody.example.com.", "("],
        ["IN", "NS", "cobbler.example.com."],
    )

    mock_config_files.open_unknown.assert_not_called()


@pytest.mark.skip("Advanced complicated test scenario for now.")
def test_write_configs_zone_template(cobbler_api: CobblerAPI):
    """
    Test to verfiy that writing zone templates via "write_configs()" works as expected.
    """
    # Arrange
    # TODO Mock zone specific template /etc/cobbler/zone_templates/{zone}
    manager = bind.get_manager(cobbler_api)

    # Act
    manager.write_configs()

    # Assert
    # TODO: Mock that template was read
    assert False


@pytest.mark.skip("Advanced complicated test scenario for now.")
def test_chrooted_named(cobbler_api: CobblerAPI):
    """
    Test to verify that a chrooted named can be detected and dealt with.
    """
    # Arrange
    manager = bind.get_manager(cobbler_api)

    # Act
    manager.write_configs()

    # Assert
    # TODO: Assert that correct paths are trying to be written
    assert False


def test_manager_restart_service(mocker: "MockerFixture", cobbler_api: CobblerAPI):
    """
    Test if the manager is able to correctly handle restarting the named server on different distros.
    """
    # Arrange
    manager = bind.get_manager(cobbler_api)
    mocked_service_name = mocker.patch(
        "cobbler.utils.named_service_name", autospec=True, return_value="named"
    )
    mock_service_restart = mocker.patch(
        "cobbler.utils.process_management.service_restart", return_value=0
    )

    # Act
    result = manager.restart_service()

    # Assert
    assert mocked_service_name.call_count == 1
    mock_service_restart.assert_called_with("named")
    assert result == 0
