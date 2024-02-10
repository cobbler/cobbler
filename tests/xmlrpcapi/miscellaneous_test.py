"""
Test module to test functions that cannot be grouped into more distinct categories.
"""

import json
import os
import pathlib
import time
from typing import Any, Callable, Dict, List, Union

import pytest

from cobbler.remote import CobblerXMLRPCInterface
from cobbler.utils import get_shared_secret


def test_clear_system_logs(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_system: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    name_distro = "testdistro_clearsystemlog"
    name_profile = "testprofile_clearsystemlog"
    name_system = "testsystem_clearsystemlog"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)

    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "a=1 b=2 c=3 c=4 c=5 d e")
    system = create_system(name_system, name_profile)

    # Act
    result = remote.clear_system_logs(system, token)

    # Assert
    assert result


def test_disable_netboot(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_system: Callable[[str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    name_distro = "test_distro_template_for_system"
    name_profile = "test_profile_template_for_system"
    name_system = "test_system_template_for_system"
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(folder, fk_kernel)
    path_initrd = os.path.join(folder, fk_initrd)

    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "text")
    create_system(name_system, name_profile)

    # Act
    result = remote.disable_netboot(name_system, token)

    # Assert
    assert result


def test_extended_version(remote: CobblerXMLRPCInterface):
    # Arrange

    # Act
    result = remote.extended_version()

    # Assert Example Dict: {'builddate': 'Mon Feb 10 15:38:48 2020', 'gitdate': '?', 'gitstamp': '?', 'version':
    #                       '3.4.0', 'version_tuple': [3, 4, 0]}
    assert type(result) == dict
    assert type(result.get("version_tuple")) == list
    assert [3, 4, 0] == result.get("version_tuple")


def test_find_items_paged(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(folder, fk_kernel)
    path_initrd = os.path.join(folder, fk_initrd)
    name_distro_1 = "distro_items_paged_1"
    name_distro_2 = "distro_items_paged_2"
    create_distro(name_distro_1, "x86_64", "suse", path_kernel, path_initrd)
    create_distro(name_distro_2, "x86_64", "suse", path_kernel, path_initrd)

    # Act
    result = remote.find_items_paged("distro", None, "name", 1, 1)

    # Assert
    # Example output
    # {'items': [{'ctime': 1589386486.9040322, 'depth': 0, 'mtime': 1589386486.9040322, 'source_repos': [],
    # 'tree_build_time': 0, 'uid': 'cbf288465c724c439cf2ede6c94de4e8', 'arch': 'x86_64', 'autoinstall_meta': {},
    # 'boot_files': {}, 'boot_loaders': '<<inherit>>', 'breed': 'suse', 'comment': '',
    # 'initrd': '/var/log/cobbler/cobbler.log', 'kernel': '/var/log/cobbler/cobbler.log', 'remote_boot_initrd': '~',
    # 'remote_boot_kernel': '~', 'kernel_options': {}, 'kernel_options_post': {},
    # 'name': 'distro_items_paged_1', 'os_version': 'virtio26', 'owners': ['admin'], 'redhat_management_key': '',
    # 'template_files': {}}], 'pageinfo': {'page': 1, 'prev_page': '~', 'next_page': 2, 'pages': [1, 2],
    # 'num_pages': 2, 'num_items': 2, 'start_item': 0, 'end_item': 1, 'items_per_page': 1,
    # 'items_per_page_list': [10, 20, 50, 100, 200, 500]}}
    assert type(result) == dict
    assert type(result.get("items")) == list  # type: ignore
    assert "pageinfo" in result  # type: ignore
    assert "pages" in result["pageinfo"]  # type: ignore
    assert result["pageinfo"]["pages"] == [1, 2]  # type: ignore


@pytest.mark.skip(
    "This functionality was implemented very quickly. The test for this needs to be fixed at a "
    "later point!"
)
def test_find_system_by_dns_name(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_system: Callable[[str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name_distro = "test_distro_template_for_system"
    name_profile = "test_profile_template_for_system"
    name_system = "test_system_template_for_system"
    dns_name = "test.cobbler-test.local"
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "text")
    system = create_system(name_system, name_profile)
    remote.modify_system(system, "dns_name", dns_name, token)
    remote.save_system(system, token)

    # Act
    result = remote.find_system_by_dns_name(dns_name)

    # Assert
    assert result


def test_generate_script(
    remote: CobblerXMLRPCInterface,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name_distro = "test_distro_template_for_system"
    name_profile = "test_profile_template_for_system"
    name_autoinstall_script = "test_generate_script"
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "text")
    # TODO: Create Autoinstall Script

    # Act
    result = remote.generate_script(name_profile, None, name_autoinstall_script)

    # Assert
    assert result


def test_get_item_as_rendered(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name = "test_item_as_rendered"
    create_distro(name, "x86_64", "suse", path_kernel, path_initrd)

    # Act
    result = remote.get_distro_as_rendered(name, token)

    # Assert
    assert result


def test_get_s_since(
    remote: CobblerXMLRPCInterface,
    create_distro: Callable[[str, str, str, str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name_distro_before = "test_distro_since_before"
    name_distro_after = "test_distro_since_after"
    create_distro(name_distro_before, "x86_64", "suse", path_kernel, path_initrd)
    mtime = float(time.time())
    create_distro(name_distro_after, "x86_64", "suse", path_kernel, path_initrd)

    # Act
    result = remote.get_distros_since(mtime)

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1


def test_get_authn_module_name(remote: CobblerXMLRPCInterface, token: str):
    # Arrange

    # Act
    result = remote.get_authn_module_name(token)

    # Assert
    assert result


def test_get_blended_data(
    remote: CobblerXMLRPCInterface,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_system: Callable[[str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name_distro = "test_distro_blended"
    name_profile = "test_profile_blended"
    name_system = "test_system_blended"
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "text")
    create_system(name_system, name_profile)

    # Act
    result = remote.get_blended_data(name_profile, name_system)

    # Assert
    assert result


def test_get_config_data(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_system: Callable[[str, str], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name_distro = "test_distro_template_for_system"
    name_profile = "test_profile_template_for_system"
    name_system = "test_system_template_for_system"
    system_hostname = "testhostname"
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "text")
    system = create_system(name_system, name_profile)
    remote.modify_system(system, "hostname", system_hostname, token)
    remote.save_system(system, token)

    # Act
    result = remote.get_config_data(system_hostname)

    # Assert
    assert json.loads(result)


def test_get_repos_compatible_with_profile(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_repo: Callable[[str, str, bool], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name_distro = "test_distro_get_repo_for_profile"
    name_profile = "test_profile_get_repo_for_profile"
    name_repo_compatible = "test_repo_compatible_profile_1"
    name_repo_incompatible = "test_repo_compatible_profile_2"
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "text")
    repo_compatible = create_repo(name_repo_compatible, "http://localhost", False)
    repo_incompatible = create_repo(name_repo_incompatible, "http://localhost", False)
    remote.modify_repo(repo_compatible, "arch", "x86_64", token)
    remote.save_repo(repo_compatible, token)
    remote.modify_repo(repo_incompatible, "arch", "ppc64le", token)
    remote.save_repo(repo_incompatible, token)

    # Act
    result = remote.get_repos_compatible_with_profile(name_profile, token)

    # Assert
    assert result != []


def test_get_status(remote: CobblerXMLRPCInterface, token: str):
    # Arrange
    logfile = pathlib.Path("/var/log/cobbler/install.log")
    if logfile.exists():
        logfile.unlink()

    # Act
    result = remote.get_status("normal", token)

    # Assert
    assert result == {}


@pytest.mark.skip(
    "The function under test appears to have a bug. For now we skip the test."
)
def test_get_template_file_for_profile(
    remote: CobblerXMLRPCInterface,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_autoinstall_template: Callable[[str, str], None],
    remove_autoinstall_template: Callable[[str], None],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name_distro = "test_distro_template_for_profile"
    name_profile = "test_profile_template_for_profile"
    name_template = "test_template_for_profile"
    content_template = "# Testtemplate"
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "text")
    create_autoinstall_template(name_template, content_template)

    # Act
    # TODO: Fix test & functionality!
    result = remote.get_template_file_for_profile(name_profile, name_template)

    # Cleanup
    remove_autoinstall_template(name_template)

    # Assert
    assert result == content_template


def test_get_template_file_for_system(
    remote: CobblerXMLRPCInterface,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_system: Callable[[str, str], str],
    create_autoinstall_template: Callable[[str, str], None],
    remove_autoinstall_template: Callable[[str], None],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name_distro = "test_distro_template_for_system"
    name_profile = "test_profile_template_for_system"
    name_system = "test_system_template_for_system"
    name_template = "test_template_for_system"
    content_template = "# Testtemplate"
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "text")
    create_system(name_system, name_profile)
    create_autoinstall_template(name_template, content_template)

    # Act
    result = remote.get_template_file_for_system(name_system, name_template)

    # Cleanup
    remove_autoinstall_template(name_template)

    # Assert
    assert result


def test_is_autoinstall_in_use(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_kernel_initrd: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)
    name_distro = "test_distro_is_autoinstall_in_use"
    name_profile = "test_profile_is_autoinstall_in_use"
    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "text")

    # Act
    result = remote.is_autoinstall_in_use(name_profile, token)

    # Assert
    assert not result


def test_logout(remote: CobblerXMLRPCInterface):
    """
    Assert that any action with a token is not successful after using the "logout" method to invalidate the token.
    """
    # Arrange
    shared_secret = get_shared_secret()
    newtoken = remote.login("", shared_secret)  # type: ignore

    # Act
    resultlogout = remote.logout(newtoken)
    resulttokencheck = remote.token_check(newtoken)

    # Assert
    assert resultlogout
    assert not resulttokencheck


@pytest.mark.parametrize(
    "setting_name,input_allow_dynamic_settings,input_value,expected_result",
    [
        ("auth_token_expiration", True, 7200, 0),
        ("manage_dhcp", True, True, 0),
        ("manage_dhcp", False, True, 1),
        ("bootloaders_ipxe_folder", True, "/my/test/folder", 0),
        ("bootloaders_modules", True, ["fake", "bootloaders"], 0),
        ("mongodb", True, {"host": "test", "port": 1234}, 0),
    ],
)
def test_modify_setting(
    remote: CobblerXMLRPCInterface,
    token: str,
    setting_name: str,
    input_allow_dynamic_settings: bool,
    input_value: Union[str, bool, float, int, Dict[Any, Any], List[Any]],
    expected_result: int,
):
    """
    Test that all types of settings can be successfully set or not.
    """
    # Arrange
    remote.api.settings().allow_dynamic_settings = input_allow_dynamic_settings

    # Act
    result = remote.modify_setting(setting_name, input_value, token)

    # Assert
    assert result == expected_result
    assert remote.get_settings().get(setting_name) == input_value


def test_read_autoinstall_template(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_autoinstall_template: Callable[[str, str], None],
    remove_autoinstall_template: Callable[[str], None],
):
    # Arrange
    name = "test_template_name"
    create_autoinstall_template(name, "# Testtemplate")

    # Act
    result = remote.read_autoinstall_template(name, token)

    # Cleanup
    remove_autoinstall_template(name)

    # Assert
    assert result


def test_write_autoinstall_template(
    remote: CobblerXMLRPCInterface,
    token: str,
    remove_autoinstall_template: Callable[[str], None],
):
    # Arrange
    name = "testtemplate"

    # Act
    result = remote.write_autoinstall_template(name, "# Testtemplate", token)

    # Cleanup
    remove_autoinstall_template(name)

    # Assert
    assert result


def test_remove_autoinstall_template(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_autoinstall_template: Callable[[str, str], None],
):
    # Arrange
    name = "test_template_remove"
    create_autoinstall_template(name, "# Testtemplate")

    # Act
    result = remote.remove_autoinstall_template(name, token)

    # Assert
    assert result


def test_read_autoinstall_snippet(
    remote: CobblerXMLRPCInterface,
    token: str,
    testsnippet: str,
    snippet_add: Callable[[str, str], None],
    snippet_remove: Callable[[str], None],
):
    # Arrange
    snippet_name = "testsnippet_read"
    snippet_add(snippet_name, testsnippet)

    # Act
    result = remote.read_autoinstall_snippet(snippet_name, token)

    # Assert
    assert result == testsnippet

    # Cleanup
    snippet_remove(snippet_name)


def test_write_autoinstall_snippet(
    remote: CobblerXMLRPCInterface,
    token: str,
    testsnippet: str,
    snippet_remove: Callable[[str], None],
):
    # Arrange
    # See fixture: testsnippet
    name = "testsnippet_write"

    # Act
    result = remote.write_autoinstall_snippet(name, testsnippet, token)

    # Assert
    assert result

    # Cleanup
    snippet_remove(name)


def test_remove_autoinstall_snippet(
    remote: CobblerXMLRPCInterface,
    token: str,
    snippet_add: Callable[[str, str], None],
    testsnippet: str,
):
    # Arrange
    name = "testsnippet_remove"
    snippet_add(name, testsnippet)

    # Act
    result = remote.remove_autoinstall_snippet(name, token)

    # Assert
    assert result


def test_run_install_triggers(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    create_distro: Callable[[str, str, str, str, str], str],
    create_profile: Callable[[str, str, Union[Dict[str, Any], str]], str],
    create_system: Callable[[str, str], str],
):
    # Arrange
    fk_kernel = "vmlinuz1"
    fk_initrd = "initrd1.img"
    name_distro = "testdistro_run_install_triggers"
    name_profile = "testprofile_run_install_triggers"
    name_system = "testsystem_run_install_triggers"
    basepath = create_kernel_initrd(fk_kernel, fk_initrd)
    path_kernel = os.path.join(basepath, fk_kernel)
    path_initrd = os.path.join(basepath, fk_initrd)

    create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
    create_profile(name_profile, name_distro, "a=1 b=2 c=3 c=4 c=5 d e")
    create_system(name_system, name_profile)

    # Act
    result_pre = remote.run_install_triggers(
        "pre", "system", name_system, "10.0.0.2", token
    )
    result_post = remote.run_install_triggers(
        "post", "system", name_system, "10.0.0.2", token
    )

    # Assert
    assert result_pre
    assert result_post


def test_version(remote: CobblerXMLRPCInterface):
    # Arrange

    # Act
    result = remote.version()

    # Assert
    # Will fail if the version is adjusted in the setup.py
    assert result == 3.4


@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_profile",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
)
def test_render_vars(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: string replacements for @@xyz@@
    """

    # Arrange --> There is nothing to be arranged
    kernel_options = "tree=http://@@http_server@@/cblr/links/@@distro_name@@"

    # Act
    distro = remote.get_item_handle("distro", "testdistro0")
    remote.modify_distro(distro, "kernel_options", kernel_options, token)
    remote.save_distro(distro, token)

    # Assert --> Let the test pass if the call is okay.
    assert True


@pytest.mark.skip("Functionality is broken!")
@pytest.mark.usefixtures(
    "create_testdistro",
    "create_testmenu",
    "create_testprofile",
    "create_testsystem",
    "remove_testdistro",
    "remove_testmenu",
    "remove_testprofile",
    "remove_testsystem",
)
def test_upload_log_data(remote: CobblerXMLRPCInterface):
    # Arrange

    # Act
    result = remote.upload_log_data("testsystem0", "testinstall.log", 0, 0, b"asdas")

    # Assert
    assert isinstance(result, bool)
    assert result
