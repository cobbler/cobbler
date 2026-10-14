from typing import Any, Callable, Dict

import pytest

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


def test_authorize_auto_assigns_owner_for_new_object_single_group(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
):
    """
    A brand-new, not-yet-persisted object whose owners were never explicitly set should be auto-assigned to the
    creating user's own group, so they aren't immediately locked out of what they just created.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(handler, {"admins": {"admin": 1}, "mygroup": {"myuser": 1}})
    distro = create_distro()
    profile = cobbler_api.new_profile()
    profile.name = "test_authorize_auto_assign_single_group"
    profile.distro = distro.uid

    # Act
    result = handler.authorize("myuser", "save_profile", profile)

    # Assert
    assert result == 1
    assert profile.owners == ["mygroup"]


def test_authorize_refuses_new_object_multiple_groups(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
):
    """
    Ownership of a brand-new object cannot be auto-decided when the creating user belongs to more than one
    non-admin group - refuse with a descriptive error rather than silently denying or guessing.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(
        handler,
        {
            "admins": {"admin": 1},
            "mygroup": {"myuser": 1},
            "othergroup": {"myuser": 1},
        },
    )
    distro = cobbler_api.new_distro()
    distro.name = "test_authorize_refuses_multi_group"

    # Act & Assert
    with pytest.raises(ValueError):
        handler.authorize("myuser", "save_distro", distro)


def test_authorize_does_not_reclaim_existing_unowned_object(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
):
    """
    An already-persisted object left at its default/inherited owner must not be auto-claimed by the next
    non-admin group member who happens to save it - only genuine creation triggers auto-assignment.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(handler, {"admins": {"admin": 1}, "mygroup": {"myuser": 1}})
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid)
    assert profile.owners != []

    # Act
    result = handler.authorize("myuser", "save_profile", profile)

    # Assert
    assert result == 0
    assert profile.owners != ["mygroup"]


def test_authorize_does_not_auto_assign_owner_for_clone_of_existing_object(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
    create_system: Callable[..., System],
):
    """
    Security regression test: remote.py's transaction handling edits a ``make_clone()`` of an existing object,
    whose ``uid`` differs from the original (``make_clone()`` deliberately drops it) even though it represents
    the same, already-persisted item. Detecting "is this a new object" by comparing ``obj.uid`` against a
    by-name lookup therefore misclassifies such a clone as new on every call after the first, letting a user with
    no real relationship to the object get it auto-assigned to their own group. The real signal must survive
    cloning and renaming - ``ctime`` does (it is only set once, on first save, and copied by ``make_clone()``).
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
    profile.owners = ["othergroup"]
    system = create_system(profile_uid=profile.uid)
    assert system.owners == ["othergroup"]  # resolved via inheritance from the profile

    clone = system.make_clone()
    assert clone.uid != system.uid
    assert clone.ctime == system.ctime

    # Act
    result = handler.authorize("myuser", "modify_system", clone)

    # Assert
    assert result == 0
    assert clone.owners != ["mygroup"]


def test_authorize_does_not_mutate_owners_of_open_object_via_clone(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
    create_system: Callable[..., System],
):
    """
    Security regression test: a clone of an existing object that is intentionally open to everyone
    (``owners == []``) must not be silently narrowed to a single group's ownership as a side effect of an
    unrelated transaction-clone modify call. The by-name-collision check only denies when the real object has
    non-empty owners, so an open object's clone reaches the "is this new" check unguarded - the fix must
    recognize the clone as not-new (via ``ctime``) regardless.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(handler, {"admins": {"admin": 1}, "mygroup": {"myuser": 1}})
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid)
    profile.owners = []
    system = create_system(profile_uid=profile.uid)
    assert system.owners == []

    clone = system.make_clone()
    assert clone.uid != system.uid

    # Act
    result = handler.authorize("myuser", "modify_system", clone)

    # Assert
    assert result == 1  # open objects remain editable by anyone
    assert (
        clone.owners == []
    )  # but must not be silently narrowed to the caller's own group


def test_authorize_bare_power_role_is_not_object_scoped(cobbler_api: CobblerAPI):
    """
    Regression test: remote.py's __start_task() calls check_access(token, "power") (no object) as a generic,
    role-level gate for background power tasks - distinct from the "power_system" resource, which IS
    object-scoped. "power" must not be classified as a modify_operation requiring an object, or every
    non-admin background power task would be unconditionally denied.
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(handler, {"admins": {"admin": 1}, "mygroup": {"myuser": 1}})

    # Act & Assert
    assert handler.authorize("myuser", "power") == 1


def test_authorize_does_not_auto_assign_owner_for_legacy_zero_ctime_object(
    cobbler_api: CobblerAPI,
    create_distro: Callable[..., Distro],
    create_profile: Callable[..., Profile],
):
    """
    Defense in depth: ``ctime`` is only populated on first save going forward, but a record deserialized from
    old or incomplete data could still have ``ctime == 0.0`` despite being genuinely persisted (``from_dict()``
    only sets fields present in the stored data). Directly modifying such an already-persisted object (i.e. not
    through a transaction clone) must not be treated as a new creation just because of that: a uid lookup in the
    object's own collection already finds it, which ``ctime`` alone cannot tell apart from "never saved".
    """
    # Arrange
    handler = ownership.get_authorization_handler(cobbler_api)
    _patch_groups(handler, {"admins": {"admin": 1}, "mygroup": {"myuser": 1}})
    distro = create_distro()
    profile = create_profile(distro_uid=distro.uid)
    assert profile.owners != []
    profile.ctime = 0.0  # simulate a legacy/incomplete record

    # Act
    result = handler.authorize("myuser", "save_profile", profile)

    # Assert
    assert result == 0
    assert profile.owners != ["mygroup"]
