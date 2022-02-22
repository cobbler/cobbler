from unittest.mock import MagicMock

from cobbler.api import CobblerAPI
from cobbler.modules import nsupdate_add_system_post
from cobbler.settings import Settings


def test_register():
    # Arrange & Act
    result = nsupdate_add_system_post.register()

    # Assert
    assert result == "/var/lib/cobbler/triggers/add/system/post/*"


def test_run(mocker):
    # Arrange
    settings_mock = MagicMock(name="nsupdate_add_system_post_setting_mock", spec=Settings)
    settings_mock.nsupdate_enabled = True
    settings_mock.nsupdate_log = "/tmp/nsupdate.log"
    settings_mock.nsupdate_tsig_key = ["example-name", "example-key"]
    settings_mock.nsupdate_tsig_algorithm = "hmac-sha512"
    api = MagicMock(spec=CobblerAPI)
    api.settings.return_value = settings_mock
    args = ["testname"]
    # FIXME realistic return values
    mocker.patch("dns.tsigkeyring.from_text", return_value=True)
    mocker.patch("dns.update.Update", return_value=True)
    mocker.patch("dns.resolver.query", return_value=True)
    mocker.patch("dns.query.tcp", return_value=True)
    mocker.patch("dns.rcode.to_text", return_value=True)

    # Act
    result = nsupdate_add_system_post.run(api, args)

    # Assert
    # FIXME improve assert
    assert result == 0
