from typing import Any, Callable, Dict

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
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
