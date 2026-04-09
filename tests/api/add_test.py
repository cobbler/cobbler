"""
Tests that are ensuring the correct functionality of the CobblerAPI in regard to adding items via it.
"""

import json
import pathlib
from typing import Callable

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.distro_group import DistroGroup
from cobbler.items.image import Image
from cobbler.items.menu import Menu
from cobbler.items.network_interface import NetworkInterface
from cobbler.items.profile import Profile
from cobbler.items.profile_group import ProfileGroup
from cobbler.items.repo import Repo
from cobbler.items.system import System
from cobbler.items.system_group import SystemGroup
from cobbler.items.template import Template


def test_distro_add(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    test_distro = Distro(cobbler_api)
    test_distro.name = "test_cobbler_api_add_distro"
    test_distro.kernel = str(pathlib.Path(folder) / fk_kernel)
    test_distro.initrd = str(pathlib.Path(folder) / fk_initrd)

    # Act
    cobbler_api.add_distro(test_distro)

    # Assert
    result_distro_json = next(
        pathlib.Path("/var/lib/cobbler/collections/distros/").iterdir()
    )
    assert result_distro_json.exists()
    json_content = json.loads(result_distro_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_distro.name


def test_distro_group_add(cobbler_api: CobblerAPI):
    # Arrange
    test_distro_group = DistroGroup(cobbler_api)
    test_distro_group.name = "test_cobbler_api_add_distro_group"

    # Act
    cobbler_api.add_distro_group(test_distro_group)

    # Assert
    result_distro_group_json = next(
        pathlib.Path("/var/lib/cobbler/collections/distro_groups/").iterdir()
    )
    assert result_distro_group_json.exists()
    json_content = json.loads(result_distro_group_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_distro_group.name


def test_image_add(cobbler_api: CobblerAPI):
    # Arrange
    test_image = Image(cobbler_api)
    test_image.name = "test_cobbler_api_add_image"

    # Act
    cobbler_api.add_image(test_image)

    # Assert
    result_image_json = next(
        pathlib.Path("/var/lib/cobbler/collections/images/").iterdir()
    )
    assert result_image_json.exists()
    json_content = json.loads(result_image_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_image.name


def test_menu_add(cobbler_api: CobblerAPI):
    # Arrange
    test_menu = Menu(cobbler_api)
    test_menu.name = "test_cobbler_api_add_menu"

    # Act
    cobbler_api.add_menu(test_menu)

    # Assert
    result_menu_json = next(
        pathlib.Path("/var/lib/cobbler/collections/menus/").iterdir()
    )
    assert result_menu_json.exists()
    json_content = json.loads(result_menu_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_menu.name


def test_network_interface_add(cobbler_api: CobblerAPI):
    # Arrange
    test_network_interface = NetworkInterface(cobbler_api, system_uid="test_uid")
    test_network_interface.name = "test_cobbler_api_add_network_interface"

    # Act
    cobbler_api.add_network_interface(test_network_interface)

    # Assert
    result_network_interface_json = next(
        pathlib.Path("/var/lib/cobbler/collections/network_interfaces/").iterdir()
    )
    assert result_network_interface_json.exists()
    json_content = json.loads(result_network_interface_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_network_interface.name


def test_profile_add(cobbler_api: CobblerAPI, create_distro: Callable[[], Distro]):
    # Arrange
    test_distro = create_distro()
    test_profile = Profile(cobbler_api)
    test_profile.name = "test_cobbler_api_add_profile"
    test_profile.distro = test_distro

    # Act
    cobbler_api.add_profile(test_profile)

    # Assert
    result_profile_json = next(
        pathlib.Path("/var/lib/cobbler/collections/profiles/").iterdir()
    )
    assert result_profile_json.exists()
    json_content = json.loads(result_profile_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_profile.name


def test_profile_group_add(cobbler_api: CobblerAPI):
    # Arrange
    test_profile_group = ProfileGroup(cobbler_api)
    test_profile_group.name = "test_cobbler_api_add_profile_group"

    # Act
    cobbler_api.add_profile_group(test_profile_group)

    # Assert
    result_profile_group_json = next(
        pathlib.Path("/var/lib/cobbler/collections/profile_groups/").iterdir()
    )
    assert result_profile_group_json.exists()
    json_content = json.loads(result_profile_group_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_profile_group.name


def test_repo_add(cobbler_api: CobblerAPI):
    # Arrange
    test_repo = Repo(cobbler_api)
    test_repo.name = "test_cobbler_api_add_repo"

    # Act
    cobbler_api.add_repo(test_repo)

    # Assert
    result_repo_json = next(
        pathlib.Path("/var/lib/cobbler/collections/repos/").iterdir()
    )
    assert result_repo_json.exists()
    json_content = json.loads(result_repo_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_repo.name


def test_system_add(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_system = System(cobbler_api)
    test_system.name = "test_cobbler_api_add_system"
    test_system.profile = test_profile

    # Act
    cobbler_api.add_system(test_system)

    # Assert
    result_system_json = next(
        pathlib.Path("/var/lib/cobbler/collections/systems/").iterdir()
    )
    assert result_system_json.exists()
    json_content = json.loads(result_system_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_system.name


def test_system_group_add(cobbler_api: CobblerAPI):
    # Arrange
    test_system_group = SystemGroup(cobbler_api)
    test_system_group.name = "test_cobbler_api_add_system_group"

    # Act
    cobbler_api.add_system_group(test_system_group)

    # Assert
    result_system_group_json = next(
        pathlib.Path("/var/lib/cobbler/collections/system_groups/").iterdir()
    )
    assert result_system_group_json.exists()
    json_content = json.loads(result_system_group_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_system_group.name


def test_template_add(cobbler_api: CobblerAPI):
    # Arrange
    test_template = Template(cobbler_api)
    test_template.name = "test_cobbler_api_add_template"
    test_template.template_type = "jinja"

    # Act
    cobbler_api.add_template(test_template)

    # Assert
    result_template_json = next(
        pathlib.Path("/var/lib/cobbler/collections/templates/").iterdir()
    )
    assert result_template_json.exists()
    json_content = json.loads(result_template_json.read_text(encoding="UTF-8"))
    assert json_content.get("name") == test_template.name


def test_case_sensitive_add(
    cobbler_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Test that two items with the same characters in different casing can be successfully added and edited.
    """
    # Arrange
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    name = "TestName"
    item1 = cobbler_api.new_distro()
    item1.name = name
    item1.kernel = str(pathlib.Path(folder) / fk_kernel)
    item1.initrd = str(pathlib.Path(folder) / fk_initrd)
    cobbler_api.add_distro(item1)
    item2 = cobbler_api.new_distro()
    item2.name = name.lower()
    item2.kernel = str(pathlib.Path(folder) / fk_kernel)
    item2.initrd = str(pathlib.Path(folder) / fk_initrd)

    # Act
    cobbler_api.add_distro(item2)
    cobbler_api.remove_distro(item1.name)
    result_item = cobbler_api.get_item("distro", item2.name)

    # Assert
    assert result_item is not None
    assert result_item.uid == item2.uid
    assert cobbler_api.get_item("distro", item1.name) is None
