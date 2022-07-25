import os

import pytest

from cobbler import enums, utils
from cobbler.actions import buildiso, mkloaders
from cobbler.actions.buildiso.netboot import AppendLineBuilder, NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System
from tests.conftest import does_not_raise


@pytest.fixture(scope="class", autouse=True)
def create_loaders(cobbler_api):
    loaders = mkloaders.MkLoaders(cobbler_api)
    loaders.run()


@pytest.fixture(autouse=True)
def cleanup_items(cobbler_api):
    yield
    test_system = cobbler_api.get_item("system", "testsystem")
    if test_system is not None:
        cobbler_api.remove_system(test_system.name)
    test_profile = cobbler_api.get_item("profile", "testprofile")
    if test_profile is not None:
        cobbler_api.remove_profile(test_profile.name)
    test_distro = cobbler_api.get_item("distro", "testdistro")
    if test_distro is not None:
        cobbler_api.remove_distro(test_distro.name)


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
        self, input_arch, result_binary_name, expected_exception, cobbler_api
    ):
        # Arrange
        test_builder = buildiso.BuildIso(cobbler_api)
        test_distro = Distro(cobbler_api)
        test_distro.name = "testdistro"
        test_distro.arch = input_arch

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

    def test_copy_boot_files(
        self, cobbler_api, create_kernel_initrd, fk_kernel, fk_initrd, tmpdir
    ):
        # Arrange
        target_folder = tmpdir.mkdir("target")
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        build_iso = buildiso.BuildIso(cobbler_api)
        testdistro = Distro(cobbler_api)
        testdistro.name = "testdistro"
        testdistro.kernel = kernel_path
        testdistro.initrd = initrd_path

        # Act
        build_iso.copy_boot_files(testdistro, target_folder)

        # Assert
        assert len(os.listdir(target_folder)) == 2

    def test_filter_system(
        self, cobbler_api, create_kernel_initrd, fk_kernel, fk_initrd
    ):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(cobbler_api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        cobbler_api.add_distro(test_distro)
        test_profile = Profile(cobbler_api)
        test_profile.name = "testprofile"
        test_profile.distro = test_distro.name
        cobbler_api.add_profile(test_profile)
        test_system = System(cobbler_api)
        test_system.name = "testsystem"
        test_system.profile = test_profile.name
        cobbler_api.add_system(test_system)
        itemlist = [test_system.name]
        build_iso = NetbootBuildiso(cobbler_api)
        expected_result = [test_system]

        # Act
        result = build_iso.filter_systems(itemlist)

        # Assert
        assert expected_result == result

    def test_filter_profile(
        self, cobbler_api, create_kernel_initrd, fk_kernel, fk_initrd, cleanup_items
    ):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(cobbler_api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        cobbler_api.add_distro(test_distro)
        test_profile = Profile(cobbler_api)
        test_profile.name = "testprofile"
        test_profile.distro = test_distro.name
        cobbler_api.add_profile(test_profile)
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
        create_kernel_initrd,
        fk_kernel,
        fk_initrd,
        cleanup_items,
        create_loaders,
        tmpdir,
    ):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(cobbler_api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        cobbler_api.add_distro(test_distro)
        build_iso = NetbootBuildiso(cobbler_api)
        iso_location = tmpdir.join("autoinst.iso")

        # Act
        build_iso.run(iso=str(iso_location), distro_name=test_distro.name)

        # Assert
        assert iso_location.exists()

    def test_standalone_run(
        self,
        cobbler_api,
        create_kernel_initrd,
        fk_kernel,
        fk_initrd,
        create_loaders,
        tmpdir_factory,
        cleanup_items,
    ):
        # Arrange
        iso_directory = tmpdir_factory.mktemp("isodir")
        iso_source = tmpdir_factory.mktemp("isosource")
        iso_location = iso_directory.join("autoinst.iso")
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(cobbler_api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        cobbler_api.add_distro(test_distro)
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
        self, cobbler_api, create_kernel_initrd, fk_kernel, fk_initrd, cleanup_items
    ):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(cobbler_api)
        test_distro.name = "testdistro"
        test_distro.breed = "suse"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        cobbler_api.add_distro(test_distro)
        test_profile = Profile(cobbler_api)
        test_profile.name = "testprofile"
        test_profile.distro = test_distro.name
        cobbler_api.add_profile(test_profile)
        test_system = System(cobbler_api)
        test_system.name = "testsystem"
        test_system.profile = test_profile.name
        cobbler_api.add_system(test_system)
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

    def test_generate_profile(
        self, cobbler_api, create_kernel_initrd, fk_kernel, fk_initrd, cleanup_items
    ):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(cobbler_api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        cobbler_api.add_distro(test_distro)
        test_profile = Profile(cobbler_api)
        test_profile.name = "testprofile"
        test_profile.distro = test_distro.name
        cobbler_api.add_profile(test_profile)
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
