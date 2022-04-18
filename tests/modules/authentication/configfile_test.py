import pytest
import yaml

from cobbler.modules.authentication import configfile


@pytest.fixture(scope="function", autouse=True)
def reset_hashfunction(cobbler_api):
    yield
    cobbler_api.settings().modules.update(
        {
            "authentication": {
                "module": "authentication.configfile",
                "hash_algorithm": "sha3_512",
            }
        }
    )


@pytest.mark.parametrize(
    "hashfunction,test_input,exepcted_output",
    [
        (
            "sha3_512",
            "testtext",
            "eb17eb7a79798b31b3e625f2ff7a5cd05932254ca5f686764e9655274dde03c28ed4a7ab70b0637b5dc97e61da2ee07cc80e0c4f7d00feceb2d74cbe3a579698",
        )
    ],
)
def test_hashfun_positive(cobbler_api, hashfunction, test_input, exepcted_output):
    # Arrange
    cobbler_api.settings().modules.update(
        {"authentication": {"hash_algorithm": hashfunction}}
    )

    # Act
    result = configfile.hashfun(cobbler_api, test_input)

    # Assert
    assert result == exepcted_output


@pytest.mark.parametrize(
    "hashfunction,test_input,exepcted_output", [("md5", "testtext", "")]
)
def test_hashfun_negative(cobbler_api, hashfunction, test_input, exepcted_output):
    # Arrange
    cobbler_api.settings().modules.update(
        {"authentication": {"hash_algorithm": hashfunction}}
    )

    # Act & Assert
    with pytest.raises(ValueError):
        configfile.hashfun(cobbler_api, test_input)


def test_register():
    assert configfile.register() is "authn"


@pytest.mark.parametrize(
    "hashfunction, username, password", [("md5", "cobbler", "cobbler")]
)
def test_authenticate_negative(cobbler_api, hashfunction, username, password):
    # Arrange
    cobbler_api.settings().modules.update(
        {"authentication": {"hash_algorithm": hashfunction}}
    )

    # Act & Assert
    with pytest.raises(ValueError):
        configfile.authenticate(cobbler_api, username, password)


@pytest.mark.parametrize(
    "hashfunction, username, password", [("sha3_512", "cobbler", "cobbler")]
)
def test_authenticate_positive(cobbler_api, hashfunction, username, password):
    # Arrange
    cobbler_api.settings().modules.update(
        {"authentication": {"hash_algorithm": hashfunction}}
    )

    # Act
    result = configfile.authenticate(cobbler_api, username, password)

    # Assert
    assert result
