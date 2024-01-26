"""
Fixtures that are shared by the XML-RPC tests that are in the "xmlrpcapi" module.
"""

import os
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Tuple, Union

import pytest

from cobbler.api import CobblerAPI
from cobbler.remote import CobblerXMLRPCInterface
from cobbler.utils import get_shared_secret


@pytest.fixture(scope="function")
def remote(
    cobbler_xmlrpc_base: Tuple[CobblerXMLRPCInterface, str]
) -> CobblerXMLRPCInterface:
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[0]


@pytest.fixture(scope="function")
def token(cobbler_xmlrpc_base: Tuple[CobblerXMLRPCInterface, str]) -> str:
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[1]


@pytest.fixture(scope="function")
def cobbler_xmlrpc_base(cobbler_api: CobblerAPI) -> Tuple[CobblerXMLRPCInterface, str]:
    """
    Initialises the api object and makes it available to the test.
    """
    # create XML-RPC client and connect to server
    remote = CobblerXMLRPCInterface(cobbler_api)
    shared_secret = get_shared_secret()
    token = remote.login("", shared_secret)  # type: ignore
    if not token:
        sys.exit(1)
    return remote, token


@pytest.fixture(scope="function")
def testsnippet() -> str:
    """
    Fixture that provides a valid minimalistic Cobbler Snippet.
    """
    return "# This is a small simple testsnippet!"


@pytest.fixture(scope="function")
def snippet_add(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[str, str], None]:
    """
    Fixture that adds a snippet to Cobbler.
    """

    def _snippet_add(name: str, data: str) -> None:
        remote.write_autoinstall_snippet(name, data, token)

    return _snippet_add


@pytest.fixture(scope="function")
def snippet_remove(remote: CobblerXMLRPCInterface, token: str) -> Callable[[str], None]:
    """
    Fixture that removed a snippet from Cobbler.
    """

    def _snippet_remove(name: str):
        remote.remove_autoinstall_snippet(name, token)

    return _snippet_remove


@pytest.fixture(scope="function")
def create_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that creates a distro and adds it to Cobbler.
    """

    def _create_distro(
        name: str, arch: str, breed: str, path_kernel: str, path_initrd: str
    ) -> str:
        distro = remote.new_distro(token)
        remote.modify_distro(distro, "name", name, token)
        remote.modify_distro(distro, "arch", arch, token)
        remote.modify_distro(distro, "breed", breed, token)
        remote.modify_distro(distro, "kernel", path_kernel, token)
        remote.modify_distro(distro, "initrd", path_initrd, token)
        remote.save_distro(distro, token)
        return distro

    return _create_distro


@pytest.fixture(scope="function")
def remove_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that removes a distro from Cobbler.
    """

    def _remove_distro(name: str):
        remote.remove_distro(name, token)

    return _remove_distro


