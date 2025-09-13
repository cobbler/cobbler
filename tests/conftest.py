"""
Fixtures that are shared between all tests inside the testsuite.
"""

import logging
import os
import pathlib
import shutil
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Generator

import pytest

from cobbler.api import CobblerAPI
from cobbler.cobbler_collections.manager import CollectionManager
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.menu import Menu
from cobbler.items.profile import Profile
from cobbler.items.system import System

logger = logging.getLogger()


@contextmanager
def does_not_raise():
    """
    Fixture that represents a context manager that will expect that no raise occurs.
    """
    yield


@pytest.fixture(name="os_setup", scope="session", autouse=True)
def fixture_os_setup():
    """
    Fixture to setup the environment for integration tests.
    """
    server = "192.168.1.1"
    bridge = "pxe"
    etc_qemu = (
        "/etc/qemu-kvm" if pathlib.Path("/etc/qemu-kvm").exists() else "/etc/qemu"
    )
    subprocess.run(
        f"ip link add {bridge} type bridge && ip address add {server}/24 dev {bridge} && ip link set up dev {bridge}",
        shell=True,
        check=True,
    )
    pathlib.Path(etc_qemu).mkdir(exist_ok=True)
    subprocess.run(
        f"echo allow {bridge} >>{etc_qemu}/bridge.conf",
        shell=True,
        check=True,
    )
    yield
    subprocess.run(f"ip link delete {bridge}", shell=True, check=True)


@pytest.fixture(name="cobbler_api", scope="function")
def fixture_cobbler_api() -> CobblerAPI:
    """
    Fixture that represents the Cobbler API for a single test.
    """
    # pylint: disable=protected-access
    CollectionManager._CollectionManager__shared_state.clear()  # type: ignore
    CollectionManager.has_loaded = False
    CobblerAPI._CobblerAPI__shared_state.clear()  # type: ignore
    CobblerAPI._CobblerAPI__has_loaded = False  # type: ignore
    return CobblerAPI()


@pytest.fixture(name="reset_settings_yaml", scope="function", autouse=True)
def fixture_reset_settings_yaml() -> Generator[None, None, None]:
    """
    Fixture that automatically resets the settings YAML after every test.
    """
    settings = pathlib.Path("/etc/cobbler/settings.yaml")
    backup_settings = pathlib.Path("/etc/cobbler/settings.yaml.bak")
    integration_test_settings = pathlib.Path(
        "/code/tests/integration/data/settings.yaml"
    )
    settings.rename("/etc/cobbler/settings.yaml.bak")
    shutil.copy(integration_test_settings, "/etc/cobbler/settings.yaml")
    yield
    pathlib.Path("/etc/cobbler/settings.yaml").unlink()
    backup_settings.rename("/etc/cobbler/settings.yaml")


@pytest.fixture(name="create_testfile", scope="function")
def fixture_create_testfile(tmp_path: pathlib.Path):
    """
    Fixture that provides a method to create an arbitrary file inside the folder specifically for a single test.
    """

    def _create_testfile(filename: str) -> str:
        path = os.path.join(tmp_path, filename)
        if not os.path.exists(path):
            Path(path).touch()
        return path

    return _create_testfile


@pytest.fixture(name="create_kernel_initrd", scope="function")
def fixture_create_kernel_initrd(create_testfile: Callable[[str], None]):
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
    Returns a function which has the distro name as an argument. The function returns a distro object.
    """

    def _create_distro(name: str = "", with_add: bool = True) -> Distro:
        test_folder = create_kernel_initrd(fk_kernel, fk_initrd)
        test_distro = cobbler_api.new_distro()
        test_distro.name = (  # type: ignore[method-assign]
            request.node.originalname  # type: ignore
            if request.node.originalname  # type: ignore
            else request.node.name  # type: ignore
        )
        if name != "":
            test_distro.name = name  # type: ignore[method-assign]
        test_distro.kernel = os.path.join(test_folder, fk_kernel)  # type: ignore
        test_distro.initrd = os.path.join(test_folder, fk_initrd)  # type: ignore
        print(test_distro.boot_loaders)
        if with_add:
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
        distro_uid: str = "", profile_uid: str = "", name: str = ""
    ) -> Profile:
        test_profile = cobbler_api.new_profile()
        test_profile.name = (  # type: ignore[method-assign]
            request.node.originalname  # type: ignore
            if request.node.originalname  # type: ignore
            else request.node.name  # type: ignore
        )
        if name != "":
            test_profile.name = name  # type: ignore[method-assign]
        if profile_uid == "":
            test_profile.distro = distro_uid  # type: ignore
        else:
            test_profile.parent = profile_uid  # type: ignore
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
        test_image.name = (  # type: ignore[method-assign]
            request.node.originalname  # type: ignore
            if request.node.originalname  # type: ignore
            else request.node.name  # type: ignore
        )
        if name != "":
            test_image.name = name  # type: ignore[method-assign]
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
        profile_uid: str = "", image_uid: str = "", name: str = ""
    ) -> System:
        test_system = cobbler_api.new_system()
        if name == "":
            test_system.name = (  # type: ignore[method-assign]
                request.node.originalname  # type: ignore
                if request.node.originalname  # type: ignore
                else request.node.name  # type: ignore
            )
        else:
            test_system.name = name  # type: ignore[method-assign]
        if profile_uid != "":
            test_system.profile = profile_uid  # type: ignore
        if image_uid != "":
            test_system.image = image_uid  # type: ignore
        cobbler_api.add_system(test_system)
        test_system_default_interface = cobbler_api.new_network_interface(
            system_uid=test_system.uid, name="default"
        )
        test_system_default_interface.name = "default"  # type: ignore[method-assign]
        cobbler_api.add_network_interface(test_system_default_interface)
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
            test_menu.name = (  # type: ignore[method-assign]
                request.node.originalname  # type: ignore
                if request.node.originalname  # type: ignore
                else request.node.name  # type: ignore
            )

        test_menu.display_name = display_name  # type: ignore

        cobbler_api.add_menu(test_menu)
        return test_menu

    return _create_menu


@pytest.fixture(scope="function", autouse=True)
def cleanup_leftover_items():
    """
    Will delete all JSON files which are left in Cobbler before a testrun!
    """
    collection_path = pathlib.Path("/var/lib/cobbler/collections")
    cobbler_collections = [
        "distros",
        "images",
        "menus",
        "profiles",
        "repos",
        "systems",
        "network_interfaces",
    ]
    for collection in cobbler_collections:
        path = collection_path / collection
        for file in path.iterdir():
            file.unlink()
            logger.info(f"Deleted {str(file)}")


@pytest.fixture(name="fk_initrd", scope="function")
def fixture_fk_initrd(request: "pytest.FixtureRequest") -> str:
    """
    The path to the first fake initrd.

    :return: A filename as a string.
    """
    return "initrd_%s.img" % (
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )


@pytest.fixture(name="fk_kernel", scope="function")
def fixture_fk_kernel(request: "pytest.FixtureRequest") -> str:
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
