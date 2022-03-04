import os

import pytest

from cobbler import enums, utils
from cobbler.actions import buildiso, mkloaders
from cobbler.actions.buildiso.netboot import AppendLineBuilder, NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.system import System
from tests.conftest import does_not_raise


@pytest.fixture(scope="class")
def api():
    return CobblerAPI()


@pytest.fixture(scope="class", autouse=True)
def create_loaders(api):
    loaders = mkloaders.MkLoaders(api)
    loaders.run()


@pytest.fixture(autouse=True)
def cleanup_items(api):
    yield
    test_system = api.get_item("system", "testsystem")
    if test_system is not None:
        api.remove_system(test_system.name)
    test_profile = api.get_item("profile", "testprofile")
    if test_profile is not None:
        api.remove_profile(test_profile.name)
    test_distro = api.get_item("distro", "testdistro")
    if test_distro is not None:
        api.remove_distro(test_distro.name)


class TestBuildiso:
    """Since BuildIso needs the collection manager and thus the api, as well as other information this test will
    require greater setup, although only this class shall be tested. Mocks are hard to program and we will try to
    avoid them.
    """

    @pytest.mark.parametrize(
        "input_arch,result_binary_name,expected_exception",
        [
            (enums.Archs.X86_64, "grubx86.efi", does_not_raise()),
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
        self, input_arch, result_binary_name, expected_exception, api
    ):
        # Arrange
        test_builder = buildiso.BuildIso(api)
        test_distro = Distro(api)
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

    def test_make_shorter(self, api):
        # Arrange
        build_iso = NetbootBuildiso(api)
        distroname = "Testdistro"

        # Act
        result = build_iso.make_shorter(distroname)

        # Assert
        assert type(result) == str
        assert distroname in build_iso.distmap
        assert result == "1"

    def test_copy_boot_files(
        self, api, create_kernel_initrd, fk_kernel, fk_initrd, tmpdir
    ):
        # Arrange
        target_folder = tmpdir.mkdir("target")
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        build_iso = buildiso.BuildIso(api)
        testdistro = Distro(api)
        testdistro.name = "testdistro"
        testdistro.kernel = kernel_path
        testdistro.initrd = initrd_path

        # Act
        build_iso.copy_boot_files(testdistro, target_folder)

        # Assert
        assert len(os.listdir(target_folder)) == 2

    def test_filter_system(self, api, create_kernel_initrd, fk_kernel, fk_initrd):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        api.add_distro(test_distro)
        test_profile = Profile(api)
        test_profile.name = "testprofile"
        test_profile.distro = test_distro.name
        api.add_profile(test_profile)
        test_system = System(api)
        test_system.name = "testsystem"
        test_system.profile = test_profile.name
        api.add_system(test_system)
        itemlist = [test_system.name]
        build_iso = NetbootBuildiso(api)
        expected_result = [test_system]

        # Act
        result = build_iso.filter_systems(itemlist)

        # Assert
        assert expected_result == result

    def test_filter_profile(
        self, api, create_kernel_initrd, fk_kernel, fk_initrd, cleanup_items
    ):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        api.add_distro(test_distro)
        test_profile = Profile(api)
        test_profile.name = "testprofile"
        test_profile.distro = test_distro.name
        api.add_profile(test_profile)
        itemlist = [test_profile.name]
        build_iso = buildiso.BuildIso(api)
        expected_result = [test_profile]

        # Act
        result = build_iso.filter_profiles(itemlist)

        # Assert
        assert expected_result == result

    def test_netboot_run(
        self,
        api,
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
        test_distro = Distro(api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        api.add_distro(test_distro)
        build_iso = NetbootBuildiso(api)
        iso_location = tmpdir.join("autoinst.iso")

        # Act
        build_iso.run(iso=str(iso_location), distro_name=test_distro.name)

        # Assert
        assert iso_location.exists()

    def test_standalone_run(
        self,
        api,
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
        test_distro = Distro(api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        api.add_distro(test_distro)
        build_iso = StandaloneBuildiso(api)

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
        self, api, create_kernel_initrd, fk_kernel, fk_initrd, cleanup_items
    ):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(api)
        test_distro.name = "testdistro"
        test_distro.breed = "suse"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        api.add_distro(test_distro)
        test_profile = Profile(api)
        test_profile.name = "testprofile"
        test_profile.distro = test_distro.name
        api.add_profile(test_profile)
        test_system = System(api)
        test_system.name = "testsystem"
        test_system.profile = test_profile.name
        api.add_system(test_system)
        blendered_data = utils.blender(api, False, test_system)
        test_builder = AppendLineBuilder(test_distro.name, blendered_data)

        # Act
        result = test_builder.generate_system(test_distro, test_system, False)

        # Assert
        # Very basic test yes but this is the expected result atm
        # TODO: Make tests more sophisticated
        assert (
            result
            == " append initrd=testdistro.img install=http://192.168.1.1:80/cblr/links/testdistro autoyast=default.ks"
        )

    def test_generate_profile(
        self, api, create_kernel_initrd, fk_kernel, fk_initrd, cleanup_items
    ):
        # Arrange
        folder = create_kernel_initrd(fk_kernel, fk_initrd)
        kernel_path = os.path.join(folder, fk_kernel)
        initrd_path = os.path.join(folder, fk_initrd)
        test_distro = Distro(api)
        test_distro.name = "testdistro"
        test_distro.kernel = kernel_path
        test_distro.initrd = initrd_path
        api.add_distro(test_distro)
        test_profile = Profile(api)
        test_profile.name = "testprofile"
        test_profile.distro = test_distro.name
        api.add_profile(test_profile)
        blendered_data = utils.blender(api, False, test_profile)
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