@pytest.fixture(scope="function")
def create_profile(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that creates a profile and adds it to Cobbler.
    """

    def _create_profile(
        name: str, distro: str, kernel_options: Union[Dict[str, Any], str]
    ) -> str:
        profile = remote.new_profile(token)
        remote.modify_profile(profile, "name", name, token)
        remote.modify_profile(profile, "distro", distro, token)
        remote.modify_profile(profile, "kernel_options", kernel_options, token)
        remote.save_profile(profile, token)
        return profile

    return _create_profile


@pytest.fixture(scope="function")
def remove_profile(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that removes a profile from Cobbler.
    """

    def _remove_profile(name: str):
        remote.remove_profile(name, token)

    return _remove_profile


@pytest.fixture(scope="function")
def create_system(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that creates a system and adds it to Cobbler.
    """

    def _create_system(name: str, profile: str) -> str:
        system = remote.new_system(token)
        remote.modify_system(system, "name", name, token)
        remote.modify_system(system, "profile", profile, token)
        remote.save_system(system, token)
        return system

    return _create_system


@pytest.fixture(scope="function")
def remove_system(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that removes a system from Cobbler.
    """

    def _remove_system(name: str):
        remote.remove_system(name, token)

    return _remove_system


@pytest.fixture(scope="function")
def create_autoinstall_template(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[str, str], None]:
    """
    Fixture that creates an autoinstall template and adds it to Cobbler.
    """

    def _create_autoinstall_template(filename: str, content: str):
        remote.write_autoinstall_template(filename, content, token)

    return _create_autoinstall_template


@pytest.fixture(scope="function")
def remove_autoinstall_template(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[str], None]:
    """
    TOFixture that removes an autoinstall template from Cobbler.DO
    """

    def _remove_autoinstall_template(name: str):
        remote.remove_autoinstall_template(name, token)

    return _remove_autoinstall_template


@pytest.fixture(scope="function")
def create_repo(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[str, str, bool], str]:
    """
    Fixture that creates a repository and adds it to Cobbler.
    """

    def _create_repo(name: str, mirror: str, mirror_locally: bool):
        repo = remote.new_repo(token)
        remote.modify_repo(repo, "name", name, token)
        remote.modify_repo(repo, "mirror", mirror, token)
        remote.modify_repo(repo, "mirror_locally", mirror_locally, token)
        remote.save_repo(repo, token)
        return repo

    return _create_repo


@pytest.fixture(scope="function")
def remove_repo(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that removes a repo from Cobbler.
    """

    def _remove_repo(name: str):
        remote.remove_repo(name, token)

    return _remove_repo


@pytest.fixture(scope="function")
def create_menu(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that creates a menu and adds it to Cobbler.
    """

    def _create_menu(name: str, display_name: str):
        menu_id = remote.new_menu(token)

        remote.modify_menu(menu_id, "name", name, token)
        remote.modify_menu(menu_id, "display_name", display_name, token)

        remote.save_menu(menu_id, token)
        return menu_id

    return _create_menu


@pytest.fixture(scope="function")
def remove_menu(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that removes a menu from Cobbler.
    """

    def _remove_menu(name: str):
        remote.remove_menu(name, token)

    return _remove_menu


@pytest.fixture(scope="function")
def create_testprofile(remote: CobblerXMLRPCInterface, token: str):
    """
    Create a profile with the name "testprofile0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    profile = remote.new_profile(token)
    remote.modify_profile(profile, "name", "testprofile0", token)
    remote.modify_profile(profile, "distro", "testdistro0", token)
    remote.modify_profile(profile, "kernel_options", "a=1 b=2 c=3 c=4 c=5 d e", token)
    remote.modify_profile(profile, "menu", "testmenu0", token)
    remote.save_profile(profile, token)


@pytest.fixture(scope="function")
def remove_testprofile(remote: CobblerXMLRPCInterface, token: str):
    """
    Removes the profile with the name "testprofile0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_profile("testprofile0", token)


@pytest.fixture(scope="function")
def remove_testdistro(remote: CobblerXMLRPCInterface, token: str):
    """
    Removes the distro "testdistro0" from the running cobbler after the test.
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_distro("testdistro0", token, False)


@pytest.fixture(scope="function")
def create_testdistro(
    remote: CobblerXMLRPCInterface,
    token: str,
    fk_kernel: str,
    fk_initrd: str,
    create_kernel_initrd: Callable[[str, str], str],
):
    """
    Creates a distro "testdistro0" with the architecture "x86_64", breed "suse" and the fixtures which are setting the
    fake kernel and initrd.
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    :param fk_kernel: See the corresponding fixture.
    :param fk_initrd: See the corresponding fixture.
    """
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    distro = remote.new_distro(token)
    remote.modify_distro(distro, "name", "testdistro0", token)
    remote.modify_distro(distro, "arch", "x86_64", token)
    remote.modify_distro(distro, "breed", "suse", token)
    remote.modify_distro(distro, "kernel", os.path.join(folder, fk_kernel), token)
    remote.modify_distro(distro, "initrd", os.path.join(folder, fk_initrd), token)
    remote.save_distro(distro, token)


@pytest.fixture(scope="function")
def create_testsystem(remote: CobblerXMLRPCInterface, token: str):
    """
    Add a system with the name "testsystem0", the system is assigend to the profile "testprofile0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    system = remote.new_system(token)
    remote.modify_system(system, "name", "testsystem0", token)
    remote.modify_system(system, "profile", "testprofile0", token)
    remote.save_system(system, token)


@pytest.fixture()
def remove_testsystem(remote: CobblerXMLRPCInterface, token: str):
    """
    Remove a system "testsystem0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_system("testsystem0", token, False)


@pytest.fixture(scope="function")
def create_testrepo(remote: CobblerXMLRPCInterface, token: str):
    """
    Create a testrepository with the name "testrepo0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    repo = remote.new_repo(token)
    remote.modify_repo(repo, "name", "testrepo0", token)
    remote.modify_repo(repo, "arch", "x86_64", token)
    remote.modify_repo(repo, "mirror", "http://something", token)
    remote.save_repo(repo, token)


@pytest.fixture(scope="function")
def remove_testrepo(remote: CobblerXMLRPCInterface, token: str):
    """
    Remove a repo "testrepo0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_repo("testrepo0", token, False)


@pytest.fixture(scope="function")
def create_testimage(remote: CobblerXMLRPCInterface, token: str):
    """
    Create a testrepository with the name "testimage0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    image = remote.new_image(token)
    remote.modify_image(image, "name", "testimage0", token)
    remote.save_image(image, token)


@pytest.fixture(scope="function")
def remove_testimage(remote: CobblerXMLRPCInterface, token: str):
    """
    Remove the image "testimage0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_image("testimage0", token, False)


@pytest.fixture(scope="function")
def create_testmenu(remote: CobblerXMLRPCInterface, token: str):
    """
    Create a menu with the name "testmenu0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """

    menu = remote.new_menu(token)
    remote.modify_menu(menu, "name", "testmenu0", token)
    remote.save_menu(menu, token)


@pytest.fixture(scope="function")
def remove_testmenu(remote: CobblerXMLRPCInterface, token: str):
    """
    Remove a menu "testmenu0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_menu("testmenu0", token, False)


@pytest.fixture(scope="function")
def template_files(redhat_autoinstall: str, suse_autoyast: str, ubuntu_preseed: str):
    """
    Create the template files and remove them afterwards.

    :return:
    """
    folder = "/var/lib/cobbler/templates"
    Path(os.path.join(folder, redhat_autoinstall)).touch()
    Path(os.path.join(folder, suse_autoyast)).touch()
    Path(os.path.join(folder, ubuntu_preseed)).touch()

    yield

    os.remove(os.path.join(folder, redhat_autoinstall))
    os.remove(os.path.join(folder, suse_autoyast))
    os.remove(os.path.join(folder, ubuntu_preseed))
