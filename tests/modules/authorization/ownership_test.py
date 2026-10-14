from typing import Any, Callable, Dict

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.menu import Menu
from cobbler.items.profile import Profile
from cobbler.items.system import System
from cobbler.modules.authorization import ownership


def test_register():
    # Arrange & Act & Assert
    assert ownership.register() == "authz"


def test_get_authorization_handler(cobbler_api: CobblerAPI):
    # Arrange & Act
    handler = ownership.get_authorization_handler(cobbler_api)
    # Assert
    assert handler.api is cobbler_api


def _patch_groups(
    handler: "ownership.OwnershipAuthorizationModule", groups: Dict[str, Dict[str, Any]]
) -> None:
    """
    Replace the handler's ``/etc/cobbler/users.conf`` parsing with a fixed in-memory mapping, so tests don't
    depend on (or mutate) the real file.
    """
    handler._OwnershipAuthorizationModule__parse_config = (  # type: ignore[attr-defined]
        lambda: groups
    )


def test_authorize_save_new_object_with_explicit_owners_succeeds(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
):
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(handler, {"admins": {"admin": 1}, "mygroup": {"myuser": 1}})
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid, with_add=False)
    profile.owners = ["mygroup"]

    # Act
    result = handler.authorize("myuser", "save_profile", profile)

    # Assert
    assert result == 1


def test_authorize_save_new_object_default_owners_denied_for_non_admin(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
):
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(handler, {"admins": {"admin": 1}, "mygroup": {"myuser": 1}})
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid, with_add=False)

    # Act
    result = handler.authorize("myuser", "save_profile", profile)

    # Assert
    assert result == 0


def test_authorize_save_existing_object_owner_allowed(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
    create_system: Callable[..., System],
):
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(
        handler,
        {
            "admins": {"admin": 1},
            "mygroup": {"myuser": 1},
            "othergroup": {"otheruser": 1},
        },
    )
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid)
    system = create_system(profile_uid=profile.uid)
    system.owners = ["mygroup"]

    # Act
    result = handler.authorize("myuser", "save_system", system)

    # Assert
    assert result == 1


def test_authorize_save_existing_object_non_owner_denied(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
    create_system: Callable[..., System],
):
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(
        handler,
        {
            "admins": {"admin": 1},
            "mygroup": {"myuser": 1},
            "othergroup": {"otheruser": 1},
        },
    )
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid)
    system = create_system(profile_uid=profile.uid)
    system.owners = ["othergroup"]

    # Act
    result = handler.authorize("myuser", "save_system", system)

    # Assert
    assert result == 0


def test_authorize_denies_unknown_user(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
    create_system: Callable[..., System],
):
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(handler, {"admins": {"admin": 1}})
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid)
    system = create_system(profile_uid=profile.uid)

    # Act
    result = handler.authorize("ghost", "save_system", system)

    # Assert
    assert result == 0


def test_authorize_remove_template_requires_ownership(cobbler_api: CobblerAPI):
    """
    Regression test: ``remove_template`` previously fell through the hand-rolled, by-name ``remove_*`` dispatch
    (which only covered distro/profile/system/repo/image) and crashed with ``ValueError``.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(
        handler,
        {
            "admins": {"admin": 1},
            "mygroup": {"myuser": 1},
            "othergroup": {"otheruser": 1},
        },
    )
    test_template = cobbler_api.new_template(
        name="test_authorize_remove_template", template_type="cheetah"
    )
    cobbler_api.add_template(test_template)
    test_template.owners = ["mygroup"]

    # Act & Assert
    assert handler.authorize("myuser", "remove_template", test_template) == 1
    assert handler.authorize("otheruser", "remove_template", test_template) == 0


def test_authorize_remove_menu_requires_ownership(
    cobbler_api: CobblerAPI, create_menu: Callable[..., Menu]
):
    """
    Regression test: ``remove_menu`` previously fell through the hand-rolled, by-name ``remove_*`` dispatch and
    crashed with ``ValueError``.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(
        handler,
        {
            "admins": {"admin": 1},
            "mygroup": {"myuser": 1},
            "othergroup": {"otheruser": 1},
        },
    )
    menu = create_menu()
    menu.owners = ["mygroup"]

    # Act & Assert
    assert handler.authorize("myuser", "remove_menu", menu) == 1
    assert handler.authorize("otheruser", "remove_menu", menu) == 0


def test_authorize_copy_requires_ownership(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
    create_system: Callable[..., System],
):
    """
    Regression test: ``copy_item()`` previously called ``check_access()`` with no object at all, so every
    non-admin copy was denied regardless of ownership.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(
        handler,
        {
            "admins": {"admin": 1},
            "mygroup": {"myuser": 1},
            "othergroup": {"otheruser": 1},
        },
    )
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid)
    system = create_system(profile_uid=profile.uid)
    system.owners = ["mygroup"]

    # Act & Assert
    assert handler.authorize("myuser", "copy_system", system) == 1
    assert handler.authorize("otheruser", "copy_system", system) == 0


def test_authorize_save_denies_name_collision_with_owned_existing_object(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
    create_system: Callable[..., System],
):
    """
    Security regression test: a user must not be able to bypass ownership of an existing, differently-owned
    object by constructing a new, unsaved object with the same name and self-assigning its (unenforced) owners -
    authorize() must check the real, already-persisted owner of that name too.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(
        handler,
        {
            "admins": {"admin": 1},
            "mygroup": {"myuser": 1},
            "othergroup": {"otheruser": 1},
        },
    )
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid)
    existing_system = create_system(profile_uid=profile.uid, name="colliding-name")
    existing_system.owners = ["othergroup"]

    colliding_new_system = cobbler_api.new_system()
    colliding_new_system.name = "colliding-name"
    colliding_new_system.profile = profile.uid
    colliding_new_system.owners = ["mygroup"]

    # Act
    result = handler.authorize("myuser", "save_system", colliding_new_system)

    # Assert
    assert result == 0


def test_authorize_power_system_requires_ownership(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
    create_system: Callable[..., System],
):
    """
    Regression test: ``power_system`` did not match any ``modify_operation`` criteria, so any authenticated
    (non-admin) user could power-cycle any system regardless of ownership.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(
        handler,
        {
            "admins": {"admin": 1},
            "mygroup": {"myuser": 1},
            "othergroup": {"otheruser": 1},
        },
    )
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid)
    system = create_system(profile_uid=profile.uid)
    system.owners = ["othergroup"]

    # Act & Assert
    assert handler.authorize("otheruser", "power_system", system) == 1
    assert handler.authorize("myuser", "power_system", system) == 0


def test_authorize_read_only_bypass_matches_known_resources(cobbler_api: CobblerAPI):
    """
    The read-only bypass is scoped to ``get_``/``read_``-prefixed resources (the real resource-name family,
    e.g. ``get_tftp_file``), not any resource that merely starts with the letters "get"/"read".
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(handler, {"admins": {"admin": 1}})

    # Act & Assert
    assert handler.authorize("ghost", "get_distro") == 1
    assert handler.authorize("ghost", "read_autoinstall_template") == 1
    assert handler.authorize("ghost", "getaway_something") == 0
