"""
Tests that validate the functionality of the module that is responsible for generating auto-installation control files.
"""

from typing import TYPE_CHECKING, Any, Callable

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.autoinstall import manager
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.items.template import Template

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_create_autoinstallation_manager(cobbler_api: CobblerAPI):
    """
    Verify that the autoinstallation manager object can be created successfully.
    """
    # Arrange

    # Act
    result = manager.AutoInstallationManager(cobbler_api)

    # Assert
    assert isinstance(result, manager.AutoInstallationManager)


def test_is_autoinstall_in_use(cobbler_api: CobblerAPI):
    """
    Test to verify that the method correctly identifies when autoinstall template is not in use.
    """
    # Arrange
    test_manager = manager.AutoInstallationManager(cobbler_api)
    template = cobbler_api.find_template(False, False, name="built-in-legacy.ks")
    assert isinstance(template, Template)

    # Act
    result = test_manager.is_autoinstall_in_use(template)

    # Assert
    assert not result


def test_validate_autoinstall_file(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test to verify that the autoinstall file validation method works as expected.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    expected_result = manager.AutoinstallValidationResult(
        True, enums.AutoinstallValidationError.NONE, ()
    )
    test_manager = manager.AutoInstallationManager(cobbler_api)

    # Act
    result = test_manager.validate_autoinstall_file(test_profile)

    # Assert
    assert result == expected_result


def test_validate_autoinstall_files(cobbler_api: CobblerAPI):
    """
    Test to verify that the method for validating all autoinstall files returns True when all files are valid.
    """
    # Arrange
    test_manager = manager.AutoInstallationManager(cobbler_api)

    # Act
    result = test_manager.validate_autoinstall_files()

    # Assert
    assert result


def test_validate_autoinstall_files_continues_after_generation_error(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Any,
):
    """
    A generator exception for one profile (e.g. cloud-init's "needs a valid
    autoinstaller subfile" ValueError) must not abort validation of the other
    profiles still queued.
    """
    # Arrange
    test_distro = create_distro()
    failing_profile = create_profile(test_distro.uid, name="failing-profile")
    healthy_profile = create_profile(test_distro.uid, name="healthy-profile")
    test_manager = manager.AutoInstallationManager(cobbler_api)

    def fake_generate_autoinstall(obj: Any, _template: Any) -> str:
        if obj.uid == failing_profile.uid:
            raise ValueError("needs a valid autoinstaller subfile")
        return "Success"

    mocker.patch.object(
        test_manager, "generate_autoinstall", side_effect=fake_generate_autoinstall
    )
    validate_spy = mocker.spy(test_manager, "validate_autoinstall_file")

    # Act
    result = test_manager.validate_autoinstall_files()

    # Assert
    assert not result
    validated_objs = [call.args[0] for call in validate_spy.call_args_list]
    assert failing_profile in validated_objs
    assert healthy_profile in validated_objs


def test_log_autoinstall_validation_errors_identifies_failing_item(
    caplog: pytest.LogCaptureFixture,
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Any,
):
    """
    The warning logged for a failed validation must identify which profile/system
    failed, not just the error content - otherwise a failure is unactionable when
    more than one profile/system is validated.
    """
    # Arrange
    test_distro = create_distro()
    failing_profile = create_profile(test_distro.uid, name="failing-profile")
    test_manager = manager.AutoInstallationManager(cobbler_api)
    mocker.patch.object(
        test_manager,
        "generate_autoinstall",
        side_effect=ValueError("needs a valid autoinstaller subfile"),
    )

    # Act
    with caplog.at_level("WARNING"):
        test_manager.validate_autoinstall_files()

    # Assert
    assert any(failing_profile.name in record.getMessage() for record in caplog.records)


def test_get_last_errors(cobbler_api: CobblerAPI):
    """
    Test to verify that the method for retrieving the last errors returns the expected list of errors.
    """
    # Arrange
    expected_result = [{"success": True}]
    test_manager = manager.AutoInstallationManager(cobbler_api)
    cobbler_api.templar.last_errors = expected_result

    # Act
    result = test_manager.get_last_errors()

    # Assert
    assert result == expected_result


@pytest.mark.parametrize(
    "input_template_type",
    [
        enums.AutoinstallerType.AUTOYAST,
        enums.AutoinstallerType.AGAMA,
        enums.AutoinstallerType.LEGACY,
        enums.AutoinstallerType.KICKSTART,
        enums.AutoinstallerType.PRESEED,
        enums.AutoinstallerType.CLOUDINIT,
    ],
)
def test_generate_autoinstall(
    mocker: "MockerFixture",
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    input_template_type: enums.AutoinstallerType,
):
    """
    Test to verify that the autoinstall generation method returns the expected result for various template types.
    """
    # Arrange
    expected_result = "Success"
    test_manager = manager.AutoInstallationManager(cobbler_api)
    mocker.patch(
        "cobbler.autoinstall.generate.agama.AgamaGenerator.generate_autoinstall",
        return_value=expected_result,
    )
    mocker.patch(
        "cobbler.autoinstall.generate.autoyast.AutoYaSTGenerator.generate_autoinstall",
        return_value=expected_result,
    )
    mocker.patch(
        "cobbler.autoinstall.generate.cloud_init.CloudInitGenerator.generate_autoinstall",
        return_value=expected_result,
    )
    mocker.patch(
        "cobbler.autoinstall.generate.kickstart.KickstartGenerator.generate_autoinstall",
        return_value=expected_result,
    )
    mocker.patch(
        "cobbler.autoinstall.generate.legacy.LegacyGenerator.generate_autoinstall",
        return_value=expected_result,
    )
    mocker.patch(
        "cobbler.autoinstall.generate.preseed.PreseedGenerator.generate_autoinstall",
        return_value=expected_result,
    )
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_template = Template(cobbler_api, name="test-template")
    test_template.tags = {input_template_type.value}

    # Act
    result = test_manager.generate_autoinstall(test_profile, test_template)

    # Assert
    assert result == expected_result
