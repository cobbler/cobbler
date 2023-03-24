import pytest

from cobbler import enums
from cobbler.items.repo import Repo

from tests.conftest import does_not_raise


def test_object_creation(cobbler_api):
    # Arrange

    # Act
    repo = Repo(cobbler_api)

    # Arrange
    assert isinstance(repo, Repo)


def test_make_clone(cobbler_api):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    result = repo.make_clone()

    # Assert
    assert result != repo


def test_to_dict(cobbler_api):
    # Arrange
    titem = Repo(cobbler_api)

    # Act
    result = titem.to_dict()

    # Assert
    assert isinstance(result, dict)
    assert result.get("proxy") == enums.VALUE_INHERITED


def test_to_dict_resolved(cobbler_api):
    # Arrange
    titem = Repo(cobbler_api)

    # Act
    result = titem.to_dict(resolved=True)

    # Assert
    assert isinstance(result, dict)
    assert result.get("proxy") == ""
    assert enums.VALUE_INHERITED not in str(result)


# Properties Tests


def test_mirror(cobbler_api):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.mirror = "https://mymirror.com"

    # Assert
    assert repo.mirror == "https://mymirror.com"


def test_mirror_type(cobbler_api):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.mirror_type = enums.MirrorType.BASEURL

    # Assert
    assert repo.mirror_type == enums.MirrorType.BASEURL


def test_keep_updated(cobbler_api):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.keep_updated = False

    # Assert
    assert not repo.keep_updated


def test_yumopts(cobbler_api):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.yumopts = {}

    # Assert
    assert testrepo.yumopts == {}


def test_rsyncopts(cobbler_api):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.rsyncopts = {}

    # Assert
    assert testrepo.rsyncopts == {}


def test_environment(cobbler_api):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.environment = {}

    # Assert
    assert testrepo.environment == {}


def test_priority(cobbler_api):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.priority = 5

    # Assert
    assert testrepo.priority == 5


def test_rpm_list(cobbler_api):
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
    cobbler_api, input_flags, expected_exception, expected_result
):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    with expected_exception:
        testrepo.createrepo_flags = input_flags

        # Assert
        assert testrepo.createrepo_flags == expected_result


def test_breed(cobbler_api):
    # Arrange
    repo = Repo(cobbler_api)

    # Act
    repo.breed = "yum"

    # Assert
    assert repo.breed == enums.RepoBreeds.YUM


def test_os_version(cobbler_api):
    # Arrange
    testrepo = Repo(cobbler_api)
    testrepo.breed = "yum"

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
def test_arch(cobbler_api, value, expected_exception):
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


def test_mirror_locally(cobbler_api):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.mirror_locally = False

    # Assert
    assert not testrepo.mirror_locally


def test_apt_components(cobbler_api):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    testrepo.apt_components = []

    # Assert
    assert testrepo.apt_components == []


def test_apt_dists(cobbler_api):
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
def test_proxy(cobbler_api, input_proxy, expected_exception, expected_result):
    # Arrange
    testrepo = Repo(cobbler_api)

    # Act
    with expected_exception:
        testrepo.proxy = input_proxy

        # Assert
        assert testrepo.proxy == expected_result
