import json
import os
import time

import pytest

from cobbler.utils import get_shared_secret


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestMiscellaneous:
    """
    Class to test remote calls to cobbler which do not belong into a specific category.
    """

    def test_clear_system_logs(self, remote, token, file_basedir, create_kernel_initrd, create_distro, create_profile,
                               create_system, delete_kernel_initrd, remove_distro, remove_profile, remove_system):
        # Arrange
        fk_kernel = "vmlinuz1"
        fk_initrd = "initrd1.img"
        name_distro = "testdistro_clearsystemlog"
        name_profile = "testprofile_clearsystemlog"
        name_system = "testsystem_clearsystemlog"
        path_kernel = os.path.join(file_basedir, fk_kernel)
        path_initrd = os.path.join(file_basedir, fk_initrd)
        create_kernel_initrd(fk_kernel, fk_initrd)

        distro = create_distro(name_distro, "x86_64", "suse", path_kernel, path_initrd)
        profile = create_profile(name_profile, name_distro, "a=1 b=2 c=3 c=4 c=5 d e")
        system = create_system(name_system, name_profile)

        # Act
        result = remote.clear_system_logs(system, token)

        # Cleanup
        remove_distro(name_distro)
        remove_profile(name_profile)
        remove_system(name_system)
        delete_kernel_initrd(fk_kernel, fk_initrd)

        # Assert
        assert result

    def test_disable_netboot(self, remote, token, create_distro, remove_distro, create_profile, remove_profile,
                             create_system, remove_system):
        # Arrange
        name_distro = "test_distro_template_for_system"
        name_profile = "test_profile_template_for_system"
        name_system = "test_system_template_for_system"
        create_distro(name_distro, "x86_64", "suse", "/var/log/cobbler/cobbler.log", "/var/log/cobbler/cobbler.log")
        create_profile(name_profile, name_distro, "text")
        create_system(name_system, name_profile)

        # Act
        result = remote.disable_netboot(name_system, token)

        # Cleanup
        remove_system(name_system)
        remove_profile(name_profile)
        remove_distro(name_distro)

        # Assert
        assert result

    def test_extended_version(self, remote):
        # Arrange

        # Act
        result = remote.extended_version()

        # Assert Example Dict: {'builddate': 'Mon Feb 10 15:38:48 2020', 'gitdate': '?', 'gitstamp': '?', 'version':
        #                       '3.1.2', 'version_tuple': [3, 1, 2]}
        assert type(result) == dict
        assert type(result.get("version_tuple")) == list
        assert [3, 2, 0] == result.get("version_tuple")

    def test_find_items_paged(self, remote, token, create_distro, remove_distro):
        # Arrange
        name_distro_1 = "distro_items_paged_1"
        name_distro_2 = "distro_items_paged_2"
        create_distro(name_distro_1, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        create_distro(name_distro_2, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")

        # Act
        result = remote.find_items_paged("distro", None, "name", 1, 1)

        # Cleanup
        remove_distro(name_distro_1)
        remove_distro(name_distro_2)

        # Assert
        # Example output
        # {'items': [{'ctime': 1589386486.9040322, 'depth': 0, 'mtime': 1589386486.9040322, 'source_repos': [],
        # 'tree_build_time': 0, 'uid': 'cbf288465c724c439cf2ede6c94de4e8', 'arch': 'x86_64', 'autoinstall_meta': {},
        # 'boot_files': {}, 'boot_loader': '<<inherit>>', 'breed': 'suse', 'comment': '', 'fetchable_files': {},
        # 'initrd': '/var/log/cobbler/cobbler.log', 'kernel': '/var/log/cobbler/cobbler.log', 'remote_boot_initrd': '~',
        # 'remote_boot_kernel': '~', 'kernel_options': {}, 'kernel_options_post': {}, 'mgmt_classes': [],
        # 'name': 'distro_items_paged_1', 'os_version': 'virtio26', 'owners': ['admin'], 'redhat_management_key': '',
        # 'template_files': {}}], 'pageinfo': {'page': 1, 'prev_page': '~', 'next_page': 2, 'pages': [1, 2],
        # 'num_pages': 2, 'num_items': 2, 'start_item': 0, 'end_item': 1, 'items_per_page': 1,
        # 'items_per_page_list': [10, 20, 50, 100, 200, 500]}}
        assert type(result) == dict
        assert type(result.get("items")) == list
        assert "pageinfo" in result
        assert "pages" in result["pageinfo"]
        assert result["pageinfo"]["pages"] == [1, 2]

    @pytest.mark.skip("This functionality was implemented very quickly. The test for this needs to be fixed at a "
                      "later point!")
    def test_find_system_by_dns_name(self, remote, token, create_distro, remove_distro, create_profile, remove_profile,
                                     create_system, remove_system):
        # Arrange
        name_distro = "test_distro_template_for_system"
        name_profile = "test_profile_template_for_system"
        name_system = "test_system_template_for_system"
        dns_name = "test.cobbler-test.local"
        create_distro(name_distro, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        create_profile(name_profile, name_distro, "text")
        system = create_system(name_system, name_profile)
        remote.modify_system(system, "dns_name", dns_name, token)
        remote.save_system(system, token)

        # Act
        result = remote.find_system_by_dns_name(dns_name)

        # Cleanup
        remove_system(name_system)
        remove_profile(name_profile)
        remove_distro(name_distro)

        # Assert
        assert result

    def test_generate_script(self, remote, create_distro, remove_distro, create_profile, remove_profile,
                             create_system, remove_system):
        # Arrange
        name_distro = "test_distro_template_for_system"
        name_profile = "test_profile_template_for_system"
        name_autoinstall_script = "test_generate_script"
        create_distro(name_distro, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        create_profile(name_profile, name_distro, "text")
        # TODO: Create Autoinstall Script

        # Act
        result = remote.generate_script(name_profile, None, name_autoinstall_script)

        # Cleanup
        remove_profile(name_profile)
        remove_distro(name_distro)

        # Assert
        assert result

    def test_get_item_as_rendered(self, remote, token, create_distro, remove_distro):
        # Arrange
        name = "test_item_as_rendered"
        create_distro(name, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")

        # Act
        result = remote.get_distro_as_rendered(name, token)

        # Cleanup
        remove_distro(name)

        # Assert
        assert result

    def test_get_s_since(self, remote, create_distro, remove_distro):
        # Arrange
        name_distro_before = "test_distro_since_before"
        name_distro_after = "test_distro_since_after"
        create_distro(name_distro_before, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        mtime = time.time()
        create_distro(name_distro_after, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")

        # Act
        result = remote.get_distros_since(mtime)

        # Cleanup
        remove_distro(name_distro_before)
        remove_distro(name_distro_after)

        # Assert
        assert type(result) == list
        assert len(result) == 1

    def test_get_authn_module_name(self, remote, token):
        # Arrange

        # Act
        result = remote.get_authn_module_name(token)

        # Assert
        assert result

    def test_get_blended_data(self, remote, create_distro, remove_distro, create_profile, remove_profile,
                              create_system, remove_system):
        # Arrange
        name_distro = "test_distro_template_for_system"
        name_profile = "test_profile_template_for_system"
        name_system = "test_system_template_for_system"
        create_distro(name_distro, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        create_profile(name_profile, name_distro, "text")
        create_system(name_system, name_profile)

        # Act
        result = remote.get_blended_data(name_profile, name_system)

        # Cleanup
        remove_system(name_system)
        remove_profile(name_profile)
        remove_distro(name_distro)

        # Assert
        assert result

    def test_get_config_data(self, remote, token, create_distro, remove_distro, create_profile, remove_profile,
                             create_system, remove_system):
        # Arrange
        name_distro = "test_distro_template_for_system"
        name_profile = "test_profile_template_for_system"
        name_system = "test_system_template_for_system"
        system_hostname = "testhostname"
        create_distro(name_distro, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        create_profile(name_profile, name_distro, "text")
        system = create_system(name_system, name_profile)
        remote.modify_system(system, "hostname", system_hostname, token)
        remote.save_system(system, token)

        # Act
        result = remote.get_config_data(system_hostname)

        # Cleanup
        remove_system(name_system)
        remove_profile(name_profile)
        remove_distro(name_distro)

        # Assert
        assert json.loads(result)

    def test_get_repos_compatible_with_profile(self, remote, token, create_distro, remove_distro, create_profile,
                                               remove_profile, create_repo, remove_repo):
        # Arrange
        name_distro = "test_distro_get_repo_for_profile"
        name_profile = "test_profile_get_repo_for_profile"
        name_repo_compatible = "test_repo_compatible_profile_1"
        name_repo_incompatible = "test_repo_compatible_profile_2"
        create_distro(name_distro, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        create_profile(name_profile, name_distro, "text")
        repo_compatible = create_repo(name_repo_compatible, "http://localhost", "0")
        repo_incompatible = create_repo(name_repo_incompatible, "http://localhost", "0")
        remote.modify_repo(repo_compatible, "arch", "x86_64", token)
        remote.save_repo(repo_compatible, token)
        remote.modify_repo(repo_incompatible, "arch", "ppc64le", token)
        remote.save_repo(repo_incompatible, token)

        # Act
        result = remote.get_repos_compatible_with_profile(name_profile, token)

        # Cleanup
        remove_profile(name_profile)
        remove_distro(name_distro)
        remove_repo(name_repo_compatible)
        remove_repo(name_repo_incompatible)

        # Assert
        assert result != []

    def test_get_status(self, remote, token):
        # Arrange

        # Act
        result = remote.get_status("normal", token)

        # Assert
        assert result == {}

    @pytest.mark.skip("The function under test appears to have a bug. For now we skip the test.")
    def test_get_template_file_for_profile(self, remote, create_distro, remove_distro, create_profile, remove_profile,
                                           create_autoinstall_template, remove_autoinstall_template):
        # Arrange
        name_distro = "test_distro_template_for_profile"
        name_profile = "test_profile_template_for_profile"
        name_template = "test_template_for_profile"
        content_template = "# Testtemplate"
        create_distro(name_distro, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        create_profile(name_profile, name_distro, "text")
        create_autoinstall_template(name_template, content_template)

        # Act
        # TODO: Fix test & functionality!
        result = remote.get_template_file_for_profile(name_profile, name_template)

        # Cleanup
        remove_profile(name_profile)
        remove_distro(name_distro)
        remove_autoinstall_template(name_template)

        # Assert
        assert result == content_template

    def test_get_template_file_for_system(self, remote, create_distro, remove_distro, create_profile, remove_profile,
                                          create_system, remove_system, create_autoinstall_template,
                                          remove_autoinstall_template):
        # Arrange
        name_distro = "test_distro_template_for_system"
        name_profile = "test_profile_template_for_system"
        name_system = "test_system_template_for_system"
        name_template = "test_template_for_system"
        content_template = "# Testtemplate"
        create_distro(name_distro, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        create_profile(name_profile, name_distro, "text")
        create_system(name_system, name_profile)
        create_autoinstall_template(name_template, content_template)

        # Act
        result = remote.get_template_file_for_system(name_system, name_template)

        # Cleanup
        remove_system(name_system)
        remove_profile(name_profile)
        remove_distro(name_distro)
        remove_autoinstall_template(name_template)

        # Assert
        assert result

    def test_is_autoinstall_in_use(self, remote, token, create_distro, remove_distro, create_profile, remove_profile):
        # Arrange
        name_distro = "test_distro_is_autoinstall_in_use"
        name_profile = "test_profile_is_autoinstall_in_use"
        create_distro(name_distro, "x86_64", "suse", "/var/log/cobbler/cobbler.log",
                      "/var/log/cobbler/cobbler.log")
        create_profile(name_profile, name_distro, "text")

        # Act
        result = remote.is_autoinstall_in_use(name_profile, token)

        # Cleanup
        remove_profile(name_profile)
        remove_distro(name_distro)

        # Assert
        assert not result

    def test_logout(self, remote):
        # Arrange
        shared_secret = get_shared_secret()
        newtoken = remote.login("", shared_secret)

        # Act
        resultlogout = remote.logout(newtoken)
        resulttokencheck = remote.token_check(newtoken)

        # Assert
        assert resultlogout
        assert not resulttokencheck

    def test_modify_setting(self, remote, token):
        # Arrange

        # Act
        result = remote.modify_setting("auth_token_expiration", 7200, token)

        # Assert
        assert result == 0

    def test_read_autoinstall_template(self, remote, token, create_autoinstall_template, remove_autoinstall_template):
        # Arrange
        name = "test_template_name"
        create_autoinstall_template(name, "# Testtemplate")

        # Act
        result = remote.read_autoinstall_template(name, token)

        # Cleanup
        remove_autoinstall_template(name)

        # Assert
        assert result

    def test_write_autoinstall_template(self, remote, token, remove_autoinstall_template):
        # Arrange
        name = "testtemplate"

        # Act
        result = remote.write_autoinstall_template(name, "# Testtemplate", token)

        # Cleanup
        remove_autoinstall_template(name)

        # Assert
        assert result

    def test_remove_autoinstall_template(self, remote, token, create_autoinstall_template):
        # Arrange
        name = "test_template_remove"
        create_autoinstall_template(name, "# Testtemplate")

        # Act
        result = remote.remove_autoinstall_template(name, token)

        # Assert
        assert result

    def test_read_autoinstall_snippet(self, remote, token, testsnippet, snippet_add, snippet_remove):
        # Arrange
        snippet_name = "testsnippet_read"
        snippet_add(snippet_name, testsnippet)

        # Act
        result = remote.read_autoinstall_snippet(snippet_name, token)

        # Assert
        assert result == testsnippet

        # Cleanup
        snippet_remove(snippet_name)

    def test_write_autoinstall_snippet(self, remote, token, testsnippet, snippet_remove):
        # Arrange
        # See fixture: testsnippet
        name = "testsnippet_write"

        # Act
        result = remote.write_autoinstall_snippet(name, testsnippet, token)

        # Assert
        assert result

        # Cleanup
        snippet_remove(name)

    def test_remove_autoinstall_snippet(self, remote, token, snippet_add, testsnippet):
        # Arrange
        name = "testsnippet_remove"
        snippet_add(name, testsnippet)

        # Act
        result = remote.remove_autoinstall_snippet(name, token)

        # Assert
        assert result

    def test_run_install_triggers(self, remote, token):
        # Arrange
        # TODO: Needs a system as a target

        # Act
        result_pre = remote.run_install_triggers("pre", "system", "systemname", "10.0.0.2", token)
        result_post = remote.run_install_triggers("post", "system", "systemname", "10.0.0.2", token)

        # Assert
        assert result_pre
        assert result_post

    def test_version(self, remote):
        # Arrange

        # Act
        result = remote.version()

        # Assert
        # Will fail if the version is adjusted in the setup.py
        assert result == 3.2

    def test_xapi_object_edit(self, remote, token, remove_distro):
        # Arrange
        name = "testdistro_xapi_edit"

        # Act
        result = remote.xapi_object_edit("distro", name, "add",
                                         {"name": name, "arch": "x86_64", "breed": "suse",
                                          "kernel": "/var/log/cobbler/cobbler.log",
                                          "initrd": "/var/log/cobbler/cobbler.log"}, token)

        # Cleanup
        remove_distro(name)

        # Assert
        assert result
