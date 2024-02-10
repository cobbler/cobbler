"""
Fixtures that are shared between all tests inside the testsuite.
"""

import os
import pathlib
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.menu import Menu
from cobbler.items.network_interface import NetworkInterface
from cobbler.items.profile import Profile
from cobbler.items.system import System


@contextmanager
def does_not_raise():
    """
    Fixture that represents a context manager that will expect that no raise occurs.
    """
    yield


@pytest.fixture(scope="function")
def cobbler_api() -> CobblerAPI:
    """
    Fixture that represents the Cobbler API for a single test.
    """
    # pylint: disable=protected-access
    CobblerAPI.__shared_state = {}  # type: ignore
    CobblerAPI.__has_loaded = False  # type: ignore
    return CobblerAPI()


@pytest.fixture(scope="function", autouse=True)
def reset_settings_yaml(tmp_path: pathlib.Path):
    """
    Fixture that automatically resets the settings YAML after every test.
    """
    filename = "settings.yaml"
    filepath = "/etc/cobbler/%s" % filename
    shutil.copy(filepath, tmp_path.joinpath(filename))
    yield
    shutil.copy(tmp_path.joinpath(filename), filepath)


@pytest.fixture(scope="function", autouse=True)
def reset_items(cobbler_api: CobblerAPI):
    """
    Fixture that deletes all items automatically after every test.
    """
    for system in cobbler_api.systems():
        cobbler_api.remove_system(system.name)
    for image in cobbler_api.images():
        cobbler_api.remove_image(image.name)
    for profile in cobbler_api.profiles():
        cobbler_api.remove_profile(profile.name)
    for distro in cobbler_api.distros():
        cobbler_api.remove_distro(distro.name)
    for repo in cobbler_api.repos():
        cobbler_api.remove_repo(repo.name)
    for menu in cobbler_api.menus():
        cobbler_api.remove_menu(menu.name)


@pytest.fixture(scope="function")
def create_testfile(tmp_path: pathlib.Path):
    """
    Fixture that provides a method to create an arbitrary file inside the folder specifically for a single test.
    """

    def _create_testfile(filename: str) -> str:
        path = os.path.join(tmp_path, filename)
        if not os.path.exists(path):
            Path(path).touch()
        return path

    return _create_testfile


@pytest.fixture(scope="function")
def create_kernel_initrd(create_testfile: Callable[[str], None]):
    """
    Creates a kernel and initrd pair in the folder for the current test.
    """

    def _create_kernel_initrd(name_kernel: str, name_initrd: str) -> str:
        create_testfile(name_kernel)
        return os.path.dirname(create_testfile(name_initrd))  # type: ignore

    return _create_kernel_initrd


