from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.repo import Repo


def test_object_creation():
    # Arrange
    test_api = CobblerAPI()

    # Act
    repo = Repo(test_api)

    # Arrange
    assert isinstance(repo, Repo)


def test_make_clone():
    # Arrange
    test_api = CobblerAPI()
    repo = Repo(test_api)

    # Act
    result = repo.make_clone()

    # Assert
    assert result != repo


# Properties Tests


def test_mirror():
    # Arrange
    test_api = CobblerAPI()
    repo = Repo(test_api)

    # Act
    repo.mirror = "https://mymirror.com"

    # Assert
    assert repo.mirror == "https://mymirror.com"


def test_mirror_type():
    # Arrange
    test_api = CobblerAPI()
    repo = Repo(test_api)

    # Act
    repo.mirror_type = enums.MirrorType.NONE

    # Assert
    assert repo.mirror_type == enums.MirrorType.NONE


def test_keep_updated():
    # Arrange
    test_api = CobblerAPI()
    repo = Repo(test_api)

    # Act
    repo.keep_updated = False

    # Assert
    assert not repo.keep_updated


def test_yumopts():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.yumopts = {}

    # Assert
    assert testrepo.yumopts == {}


def test_rsyncopts():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.rsyncopts = {}

    # Assert
    assert testrepo.rsyncopts == {}


def test_environment():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.environment = {}

    # Assert
    assert testrepo.environment == {}


def test_priority():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.priority = 5

    # Assert
    assert testrepo.priority == 5


def test_rpm_list():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.rpm_list = []

    # Assert
    assert testrepo.rpm_list == []


def test_createrepo_flags():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.createrepo_flags = {}

    # Assert
    assert testrepo.createrepo_flags == {}


def test_breed():
    # Arrange
    test_api = CobblerAPI()
    repo = Repo(test_api)

    # Act
    repo.breed = "yum"

    # Assert
    assert repo.breed == enums.RepoBreeds.YUM


def test_os_version():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)
    testrepo.breed = "yum"

    # Act
    testrepo.os_version = "rhel4"

    # Assert
    assert testrepo.breed == enums.RepoBreeds.YUM
    assert testrepo.os_version == "rhel4"


def test_arch():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.arch = "x86_64"

    # Assert
    assert testrepo.arch == enums.RepoArchs.X86_64


def test_mirror_locally():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.mirror_locally = False

    # Assert
    assert not testrepo.mirror_locally


def test_apt_components():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.apt_components = []

    # Assert
    assert testrepo.apt_components == []


def test_apt_dists():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.apt_dists = []

    # Assert
    assert testrepo.apt_dists == []


def test_proxy():
    # Arrange
    test_api = CobblerAPI()
    testrepo = Repo(test_api)

    # Act
    testrepo.proxy = ""

    # Assert
    assert testrepo.proxy == ""
