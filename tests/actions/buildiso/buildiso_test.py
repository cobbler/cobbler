import os

import pytest

from cobbler import enums
from cobbler.actions import buildiso
from cobbler.actions.buildiso import LoaderCfgsParts
from cobbler.actions.buildiso.netboot import NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso
from tests.conftest import does_not_raise


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
    input_arch,
    result_binary_name,
    expected_exception,
    cobbler_api,
):
    # Arrange
    test_builder = buildiso.BuildIso(cobbler_api)

    # Act
    with expected_exception:
        result = test_builder.calculate_grub_name(input_arch)

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
def test_add_remaining_kopts(input_kopts_dict, exepcted_output):
    # Arrange (missing)
    # Act
    output = buildiso.add_remaining_kopts(input_kopts_dict)

    # Assert
    assert output == exepcted_output


def test_make_shorter(cobbler_api):
    # Arrange
    build_iso = NetbootBuildiso(cobbler_api)
    distroname = "Testdistro"

    # Act
    result = build_iso.make_shorter(distroname)

    # Assert
    assert type(result) == str
    assert distroname in build_iso.distmap
    assert result == "1"


def test_copy_boot_files(cobbler_api, create_distro, tmpdir):
    # Arrange
    target_folder = tmpdir.mkdir("target")
    build_iso = buildiso.BuildIso(cobbler_api)
    testdistro = create_distro()

    # Act
    build_iso._copy_boot_files(testdistro.kernel, testdistro.initrd, target_folder)

    # Assert
    assert len(os.listdir(target_folder)) == 2

def test_netboot_generate_boot_loader_configs(
    cobbler_api, create_distro, create_profile, create_system
):
    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    test_system = create_system(test_profile.name)
    build_iso = NetbootBuildiso(cobbler_api)

    # Act
    result = build_iso._generate_boot_loader_configs(
        [test_profile.name], [test_system.name], True
    )
    matching_isolinux_kernel = [
        part for part in result.isolinux if "KERNEL /1.krn" in part
    ]
    matching_isolinux_initrd = [
        part for part in result.isolinux if "initrd=/1.img" in part
    ]
    matching_grub_kernel = [part for part in result.grub if "linux /1.krn" in part]
    matching_grub_initrd = [part for part in result.grub if "initrd /1.img" in part]

    # Assert
    assert isinstance(result, LoaderCfgsParts)
    for iterable_to_check in [
        matching_isolinux_kernel,
        matching_isolinux_initrd,
        matching_grub_kernel,
        matching_grub_initrd,
        result.bootfiles_copysets,
    ]:
        print(iterable_to_check)
        # one entry for the profile, one for the system
        assert len(iterable_to_check) == 2



def test_filter_system(cobbler_api, create_distro, create_profile, create_system):
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


def test_filter_profile(cobbler_api, create_distro, create_profile):
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
