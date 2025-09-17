"""
Tests that validate the functionality of the module that is responsible for providing repository related functionality.
"""

from typing import TYPE_CHECKING, Any

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.repo import Repo
from cobbler.settings import Settings

from tests.conftest import does_not_raise

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(name="test_settings")
def fixture_test_settings(mocker: "MockerFixture", cobbler_api: CobblerAPI) -> Settings:
    """
    Fixture to allow asserting actions taken on the settings for all repository unit tests.
    """
    settings = mocker.MagicMock(name="repo_setting_mock", spec=cobbler_api.settings())
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_object_creation(cobbler_api: CobblerAPI):
    """
    Test to verify that the Repo object is created correctly.
    """
    # Arrange

    # Act
    repo = Repo(cobbler_api)

    # Arrange
    assert isinstance(repo, Repo)


def test_make_clone(cobbler_api: CobblerAPI):
    """
    Test to verify that cloning the Repo object works as expected.
    """
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    result = repo.make_clone()

    # Assert
    assert result != repo


def test_to_dict(cobbler_api: CobblerAPI):
    """
    Test to verify that the to_dict method works as expected.
    """
    # Arrange
    titem = Repo(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert result.get("proxy") == enums.VALUE_INHERITED


def test_to_dict_resolved(cobbler_api: CobblerAPI):
    """
    Test to verify that the to_dict method with resolved=True works as expected.
    """
    # Arrange
    titem = Repo(cobbler_api)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("proxy") == ""
    assert enums.VALUE_INHERITED not in str(result)


# Properties Tests


def test_mirror(cobbler_api: CobblerAPI):
    """
    Test to verify that the mirror property works as expected.
    """
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.mirror = "https://mymirror.com"

    # Assert
    assert repo.mirror == "https://mymirror.com"


def test_mirror_type(cobbler_api: CobblerAPI):
    """
    Test to verify that the mirror_type property works as expected.
    """
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.mirror_type = enums.MirrorType.BASEURL

    # Assert
    assert repo.mirror_type == enums.MirrorType.BASEURL


def test_keep_updated(cobbler_api: CobblerAPI):
    """
    Test to verify that the keep_updated property works as expected.
    """
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.keep_updated = False

    # Assert
    assert not repo.keep_updated


def test_yumopts(cobbler_api: CobblerAPI):
    """
    Test to verify that the yumopts property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.yumopts = {}

    # Assert
    assert testrepo.yumopts == {}


def test_rsyncopts(cobbler_api: CobblerAPI):
    """
    Test to verify that the rsyncopts property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.rsyncopts = {}

    # Assert
    assert testrepo.rsyncopts == {}


def test_environment(cobbler_api: CobblerAPI):
    """
    Test to verify that the environment property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.environment = {}

    # Assert
    assert testrepo.environment == {}


def test_priority(cobbler_api: CobblerAPI):
    """
    Test to verify that the priority property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.priority = 5

    # Assert
    assert testrepo.priority == 5


def test_rpm_list(cobbler_api: CobblerAPI):
    """
    Test to verify that the rpm_list property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.rpm_list = []

    # Assert
    assert testrepo.rpm_list == []


@pytest.mark.parametrize(
    "input_flags,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        (
            "<<inherit>>",
            does_not_raise(),
            "-c cache -s sha",
        ),  # Result is coming from settings.yaml
        (0, pytest.raises(TypeError), ""),
    ],
)
def test_createrepo_flags(
    cobbler_api: CobblerAPI,
    input_flags: Any,
    expected_exception: Any,
    expected_result: str,
):
    """
    Test to verify that the createrepo_flags property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    with expected_exception:
        testrepo.createrepo_flags = input_flags

        # Assert
        assert testrepo.createrepo_flags == expected_result


def test_breed(cobbler_api: CobblerAPI):
    """
    Test to verify that the breed property works as expected.
    """
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.breed = "yum"  # type: ignore

    # Assert
    assert repo.breed == enums.RepoBreeds.YUM


def test_os_version(cobbler_api: CobblerAPI):
    """
    Test to verify that the os_version property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)
    testrepo.breed = "yum"  # type: ignore

    # Act
    testrepo.os_version = "rhel4"

    # Assert
    assert testrepo.breed == enums.RepoBreeds.YUM
    assert testrepo.os_version == "rhel4"


@pytest.mark.parametrize(
    "value,expected_exception",
    [
        ("x86_64", does_not_raise()),
        (enums.RepoArchs.X86_64, does_not_raise()),
        (enums.Archs.X86_64, pytest.raises(AssertionError)),
        (False, pytest.raises(TypeError)),
        ("", pytest.raises(ValueError)),
    ],
)
def test_arch(cobbler_api: CobblerAPI, value: Any, expected_exception: Any):
    """
    Test to verify that the arch property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    with expected_exception:
        testrepo.arch = value

        # Assert
        if isinstance(value, str):
            assert testrepo.arch.value == value
        else:
            assert testrepo.arch == value


def test_mirror_locally(cobbler_api: CobblerAPI):
    """
    Test to verify that the mirror_locally property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.mirror_locally = False

    # Assert
    assert not testrepo.mirror_locally


def test_apt_components(cobbler_api: CobblerAPI):
    """
    Test to verify that the apt_components property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.apt.components = []

    # Assert
    assert testrepo.apt.components == []


def test_apt_dists(cobbler_api: CobblerAPI):
    """
    Test to verify that the apt_dists property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.apt.dists = []

    # Assert
    assert testrepo.apt.dists == []


@pytest.mark.parametrize(
    "input_proxy,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), ""),
        (0, pytest.raises(TypeError), ""),
    ],
)
def test_proxy(
    cobbler_api: CobblerAPI,
    input_proxy: Any,
    expected_exception: Any,
    expected_result: str,
):
    """
    Test to verify that the proxy property works as expected.
    """
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    with expected_exception:
        testrepo.proxy = input_proxy

        # Assert
        assert testrepo.proxy == expected_result


def test_inheritance(
    mocker: "MockerFixture", cobbler_api: CobblerAPI, test_settings: Settings
):
    """
    Checking that inherited properties are correctly inherited from settings and
    that the <<inherit>> value can be set for them.
    """
    # Arrange
    mocker.patch.object(cobbler_api, "settings", return_value=test_settings)
    testrepo = Repo(cobbler_api)

    # Act
    for key, key_value in testrepo.__dict__.items():
        if key_value == enums.VALUE_INHERITED:
            new_key = key[1:].lower()
            new_value = getattr(testrepo, new_key)
            settings_name = new_key
            if new_key == "owners":
                settings_name = "default_ownership"
            elif new_key == "proxy":
                settings_name = "proxy_url_ext"
            if hasattr(test_settings, f"default_{settings_name}"):
                settings_name = f"default_{settings_name}"
            if hasattr(test_settings, settings_name):
                setting = getattr(test_settings, settings_name)
                if isinstance(setting, str):
                    new_value = "test_inheritance"
                elif isinstance(setting, bool):
                    new_value = True
                elif isinstance(setting, int):
                    new_value = 1
                elif isinstance(setting, float):
                    new_value = 1.0
                elif isinstance(setting, dict):
                    new_value = {"test_inheritance": "test_inheritance"}
                elif isinstance(setting, list):
                    new_value = ["test_inheritance"]
                setattr(test_settings, settings_name, new_value)

            prev_value = getattr(testrepo, new_key)
            setattr(testrepo, new_key, enums.VALUE_INHERITED)

            # Assert
            assert prev_value == new_value
            assert prev_value == getattr(testrepo, new_key)
