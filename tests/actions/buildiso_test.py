import os

import pytest

from cobbler import enums, utils
from cobbler.actions import buildiso, mkloaders
from cobbler.actions.buildiso.netboot import AppendLineBuilder, NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso
from tests.conftest import does_not_raise


@pytest.fixture(scope="class", autouse=True)
def create_loaders(cobbler_api):
    loaders = mkloaders.MkLoaders(cobbler_api)
    loaders.run()


class TestBuildiso:
    """Since BuildIso needs the collection manager and thus the api, as well as other information this test will
    require greater setup, although only this class shall be tested. Mocks are hard to program and we will try to
    avoid them.
    """

    @pytest.mark.parametrize(
        "input_arch,result_binary_name,expected_exception",
        [
            (enums.Archs.X86_64, "grubx64.efi", does_not_raise()),
            (enums.Archs.PPC, "grub.ppc64le", does_not_raise()),
            (enums.Archs.PPC64, "grub.ppc64le", does_not_raise()),
            (enums.Archs.PPC64EL, "grub.ppc64le", does_not_raise()),
            (enums.Archs.PPC64LE, "grub.ppc64le", does_not_raise()),
            (enums.Archs.AARCH64, "grubaa64.efi", does_not_raise()),
            (enums.Archs.ARM, "bootarm.efi", does_not_raise()),
            (enums.Archs.I386, "bootia32.efi", does_not_raise()),
            (enums.Archs.IA64, "bootia64.efi", does_not_raise()),
        ],
    )
    def test_calculate_grub_name(
        self,
        input_arch,
        result_binary_name,
        expected_exception,
        cobbler_api,
        create_distro,
    ):
        # Arrange
        test_builder = buildiso.BuildIso(cobbler_api)
        test_distro = create_distro()

        # Act
        with expected_exception:
            result = test_builder.calculate_grub_name(test_distro)

            # Assert
            assert result == result_binary_name

    @pytest.mark.parametrize(
        "input_kopts_dict,exepcted_output",
        [
            ({}, ""),
            ({"test": 1}, " test=1"),
            ({"test": None}, " test"),
            ({"test": '"test"'}, ' test="test"'),
            ({"test": "test test test"}, ' test="test test test"'),
            ({"test": 'test "test" test'}, ' test="test "test" test"'),
            ({"test": ['"test"']}, ' test="test"'),
            ({"test": ['"test"', "test"]}, ' test="test" test=test'),
        ],
    )
    def test_add_remaining_kopts(self, input_kopts_dict, exepcted_output):
        # Arrange (missing)
        # Act
        output = buildiso.add_remaining_kopts(input_kopts_dict)

        # Assert
        assert output == exepcted_output

    def test_make_shorter(self, cobbler_api):
        # Arrange
        build_iso = NetbootBuildiso(cobbler_api)
        distroname = "Testdistro"

        # Act
        result = build_iso.make_shorter(distroname)

        # Assert
        assert type(result) == str
        assert distroname in build_iso.distmap
        assert result == "1"

    def test_copy_boot_files(self, cobbler_api, create_distro, tmpdir):
        # Arrange
        target_folder = tmpdir.mkdir("target")
        build_iso = buildiso.BuildIso(cobbler_api)
        testdistro = create_distro()

        # Act
        build_iso.copy_boot_files(testdistro, target_folder)

        # Assert
        assert len(os.listdir(target_folder)) == 2

    def test_filter_system(
        self, cobbler_api, create_distro, create_profile, create_system
    ):
        # Arrange
        test_distro = create_distro()
        test_profile = create_profile(test_distro.name)
        test_system = create_system(profile_name=test_profile.name)
        itemlist = [test_system.name]
        build_iso = NetbootBuildiso(cobbler_api)
        expected_result = [test_system]

        # Act
        result = build_iso.filter_systems(itemlist)

        # Assert
        assert expected_result == result

    def test_filter_profile(self, cobbler_api, create_distro, create_profile):
        # Arrange
        test_distro = create_distro()
        test_profile = create_profile(test_distro.name)
        itemlist = [test_profile.name]
        build_iso = buildiso.BuildIso(cobbler_api)
        expected_result = [test_profile]

        # Act
        result = build_iso.filter_profiles(itemlist)

        # Assert
        assert expected_result == result

    def test_netboot_run(
        self,
        cobbler_api,
        create_distro,
        create_loaders,
        tmpdir,
    ):
        # Arrange
        test_distro = create_distro()
        build_iso = NetbootBuildiso(cobbler_api)
        iso_location = tmpdir.join("autoinst.iso")

        # Act
        build_iso.run(iso=str(iso_location), distro_name=test_distro.name)

        # Assert
        assert iso_location.exists()

    def test_standalone_run(
        self,
        cobbler_api,
        create_distro,
        create_loaders,
        tmpdir_factory,
    ):
        # Arrange
        iso_directory = tmpdir_factory.mktemp("isodir")
        iso_source = tmpdir_factory.mktemp("isosource")
        iso_location = iso_directory.join("autoinst.iso")
        test_distro = create_distro()
        build_iso = StandaloneBuildiso(cobbler_api)

        # Act
        build_iso.run(
            iso=str(iso_location), distro_name=test_distro.name, source=str(iso_source)
        )

        # Assert
        assert iso_location.exists()


class TestAppendLineBuilder:
    def test_init(self):
        assert isinstance(AppendLineBuilder("", {}), AppendLineBuilder)

    def test_generate_system(
        self, cobbler_api, create_distro, create_profile, create_system
    ):
        # Arrange
        test_distro = create_distro()
        test_distro.breed = "suse"
        cobbler_api.add_distro(test_distro)
        test_profile = create_profile(test_distro.name)
        test_system = create_system(profile_name=test_profile.name)
        blendered_data = utils.blender(cobbler_api, False, test_system)
        test_builder = AppendLineBuilder(test_distro.name, blendered_data)

        # Act
        result = test_builder.generate_system(test_distro, test_system, False)

        # Assert
        # Very basic test yes but this is the expected result atm
        # TODO: Make tests more sophisticated
        assert (
            result
            == "  APPEND initrd=testdistro.img install=http://192.168.1.1:80/cblr/links/testdistro autoyast=default.ks"
        )

    def test_generate_profile(self, cobbler_api, create_distro, create_profile):
        # Arrange
        test_distro = create_distro()
        test_profile = create_profile(test_distro.name)
        blendered_data = utils.blender(cobbler_api, False, test_profile)
        test_builder = AppendLineBuilder(test_distro.name, blendered_data)

        # Act
        result = test_builder.generate_profile("suse")

        # Assert
        # Very basic test yes but this is the expected result atm
        # TODO: Make tests more sophisticated
        assert (
            result
            == " append initrd=testdistro.img install=http://192.168.1.1:80/cblr/links/testdistro autoyast=default.ks"
        )
