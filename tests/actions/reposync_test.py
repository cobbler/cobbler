import os
import glob

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.actions.reposync import RepoSync
from cobbler.items.repo import Repo
from cobbler import cexceptions
from tests.conftest import does_not_raise


@pytest.fixture(scope="class")
def api():
    return CobblerAPI()


@pytest.fixture(scope="class")
def reposync(api):
    test_reposync = RepoSync(api, tries=2, nofail=False)
    return test_reposync


@pytest.fixture
def repo(api):
    """
    Creates a Repository "testrepo0" with a keep_updated=True and mirror_locally=True".
    """
    test_repo = Repo(api)
    test_repo.name = "testrepo0"
    test_repo.mirror_locally = True
    test_repo.keep_updated = True
    api.add_repo(test_repo)
    return test_repo


@pytest.fixture
def remove_repo(api):
    """
    Removes the Repository "testrepo0" which can be created with repo.
    """
    yield
    test_repo = api.find_repo("testrepo0")
    if test_repo is not None:
        api.remove_repo(test_repo.name)


class TestRepoSync:
    @pytest.mark.usefixtures("remove_repo")
    @pytest.mark.parametrize(
        "input_mirror_type,input_mirror,expected_exception",
        [
            (
                enums.MirrorType.BASEURL,
                "http://download.fedoraproject.org/pub/fedora/linux/releases/35/Everything/x86_64/os",
                does_not_raise()
            ),
            (
                enums.MirrorType.MIRRORLIST,
                "https://mirrors.fedoraproject.org/mirrorlist?repo=fedora-35&arch=x86_64",
                does_not_raise()
            ),
            (
                enums.MirrorType.METALINK,
                "https://mirrors.fedoraproject.org/metalink?repo=fedora-35&arch=x86_64",
                does_not_raise()
            ),
            (
                enums.MirrorType.BASEURL,
                "http://www.example.com/path/to/some/repo",
                pytest.raises(cexceptions.CX)
            ),
        ],
    )
    def test_reposync_yum(
        self,
        input_mirror_type,
        input_mirror,
        expected_exception,
        api,
        repo,
        reposync
    ):
        # Arrange
        test_repo = repo
        test_repo.breed = enums.RepoBreeds.YUM
        test_repo.mirror = input_mirror
        test_repo.mirror_type = input_mirror_type
        test_repo.rpm_list = "fedora-gpg-keys"
        test_settings = api.settings()
        repo_path = os.path.join(test_settings.webdir, "repo_mirror", test_repo.name)

        # Act & Assert
        with expected_exception:
            reposync.run(test_repo.name)
            result = os.path.exists(repo_path)
            if test_repo.rpm_list and test_repo.rpm_list != []:
                for rpm in test_repo.rpm_list:
                    assert glob.glob(os.path.join(repo_path, "**", rpm) + "*.rpm", recursive=True) != []
            assert result
            # Test that re-downloading the metadata in .origin/repodata will not result in an error
            reposync.run(test_repo.name)

    @pytest.mark.usefixtures("remove_repo")
    @pytest.mark.parametrize(
        "input_mirror_type,input_mirror,input_arch,input_rpm_list,expected_exception",
        [
            (
                enums.MirrorType.BASEURL,
                "http://ftp.debian.org/debian",
                enums.RepoArchs.X86_64,
                "",
                does_not_raise()
            ),
            (
                enums.MirrorType.MIRRORLIST,
                "http://ftp.debian.org/debian",
                enums.RepoArchs.X86_64,
                "",
                pytest.raises(cexceptions.CX)
            ),
            (
                enums.MirrorType.METALINK,
                "http://ftp.debian.org/debian",
                enums.RepoArchs.X86_64,
                "",
                pytest.raises(cexceptions.CX)
            ),
            (
                enums.MirrorType.BASEURL,
                "http://www.example.com/path/to/some/repo",
                enums.RepoArchs.X86_64,
                "",
                pytest.raises(cexceptions.CX)
            ),
            (
                enums.MirrorType.BASEURL,
                "http://ftp.debian.org/debian",
                enums.RepoArchs.NONE,
                "",
                pytest.raises(cexceptions.CX)
            ),
            (
                enums.MirrorType.BASEURL,
                "http://ftp.debian.org/debian",
                enums.RepoArchs.X86_64,
                "dpkg",
                pytest.raises(cexceptions.CX)
            ),
        ],
    )
    def test_reposync_apt(
        self,
        input_mirror_type,
        input_mirror,
        input_arch,
        input_rpm_list,
        expected_exception,
        api,
        repo,
        reposync
    ):
        # Arrange
        test_repo = repo
        test_repo.breed = enums.RepoBreeds.APT
        test_repo.arch = input_arch
        test_repo.apt_components = "main"
        test_repo.apt_dists = "stable"
        test_repo.mirror = input_mirror
        test_repo.mirror_type = input_mirror_type
        test_repo.rpm_list = input_rpm_list
        test_repo.yumopts = "--exclude=.* --include=dpkg.* --no-check-gpg --rsync-extra=none"
        test_settings = api.settings()
        repo_path = os.path.join(test_settings.webdir, "repo_mirror", test_repo.name)

        # Act & Assert
        with expected_exception:
            reposync.run(test_repo.name)
            result = os.path.exists(repo_path)
            for rpm in ["dpkg"]:
                assert glob.glob(os.path.join(repo_path, "**", "dpkg") + "*", recursive=True) != []
            assert result

    @pytest.mark.skip("To flaky and thus not reliable. Needs to be mocked to be of use.")
    @pytest.mark.usefixtures("remove_repo")
    @pytest.mark.parametrize(
        "input_mirror_type,input_mirror,expected_exception",
        [
            (
                enums.MirrorType.BASEURL,
                "http://download.fedoraproject.org/pub/fedora/linux/releases/35/Everything/x86_64/os/Packages/2",
                does_not_raise()
            ),
            (
                enums.MirrorType.MIRRORLIST,
                "http://download.fedoraproject.org/pub/fedora/linux/releases/35/Everything/x86_64/os/Packages/2",
                pytest.raises(cexceptions.CX)
            ),
            (
                enums.MirrorType.METALINK,
                "http://download.fedoraproject.org/pub/fedora/linux/releases/35/Everything/x86_64/os/Packages/2",
                pytest.raises(cexceptions.CX)
            ),
            (
                enums.MirrorType.BASEURL,
                "http://www.example.com/path/to/some/repo",
                pytest.raises(cexceptions.CX)
            ),
        ],
    )
    def test_reposync_wget(
        self,
        input_mirror_type,
        input_mirror,
        expected_exception,
        api,
        repo,
        reposync
    ):
        # Arrange
        test_repo = repo
        test_repo.breed = enums.RepoBreeds.WGET
        test_repo.mirror = input_mirror
        test_repo.mirror_type = input_mirror_type
        test_settings = api.settings()
        repo_path = os.path.join(test_settings.webdir, "repo_mirror", test_repo.name)

        # Act & Assert
        with expected_exception:
            reposync.run(test_repo.name)
            result = os.path.exists(repo_path)
            for rpm in ["rpm"]:
                assert glob.glob(os.path.join(repo_path, "**", "2") + "*", recursive=True) != []
            assert result


@pytest.mark.skip("TODO")
def test_reposync_rhn():
    # Arrange
    # Act
    # Assert
    assert False


@pytest.mark.skip("TODO")
def test_reposync_rsync():
    # Arrange
    # Act
    # Assert
    assert False
