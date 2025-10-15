"""
Fixtures that are shared by the XML-RPC tests that are in the "xmlrpcapi" module.
"""

import os
import pathlib
import sys
import time
from typing import Any, Callable, Dict, Tuple, Union

import pytest

from cobbler.api import CobblerAPI
from cobbler.remote import CobblerXMLRPCInterface
from cobbler.utils import get_shared_secret

WaitTaskEndType = Callable[[str, CobblerXMLRPCInterface], None]


@pytest.fixture(name="remote", scope="function")
def fixture_remote(
    cobbler_xmlrpc_base: Tuple[CobblerXMLRPCInterface, str],
) -> CobblerXMLRPCInterface:
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[0]


@pytest.fixture(name="token", scope="function")
def fixture_token(cobbler_xmlrpc_base: Tuple[CobblerXMLRPCInterface, str]) -> str:
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[1]


@pytest.fixture(name="token2", scope="function")
def fixture_token2(remote: CobblerXMLRPCInterface) -> str:
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    shared_secret = get_shared_secret()
    token = remote.login("", shared_secret)  # type: ignore
    if not token:
        sys.exit(1)
    return token


@pytest.fixture(name="cobbler_xmlrpc_base", scope="function")
def fixture_cobbler_xmlrpc_base(
    cobbler_api: CobblerAPI,
) -> Tuple[CobblerXMLRPCInterface, str]:
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
def create_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture that creates a distro and adds it to Cobbler.
    """

    def _create_distro(
        name: str, arch: str, breed: str, path_kernel: str, path_initrd: str
    ) -> str:
        distro = remote.new_distro(token)
        remote.modify_distro(distro, ["name"], name, token)
        remote.modify_distro(distro, ["arch"], arch, token)
        remote.modify_distro(distro, ["breed"], breed, token)
        remote.modify_distro(distro, ["kernel"], path_kernel, token)
        remote.modify_distro(distro, ["initrd"], path_initrd, token)
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
        remote.modify_profile(profile, ["name"], name, token)
        remote.modify_profile(profile, ["distro"], distro, token)
        remote.modify_profile(profile, ["kernel_options"], kernel_options, token)
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
        remote.modify_system(system, ["name"], name, token)
        remote.modify_system(system, ["profile"], profile, token)
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


@pytest.fixture(name="create_autoinstall_template", scope="function")
def fixture_create_autoinstall_template(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[str, str], str]:
    """
    Fixture that creates an autoinstall template and adds it to Cobbler.
    """

    def _create_autoinstall_template(filename: str, content: str) -> str:
        template_path = pathlib.Path("/var/lib/cobbler/templates") / filename
        template_path.write_text(content, encoding="UTF-8")
        template = remote.new_template(token)
        remote.modify_template(template, ["name"], filename, token)
        remote.modify_template(template, ["template_type"], "cheetah", token)
        remote.modify_template(template, ["uri", "schema"], "file", token)
        remote.modify_template(template, ["uri", "path"], filename, token)
        remote.save_template(template, token, "new")
        return template

    return _create_autoinstall_template


@pytest.fixture(scope="function")
def create_repo(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[str, str, bool], str]:
    """
    Fixture that creates a repository and adds it to Cobbler.
    """

    def _create_repo(name: str, mirror: str, mirror_locally: bool):
        repo = remote.new_repo(token)
        remote.modify_repo(repo, ["name"], name, token)
        remote.modify_repo(repo, ["mirror"], mirror, token)
        remote.modify_repo(repo, ["mirror_locally"], mirror_locally, token)
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

        remote.modify_menu(menu_id, ["name"], name, token)
        remote.modify_menu(menu_id, ["display_name"], display_name, token)

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
    distro_uid = remote.get_distro_handle("testdistro0")
    menu_uid = remote.get_menu_handle("testmenu0")
    profile = remote.new_profile(token)
    remote.modify_profile(profile, ["name"], "testprofile0", token)
    remote.modify_profile(profile, ["distro"], distro_uid, token)
    remote.modify_profile(profile, ["kernel_options"], "a=1 b=2 c=3 c=4 c=5 d e", token)
    remote.modify_profile(profile, ["menu"], menu_uid, token)
    remote.save_profile(profile, token)


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
    remote.modify_distro(distro, ["name"], "testdistro0", token)
    remote.modify_distro(distro, ["arch"], "x86_64", token)
    remote.modify_distro(distro, ["breed"], "suse", token)
    remote.modify_distro(distro, ["kernel"], os.path.join(folder, fk_kernel), token)
    remote.modify_distro(distro, ["initrd"], os.path.join(folder, fk_initrd), token)
    remote.save_distro(distro, token)


@pytest.fixture(scope="function")
def create_testsystem(remote: CobblerXMLRPCInterface, token: str):
    """
    Add a system with the name "testsystem0", the system is assigend to the profile "testprofile0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    profile_uid = remote.get_profile_handle("testprofile0")
    system = remote.new_system(token)
    remote.modify_system(system, ["name"], "testsystem0", token)
    remote.modify_system(system, ["profile"], profile_uid, token)
    remote.save_system(system, token)


@pytest.fixture(scope="function")
def create_testrepo(remote: CobblerXMLRPCInterface, token: str):
    """
    Create a testrepository with the name "testrepo0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    repo = remote.new_repo(token)
    remote.modify_repo(repo, ["name"], "testrepo0", token)
    remote.modify_repo(repo, ["arch"], "x86_64", token)
    remote.modify_repo(repo, ["mirror"], "http://something", token)
    remote.save_repo(repo, token)


@pytest.fixture(scope="function")
def create_testimage(remote: CobblerXMLRPCInterface, token: str):
    """
    Create a testrepository with the name "testimage0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    image = remote.new_image(token)
    remote.modify_image(image, ["name"], "testimage0", token)
    remote.save_image(image, token)


@pytest.fixture(scope="function")
def create_testmenu(remote: CobblerXMLRPCInterface, token: str):
    """
    Create a menu with the name "testmenu0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """

    menu = remote.new_menu(token)
    remote.modify_menu(menu, ["name"], "testmenu0", token)
    remote.save_menu(menu, token)


@pytest.fixture(scope="function")
def template_files(create_autoinstall_template: Callable[[str, str], str]):
    """
    Create the template files and remove them afterwards.
    """
    create_autoinstall_template("test.ks", "")
    create_autoinstall_template("test.xml", "")
    create_autoinstall_template("test.seed", "")


@pytest.fixture(name="wait_task_end", scope="function")
def fixture_wait_task_end() -> WaitTaskEndType:
    """
    Wait until a task is finished
    """

    def _wait_task_end(tid: str, remote: CobblerXMLRPCInterface) -> None:
        timeout = 0
        # "complete" is the constant: EVENT_COMPLETE from cobbler.remote
        while remote.get_task_status(tid)[2] != "complete":
            if remote.get_task_status(tid)[2] == "failed":
                pytest.fail("Task failed")
            print(f"task {tid} status: {remote.get_task_status(tid)}")
            time.sleep(5)
            timeout += 5
            if timeout == 60:
                pytest.fail(f"Timeout reached for waiting for task {tid}!")

    return _wait_task_end
