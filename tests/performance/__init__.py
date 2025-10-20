"""
Module that contains a helper class which supports the performance testsuite. This is not a pytest style fixture but
rather related pytest-benchmark. Thus, the different style in usage.
"""

import os
from typing import Callable

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.image import Image
from cobbler.items.menu import Menu
from cobbler.items.network_interface import NetworkInterface
from cobbler.items.profile import Profile
from cobbler.items.repo import Repo
from cobbler.items.system import System


class CobblerTree:
    """
    Helper class that defines methods that can be used during benchmark testing.
    """

    objs_default_count = 10
    repos_count = objs_default_count
    distros_count = objs_default_count
    menus_count = objs_default_count
    profiles_count = 300
    images_count = objs_default_count
    systems_count = 1000
    test_rounds = int(os.environ.get("COBBLER_PERFORMANCE_TEST_ROUNDS", 1))
    test_iterations = int(os.environ.get("COBBLER_PERFORMANCE_TEST_ITERATIONS", -1))
    tree_levels = 3

    @staticmethod
    def create_repos(api: CobblerAPI, save: bool, with_triggers: bool, with_sync: bool):
        """
        Create a number of repos for benchmark testing.
        """
        for i in range(CobblerTree.repos_count):
            test_item: Repo = Repo(api)
            test_item.name = f"test_repo_{i}"  # type: ignore[method-assign]
            api.repos().add(
                test_item, save=save, with_triggers=with_triggers, with_sync=with_sync
            )

    @staticmethod
    def create_distros(
        api: CobblerAPI,
        create_distro: Callable[[str, bool], Distro],
        save: bool,
        with_triggers: bool,
        with_sync: bool,
    ):
        """
        Create a number of distros for benchmark testing. This pairs the distros with the repositories and mgmt classes.
        """
        for i in range(CobblerTree.distros_count):
            repo = api.repos().find(name=f"test_repo_{i % CobblerTree.repos_count}")
            if isinstance(repo, list) or repo is None:
                raise ValueError("Could not find the test repo that was just created.")
            test_item = create_distro(f"test_distro_{i}", False)
            test_item.source_repos = [repo.uid]  # type: ignore[method-assign]
            api.distros().add(
                test_item, save=save, with_triggers=with_triggers, with_sync=with_sync
            )

    @staticmethod
    def create_menus(api: CobblerAPI, save: bool, with_triggers: bool, with_sync: bool):
        """
        Create a number of menus for benchmark testing. Depending on the menu depth this method also adds children for
        the menus.
        """
        for l in range(CobblerTree.tree_levels):
            for i in range(CobblerTree.menus_count):
                test_item: Menu = Menu(api)
                test_item.name = f"level_{l}_test_menu_{i}"  # type: ignore[method-assign]
                if l > 0:
                    menu = api.menus().find(name=f"level_{l - 1}_test_menu_{i}")
                    if isinstance(menu, list) or menu is None:
                        raise ValueError(
                            "Could not find the test menu that was just created."
                        )
                    test_item.parent = menu.uid  # type: ignore[method-assign]
                else:
                    test_item.parent = ""  # type: ignore[method-assign]
                api.menus().add(
                    test_item,
                    save=save,
                    with_triggers=with_triggers,
                    with_sync=with_sync,
                )

    @staticmethod
    def create_profiles(
        api: CobblerAPI, save: bool, with_triggers: bool, with_sync: bool
    ):
        """
        Create a number of profiles for benchmark testing. Depending on the menu depth this method also pairs the
        profile with a menu.
        """
        for l in range(CobblerTree.tree_levels):
            for i in range(CobblerTree.profiles_count):
                menu = api.menus().find(
                    name=f"level_{l}_test_menu_{i % CobblerTree.menus_count}"
                )
                if isinstance(menu, list) or menu is None:
                    raise ValueError(
                        "Could not find the test menu that was just created."
                    )
                test_item: Profile = Profile(api)
                test_item.name = f"level_{l}_test_profile_{i}"  # type: ignore[method-assign]
                if l > 0:
                    profile = api.profiles().find(
                        name=f"level_{l - 1}_test_profile_{i}"
                    )
                    if isinstance(profile, list) or profile is None:
                        raise ValueError(
                            "Could not find the test profile that was just created."
                        )
                    test_item.parent = profile.uid  # type: ignore[method-assign]
                else:
                    distro = api.distros().find(
                        name=f"test_distro_{i % CobblerTree.distros_count}"
                    )
                    if isinstance(distro, list) or distro is None:
                        raise ValueError(
                            "Could not find the test distro that was just created."
                        )
                    test_item.distro = distro.uid  # type: ignore[method-assign]
                test_item.menu = menu.uid  # type: ignore[method-assign]
                test_item.autoinstall = "built-in-sample.ks"  # type: ignore[method-assign]
                api.profiles().add(
                    test_item,
                    save=save,
                    with_triggers=with_triggers,
                    with_sync=with_sync,
                )

    @staticmethod
    def create_images(
        api: CobblerAPI, save: bool, with_triggers: bool, with_sync: bool
    ):
        """
        Create a number of images for benchmark testing.
        """
        for i in range(CobblerTree.images_count):
            menu = api.menus().find(
                name=f"level_{CobblerTree.tree_levels - 1}_test_menu_{i % CobblerTree.menus_count}"
            )
            if isinstance(menu, list) or menu is None:
                raise ValueError("Could not find the test menu that was just created.")
            test_item: Image = Image(api)
            test_item.name = f"test_image_{i}"  # type: ignore[method-assign]
            test_item.menu = menu.uid  # type: ignore[method-assign]
            test_item.autoinstall = "built-in-sample.ks"  # type: ignore[method-assign]
            api.images().add(
                test_item, save=save, with_triggers=with_triggers, with_sync=with_sync
            )

    @staticmethod
    def create_systems(
        api: CobblerAPI, save: bool, with_triggers: bool, with_sync: bool
    ):
        """
        Create a number of systems for benchmark testing. Depending on the strategy the system is paired with a profile
        or image.
        """
        for i in range(CobblerTree.systems_count):
            test_item: System = System(api)
            test_item.name = f"test_system_{i}"  # type: ignore[method-assign]
            if i % 2 == 0:
                profile = api.profiles().find(
                    name=f"level_{CobblerTree.tree_levels - 1}_test_profile_{i % CobblerTree.profiles_count}"
                )
                if isinstance(profile, list) or profile is None:
                    raise ValueError(
                        "Could not find the test profile that was just created."
                    )
                test_item.profile = profile.uid  # type: ignore[method-assign]
            else:
                image = api.images().find(
                    name=f"test_image_{i % CobblerTree.images_count}"
                )
                if isinstance(image, list) or image is None:
                    raise ValueError(
                        "Could not find the test image that was just created."
                    )
                test_item.image = image.uid  # type: ignore[method-assign]
            api.systems().add(
                test_item, save=save, with_triggers=with_triggers, with_sync=with_sync
            )
            api.network_interfaces().add(
                NetworkInterface(api=api, system_uid=test_item.uid, name="default")
            )

    @staticmethod
    def create_all_objs(
        api: CobblerAPI,
        create_distro: Callable[[str, bool], Distro],
        save: bool,
        with_triggers: bool,
        with_sync: bool,
    ):
        """
        Method that collectively creates all items at the same time.
        """
        CobblerTree.create_repos(api, save, with_triggers, with_sync)
        CobblerTree.create_distros(api, create_distro, save, with_triggers, with_sync)
        CobblerTree.create_menus(api, save, with_triggers, with_sync)
        CobblerTree.create_profiles(api, save, with_triggers, with_sync)
        CobblerTree.create_images(api, save, with_triggers, with_sync)
        CobblerTree.create_systems(api, save, with_triggers, with_sync)

    @staticmethod
    def remove_repos(api: CobblerAPI):
        """
        Method that removes all repositories.
        """
        for test_item in api.repos():
            api.repos().remove(test_item, with_triggers=False, with_sync=False)

    @staticmethod
    def remove_distros(api: CobblerAPI):
        """
        Method that removes all distributions.
        """
        for test_item in api.distros():
            api.distros().remove(test_item, with_triggers=False, with_sync=False)

    @staticmethod
    def remove_menus(api: CobblerAPI):
        """
        Method that removes all menus.
        """
        while len(api.menus()) > 0:
            api.menus().remove(
                list(api.menus())[0],
                recursive=True,
                with_triggers=False,
                with_sync=False,
            )

    @staticmethod
    def remove_profiles(api: CobblerAPI):
        """
        Method that removes all profiles.
        """
        while len(api.profiles()) > 0:
            api.profiles().remove(
                list(api.profiles())[0],
                recursive=True,
                with_triggers=False,
                with_sync=False,
            )

    @staticmethod
    def remove_images(api: CobblerAPI):
        """
        Method that removes all images.
        """
        for test_item in api.images():
            api.images().remove(test_item, with_triggers=False, with_sync=False)

    @staticmethod
    def remove_systems(api: CobblerAPI):
        """
        Method that removes all systems.
        """
        for test_item in api.systems():
            api.systems().remove(test_item, with_triggers=False, with_sync=False)

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