@pytest.fixture(scope="function")
def create_distro(
    request: "pytest.FixtureRequest",
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Returns a function which has the distro name as an argument. The function returns a distro object. The distro is
    already added to the CobblerAPI.
    """

    def _create_distro(name: str = "") -> Distro:
        test_folder = create_kernel_initrd(fk_kernel, fk_initrd)
        test_distro = cobbler_api.new_distro()
        test_distro.name = (
            request.node.originalname  # type: ignore
            if request.node.originalname  # type: ignore
            else request.node.name
        )
        if name != "":
            test_distro.name = name
        test_distro.kernel = os.path.join(test_folder, fk_kernel)
        test_distro.initrd = os.path.join(test_folder, fk_initrd)
        cobbler_api.add_distro(test_distro)
        return test_distro

    return _create_distro


@pytest.fixture(scope="function")
def create_profile(request: "pytest.FixtureRequest", cobbler_api: CobblerAPI):
    """
    Returns a function which has the distro or profile name as an argument. The function returns a profile object. The profile is
    already added to the CobblerAPI.
    """

    def _create_profile(
        distro_name: str = "", profile_name: str = "", name: str = ""
    ) -> Profile:
        test_profile = cobbler_api.new_profile()
        test_profile.name = (
            request.node.originalname  # type: ignore
            if request.node.originalname  # type: ignore
            else request.node.name
        )
        if name != "":
            test_profile.name = name
        if profile_name == "":
            test_profile.distro = distro_name
        else:
            test_profile.parent = profile_name
        cobbler_api.add_profile(test_profile)
        return test_profile

    return _create_profile


@pytest.fixture(scope="function")
def create_image(request: "pytest.FixtureRequest", cobbler_api: CobblerAPI):
    """
    Returns a function which has the image name as an argument. The function returns an image object. The image is already added to the
    CobblerAPI.
    """

    def _create_image(name: str = "") -> Image:
        test_image = cobbler_api.new_image()
        test_image.name = (
            request.node.originalname  # type: ignore
            if request.node.originalname  # type: ignore
            else request.node.name
        )
        if name != "":
            test_image.name = name
        cobbler_api.add_image(test_image)
        return test_image

    return _create_image


@pytest.fixture(scope="function")
def create_system(request: "pytest.FixtureRequest", cobbler_api: CobblerAPI):
    """
    Returns a function which has the profile name as an argument. The function returns a system object. The system is
    already added to the CobblerAPI.
    """

    def _create_system(
        profile_name: str = "", image_name: str = "", name: str = ""
    ) -> System:
        test_system = cobbler_api.new_system()
        if name == "":
            test_system.name = (
                request.node.originalname  # type: ignore
                if request.node.originalname  # type: ignore
                else request.node.name
            )
        else:
            test_system.name = name
        if profile_name != "":
            test_system.profile = profile_name
        if image_name != "":
            test_system.image = image_name
        test_system.interfaces = {"default": NetworkInterface(cobbler_api)}
        cobbler_api.add_system(test_system)
        return test_system

    return _create_system


@pytest.fixture(scope="function")
def create_menu(request: "pytest.FixtureRequest", cobbler_api: CobblerAPI):
    """
    Returns a function which has the profile name as an argument. The function returns a system object. The system is
    already added to the CobblerAPI.
    """

    def _create_menu(name: str = "", display_name: str = "") -> Menu:
        test_menu = cobbler_api.new_menu()

        if name == "":
            test_menu.name = (
                request.node.originalname  # type: ignore
                if request.node.originalname  # type: ignore
                else request.node.name
            )

        test_menu.display_name = display_name

        cobbler_api.add_menu(test_menu)
        return test_menu

    return _create_menu


@pytest.fixture(scope="function", autouse=True)
def cleanup_leftover_items():
    """
    Will delete all JSON files which are left in Cobbler before a testrun!
    """
    cobbler_collections = [
        "distros",
        "images",
        "menus",
        "profiles",
        "repos",
        "systems",
    ]
    for collection in cobbler_collections:
        path = os.path.join("/var/lib/cobbler/collections", collection)
        for file in os.listdir(path):
            json_file = os.path.join(path, file)
            os.remove(json_file)


@pytest.fixture(scope="function")
def fk_initrd(request: "pytest.FixtureRequest") -> str:
    """
    The path to the first fake initrd.

    :return: A filename as a string.
    """
    return "initrd_%s.img" % (
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )


@pytest.fixture(scope="function")
def fk_kernel(request: "pytest.FixtureRequest") -> str:
    """
    The path to the first fake kernel.

    :return: A path as a string.
    """
    return "vmlinuz_%s" % (
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )


@pytest.fixture(scope="function")
def redhat_autoinstall() -> str:
    """
    The path to the test.ks file for redhat autoinstall.

    :return: A path as a string.
    """
    return "test.ks"


@pytest.fixture(scope="function")
def suse_autoyast() -> str:
    """
    The path to the suse autoyast xml-file.
    :return: A path as a string.
    """
    return "test.xml"


@pytest.fixture(scope="function")
def ubuntu_preseed() -> str:
    """
    The path to the ubuntu preseed file.
    :return: A path as a string.
    """
    return "test.seed"
