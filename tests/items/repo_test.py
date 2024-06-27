import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.repo import Repo

from tests.conftest import does_not_raise


@pytest.fixture()
def test_settings(mocker, cobbler_api: CobblerAPI):
    settings = mocker.MagicMock(name="repo_setting_mock", spec=cobbler_api.settings())
    orig = cobbler_api.settings()
    for key in orig.to_dict():
        setattr(settings, key, getattr(orig, key))
    return settings


def test_object_creation(cobbler_api: CobblerAPI):
    # Arrange

    # Act
    repo = Repo(cobbler_api)

    # Arrange
    assert isinstance(repo, Repo)


def test_make_clone(cobbler_api: CobblerAPI):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    result = repo.make_clone()

    # Assert
    assert result != repo


# Properties Tests


def test_mirror(cobbler_api: CobblerAPI):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.mirror = "https://mymirror.com"

    # Assert
    assert repo.mirror == "https://mymirror.com"


def test_mirror_type(cobbler_api: CobblerAPI):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.mirror_type = enums.MirrorType.BASEURL

    # Assert
    assert repo.mirror_type == enums.MirrorType.BASEURL


def test_keep_updated(cobbler_api: CobblerAPI):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.keep_updated = False

    # Assert
    assert not repo.keep_updated


def test_yumopts(cobbler_api: CobblerAPI):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.yumopts = {}

    # Assert
    assert testrepo.yumopts == {}


def test_rsyncopts(cobbler_api: CobblerAPI):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.rsyncopts = {}

    # Assert
    assert testrepo.rsyncopts == {}


def test_environment(cobbler_api: CobblerAPI):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.environment = {}

    # Assert
    assert testrepo.environment == {}


def test_priority(cobbler_api: CobblerAPI):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.priority = 5

    # Assert
    assert testrepo.priority == 5


def test_rpm_list(cobbler_api: CobblerAPI):
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
    cobbler_api: CobblerAPI, input_flags, expected_exception, expected_result
):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    with expected_exception:
        testrepo.createrepo_flags = input_flags

        # Assert
        assert testrepo.createrepo_flags == expected_result


def test_breed(cobbler_api: CobblerAPI):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.breed = "yum"

    # Assert
    assert repo.breed == enums.RepoBreeds.YUM


def test_os_version(cobbler_api: CobblerAPI):
    # Arrange
    testrepo = Repo(cobbler_api)
    testrepo.breed = "yum"

    # Act
    testrepo.os_version = "rhel4"

    # Assert
    assert testrepo.breed == enums.RepoBreeds.YUM
    assert testrepo.os_version == "rhel4"


@pytest.mark.parametrize("value,expected_exception", [
    ("x86_64", does_not_raise()),
    (enums.RepoArchs.X86_64, does_not_raise()),
    (enums.Archs.X86_64, pytest.raises(AssertionError)),
    (False, pytest.raises(TypeError)),
    ("", pytest.raises(ValueError))
])
def test_arch(cobbler_api: CobblerAPI, value, expected_exception):
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
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.mirror_locally = False

    # Assert
    assert not testrepo.mirror_locally


def test_apt_components(cobbler_api: CobblerAPI):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.apt_components = []

    # Assert
    assert testrepo.apt_components == []


def test_apt_dists(cobbler_api: CobblerAPI):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.apt_dists = []

    # Assert
    assert testrepo.apt_dists == []


@pytest.mark.parametrize(
    "input_proxy,expected_exception,expected_result",
    [
        ("", does_not_raise(), ""),
        ("<<inherit>>", does_not_raise(), ""),
        (0, pytest.raises(TypeError), ""),
    ],
)
def test_proxy(cobbler_api: CobblerAPI, input_proxy, expected_exception, expected_result):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    with expected_exception:
        testrepo.proxy = input_proxy

        # Assert
        assert testrepo.proxy == expected_result


def test_inheritance(mocker, cobbler_api: CobblerAPI, test_settings):
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
