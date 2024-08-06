"""
Tests that validate the functionality of the module that is responsible for LDAP authentication.
"""

from typing import TYPE_CHECKING

import pytest

import cobbler.settings
from cobbler.api import CobblerAPI
from cobbler.modules.authentication import ldap

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="test_settings")
def fixture_test_settings(
    mocker: "MockerFixture", cobbler_api: CobblerAPI
) -> cobbler.settings.Settings:
    settings = mocker.MagicMock(
        name="ldap_setting_mock", spec=cobbler.settings.Settings
    )
    settings.ldap_server = "localhost"
    settings.ldap_port = 389
    settings.ldap_base_dn = "dc=example,dc=com"
    settings.ldap_search_prefix = "uid="
    settings.ldap_anonymous_bind = True
    settings.ldap_reqcert = "hard"
    settings.ldap_tls_cipher_suite = ""
    settings.ldap_tls_cacertfile = ""
    settings.ldap_tls_keyfile = ""
    settings.ldap_tls_certfile = ""
    settings.ldap_tls_reqcert = "hard"
    return settings


class TestLdap:
    @pytest.mark.parametrize(
        "anonymous_bind, username, password", [(True, "test", "test")]
    )
    def test_anon_bind_positive(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        anonymous_bind: bool,
        username: str,
        password: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_anonymous_bind = anonymous_bind
        test_settings.ldap_tls = False

        # Act
        result = ldap.authenticate(cobbler_api, username, password)

        # Assert
        assert result

    @pytest.mark.parametrize(
        "anonymous_bind, username, password", [(True, "test", "bad")]
    )
    def test_anon_bind_negative(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        anonymous_bind: bool,
        username: str,
        password: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_anonymous_bind = anonymous_bind
        test_settings.ldap_tls = False

        # Act
        result = ldap.authenticate(cobbler_api, username, password)

        # Assert
        assert not result

    @pytest.mark.parametrize(
        "anonymous_bind, bind_user, bind_password, username, password",
        [(False, "uid=user,dc=example,dc=com", "test", "test", "test")],
    )
    def test_user_bind_positive(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        anonymous_bind: bool,
        bind_user: str,
        bind_password: str,
        username: str,
        password: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_anonymous_bind = anonymous_bind
        test_settings.ldap_search_bind_dn = bind_user
        test_settings.ldap_search_passwd = bind_password
        test_settings.ldap_tls = False

        # Act
        result = ldap.authenticate(cobbler_api, username, password)

        # Assert
        assert result

    @pytest.mark.parametrize(
        "anonymous_bind, bind_user, bind_password, username, password",
        [(False, "uid=user,dc=example,dc=com", "bad", "test", "test")],
    )
    def test_user_bind_negative(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        anonymous_bind: bool,
        bind_user: str,
        bind_password: str,
        username: str,
        password: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_anonymous_bind = anonymous_bind
        test_settings.ldap_search_bind_dn = bind_user
        test_settings.ldap_search_passwd = bind_password
        test_settings.ldap_tls = False

        # Act
        result = ldap.authenticate(cobbler_api, username, password)

        # Assert
        assert not result

    @pytest.mark.parametrize(
        "tls_cadir, tls_cert, tls_key",
        [("/etc/ssl/certs", "/etc/ssl/ldap.crt", "/etc/ssl/ldap.key")],
    )
    def test_cadir_positive(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        tls_cadir: str,
        tls_cert: str,
        tls_key: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_tls = True
        test_settings.ldap_tls_cacertdir = tls_cadir
        test_settings.ldap_tls_cacertfile = None  # type: ignore[reportAttributeAccessIssue]
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act
        result = ldap.authenticate(cobbler_api, "test", "test")

        # Assert
        assert result

    @pytest.mark.parametrize(
        "tls_cadir, tls_cert, tls_key",
        [("/etc/ssl/certs", "/etc/ssl/bad.crt", "/etc/ssl/bad.key")],
    )
    def test_cadir_negative(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        tls_cadir: str,
        tls_cert: str,
        tls_key: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_tls = True
        test_settings.ldap_tls_cacertdir = tls_cadir
        test_settings.ldap_tls_cacertfile = None  # type: ignore[reportAttributeAccessIssue]
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act
        result = ldap.authenticate(cobbler_api, "test", "test")

        # Assert
        assert not result

    @pytest.mark.parametrize(
        "tls_cafile, tls_cert, tls_key",
        [("/etc/ssl/ca-slapd.crt", "/etc/ssl/ldap.crt", "/etc/ssl/ldap.key")],
    )
    def test_cafile_positive(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        tls_cafile: str,
        tls_cert: str,
        tls_key: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_tls = True
        test_settings.ldap_tls_cacertdir = None  # type: ignore[reportAttributeAccessIssue]
        test_settings.ldap_tls_cacertfile = tls_cafile
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act
        result = ldap.authenticate(cobbler_api, "test", "test")

        # Assert
        assert result

    @pytest.mark.parametrize(
        "tls_cafile, tls_cert, tls_key",
        [("/etc/ssl/ca-slapd.crt", "/etc/ssl/bad.crt", "/etc/ssl/bad.key")],
    )
    def test_cafile_negative(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        tls_cafile: str,
        tls_cert: str,
        tls_key: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_tls = True
        test_settings.ldap_tls_cacertdir = None  # type: ignore[reportAttributeAccessIssue]
        test_settings.ldap_tls_cacertfile = tls_cafile
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act
        result = ldap.authenticate(cobbler_api, "test", "test")

        # Assert
        assert not result

    @pytest.mark.parametrize(
        "tls_cafile, tls_cert, tls_key",
        [("/etc/ssl/ca-slapd.crt", "/etc/ssl/ldap.crt", "/etc/ssl/ldap.key")],
    )
    def test_ldaps_positive(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        tls_cafile: str,
        tls_cert: str,
        tls_key: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_tls = False
        test_settings.ldap_port = 636
        test_settings.ldap_tls_cacertdir = None  # type: ignore[reportAttributeAccessIssue]
        test_settings.ldap_tls_cacertfile = tls_cafile
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act
        result = ldap.authenticate(cobbler_api, "test", "test")

        # Assert
        assert result

    @pytest.mark.parametrize(
        "tls_cafile, tls_cert, tls_key",
        [("/etc/ssl/ca-slapd.crt", "/etc/ssl/bad.crt", "/etc/ssl/bad.key")],
    )
    def test_ldaps_negative(
        self,
        mocker: "MockerFixture",
        cobbler_api: CobblerAPI,
        test_settings: cobbler.settings.Settings,
        tls_cafile: str,
        tls_cert: str,
        tls_key: str,
    ):
        # Arrange
        mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
        test_settings.ldap_tls = False
        test_settings.ldap_port = 636
        test_settings.ldap_tls_cacertdir = None  # type: ignore[reportAttributeAccessIssue]
        test_settings.ldap_tls_cacertfile = tls_cafile
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act & Assert
        with pytest.raises(ValueError):
            ldap.authenticate(cobbler_api, "test", "test")
