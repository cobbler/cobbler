import pytest
from unittest.mock import Mock, MagicMock, create_autospec, PropertyMock

import cobbler.actions.sync
import cobbler.modules.managers.bind
import cobbler.modules.managers.isc
from cobbler.api import CobblerAPI
from cobbler.items.image import Image
from tests.conftest import does_not_raise


@pytest.mark.parametrize("input_verbose,input_what,expected_exception", [
    (None, None, does_not_raise()),
    (True, [], does_not_raise()),
    (False, [], does_not_raise()),
    (True, ["dhcp"], does_not_raise()),
    (True, ["dns"], does_not_raise()),
    (True, ["dns", "dhcp"], does_not_raise())
])
def test_sync(input_verbose, input_what, expected_exception, mocker):
    # Arrange
    stub = create_autospec(spec=cobbler.actions.sync.CobblerSync)
    stub_dhcp = mocker.stub()
    stub_dns = mocker.stub()
    mocker.patch.object(CobblerAPI, "get_sync", return_value=stub)
    mocker.patch.object(CobblerAPI, "sync_dhcp", new=stub_dhcp)
    mocker.patch.object(CobblerAPI, "sync_dns", new=stub_dns)
    test_api = CobblerAPI()

    # Act
    with expected_exception:
        test_api.sync(input_verbose, input_what)

    # Assert
    if not input_what:
        stub.run.assert_called_once()
    if input_what and "dhcp" in input_what:
        stub_dhcp.assert_called_once()
    if input_what and "dns" in input_what:
        stub_dns.assert_called_once()


@pytest.mark.parametrize("input_manage_dns", [
    (True),
    (False)
])
def test_sync_dns(input_manage_dns, mocker):
    # Arrange
    mock = MagicMock()
    m_property = PropertyMock(return_value=input_manage_dns)
    type(mock).manage_dns = m_property
    mocker.patch.object(CobblerAPI, "settings", return_value=mock)

    # mock get_manager() and ensure mock object has the same api as the object it is replacing.
    # see https://docs.python.org/3/library/unittest.mock.html#unittest.mock.create_autospec
    stub = create_autospec(spec=cobbler.modules.managers.bind._BindManager)
    mocker.patch("cobbler.modules.managers.bind.get_manager", return_value=stub)
    test_api = CobblerAPI()

    # Act
    test_api.sync_dns()

    # Assert
    m_property.assert_called_once()
    assert stub.sync.called == input_manage_dns


@pytest.mark.parametrize("input_manager_dhcp", [
    (True),
    (False)
])
def test_sync_dhcp(input_manager_dhcp, mocker):
    # Arrange
    mock = MagicMock()
    m_property = PropertyMock(return_value=input_manager_dhcp)
    type(mock).manage_dhcp = m_property
    mocker.patch.object(CobblerAPI, "settings", return_value=mock)

    stub = create_autospec(spec=cobbler.modules.managers.isc._IscManager)
    mocker.patch("cobbler.modules.managers.isc.get_manager", return_value=stub)
    test_api = CobblerAPI()

    # Act
    test_api.sync_dhcp()

    # Assert
    m_property.assert_called_once()
    assert stub.sync.called == input_manager_dhcp


def test_get_sync(mocker):
    # Arrange
    stub = Mock()
    mocker.patch.object(CobblerAPI, "get_module_from_file", new=stub)
    test_api = CobblerAPI()

    # Act
    result = test_api.get_sync()

    # Assert
    # has to be called 3 times by the method
    assert stub.call_count == 3
    assert isinstance(result, cobbler.actions.sync.CobblerSync)


@pytest.mark.parametrize("input_verbose,input_systems,expected_exception", [
    (None, ["t1.systems.de"], does_not_raise()),
    (True, ["t1.systems.de"], does_not_raise()),
    (False, ["t1.systems.de"], does_not_raise()),
    (False, [42], pytest.raises(TypeError)),
    (False, "t1.systems.de", pytest.raises(TypeError))
])
def test_sync_systems(input_systems, input_verbose, expected_exception, mocker):
    # Arrange
    stub = create_autospec(spec=cobbler.actions.sync.CobblerSync)
    mocker.patch.object(CobblerAPI, "get_sync", return_value=stub)
    test_api = CobblerAPI()

    # Act
    with expected_exception:
        test_api.sync_systems(input_systems, input_verbose)

        # Assert
        stub.run_sync_systems.assert_called_once()
        stub.run_sync_systems.assert_called_with(input_systems)


def test_image_rename():
    # Arrange
    test_api = CobblerAPI()
    testimage = Image(test_api)
    testimage.name = "myimage"
    test_api.add_image(testimage, save=False)

    # Act
    test_api.rename_image(testimage, "new_name")

    # Assert
    assert test_api.images().get("new_name")
    assert test_api.images().get("myimage") is None
