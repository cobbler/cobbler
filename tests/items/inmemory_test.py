"""
TODO
"""

import os
import pathlib
from typing import Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.cobbler_collections import manager
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.menu import Menu
from cobbler.items.profile import Profile
from cobbler.items.repo import Repo
from cobbler.items.system import System


@pytest.fixture(scope="function")
def inmemory_api() -> CobblerAPI:
    """
    TODO
    """
    CobblerAPI.__shared_state = {}
    CobblerAPI.__has_loaded = False
    api = CobblerAPI()
    api.settings().lazy_start = True
    manager.CollectionManager.has_loaded = False
    manager.CollectionManager.__shared_state = {}
    api._collection_mgr = manager.CollectionManager(api)
    return api


def test_inmemory(
    inmemory_api: CobblerAPI,
    create_kernel_initrd: Callable[[str, str], str],
    fk_initrd: str,
    fk_kernel: str,
):
    """
    TODO
    """
    # Arrange
    test_repo = Repo(inmemory_api, **{"name": "test_repo", "comment": "test comment"})
    inmemory_api.add_repo(test_repo)
    test_menu1 = Menu(inmemory_api, **{"name": "test_menu1", "comment": "test comment"})
    inmemory_api.add_menu(test_menu1)
    test_menu2 = Menu(
        inmemory_api,
        **{
            "name": "test_menu2",
            "parent": test_menu1.name,
            "comment": "test comment",
        },
    )
    inmemory_api.add_menu(test_menu2)

    directory = create_kernel_initrd(fk_kernel, fk_initrd)
    (pathlib.Path(directory) / "images").mkdir()
    test_distro = Distro(
        inmemory_api,
        **{
            "name": "test_distro",
            "kernel": str(os.path.join(directory, fk_kernel)),
            "initrd": str(os.path.join(directory, fk_initrd)),
            "comment": "test comment",
        },
    )
    inmemory_api.add_distro(test_distro)

    test_profile1 = Profile(
        inmemory_api,
        **{
            "name": "test_profile1",
            "distro": test_distro.name,
            "enable_menu": False,
            "repos": [test_repo.name],
            "menu": test_menu1.name,
            "comment": "test comment",
        },
    )
    inmemory_api.add_profile(test_profile1)
    test_profile2 = Profile(
        inmemory_api,
        **{
            "name": "test_profile2",
            "parent": test_profile1.name,
            "enable_menu": False,
            "menu": test_menu2.name,
            "comment": "test comment",
        },
    )
    inmemory_api.add_profile(test_profile2)
    test_profile3 = Profile(
        inmemory_api,
        **{
            "name": "test_profile3",
            "parent": test_profile1.name,
            "enable_menu": False,
            "repos": [test_repo.name],
            "menu": test_menu1.name,
            "comment": "test comment",
        },
    )
    inmemory_api.add_profile(test_profile3)
    test_image = Image(
        inmemory_api,
        **{"name": "test_image", "menu": test_menu1.name, "comment": "test comment"},
    )
    inmemory_api.add_image(test_image)
    test_system1 = System(
        inmemory_api,
        **{
            "name": "test_system1",
            "profile": test_profile1.name,
            "comment": "test comment",
        },
    )
    inmemory_api.add_system(test_system1)
    test_system2 = System(
        inmemory_api,
        **{"name": "test_system2", "image": test_image.name, "comment": "test comment"},
    )
    inmemory_api.add_system(test_system2)

    inmemory_api.systems().listing.pop(test_system2.name)
    inmemory_api.systems().listing.pop(test_system1.name)
    inmemory_api.images().listing.pop(test_image.name)
    inmemory_api.profiles().listing.pop(test_profile3.name)
    inmemory_api.profiles().listing.pop(test_profile2.name)
    inmemory_api.profiles().listing.pop(test_profile1.name)
    inmemory_api.distros().listing.pop(test_distro.name)
    inmemory_api.menus().listing.pop(test_menu2.name)
    inmemory_api.menus().listing.pop(test_menu1.name)
    inmemory_api.repos().listing.pop(test_repo.name)

    inmemory_api.deserialize()

    test_repo = inmemory_api.find_repo("test_repo")
    test_menu1 = inmemory_api.find_menu("test_menu1")
    test_menu2 = inmemory_api.find_menu("test_menu2")
    test_distro = inmemory_api.find_distro("test_distro")
    test_profile1 = inmemory_api.find_profile("test_profile1")
    test_profile2 = inmemory_api.find_profile("test_profile2")
    test_profile3 = inmemory_api.find_profile("test_profile3")
    test_image = inmemory_api.find_image("test_image")
    test_system1 = inmemory_api.find_system("test_system1")
    test_system2 = inmemory_api.find_system("test_system2")

    # Act
    result = True
    for collection in [
        "repo",
        "distro",
        "menu",
        "image",
        "profile",
        "system",
    ]:
        for obj in inmemory_api.get_items(collection):
            result = obj.inmemory is False if result else result
            result = obj.__dict__["_comment"] == "" if result else result

    comment = test_system1.comment if result else result
    result = test_repo.inmemory if result else result
    result = test_menu1.inmemory if result else result
    result = not test_menu2.inmemory if result else result
    result = test_distro.inmemory if result else result
    result = test_profile1.inmemory if result else result
    result = not test_profile2.inmemory if result else result
    result = not test_profile3.inmemory if result else result
    result = not test_image.inmemory if result else result
    result = test_system1.inmemory if result else result
    result = not test_system2.inmemory if result else result

    result = test_repo.__dict__["_comment"] == "test comment" if result else result
    result = test_menu1.__dict__["_comment"] == "test comment" if result else result
    result = test_menu2.__dict__["_comment"] == "" if result else result
    result = test_distro.__dict__["_comment"] == "test comment" if result else result
    result = test_profile1.__dict__["_comment"] == "test comment" if result else result
    result = test_profile2.__dict__["_comment"] == "" if result else result
    result = test_profile3.__dict__["_comment"] == "" if result else result
    result = test_image.__dict__["_comment"] == "" if result else result
    result = test_system1.__dict__["_comment"] == "test comment" if result else result
    result = test_system2.__dict__["_comment"] == "" if result else result

    # Cleanup
    inmemory_api.remove_system(test_system1)
    inmemory_api.remove_system(test_system2)
    inmemory_api.remove_image(test_image)
    inmemory_api.remove_profile(test_profile3)
    inmemory_api.remove_profile(test_profile2)
    inmemory_api.remove_profile(test_profile1)
    inmemory_api.remove_distro(test_distro)
    inmemory_api.remove_menu(test_menu2)
    inmemory_api.remove_menu(test_menu1)
    inmemory_api.remove_repo(test_repo)

    # Assert
    assert result
