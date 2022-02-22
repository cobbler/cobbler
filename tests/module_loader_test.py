import pytest

from cobbler.cexceptions import CX
from cobbler import module_loader
from tests.conftest import does_not_raise


@pytest.fixture(scope="function")
def reset_modules():
    module_loader.MODULE_CACHE = {}
    module_loader.MODULES_BY_CATEGORY = {}


@pytest.fixture(scope="function")
def load_modules():
    module_loader.load_modules()


def test_load_modules():
    # Arrange

    # Act
    module_loader.load_modules()

    # Assert
    assert module_loader.MODULE_CACHE != {}
    assert module_loader.MODULES_BY_CATEGORY != {}


@pytest.mark.usefixtures("reset_modules", "load_modules")
@pytest.mark.parametrize(
    "module_name",
    [
        ("nsupdate_add_system_post"),
        ("nsupdate_delete_system_pre"),
        ("scm_track"),
        ("sync_post_restart_services")
        # ("sync_post_wingen")
    ],
)
def test_get_module_by_name(module_name):
    # Arrange -> Done in fixtures

    # Act
    returned_module = module_loader.get_module_by_name(module_name)

    # Assert
    assert isinstance(returned_module.register(), str)


@pytest.mark.usefixtures("reset_modules", "load_modules")
@pytest.mark.parametrize(
    "module_section,fallback_name,expected_result,expected_exception",
    [
        ("authentication", "", "authentication.configfile", does_not_raise()),
        ("authorization", "", "authorization.allowall", does_not_raise()),
        ("dns", "", "managers.bind", does_not_raise()),
        ("dhcp", "", "managers.isc", does_not_raise()),
        ("tftpd", "", "managers.in_tftpd", does_not_raise()),
        ("wrong_section", None, "", pytest.raises(CX)),
        (
            "wrong_section",
            "authentication.configfile",
            "authentication.configfile",
            does_not_raise(),
        ),
    ],
)
def test_get_module_name(
    module_section, fallback_name, expected_result, expected_exception
):
    # Arrange -> Done in fixtures

    # Act
    with expected_exception:
        result_name = module_loader.get_module_name(
            module_section, "module", fallback_name
        )

        # Assert
        assert result_name == expected_result


@pytest.mark.usefixtures("reset_modules", "load_modules")
@pytest.mark.parametrize(
    "module_section,fallback_name,expected_exception",
    [
        ("authentication", "", does_not_raise()),
        ("authorization", "", does_not_raise()),
        ("dns", "", does_not_raise()),
        ("dhcp", "", does_not_raise()),
        ("tftpd", "", does_not_raise()),
        ("wrong_section", "", pytest.raises(CX)),
        ("wrong_section", "authentication.configfile", does_not_raise()),
    ],
)
def test_get_module_from_file(module_section, fallback_name, expected_exception):
    # Arrange -> Done in fixtures

    # Act
    with expected_exception:
        result_module = module_loader.get_module_from_file(
            module_section, "module", fallback_name
        )

        # Assert
        assert isinstance(result_module.register(), str)


@pytest.mark.usefixtures("reset_modules", "load_modules")
@pytest.mark.parametrize(
    "category,expected_names",
    [
        (
            "/var/lib/cobbler/triggers/add/system/post/*",
            ["cobbler.modules.nsupdate_add_system_post"],
        ),
        (
            "/var/lib/cobbler/triggers/sync/post/*",
            [
                "cobbler.modules.sync_post_restart_services",
                "cobbler.modules.sync_post_wingen",
            ],
        ),
        (
            "/var/lib/cobbler/triggers/delete/system/pre/*",
            ["cobbler.modules.nsupdate_delete_system_pre"],
        ),
        (
            "/var/lib/cobbler/triggers/change/*",
            ["cobbler.modules.managers.genders", "cobbler.modules.scm_track"],
        ),
        (
            "/var/lib/cobbler/triggers/install/post/*",
            [
                "cobbler.modules.installation.post_log",
                "cobbler.modules.installation.post_power",
                "cobbler.modules.installation.post_puppet",
                "cobbler.modules.installation.post_report",
            ],
        ),
        (
            "/var/lib/cobbler/triggers/install/pre/*",
            [
                "cobbler.modules.installation.pre_clear_anamon_logs",
                "cobbler.modules.installation.pre_log",
                "cobbler.modules.installation.pre_puppet",
            ],
        ),
        (
            "manage",
            [
                "cobbler.modules.managers.bind",
                "cobbler.modules.managers.dnsmasq",
                "cobbler.modules.managers.in_tftpd",
                "cobbler.modules.managers.isc",
                "cobbler.modules.managers.ndjbdns",
            ],
        ),
        ("manage/import", ["cobbler.modules.managers.import_signatures"]),
        (
            "serializer",
            ["cobbler.modules.serializers.file", "cobbler.modules.serializers.mongodb"],
        ),
        (
            "authz",
            [
                "cobbler.modules.authorization.allowall",
                "cobbler.modules.authorization.configfile",
                "cobbler.modules.authorization.ownership",
            ],
        ),
        (
            "authn",
            [
                "cobbler.modules.authentication.configfile",
                "cobbler.modules.authentication.denyall",
                "cobbler.modules.authentication.ldap",
                "cobbler.modules.authentication.pam",
                "cobbler.modules.authentication.passthru",
                "cobbler.modules.authentication.spacewalk",
            ],
        ),
    ],
)
def test_get_modules_in_category(category, expected_names):
    # Arrange -> Done in fixtures

    # Act
    result = module_loader.get_modules_in_category(category)

    # Assert
    assert len(result) > 0
    actual_result = []
    for name in result:
        actual_result.append(name.__name__)
    actual_result.sort()
    assert actual_result == expected_names
