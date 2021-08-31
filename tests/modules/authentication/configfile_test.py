import pytest

from cobbler.modules.authentication import configfile


@pytest.fixture(scope="function")
def adjust_hashfunction():
    def _adjust_hashfunction(hashfunction):
        modulesconf = "/etc/cobbler/modules.conf"
        with open(modulesconf, 'r') as file:
            data = file.readlines()

        print(data[6])
        data[6] = "hash_algorithm = %s\n" % hashfunction
        print(data[6])

        with open(modulesconf, 'w') as file:
            file.writelines(data)
    return _adjust_hashfunction


class TestConfigfile:

    @pytest.mark.parametrize("hashfunction,test_input,exepcted_output", [
        ("sha3_512", "testtext", "eb17eb7a79798b31b3e625f2ff7a5cd05932254ca5f686764e9655274dde03c28ed4a7ab70b0637b5dc97e61da2ee07cc80e0c4f7d00feceb2d74cbe3a579698")
    ])
    def test_hashfun_positive(self, adjust_hashfunction, hashfunction, test_input, exepcted_output):
        # Arrange
        adjust_hashfunction(hashfunction)

        # Act
        result = configfile.hashfun(test_input)

        # Assert
        assert result == exepcted_output

    @pytest.mark.parametrize("hashfunction,test_input,exepcted_output", [
        ("md5", "testtext", "")
    ])
    def test_hashfun_negative(self, adjust_hashfunction, hashfunction, test_input, exepcted_output):
        # Arrange
        adjust_hashfunction(hashfunction)

        # Act & Assert
        with pytest.raises(ValueError):
            configfile.hashfun(test_input)

    def test_register(self):
        assert configfile.register() is "authn"

    @pytest.mark.parametrize("hashfunction, username, password", [
        ("md5", "cobbler", "cobbler")
    ])
    def test_authenticate_negative(self, adjust_hashfunction, hashfunction, username, password):
        # Arrange
        adjust_hashfunction(hashfunction)

        # Act & Assert
        with pytest.raises(ValueError):
            configfile.authenticate(None, username, password)

    @pytest.mark.parametrize("hashfunction, username, password", [
        ("sha3_512", "cobbler", "cobbler")
    ])
    def test_authenticate_positive(self, adjust_hashfunction, hashfunction, username, password):
        # Arrange
        adjust_hashfunction(hashfunction)

        # Act
        result = configfile.authenticate(None, username, password)

        # Assert
        assert result
