import pytest


@pytest.mark.usefixtures("cobbler_xmlrpc_base")
class TestKoan:
    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "create_testsystem",
                             "remove_testdistro", "remove_testmenu", "remove_testprofile", "remove_testsystem")
    def test_get_systems_koan(self, remote):
        # Arrange

        # Act
        systems = remote.get_systems()

        # Assert
        # TODO Test more attributes
        for system in systems:
            if "autoinstall_meta" in system:
                assert "ks_meta" in system
                assert system.get("ks_meta") == system.get("autoinstall_meta")
            if "autoinstall" in system:
                assert "kickstart" in system
                assert system.get("kickstart") == system.get("autoinstall")

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "create_testsystem",
                             "remove_testdistro", "remove_testmenu", "remove_testprofile", "remove_testsystem")
    def test_get_system_for_koan(self, remote):
        # Arrange

        # Act
        system = remote.get_system_for_koan("testsystem0")

        # Assert
        assert "ks_meta" in system
        assert "kickstart" in system

    @pytest.mark.usefixtures("create_testdistro", "create_testmenu", "create_testprofile", "remove_testdistro",
                             "remove_testmenu", "remove_testprofile")
    def test_get_profile_for_koan(self, remote):
        # Arrange

        # Act
        profile = remote.get_profile_for_koan("testprofile0")

        # Assert
        assert "ks_meta" in profile
        assert "kickstart" in profile

    @pytest.mark.usefixtures("create_testdistro", "remove_testdistro")
    def test_get_distro_for_koan(self, remote):
        # Arrange

        # Act
        distro = remote.get_distro_for_koan("testdistro0")

        # Assert
        assert "ks_meta" in distro
        assert "kickstart" not in distro

    @pytest.mark.usefixtures("create_testrepo", "remove_testrepo")
    def test_get_repo_for_koan(self, remote):
        # Arrange

        # Act
        repo = remote.get_repo_for_koan("testrepo0")

        # Assert
        assert "ks_meta" not in repo
        assert "kickstart" not in repo

    @pytest.mark.usefixtures("create_testimage", "remove_testimage")
    def test_get_image_for_koan(self, remote):
        # Arrange

        # Act
        image = remote.get_image_for_koan("testimage0")

        # Assert
        assert "ks_meta" not in image
        assert "kickstart" in image

    @pytest.mark.usefixtures("create_mgmtclass", "remove_mgmtclass")
    def test_get_mgmtclass_for_koan(self, remote):
        # Arrange

        # Act
        mgmt_class = remote.get_mgmtclass_for_koan("mgmtclass0")

        # Assert
        assert "ks_meta" not in mgmt_class
        assert "kickstart" not in mgmt_class

    @pytest.mark.usefixtures("create_testpackage", "remove_testpackage")
    def test_get_package_for_koan(self, remote):
        # Arrange

        # Act
        package = remote.get_package_for_koan("package0")

        # Assert
        assert "ks_meta" not in package
        assert "kickstart" not in package

    @pytest.mark.usefixtures("create_testfile", "remove_testfile")
    def test_get_file_for_koan(self, remote):
        # Arrange

        # Act
        file = remote.get_file_for_koan("file0")

        # Assert
        assert "ks_meta" not in file
        assert "kickstart" not in file

    @pytest.mark.usefixtures("create_testmenu", "remove_testmenu")
    def test_get_menu_for_koan(self, remote):
        # Arrange

        # Act
        menu = remote.get_menu_for_koan("testmenu0")

        # Assert
        assert "ks_meta" not in menu
        assert "kickstart" not in menu