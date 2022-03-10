import os
import sys
from pathlib import Path

import pytest

from cobbler.utils import get_shared_secret
from cobbler.remote import CobblerXMLRPCInterface


@pytest.fixture(scope="function")
def remote(cobbler_xmlrpc_base) -> CobblerXMLRPCInterface:
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[0]


@pytest.fixture(scope="function")
def token(cobbler_xmlrpc_base) -> str:
    """

    :param cobbler_xmlrpc_base:
    :return:
    """
    return cobbler_xmlrpc_base[1]


@pytest.fixture(scope="function")
def cobbler_xmlrpc_base(cobbler_api):
    """
    Initialises the api object and makes it available to the test.
    """
    # create XML-RPC client and connect to server
    remote = CobblerXMLRPCInterface(cobbler_api)
    shared_secret = get_shared_secret()
    token = remote.login("", shared_secret)
    if not token:
        sys.exit(1)
    return remote, token


@pytest.fixture(scope="function")
def testsnippet() -> str:
    return "# This is a small simple testsnippet!"


@pytest.fixture(scope="function")
def snippet_add(remote, token):
    def _snippet_add(name: str, data):
        remote.write_autoinstall_snippet(name, data, token)
    return _snippet_add


@pytest.fixture(scope="function")
def snippet_remove(remote, token):
    def _snippet_remove(name: str):
        remote.remove_autoinstall_snippet(name, token)
    return _snippet_remove


@pytest.fixture(scope="function")
def create_distro(remote, token):
    def _create_distro(name: str, arch: str, breed: str, path_kernel: str, path_initrd: str):
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
def remove_distro(remote, token):
    def _remove_distro(name: str):
        remote.remove_distro(name, token)
    return _remove_distro


@pytest.fixture(scope="function")
def create_profile(remote, token):
    def _create_profile(name, distro, kernel_options):
        profile = remote.new_profile(token)
        remote.modify_profile(profile, "name", name, token)
        remote.modify_profile(profile, "distro", distro, token)
        remote.modify_profile(profile, "kernel_options", kernel_options, token)
        remote.save_profile(profile, token)
        return profile
    return _create_profile


@pytest.fixture(scope="function")
def remove_profile(remote, token):
    def _remove_profile(name):
        remote.remove_profile(name, token)
    return _remove_profile


@pytest.fixture(scope="function")
def create_system(remote, token):
    def _create_system(name, profile):
        system = remote.new_system(token)
        remote.modify_system(system, "name", name, token)
        remote.modify_system(system, "profile", profile, token)
        remote.save_system(system, token)
        return system
    return _create_system


@pytest.fixture(scope="function")
def remove_system(remote, token):
    def _remove_system(name):
        remote.remove_system(name, token)
    return _remove_system


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
def remove_mgmt_class(remote, token):
    def _remove_mgmt_class(name):
        remote.remove_mgmtclass(name, token)
    return _remove_mgmt_class


@pytest.fixture(scope="function")
def create_autoinstall_template(remote, token):
    def _create_autoinstall_template(filename, content):
        remote.write_autoinstall_template(filename, content, token)
    return _create_autoinstall_template


@pytest.fixture(scope="function")
def remove_autoinstall_template(remote, token):
    def _remove_autoinstall_template(name):
        remote.remove_autoinstall_template(name, token)
    return _remove_autoinstall_template


@pytest.fixture(scope="function")
def create_repo(remote, token):
    def _create_repo(name, mirror, mirror_locally):
        repo = remote.new_repo(token)
        remote.modify_repo(repo, "name", name, token)
        remote.modify_repo(repo, "mirror", mirror, token)
        remote.modify_repo(repo, "mirror_locally", mirror_locally, token)
        remote.save_repo(repo, token)
        return repo
    return _create_repo


@pytest.fixture(scope="function")
def remove_repo(remote, token):
    def _remove_repo(name):
        remote.remove_repo(name, token)
    return _remove_repo


