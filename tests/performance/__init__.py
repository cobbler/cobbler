"""
Module that contains a helper class which supports the performance testsuite. This is not a pytest style fixture but
rather related pytest-benchmark. Thus the different style in usage.
"""

from typing import Callable

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.menu import Menu
from cobbler.items.profile import Profile
from cobbler.items.repo import Repo
from cobbler.items.system import System


class CobblerTree:
    """
    Helper class that defines methods that can be used during benchmark testing.
    """

    objs_count = 2
    test_rounds = 1
    tree_levels = 3

    @staticmethod
    def create_repos(api: CobblerAPI):
        """
        Create a number of repos for benchmark testing.
        """
        for i in range(CobblerTree.objs_count):
            test_item = Repo(api)
            test_item.name = f"test_repo_{i}"
            api.add_repo(test_item)

    @staticmethod
    def create_distros(api: CobblerAPI, create_distro: Callable[[str], Distro]):
        """
        Create a number of distros for benchmark testing. This pairs the distros with the repositories and mgmt classes.
        """
        for i in range(CobblerTree.objs_count):
            test_item = create_distro(name=f"test_distro_{i}")
            test_item.source_repos = [f"test_repo_{i}"]

    @staticmethod
    def create_menus(api: CobblerAPI):
        """
        Create a number of menus for benchmark testing. Depending on the menu depth this method also adds children for
        the menus.
        """
        for l in range(CobblerTree.tree_levels):
            for i in range(CobblerTree.objs_count):
                test_item = Menu(api)
                test_item.name = f"level_{l}_test_menu_{i}"
                if l > 0:
                    test_item.parent = f"level_{l - 1}_test_menu_{i}"
                else:
                    test_item.parent = ""
                api.add_menu(test_item)

    @staticmethod
    def create_profiles(
        api: CobblerAPI, create_profile: Callable[[str, str, str], Profile]
    ):
        """
        Create a number of profiles for benchmark testing. Depending on the menu depth this method also pairs the
        profile with a menu.
        """
        for l in range(CobblerTree.tree_levels):
            for i in range(CobblerTree.objs_count):
                if l > 0:
                    test_item = create_profile(
                        profile_name=f"level_{l - 1}_test_profile_{i}",
                        name=f"level_{l}_test_profile_{i}",
                    )
                else:
                    test_item = create_profile(
                        distro_name=f"test_distro_{i}",
                        name=f"level_{l}_test_profile_{i}",
                    )
                test_item.menu = f"level_{l}_test_menu_{i}"
                test_item.autoinstall = "sample.ks"

    @staticmethod
    def create_images(api: CobblerAPI, create_image: Callable[[str], Image]):
        """
        Create a number of images for benchmark testing.
        """
        for i in range(CobblerTree.objs_count):
            test_item = create_image(name=f"test_image_{i}")
            test_item.menu = f"level_{CobblerTree.tree_levels - 1}_test_menu_{i}"
            test_item.autoinstall = "sample.ks"

    @staticmethod
    def create_systems(
        api: CobblerAPI, create_system: Callable[[str, str, str], System]
    ):
        """
        Create a number of systems for benchmark testing. Depending on the strategy the system is paired with a profile
        or image.
        """
        for i in range(CobblerTree.objs_count):
            if i % 2 == 0:
                test_item = create_system(
                    name=f"test_system_{i}",
                    profile_name=f"level_{CobblerTree.tree_levels - 1}_test_profile_{i}",
                )
            else:
                test_item = create_system(
                    name=f"test_system_{i}", image_name=f"test_image_{i}"
                )

    @staticmethod
    def create_all_objs(
        api: CobblerAPI,
        create_distro: Callable[[str], Distro],
        create_profile: Callable[[str, str, str], Profile],
        create_image: Callable[[str], Image],
        create_system: Callable[[str, str, str], System],
    ):
        """
        Method that collectively creates all items at the same time.
        """
        CobblerTree.create_repos(api)
        CobblerTree.create_distros(api, create_distro)
        CobblerTree.create_menus(api)
        CobblerTree.create_profiles(api, create_profile)
        CobblerTree.create_images(api, create_image)
        CobblerTree.create_systems(api, create_system)

    @staticmethod
    def remove_repos(api: CobblerAPI):
        """
        Method that removes all repositories.
        """
        for test_item in api.repos():
            api.remove_repo(test_item.name)

    @staticmethod
    def remove_distros(api: CobblerAPI):
        """
        Method that removes all distributions.
        """
        for test_item in api.distros():
            api.remove_distro(test_item.name)

    @staticmethod
    def remove_menus(api: CobblerAPI):
        """
        Method that removes all menus.
        """
        while len(api.menus()) > 0:
            api.remove_menu(list(api.menus())[0], recursive=True)

    @staticmethod
    def remove_profiles(api: CobblerAPI):
        """
        Method that removes all profiles.
        """
        while len(api.profiles()) > 0:
            api.remove_profile(list(api.profiles())[0], recursive=True)

    @staticmethod
    def remove_images(api: CobblerAPI):
        """
        Method that removes all images.
        """
        for test_item in api.images():
            api.remove_image(test_item.name)

    @staticmethod
    def remove_systems(api: CobblerAPI):
        """
        Method that removes all systems.
        """
        for test_item in api.systems():
            api.remove_system(test_item.name)

    @staticmethod
    def remove_all_objs(api: CobblerAPI):
        """
        Method that collectively removes all items at the same time.
        """
        CobblerTree.remove_systems(api)
        CobblerTree.remove_images(api)
        CobblerTree.remove_profiles(api)
        CobblerTree.remove_menus(api)
        CobblerTree.remove_distros(api)
        CobblerTree.remove_repos(api)
