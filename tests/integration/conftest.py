"""
Shared fixture module for all integration tests.
"""

import pathlib
import time
import xmlrpc.client
from typing import Any, Callable, Generator, List, Tuple

import pytest

from cobbler.remote import CobblerXMLRPCInterface
from cobbler.utils import get_shared_secret
from cobbler.utils.process_management import service_restart

WaitTaskEndType = Callable[[str, CobblerXMLRPCInterface], None]


@pytest.fixture(name="listings_directory")
def fixture_listings_directory() -> pathlib.Path:
    """
    Return the directory for all integration test ISO listings.
    """
    return pathlib.Path("/code/system-tests/listings")


@pytest.fixture(name="images_fake_path")
def fixture_images_fake_path() -> pathlib.Path:
    """
    Return the directory for our fake image.
    """
    return pathlib.Path("/code/system-tests/images/fake")


@pytest.fixture(name="images_dummy_path")
def fixture_images_dummy_path() -> pathlib.Path:
    """
    Return the directory for our dummy image.
    """
    return pathlib.Path("/code/system-tests/images/dummy")


@pytest.fixture(name="restart_cobbler")
def fixture_restart_cobbler() -> Callable[[], None]:
    """
    Fixture to restart the Cobbler Daemon.
    """

    def _restart_cobbler() -> None:
        result = service_restart("cobblerd")
        if result != 0:
            pytest.fail("Failed to restart cobbler")

    return _restart_cobbler


@pytest.fixture(name="reset_cobbler", autouse=True)
def fixture_reset_cobbler(
    restart_cobbler: Callable[[], None],
) -> Generator[None, None, None]:
    """
    Fixture to reset Cobbler after each test.
    """
    restart_cobbler()
    yield


@pytest.fixture(scope="function", name="cobbler_xmlrpc_base")
def fixture_cobbler_xmlrpc_base() -> Tuple[CobblerXMLRPCInterface, str]:
    """
    Initialises the api object and makes it available to the test.
    """
    # create XML-RPC client and connect to server
    remote: CobblerXMLRPCInterface = xmlrpc.client.ServerProxy("http://localhost/cobbler_api")  # type: ignore
    shared_secret = get_shared_secret()
    if isinstance(shared_secret, int):
        pytest.fail("Could not get shared secret to login to XML-RPC")
    token = remote.login("", shared_secret)
    if not token:
        pytest.fail("Could not get XML-RPC token!")
    return remote, token


@pytest.fixture(scope="function", name="remote")
def fixture_remote(
    cobbler_xmlrpc_base: Tuple[CobblerXMLRPCInterface, str],
) -> CobblerXMLRPCInterface:
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[0]


@pytest.fixture(scope="function", name="token")
def fixture_token(cobbler_xmlrpc_base: Tuple[CobblerXMLRPCInterface, str]) -> str:
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[1]


@pytest.fixture(name="create_distro")
def fixture_create_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Fixture to create a Cobbler Distro via XML-RPC.
    """

    def _create_distro(args: List[Tuple[List[str], Any]]) -> str:
        did = remote.new_distro(token)
        for key, value in args:
            remote.modify_distro(did, key, value, token)
        remote.save_distro(did, token, "new")
        return did

    return _create_distro


@pytest.fixture(name="create_profile")
def fixture_create_profile(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[List[Tuple[List[str], Any]]], str]:
    """
    Fixture to create a Cobbler Profile via XML-RPC.
    """

    def _create_profile(args: List[Tuple[List[str], Any]]) -> str:
        pid = remote.new_profile(token)
        for key, value in args:
            remote.modify_profile(pid, key, value, token)
        remote.save_profile(pid, token, "new")
        return pid

    return _create_profile


@pytest.fixture(name="create_system")
def fixture_create_system(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[List[Tuple[List[str], Any]]], str]:
    """
    Fixture to create a Cobbler System via XML-RPC
    """

    def _create_system(args: List[Tuple[List[str], Any]]) -> str:
        sid = remote.new_system(token)
        for key, value in args:
            remote.modify_system(sid, key, value, token)
        remote.save_system(sid, token, "new")
        return sid

    return _create_system


@pytest.fixture(name="create_network_interface")
def fixture_create_network_interface(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[str, List[Tuple[List[str], Any]]], str]:
    """
    Fixture to create a Cobbler Network Interface via XML-RPC
    """

    def _create_network_interface(sid: str, args: List[Tuple[List[str], Any]]) -> str:
        nid = remote.new_network_interface(sid, token)
        for key, value in args:
            remote.modify_network_interface(nid, key, value, token)
        remote.save_network_interface(nid, token, "new")
        return nid

    return _create_network_interface


@pytest.fixture(name="create_autoinstall_template", scope="function")
def fixture_create_autoinstall_template(
    remote: CobblerXMLRPCInterface, token: str
) -> Callable[[str, str, List[str]], str]:
    """
    Fixture that creates an autoinstall template and adds it to Cobbler.
    """

    def _create_autoinstall_template(
        filename: str, content: str, tags: List[str]
    ) -> str:
        template_path = pathlib.Path("/var/lib/cobbler/templates") / filename
        template_path.write_text(content, encoding="UTF-8")
        template = remote.new_template(token)
        remote.modify_template(template, ["name"], filename, token)
        remote.modify_template(template, ["template_type"], "cheetah", token)
        remote.modify_template(template, ["uri", "schema"], "file", token)
        remote.modify_template(template, ["uri", "path"], filename, token)
        remote.modify_template(template, ["tags"], tags, token)
        remote.save_template(template, token, "new")
        return template

    return _create_autoinstall_template


@pytest.fixture(scope="function")
def wait_task_end() -> WaitTaskEndType:
    """
    Wait until a task is finished
    """

    def _wait_task_end(tid: str, remote: CobblerXMLRPCInterface) -> None:
        timeout = 0
        # "complete" is the constant: EVENT_COMPLETE from cobbler.remote
        while remote.get_task_status(tid)[2] != "complete":
            if remote.get_task_status(tid)[2] == "failed":
                print(
                    (
                        pathlib.Path("/var/log/cobbler/tasks") / (tid + ".log")
                    ).read_text()
                )
                pytest.fail("Task failed")
            print(f"task {tid} status: {remote.get_task_status(tid)}")
            time.sleep(5)
            timeout += 5
            if timeout == 60:
                print(
                    (
                        pathlib.Path("/var/log/cobbler/tasks") / (tid + ".log")
                    ).read_text()
                )
                pytest.fail(f'Task with tid "{tid}" failed to complete!')

        print((pathlib.Path("/var/log/cobbler/tasks") / (tid + ".log")).read_text())

    return _wait_task_end
