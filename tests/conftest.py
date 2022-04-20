import os
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System


@contextmanager
def does_not_raise():
    yield


@pytest.fixture(scope="function")
def cobbler_api() -> CobblerAPI:
    CobblerAPI.__shared_state = {}
    CobblerAPI.__has_loaded = False
    return CobblerAPI()


@pytest.fixture(scope="function", autouse=True)
def reset_settings_yaml(tmp_path):
    filename = "settings.yaml"
    filepath = "/etc/cobbler/%s" % filename
    shutil.copy(filepath, tmp_path.joinpath(filename))
    yield
    shutil.copy(tmp_path.joinpath(filename), filepath)


@pytest.fixture(scope="function", autouse=True)
def reset_items(cobbler_api):
    for system in cobbler_api.systems():
        cobbler_api.remove_system(system.name)
    for image in cobbler_api.images():
        cobbler_api.remove_distro(image.name)
    for profile in cobbler_api.profiles():
        cobbler_api.remove_profile(profile.name)
    for distro in cobbler_api.distros():
        cobbler_api.remove_distro(distro.name)
    for package in cobbler_api.packages():
        cobbler_api.remove_package(package.name)
    for repo in cobbler_api.repos():
        cobbler_api.remove_repo(repo.name)
    for mgmtclass in cobbler_api.mgmtclasses():
        cobbler_api.remove_mgmtclass(mgmtclass.name)
    for file in cobbler_api.files():
        cobbler_api.remove_file(file.name)
    for menu in cobbler_api.menus():
        cobbler_api.remove_menu(menu.name)


@pytest.fixture(scope="function")
def create_testfile(tmp_path):
    def _create_testfile(filename):
        path = os.path.join(tmp_path, filename)
        if not os.path.exists(path):
            Path(path).touch()
        return path
    return _create_testfile


@pytest.fixture(scope="function")
def create_kernel_initrd(create_testfile):
    def _create_kernel_initrd(name_kernel, name_initrd):
        create_testfile(name_kernel)
        return os.path.dirname(create_testfile(name_initrd))
    return _create_kernel_initrd


@pytest.fixture(scope="function")
def create_distro(request, cobbler_api, create_kernel_initrd, fk_kernel, fk_initrd):
    """
    Returns a function which has no arguments. The function returns a distro object. The distro is already added to
    the CobblerAPI.
    """

    def _create_distro():
        test_folder = create_kernel_initrd(fk_kernel, fk_initrd)
        test_distro = Distro(cobbler_api)
        test_distro.name = request.node.originalname
        test_distro.kernel = os.path.join(test_folder, fk_kernel)
        test_distro.initrd = os.path.join(test_folder, fk_initrd)
        cobbler_api.add_distro(test_distro)
        return test_distro

    return _create_distro


@pytest.fixture(scope="function")
def create_profile(request, cobbler_api):
    """
    Returns a function which has the distro name as an argument. The function returns a profile object. The profile is
    already added to the CobblerAPI.
    """

    def _create_profile(distro_name):
        test_profile = Profile(cobbler_api)
        test_profile.name = request.node.originalname
        test_profile.distro = distro_name
        cobbler_api.add_profile(test_profile)
        return test_profile

    return _create_profile


@pytest.fixture(scope="function")
def create_system(request, cobbler_api):
    """
    Returns a function which has the profile name as an argument. The function returns a system object. The system is
    already added to the CobblerAPI.
    """

    def _create_system(profile_name="", image_name=""):
        test_system = System(cobbler_api)
        test_system.name = request.node.originalname
        if profile_name != "":
            test_system.profile = profile_name
        if image_name != "":
            test_system.image = image_name
        cobbler_api.add_system(test_system)
        return test_system

    return _create_system


@pytest.fixture(scope="function", autouse=True)
def cleanup_leftover_items():
    """
    Will delete all JSON files which are left in Cobbler before a testrun!
    """
    cobbler_collections = ["distros", "files", "images", "menus", "mgmtclasses", "packages", "profiles", "repos",
                           "systems"]
    for collection in cobbler_collections:
        path = os.path.join("/var/lib/cobbler/collections", collection)
        for file in os.listdir(path):
            json_file = os.path.join(path, file)
            os.remove(json_file)


@pytest.fixture(scope="function")
def fk_initrd(request):
    """
    The path to the first fake initrd.

    :return: A filename as a string.
    """
    return "initrd_%s.img" % request.node.originalname


@pytest.fixture(scope="function")
def fk_kernel(request):
    """
    The path to the first fake kernel.

    :return: A path as a string.
    """
    return "vmlinuz_%s" % request.node.originalname


@pytest.fixture(scope="function")
def redhat_autoinstall():
    """
    The path to the test.ks file for redhat autoinstall.

    :return: A path as a string.
    """
    return "test.ks"


@pytest.fixture(scope="function")
def suse_autoyast():
    """
    The path to the suse autoyast xml-file.
    :return: A path as a string.
    """
    return "test.xml"


@pytest.fixture(scope="function")
def ubuntu_preseed():
    """
    The path to the ubuntu preseed file.
    :return: A path as a string.
    """
    return "test.seed"
