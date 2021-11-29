import pytest
from cobbler.api import CobblerAPI
from cobbler.settings import Settings
from cobbler.modules.authentication import ldap

@pytest.fixture()
def api():
    return CobblerAPI()

class TestLdap:
    @pytest.mark.parametrize("anonymous_bind, username, password", [
        (True, "test", "test")
    ])
    def test_anon_bind_positive(self, api, anonymous_bind, username, password):
        # Arrange
        test_settings = api.settings()
        test_settings.ldap_server = "localhost"
        test_settings.ldap_anonymous_bind = anonymous_bind
        test_settings.ldap_tls = False

        # Act
        result = ldap.authenticate(api, username, password)

        # Assert
        assert result

    @pytest.mark.parametrize("anonymous_bind, username, password", [
        (True, "test", "bad")
    ])
    def test_anon_bind_negative(self, api, anonymous_bind, username, password):
        # Arrange
        test_settings = api.settings()
        test_settings.ldap_server = "localhost"
        test_settings.ldap_anonymous_bind = anonymous_bind
        test_settings.ldap_tls = False

        # Act
        result = ldap.authenticate(api, username, password)

        # Assert
        assert not result

    @pytest.mark.parametrize("anonymous_bind, bind_user, bind_password, username, password", [
        (False, "uid=user,dc=example,dc=com", "test", "test", "test")
    ])
    def test_user_bind_positive(self, api, anonymous_bind, bind_user, bind_password, username, password):
        # Arrange
        test_settings = api.settings()
        test_settings.ldap_server = "localhost"
        test_settings.ldap_anonymous_bind = anonymous_bind
        test_settings.ldap_search_bind_dn = bind_user
        test_settings.ldap_search_passwd = bind_password
        test_settings.ldap_tls = False

        # Act
        result = ldap.authenticate(api, username, password)

        # Assert
        assert result

    @pytest.mark.parametrize("anonymous_bind, bind_user, bind_password, username, password", [
        (False, "uid=user,dc=example,dc=com", "bad", "test", "test")
    ])
    def test_user_bind_negative(self, api, anonymous_bind, bind_user, bind_password, username, password):
        # Arrange
        test_api = CobblerAPI()
        test_settings = api.settings()
        test_settings.ldap_server = "localhost"
        test_settings.ldap_anonymous_bind = anonymous_bind
        test_settings.ldap_search_bind_dn = bind_user
        test_settings.ldap_search_passwd = bind_password
        test_settings.ldap_tls = False

        # Act
        result = ldap.authenticate(api, username, password)

        # Assert
        assert not result

    @pytest.mark.parametrize("tls_ca, tls_cert, tls_key", [
        ("/etc/ssl/ca-slapd.crt",
         "/etc/ssl/ldap.crt",
         "/etc/ssl/ldap.key")
    ])
    def test_tls_positive(self, api, tls_ca, tls_cert, tls_key):
        # Arrange
        test_settings = api.settings()
        test_settings.ldap_server = "localhost"
        test_settings.ldap_base_dn = "dc=example,dc=com"
        test_settings.ldap_anonymous_bind = True
        test_settings.ldap_tls = True
        test_settings.ldap_tls_cacertfile = tls_ca
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act
        result = ldap.authenticate(api, "test", "test")

        # Assert
        assert result

    @pytest.mark.parametrize("tls_ca, tls_cert, tls_key", [
        ("/etc/ssl/ca-slapd.crt",
         "/etc/ssl/bad.crt",
         "/etc/ssl/bad.key")
    ])
    def test_tls_negative(self, api, tls_ca, tls_cert, tls_key):
        # Arrange
        test_settings = api.settings()
        test_settings.ldap_server = "localhost"
        test_settings.ldap_anonymous_bind = True
        test_settings.ldap_tls = True
        test_settings.ldap_tls_cacertfile = tls_ca
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act
        result = ldap.authenticate(api, "test", "test")

        # Assert
        assert not result

    @pytest.mark.parametrize("tls_ca, tls_cert, tls_key", [
        ("/etc/ssl/ca-slapd.crt",
         "/etc/ssl/ldap.crt",
         "/etc/ssl/ldap.key")
    ])
    def test_ldaps_positive(self, api, tls_ca, tls_cert, tls_key):
        # Arrange
        test_settings = api.settings()
        test_settings.ldap_server = "localhost"
        test_settings.ldap_tls = False
        test_settings.ldap_port = 636
        test_settings.ldap_base_dn = "dc=example,dc=com"
        test_settings.ldap_anonymous_bind = True
        test_settings.ldap_tls_cacertfile = tls_ca
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act
        result = ldap.authenticate(api, "test", "test")

        # Assert
        assert result

    @pytest.mark.parametrize("tls_ca, tls_cert, tls_key", [
        ("/etc/ssl/ca-slapd.crt",
         "/etc/ssl/bad.crt",
         "/etc/ssl/bad.key")
    ])
    def test_ldaps_negative(self, api, tls_ca, tls_cert, tls_key):
        # Arrange
        test_settings = api.settings()
        test_settings.ldap_server = "localhost"
        test_settings.ldap_tls = False
        test_settings.ldap_port = 636
        test_settings.ldap_anonymous_bind = True
        test_settings.ldap_tls_cacertfile = tls_ca
        test_settings.ldap_tls_certfile = tls_cert
        test_settings.ldap_tls_keyfile = tls_key

        # Act & Assert
        with pytest.raises(ValueError):
            result = ldap.authenticate(api, "test", "test")