@pytest.fixture(scope="function")
def create_menu(remote, token):
    def _create_menu(name, display_name):
        menu_id = remote.new_menu(token)

        remote.modify_menu(menu_id, "name", name, token)
        remote.modify_menu(menu_id, "display_name", display_name, token)

        remote.save_menu(menu_id, token)
        return menu_id
    return _create_menu


@pytest.fixture(scope="function")
def remove_menu(remote, token):
    def _remove_menu(name):
        remote.remove_menu(name, token)
    return _remove_menu


@pytest.fixture(scope="function")
def create_testprofile(remote, token):
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
def remove_testprofile(remote, token):
    """
    Removes the profile with the name "testprofile0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_profile("testprofile0", token)


@pytest.fixture(scope="function")
def remove_testdistro(remote, token):
    """
    Removes the distro "testdistro0" from the running cobbler after the test.
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_distro("testdistro0", token, False)


@pytest.fixture(scope="function")
def create_testdistro(remote, token, fk_kernel, fk_initrd, create_kernel_initrd):
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
def create_testsystem(remote, token):
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
def remove_testsystem(remote, token):
    """
    Remove a system "testsystem0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_system("testsystem0", token, False)


@pytest.fixture(scope="function")
def create_testrepo(remote, token):
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
def remove_testrepo(remote, token):
    """
    Remove a repo "testrepo0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_repo("testrepo0", token, False)


@pytest.fixture(scope="function")
def create_testimage(remote, token):
    """
    Create a testrepository with the name "testimage0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    image = remote.new_image(token)
    remote.modify_image(image, "name", "testimage0", token)
    remote.save_image(image, token)


@pytest.fixture(scope="function")
def remove_testimage(remote, token):
    """
    Remove the image "testimage0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_image("testimage0", token, False)


@pytest.fixture(scope="function")
def create_testpackage(remote, token):
    """
    Create a testpackage with the name "testpackage0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    package = remote.new_package(token)
    remote.modify_package(package, "name", "testpackage0", token)
    remote.save_package(package, token)


@pytest.fixture(scope="function")
def remove_testpackage(remote, token):
    """
    Remove a package "testpackage0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """

    yield
    remote.remove_package("testpackage0", token, False)


@pytest.fixture(scope="function")
def create_testfile_item(remote, token):
    """
    Create a testfile with the name "testfile0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """

    mfile = remote.new_file(token)
    remote.modify_file(mfile, "name", "testfile0", token)
    remote.modify_file(mfile, "path", "/dev/shm/", token)
    remote.modify_file(mfile, "group", "root", token)
    remote.modify_file(mfile, "owner", "root", token)
    remote.modify_file(mfile, "mode", "0600", token)
    remote.modify_file(mfile, "is_dir", "True", token)
    remote.save_file(mfile, token)


@pytest.fixture(scope="function")
def remove_testfile(remote, token):
    """
    Remove a file "testfile0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_file("testfile0", token, False)


@pytest.fixture(scope="function")
def create_mgmtclass(remote, token):
    """
    Create a mgmtclass with the name "mgmtclass0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """

    mgmtclass0 = remote.new_mgmtclass(token)
    remote.modify_mgmtclass(mgmtclass0, "name", "mgmtclass0", token)
    remote.save_mgmtclass(mgmtclass0, token)


@pytest.fixture(scope="function")
def remove_mgmtclass(remote, token):
    """
    Remove a mgmtclass "mgmtclass0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_mgmtclass("mgmtclass0", token, False)


@pytest.fixture(scope="function")
def create_testmenu(remote, token):
    """
    Create a menu with the name "testmenu0"
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """

    menu = remote.new_menu(token)
    remote.modify_menu(menu, "name", "testmenu0", token)
    remote.save_menu(menu, token)


@pytest.fixture(scope="function")
def remove_testmenu(remote, token):
    """
    Remove a menu "testmenu0".
    :param remote: See the corresponding fixture.
    :param token: See the corresponding fixture.
    """
    yield
    remote.remove_menu("testmenu0", token, False)


@pytest.fixture(scope="function")
def template_files(redhat_autoinstall, suse_autoyast, ubuntu_preseed):
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
