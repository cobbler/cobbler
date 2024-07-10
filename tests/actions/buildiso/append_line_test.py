from cobbler.actions.buildiso.netboot import AppendLineBuilder
from cobbler import utils


def test_init():
    assert isinstance(AppendLineBuilder("", {}), AppendLineBuilder)


def test_generate_system(
    request, cobbler_api, create_distro, create_profile, create_system
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
        == "  APPEND initrd=/%s.img install=http://192.168.1.1:80/cblr/links/%s autoyast=default.ks"
        % (test_distro.name, test_distro.name)
    )


def test_generate_profile(request, cobbler_api, create_distro, create_profile):
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
        == "  APPEND initrd=/%s.img install=http://192.168.1.1:80/cblr/links/%s autoyast=default.ks"
        % (test_distro.name, test_distro.name)
    )
