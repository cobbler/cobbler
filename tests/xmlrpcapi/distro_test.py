import os
import threading
from typing import TYPE_CHECKING, Any, Callable, Dict, List, cast

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.cexceptions import CX
from cobbler.items.distro import Distro
from cobbler.remote import CobblerXMLRPCInterface

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def cleanup_create_distro_positive(cobbler_api: CobblerAPI):
    yield
    cobbler_api.remove_distro("create_distro_positive")


def test_get_distros(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: get distros
    """
    # Arrange --> Nothing to arrange

    # Act
    result = remote.get_distros(token)

    # Assert
    assert result == []


@pytest.mark.parametrize(
    "field_name,field_value",
    [
        (["arch"], "i386"),
        (["breed"], "debian"),
        (["breed"], "freebsd"),
        (["breed"], "redhat"),
        (["breed"], "suse"),
        (["breed"], "ubuntu"),
        (["breed"], "unix"),
        (["breed"], "vmware"),
        (["breed"], "windows"),
        (["breed"], "xen"),
        (["breed"], "generic"),
        (["comment"], "test comment"),
        (["initrd"], ""),
        (["name"], "testdistro0"),
        (["kernel"], ""),
        (["kernel_options"], "a=1 b=2 c=3 c=4 c=5 d e"),
        (["kernel_options_post"], "a=1 b=2 c=3 c=4 c=5 d e"),
        (["autoinstall_meta"], "a=1 b=2 c=3 c=4 c=5 d e"),
        (["os_version"], "rhel4"),
        (["owners"], "user1 user2 user3"),
        (["boot_loaders"], "pxe ipxe grub"),
    ],
)
def test_create_distro_positive(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    field_name: List[str],
    field_value: str,
    cleanup_create_distro_positive: Any,
):
    """
    Test: create/edit a distro with valid values
    """
    # Arrange --> Nothing to do.
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    distro = remote.new_distro(token)
    remote.modify_distro(distro, ["name"], "create_distro_positive", token)

    # Act
    if field_name == ["kernel"]:
        field_value = os.path.join(folder, fk_kernel)
    if field_name == ["initrd"]:
        field_value = os.path.join(folder, fk_initrd)
    result = remote.modify_distro(distro, field_name, field_value, token)

    # Assert
    assert result


@pytest.mark.parametrize(
    "field_name,field_value",
    [(["arch"], "badarch"), (["breed"], "badbreed"), (["boot_loaders"], "badloader")],
)
def test_create_distro_negative(
    remote: CobblerXMLRPCInterface, token: str, field_name: List[str], field_value: str
):
    """
    Test: create/edit a distro with invalid values
    """
    # Arrange
    distro = remote.new_distro(token)
    remote.modify_distro(distro, ["name"], "testdistro0", token)

    # Act & Assert
    try:
        remote.modify_distro(distro, field_name, field_value, token)
    except (CX, TypeError, ValueError):
        assert True
    else:
        pytest.fail("Bad field did not raise an exception!")


@pytest.mark.usefixtures("create_testdistro")
def test_get_distro(remote: CobblerXMLRPCInterface, fk_initrd: str, fk_kernel: str):
    """
    Test: get a distro object
    """
    # Arrange --> Done in fixture

    # Act
    distro_handle = remote.get_distro_handle("testdistro0")
    distro = remote.get_distro(distro_handle)

    # Assert
    assert distro.get("name") == "testdistro0"  # type: ignore
    assert distro.get("redhat_management_key") == enums.VALUE_INHERITED  # type: ignore
    assert distro.get("redhat_management_org") == enums.VALUE_INHERITED  # type: ignore
    assert distro.get("redhat_management_user") == enums.VALUE_INHERITED  # type: ignore
    assert distro.get("redhat_management_password") == enums.VALUE_INHERITED  # type: ignore
    assert fk_initrd in distro.get("initrd")  # type: ignore
    assert fk_kernel in distro.get("kernel")  # type: ignore


def test_get_system(remote: CobblerXMLRPCInterface):
    """
    Test: get a system object
    """
    # Arrange --> There should be no system present. --> Nothing to Init.

    # Act
    system = remote.get_system("testsystem0")

    # Assert
    assert system is "~"


def test_find_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: find a distro object
    """
    # Arrange --> No distros means no setup

    # Act
    result = remote.find_distro(criteria={"name": "testdistro0"}, token=token)

    # Assert
    assert result == []


@pytest.mark.usefixtures("create_testdistro")
def test_copy_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: copy a distro object
    """
    # Arrange --> Done in the fixture

    # Act
    distro = remote.get_item_handle("distro", "testdistro0")
    result = remote.copy_distro(distro, "testdistrocopy", token)

    # Assert
    assert result

    # Cleanup --> Plus fixture
    remote.remove_distro(remote.get_distro_handle("testdistrocopy"), token)


@pytest.mark.usefixtures("create_testdistro")
def test_rename_distro(remote: CobblerXMLRPCInterface, token: str):
    """
    Test: rename a distro object
    """
    # Arrange
    distro = remote.get_item_handle("distro", "testdistro0")

    # Act
    result = remote.rename_distro(distro, "testdistro1", token)

    # Assert
    assert result

    # Cleanup
    remote.remove_distro(distro, token)


def test_remove_distro(
    request: "pytest.FixtureRequest",
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    create_distro: Callable[[str, str, str, str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: remove a distro object
    """
    # Arrange
    distro_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    distro_handle = create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore

    # Act
    result = remote.remove_distro(distro_handle, token)  # type: ignore

    # Assert
    assert result


def test_get_valid_distro_boot_loaders(
    request: "pytest.FixtureRequest",
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    create_distro: Callable[[str, str, str, str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    Test: get the valid boot loaders for a distro
    """
    # Arrange
    distro_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    distro_uid = create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore

    # Act
    result = remote.get_valid_distro_boot_loaders(distro_uid, token)

    # Assert
    assert isinstance(result, list)
    assert result != []


def test_get_valid_distro_boot_loaders_no_distro(
    remote: CobblerXMLRPCInterface, token: str
):
    """
    Test: get the valid boot loaders when no distro id is given returns all supported boot loaders
    """
    # Act
    result = remote.get_valid_distro_boot_loaders(None, token)

    # Assert
    assert isinstance(result, list)
    assert result != []


def test_classic_edit_conflict_raises_and_allows_retry(
    request: "pytest.FixtureRequest",
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    create_distro: Callable[[str, str, str, str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
    token2: str,
):
    """
    Classic-edit lost-update race regression test: two classic (non-transaction) editors racing on
    the same distro must not silently clobber each other. ``modify_item()`` clones the live object
    per (token, object_id) edit and captures its mtime; ``save_item()`` rejects the losing editor's
    save with a ``ValueError`` instead of overwriting the other editor's change, and the loser can
    recover by re-fetching and retrying.
    """
    # Arrange
    distro_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    distro_id = create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore

    # Act - two editors start editing the same distro before either saves.
    remote.modify_distro(distro_id, ["comment"], "editor A", token)
    remote.modify_distro(distro_id, ["comment"], "editor B", token2)

    # Editor A saves first and wins cleanly.
    assert remote.save_distro(distro_id, True, False, "bypass", token)
    assert cast(Dict[Any, Any], remote.get_distro(distro_id))["comment"] == "editor A"

    # Editor B's clone was taken before editor A's save bumped the live item's mtime, so editor
    # B's save must raise instead of overwriting editor A's change.
    with pytest.raises(ValueError):
        remote.save_distro(distro_id, True, False, "bypass", token2)
    assert cast(Dict[Any, Any], remote.get_distro(distro_id))["comment"] == "editor A"

    # Editor B recovers by re-reading the current state and retrying.
    remote.modify_distro(distro_id, ["comment"], "editor B retried", token2)
    assert remote.save_distro(distro_id, True, False, "bypass", token2)
    assert (
        cast(Dict[Any, Any], remote.get_distro(distro_id))["comment"]
        == "editor B retried"
    )


def test_concurrent_modify_item_same_token_does_not_lose_staged_clone(
    mocker: "MockerFixture",
    request: "pytest.FixtureRequest",
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
    create_distro: Callable[[str, str, str, str, str], str],
    remote: CobblerXMLRPCInterface,
    token: str,
):
    """
    ``editing_items`` staging-dict race regression test: two concurrent ``modify_item()`` calls for
    the SAME ``(token, object_id)`` must not race on the check-then-act sequence
    (``self.editing_items[token].get(object_id)`` -> clone -> insert) - that sequence is guarded by
    a dedicated lock (``self.editing_items_lock``), so only the first thread to acquire it calls
    ``make_clone()``; the second reuses the already-staged clone instead of discarding it.

    Patches ``Distro.make_clone()`` with a short rendezvous barrier placed *after* the "is there
    already a staged clone?" check but *before* the dict insert, to force both threads to the same
    point. With the lock in place, only the first thread to acquire it ever calls
    ``make_clone()``, so the barrier on the second thread's call times out quickly - expected, not
    a failure.
    """
    # Arrange
    distro_name = (  # type: ignore
        request.node.originalname if request.node.originalname else request.node.name  # type: ignore
    )
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_initrd)
    distro_id = create_distro(distro_name, "x86_64", "suse", kernel_path, initrd_path)  # type: ignore

    barrier = threading.Barrier(2)
    original_make_clone = Distro.make_clone

    def patched_make_clone(self: Distro, keep_uid: bool = False) -> Distro:
        try:
            barrier.wait(timeout=0.5)
        except threading.BrokenBarrierError:
            pass
        return original_make_clone(self, keep_uid=keep_uid)

    mocker.patch.object(Distro, "make_clone", patched_make_clone)

    errors: List[BaseException] = []

    def worker(attribute: str, value: Any) -> None:
        try:
            remote.modify_distro(distro_id, [attribute], value, token)
        except Exception as error:  # pylint: disable=broad-except
            errors.append(error)

    thread_a = threading.Thread(target=worker, args=("comment", "thread-A-comment"))
    thread_b = threading.Thread(target=worker, args=("owners", ["thread-B-owner"]))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=10)
    thread_b.join(timeout=10)

    # Act
    assert not errors, f"modify_distro raised unexpectedly: {errors}"
    assert remote.save_distro(distro_id, True, False, "bypass", token)

    # Assert - both concurrent edits must have landed on the one shared staged clone, not just
    # whichever write won a dict-overwrite.
    result = cast(Dict[Any, Any], remote.get_distro(distro_id))
    assert result["comment"] == "thread-A-comment"
    assert result["owners"] == ["thread-B-owner"]

    # Cleanup
    remote.remove_distro(distro_id, token)
