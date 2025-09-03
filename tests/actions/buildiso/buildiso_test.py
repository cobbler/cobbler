"""
Tests that validate the functionality of the module that is responsible for building bootable ISOs.
"""

import os
from typing import Any, Callable, Dict, List

import pytest

from cobbler import enums
from cobbler.actions import buildiso
from cobbler.actions.buildiso import LoaderCfgsParts
from cobbler.actions.buildiso.netboot import NetbootBuildiso
from cobbler.actions.buildiso.standalone import StandaloneBuildiso
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.profile import Profile
from cobbler.items.system import System

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
    input_arch: enums.Archs,
    result_binary_name: str,
    expected_exception: Any,
    cobbler_api: CobblerAPI,
):
    """
    Test to verify that the correct grub binary name is calculated based on the architecture.
    """
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
def test_add_remaining_kopts(input_kopts_dict: Dict[str, Any], exepcted_output: str):
    """
    Test to verify that the kernel options are correctly formatted and added.
    """
    # Arrange (missing)
    # Act
    output = buildiso.add_remaining_kopts(input_kopts_dict)

    # Assert
    assert output == exepcted_output


def test_make_shorter(cobbler_api: CobblerAPI):
    """
    Test to verify that the make_shorter function generates a shorter unique identifier
    for a given distribution name and maintains a mapping.
    """
    # Arrange
    build_iso = NetbootBuildiso(cobbler_api)
    distroname = "Testdistro"

    # Act
    result = build_iso.make_shorter(distroname)

    # Assert
    assert isinstance(result, str)
    assert distroname in build_iso.distmap
    assert result == "1"


def test_copy_boot_files(
    cobbler_api: CobblerAPI, create_distro: Callable[[], Distro], tmpdir: Any
):
    """
    Test to verify that the boot files (kernel and initrd) are correctly copied to the target folder.
    """
    # Arrange
    target_folder: str = tmpdir.mkdir("target")
    build_iso = buildiso.BuildIso(cobbler_api)
    testdistro = create_distro()

    # Act
    # pylint: disable-next=protected-access
    build_iso._copy_boot_files(testdistro.kernel, testdistro.initrd, target_folder)  # type: ignore[reportPrivateUsage]

    # Assert
    assert len(os.listdir(target_folder)) == 2


def test_netboot_generate_boot_loader_configs(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
):
    """
    Test to verify that the boot loader configurations are correctly generated for both isolinux and grub,
    including kernel options from distro, profile, and system levels.
    """
    test_distro = create_distro()
    test_distro.kernel_options = "test_distro_option=distro"  # type: ignore
    test_profile = create_profile(test_distro.uid)
    test_profile.kernel_options = "test_profile_option=profile"  # type: ignore
    test_system = create_system(test_profile.uid)
    test_system.kernel_options = "test_system_option=system"  # type: ignore
    build_iso = NetbootBuildiso(cobbler_api)

    # Act
    # pylint: disable-next=protected-access
    result = build_iso._generate_boot_loader_configs(  # type: ignore[reportPrivateUsage]
        [test_profile], [test_system], True
    )
    matching_isolinux_kernel = [
        part for part in result.isolinux if "KERNEL /1.krn" in part
    ]
    matching_isolinux_initrd = [
        part for part in result.isolinux if "initrd=/1.img" in part
    ]
    matching_grub_kernel = [part for part in result.grub if "linux /1.krn" in part]
    matching_grub_initrd = [part for part in result.grub if "initrd /1.img" in part]
    matching_grub_distro_kopts = [
        part for part in result.grub if "test_distro_option=distro" in part
    ]
    matching_grub_profile_kopts = [
        part for part in result.grub if "test_profile_option=profile" in part
    ]
    matching_grub_system_kopts = [
        part for part in result.grub if "test_system_option=system" in part
    ]
    matching_isolinux_distro_kopts = [
        part for part in result.isolinux if "test_distro_option=distro" in part
    ]
    matching_isolinux_profile_kopts = [
        part for part in result.isolinux if "test_profile_option=profile" in part
    ]
    matching_isolinux_system_kopts = [
        part for part in result.isolinux if "test_system_option=system" in part
    ]

    # Assert
    assert isinstance(result, LoaderCfgsParts)
    for iterable_to_check in [
        matching_isolinux_kernel,
        matching_isolinux_initrd,
        matching_grub_kernel,
        matching_grub_initrd,
        result.bootfiles_copysets,
        matching_grub_distro_kopts,
        matching_grub_profile_kopts,
        matching_isolinux_distro_kopts,
        matching_isolinux_profile_kopts,
    ]:
        print(iterable_to_check)
        # one entry for the profile, one for the system
        assert len(iterable_to_check) == 2  # type: ignore

    # only system entries have system kernel opts
    assert len(matching_grub_system_kopts) == 1
    assert len(matching_isolinux_system_kopts) == 1


