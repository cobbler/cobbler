from cobbler.modules.managers import ndjbdns
from cobbler.items.system import NetworkInterface, System


def test_register():
    # Arrange
    # Act
    result = ndjbdns.register()

    # Assert
    assert result == "manage"


def test_get_manager(cobbler_api):
    # Arrange & Act
    result = ndjbdns.get_manager(cobbler_api)

    # Assert
    isinstance(result, ndjbdns._NDjbDnsManager)


def test_manager_what():
    # Arrange & Act & Assert
    assert ndjbdns._NDjbDnsManager.what() == "ndjbdns"


class MockedPopen:
    """
    See https://stackoverflow.com/a/53793739
    """

    def __init__(self, args, **kwargs):
        self.args = args
        self.returncode = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, traceback):
        pass

    def communicate(self, input=None, timeout=None):
        stdout = "output"
        stderr = "error"
        self.returncode = 0

        return stdout, stderr


def test_manager_write_configs(mocker, cobbler_api):
    # Arrange
    mocker.patch("builtins.open", mocker.mock_open(read_data="test"))
    mocker.patch("subprocess.Popen", MockedPopen)
    mock_system = System(cobbler_api)
    mock_system.name = "test_manager_regen_hosts_system"
    mock_system.interfaces = {"default": NetworkInterface(cobbler_api)}
    mock_system.interfaces["default"].dns_name = "host.example.org"
    mock_system.interfaces["default"].mac_address = "aa:bb:cc:dd:ee:ff"
    mock_system.interfaces["default"].ip_address = "192.168.1.2"
    mock_system.interfaces["default"].ipv6_address = "::1"
    ndjbdns.MANAGER = None
    test_manager = ndjbdns.get_manager(cobbler_api)
    test_manager.systems = [mock_system]

    # Act
    test_manager.write_configs()

    # Assert
    test_manager.templar.render.assert_called_once_with(
        "test", {"forward": [("host.example.org", "192.168.1.2")]}, "/etc/ndjbdns/data"
    )
