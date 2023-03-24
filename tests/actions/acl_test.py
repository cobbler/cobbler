import pytest

from cobbler.actions import acl
from cobbler.cexceptions import CX

from tests.conftest import does_not_raise


@pytest.fixture(scope="function")
def acl_object(cobbler_api):
    return acl.AclConfig(cobbler_api)


def test_object_creation(cobbler_api):
    # Arrange & Act
    result = acl.AclConfig(cobbler_api)

    # Assert
    assert isinstance(result, acl.AclConfig)


@pytest.mark.parametrize(
    "input_adduser,input_addgroup,input_removeuser,input_removegroup,expected_isadd,expected_isuser, expected_who,"
    "expected_exception",
    [
        ("test", None, None, None, True, True, "test", does_not_raise()),
        (None, "test", None, None, True, False, "test", does_not_raise()),
        (None, None, "test", None, False, True, "test", does_not_raise()),
        (None, None, None, "test", False, False, "test", does_not_raise()),
        (None, None, None, None, True, True, "", pytest.raises(CX)),
    ],
)
def test_run(
    mocker,
    acl_object,
    input_adduser,
    input_addgroup,
    input_removeuser,
    input_removegroup,
    expected_isadd,
    expected_isuser,
    expected_who,
    expected_exception,
):
    # Arrange
    mock_modacl = mocker.patch.object(acl_object, "modacl")

    # Act
    with expected_exception:
        acl_object.run(
            input_adduser, input_addgroup, input_removeuser, input_removegroup
        )

        # Assert
        mock_modacl.assert_called_with(expected_isadd, expected_isuser, expected_who)


@pytest.mark.parametrize(
    "input_isadd,input_isuser,input_user,input_subprocess_call_effect,expected_mock_die_count,expected_first_setfacl",
    [
        (
            True,
            True,
            "test",
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            0,
            ["setfacl", "-d", "-R", "-m", "u:test:rwx", "/var/log/cobbler"],
        ),
        (
            True,
            False,
            "test",
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            0,
            ["setfacl", "-d", "-R", "-m", "g:test:rwx", "/var/log/cobbler"],
        ),
        (
            False,
            True,
            "test",
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            0,
            ["setfacl", "-d", "-R", "-x", "u:test", "/var/log/cobbler"],
        ),
        (
            False,
            False,
            "test",
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            0,
            ["setfacl", "-d", "-R", "-x", "g:test", "/var/log/cobbler"],
        ),
    ],
)
def test_modacl(
    mocker,
    acl_object,
    input_isadd,
    input_isuser,
    input_user,
    input_subprocess_call_effect,
    expected_mock_die_count,
    expected_first_setfacl,
):
    # Arrange
    # Each subprocess.call is used two times per directory of which we have (seven in a default config)
    mock_subprocess_call = mocker.patch(
        "cobbler.utils.subprocess_call", side_effect=input_subprocess_call_effect
    )
    mock_die = mocker.patch("cobbler.utils.die")

    # Act
    acl_object.modacl(input_isadd, input_isuser, input_user)

    # Assert
    print(mock_subprocess_call.mock_calls)
    mock_subprocess_call.assert_any_call(expected_first_setfacl, shell=False)
    assert mock_die.call_count == expected_mock_die_count
