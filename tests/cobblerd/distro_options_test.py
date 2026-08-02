from pytest_mock import MockerFixture

from cobbler.cobblerd.distro_options import get_distro_options


def test_redhat_efi_loader_folders_use_package_paths(mocker: MockerFixture):
    mocker.patch("cobbler.cobblerd.distro_options.get_family", return_value="redhat")

    result = get_distro_options()

    assert result.shim_folder == r"/usr/share/efi/*/"
    assert result.secure_grub_folder == r"/usr/share/efi/*/"
    assert "/boot/efi" not in result.shim_folder
    assert "/boot/efi" not in result.secure_grub_folder
