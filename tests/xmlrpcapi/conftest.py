import logging
import sys
import xmlrpc.client as xmlrpcclient

import pytest

from cobbler.utils import local_get_cobbler_api_url, get_shared_secret

# "import xmlrpc.client" does currently not work. No explanation found anywhere.


@pytest.fixture(scope="session")
def remote(cobbler_xmlrpc_base):
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[0]


@pytest.fixture(scope="session")
def token(cobbler_xmlrpc_base):
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[1]


@pytest.fixture(scope="session")
def cobbler_xmlrpc_base():
    """
    Initialises the api object and makes it available to the test.
    """
    # create logger
    logging.basicConfig(stream=sys.stderr)
    logger = logging.getLogger("xobbler_xmlrpc_base")
    logger.setLevel(logging.DEBUG)

    # create XML-RPC client and connect to server
    api_url = local_get_cobbler_api_url()
    remote = xmlrpcclient.Server(api_url, allow_none=True)
    shared_secret = get_shared_secret()
    token = remote.login("", shared_secret)
    if not token:
        sys.exit(1)
    yield remote, token


@pytest.fixture(scope="class")
def testsnippet():
    return "# This is a small simple testsnippet!"


@pytest.fixture()
def snippet_add(remote, token):
    def _snippet_add(name, data):
        remote.write_autoinstall_snippet(name, data, token)
    return _snippet_add


@pytest.fixture()
def snippet_remove(remote, token):
    def _snippet_remove(name):
        remote.remove_autoinstall_snippet(name, token)
    return _snippet_remove


@pytest.fixture()
def create_distro(remote, token):
    def _create_distro(name, arch, breed, path_kernel, path_initrd):
        distro = remote.new_distro(token)
        remote.modify_distro(distro, "name", name, token)
        remote.modify_distro(distro, "arch", arch, token)
        remote.modify_distro(distro, "breed", breed, token)
        remote.modify_distro(distro, "kernel", path_kernel, token)
        remote.modify_distro(distro, "initrd", path_initrd, token)
        remote.save_distro(distro, token)
        return distro
    return _create_distro


@pytest.fixture()
def remove_distro(remote, token):
    def _remove_distro(name):
        remote.remove_distro(name, token)
    return _remove_distro


@pytest.fixture()
def create_profile(remote, token):
    def _create_profile(name, distro, kernel_options):
        profile = remote.new_profile(token)
        remote.modify_profile(profile, "name", name, token)
        remote.modify_profile(profile, "distro", distro, token)
        remote.modify_profile(profile, "kernel_options", kernel_options, token)
        remote.save_profile(profile, token)
        return profile
    return _create_profile


@pytest.fixture()
def remove_profile(remote, token):
    def _remove_profile(name):
        remote.remove_profile(name, token)
    return _remove_profile


@pytest.fixture()
def create_system(remote, token):
    def _create_system(name, profile):
        system = remote.new_system(token)
        remote.modify_system(system, "name", name, token)
        remote.modify_system(system, "profile", profile, token)
        remote.save_system(system, token)
        return system
    return _create_system


@pytest.fixture()
def remove_system(remote, token):
    def _remove_system(name):
        remote.remove_system(name, token)
    return _remove_system


@pytest.fixture()
def create_file(remote, token):
    def _create_file(name, is_directory, action, group, mode, owner, path, template):
        file_id = remote.new_file(token)

        remote.modify_file(file_id, "name", name, token)
        remote.modify_file(file_id, "is_directory", is_directory, token)
        remote.modify_file(file_id, "action", action, token)
        remote.modify_file(file_id, "group", group, token)
        remote.modify_file(file_id, "mode", mode, token)
        remote.modify_file(file_id, "owner", owner, token)
        remote.modify_file(file_id, "path", path, token)
        remote.modify_file(file_id, "template", template, token)

        remote.save_file(file_id, token)
        return file_id
    return _create_file


@pytest.fixture()
def remove_file(remote, token):
    def _remove_file(name):
        remote.remove_file(name, token)
    return _remove_file


@pytest.fixture()
def create_mgmt_class(remote, token):
    def _create_mgmt_class(name):
        mgmtclass = remote.new_mgmtclass(token)
        remote.modify_mgmtclass(mgmtclass, "name", name, token)
        remote.save_mgmtclass(mgmtclass, token)
        return mgmtclass
    return _create_mgmt_class


@pytest.fixture()
def remove_mgmt_class(remote, token):
    def _remove_mgmt_class(name):
        remote.remove_mgmtclass(name, token)
    return _remove_mgmt_class


@pytest.fixture()
def create_autoinstall_template(remote, token):
    def _create_autoinstall_template(filename, content):
        remote.write_autoinstall_template(filename, content, token)
    return _create_autoinstall_template


@pytest.fixture()
def remove_autoinstall_template(remote, token):
    def _remove_autoinstall_template(name):
        remote.remove_autoinstall_template(name, token)
    return _remove_autoinstall_template


@pytest.fixture
def create_repo(remote, token):
    def _create_repo(name, mirror, mirror_locally):
        repo = remote.new_repo(token)
        remote.modify_repo(repo, "name", name, token)
        remote.modify_repo(repo, "mirror", mirror, token)
        remote.modify_repo(repo, "mirror_locally", mirror_locally, token)
        remote.save_repo(repo, token)
        return repo
    return _create_repo


@pytest.fixture
def remove_repo(remote, token):
    def _remove_repo(name):
        remote.remove_repo(name, token)
    return _remove_repo