def test_netboot_generate_boot_loader_config_for_profile_only(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Callable[[str], System],
):
    """
    Test to verify that the boot loader configurations are correctly generated for both isolinux and grub,
    including kernel options from distro and profile levels, but not system level when no systems are provided
    """
    test_distro = create_distro()
    test_distro.kernel_options = "test_distro_option=distro"  # type: ignore
    test_profile = create_profile(test_distro.uid)
    test_profile.kernel_options = "test_profile_option=profile"  # type: ignore
    test_system = create_system(test_profile.uid)
    test_system.kernel_options = "test_system_option=system"  # type: ignore
    build_iso = NetbootBuildiso(cobbler_api)

    # Act
    # pylint: disable-next=protected-access
    result = build_iso._generate_boot_loader_configs([test_profile], [], True)  # type: ignore[reportPrivateUsage]
    matching_isolinux_kernel = [
        part for part in result.isolinux if "KERNEL /1.krn" in part
    ]
    matching_isolinux_initrd = [
        part for part in result.isolinux if "initrd=/1.img" in part
    ]
    matching_grub_kernel = [part for part in result.grub if "linux /1.krn" in part]
    matching_grub_initrd = [part for part in result.grub if "initrd /1.img" in part]
    matching_grub_distro_kopts = [
        part for part in result.grub if "test_distro_option=distro" in part
    ]
    matching_grub_profile_kopts = [
        part for part in result.grub if "test_profile_option=profile" in part
    ]
    matching_grub_system_kopts = [
        part for part in result.grub if "test_system_option=system" in part
    ]
    matching_isolinux_distro_kopts = [
        part for part in result.isolinux if "test_distro_option=distro" in part
    ]
    matching_isolinux_profile_kopts = [
        part for part in result.isolinux if "test_profile_option=profile" in part
    ]
    matching_isolinux_system_kopts = [
        part for part in result.isolinux if "test_system_option=system" in part
    ]

    # Assert
    assert isinstance(result, LoaderCfgsParts)
    for iterable_to_check in [
        matching_isolinux_kernel,
        matching_isolinux_initrd,
        matching_grub_kernel,
        matching_grub_initrd,
        result.bootfiles_copysets,
        matching_grub_distro_kopts,
        matching_grub_profile_kopts,
        matching_isolinux_distro_kopts,
        matching_isolinux_profile_kopts,
    ]:
        print(iterable_to_check)
        # one entry for the profile, and none for the system
        assert len(iterable_to_check) == 1  # type: ignore

    # there are no system entries
    assert len(matching_grub_system_kopts) == 0
    assert len(matching_isolinux_system_kopts) == 0


def test_filter_system(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    create_system: Any,
    create_image: Callable[[], Image],
):
    """
    Test to verify that the filter_systems function correctly filters systems based on provided names,
    considering both profile and image associations.
    """
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system_profile = create_system(profile_uid=test_profile.uid)
    test_image = create_image()
    test_system_image: System = create_system(
        image_uid=test_image.uid, name="test_filter_system_image_image"
    )
    itemlist = [test_system_profile.name, test_system_image.name]
    build_iso = NetbootBuildiso(cobbler_api)
    expected_result = [test_system_profile]

    # Act
    result = build_iso.filter_systems(itemlist)

    # Assert
    assert expected_result == result


def test_filter_profile(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that the filter_profiles function correctly filters profiles based on provided names.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    itemlist = [test_profile.name]
    build_iso = buildiso.BuildIso(cobbler_api)
    expected_result = [test_profile]

    # Act
    result = build_iso.filter_profiles(itemlist)

    # Assert
    assert expected_result == result


def test_filter_profile_disabled(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that the filter_profiles function correctly excludes disabled profiles.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.enable_menu = False  # type: ignore
    itemlist = [test_profile.name]
    build_iso = buildiso.BuildIso(cobbler_api)
    expected_result: List[Any] = []  # No enabled profiles

    # Act
    result = build_iso.filter_profiles(itemlist)

    # Assert
    assert expected_result == result


def test_netboot_run(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    tmpdir: Any,
):
    """
    Test to verify that a netboot ISO can be built and the output file is created.
    """
    # Arrange
    test_distro = create_distro()
    create_profile(test_distro.uid)
    build_iso = NetbootBuildiso(cobbler_api)
    iso_location = tmpdir.join("autoinst.iso")

    # Act
    build_iso.run(iso=str(iso_location), distro_name=test_distro.name)

    # Assert
    assert iso_location.exists()


def test_netboot_run_autodetect_distro(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    tmpdir: Any,
):
    """
    Test to verify that a netboot ISO can be built by autodetecting the distro from the profile.
    """
    # Arrange
    test_distro = create_distro()
    create_profile(test_distro.uid)
    build_iso = NetbootBuildiso(cobbler_api)
    iso_location = tmpdir.join("autoinst.iso")

    # Act
    build_iso.run(iso=str(iso_location))

    # Assert
    assert iso_location.exists()


def test_standalone_run(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    tmpdir_factory: pytest.TempPathFactory,
):
    """
    Test to verify that a standalone ISO can be built and the output file is created.
    """
    # Arrange
    iso_directory = tmpdir_factory.mktemp("isodir")
    iso_source = tmpdir_factory.mktemp("isosource")
    iso_location: Any = iso_directory.join("autoinst.iso")  # type: ignore
    test_distro = create_distro()
    build_iso = StandaloneBuildiso(cobbler_api)

    # Act
    build_iso.run(
        iso=str(iso_location), distro_name=test_distro.name, source=str(iso_source)  # type: ignore
    )

    # Assert
    assert iso_location.exists()  # type: ignore


def test_standalone_run_autodetect_distro(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    tmpdir_factory: pytest.TempPathFactory,
):
    """
    Test to verify that a standalone ISO can be built by autodetecting the distro from the profile.
    """
    # Arrange
    iso_directory = tmpdir_factory.mktemp("isodir")
    iso_source = tmpdir_factory.mktemp("isosource")
    iso_location: Any = iso_directory.join("autoinst.iso")  # type: ignore
    test_distro = create_distro()
    create_profile(test_distro.uid)
    build_iso = StandaloneBuildiso(cobbler_api)

    # Act
    build_iso.run(iso=str(iso_location), source=str(iso_source))  # type: ignore

    # Assert
    assert iso_location.exists()  # type: ignore
