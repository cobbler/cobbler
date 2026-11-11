"""
Concurrency / data-integrity regression tests for the XML-RPC API and the sync pipeline.

These tests target four specific, statically-identified race conditions that are NOT fixed by the
``fix/concurrent-item-sync-race`` branch:

* Duplicate-name race -- ``Collection.add()`` checks for a duplicate name *before* taking its lock and inserting
  into ``self.listing`` (``cobbler/cobbler_collections/collection.py``), so two concurrent "new" saves racing on
  the same name can both pass the check.
* Quick-sync/full-sync race (FIXED) -- ``Collection.add()``/``remove()`` -> ``add_quick_pxe_sync()``/
  ``remove_quick_pxe_sync()`` never took ``/var/lib/cobbler/lock`` (``cobbler/actions/sync.py``), so a per-item
  "quick sync" could run concurrently with a full ``cobbler sync``, which ``rmtree()``s and recreates the shared
  TFTP/webdir directory trees under that very lock. Every quick-sync call site now takes that same lock,
  including the multi-item transaction-commit path (``CobblerAPI.add_remove_items()``), which now holds the
  lock continuously for the *entire* method - every item's add/remove, its on-disk serialization, its
  quick-sync, and the final menu rebuild - instead of re-acquiring it between items. This was only safe to
  close completely after also unifying the serializer's own on-disk writes
  (``cobbler/serializer.py``'s ``serialize_item()``/``serialize_delete()``) onto this same reentrant lock
  primitive instead of their previous independent, non-reentrant ``fcntl.flock()`` on the same file - two
  separate, uncoordinated lock acquisitions on one file from the same thread would otherwise deadlock. Two
  test functions below cover the quick-sync/full-sync race end-to-end: the base single-item case, and a
  reentrancy variant for a profile with attached systems; the whole-transaction single-acquisition claim
  itself is covered by unit tests in ``tests/xmlrpcapi/transaction_test.py``.
* Classic-edit lost-update race (FIXED) -- the classic (non-transaction) edit path (``modify_item``/
  ``save_item`` in ``cobbler/remote.py``) used to mutate the live, shared item object directly with no lock and
  no mtime/version check. It now clones the item per (token, object_id) edit and rejects a stale save with a
  ``ValueError``, mirroring the transaction path's existing compare-and-swap; staging/unstaging that clone is
  itself guarded by a dedicated lock so two concurrent edits sharing the same token can't silently drop one
  another's staged clone. The test below now asserts that a losing concurrent editor gets an explicit conflict
  it can retry from, rather than a silently dropped update.
* DHCP-manager race -- the DHCP manager (``cobbler/modules/managers/isc.py``/``dnsmasq.py``) mutates a shared,
  unlocked, process-wide ``self.config`` dict via a read-merge-write pattern in ``sync_single_system()``.

Every test here is intentionally timing-sensitive: it runs a stress loop of many rounds, each with several
barrier-synchronized concurrent XML-RPC clients, because a single attempt is unlikely to hit a narrow race window.
A test failure here is a successful finding (it should be read together with the captured diagnostic output, not
just the assertion message), not a flake to be silenced.
"""

import pathlib
import threading
import xmlrpc.client
from typing import Any, Callable, Dict, List, Tuple

import pytest

from cobbler import enums
from cobbler import utils as cobbler_utils
from cobbler.api import CobblerAPI
from cobbler.remote import CobblerXMLRPCInterface
from cobbler.utils import get_shared_secret

from tests.integration.conftest import WaitTaskEndType

pytestmark = pytest.mark.integration

COBBLERD_STDERR_LOG = pathlib.Path("/var/log/supervisord/cobblerd_stderr.log")


def _new_connection() -> Tuple[CobblerXMLRPCInterface, str]:
    """
    Open a brand-new XML-RPC connection and log in independently.

    Reusing one ``xmlrpc.client.ServerProxy``/token across threads would serialize requests on a single HTTP
    connection and defeat the purpose of these tests: each concurrent "client" needs its own socket so that
    cobblerd's ``ThreadingMixIn`` XML-RPC server actually dispatches the calls to separate request-handling
    threads.
    """
    remote: CobblerXMLRPCInterface = xmlrpc.client.ServerProxy(  # type: ignore[assignment]
        "http://localhost/cobbler_api"
    )
    shared_secret = get_shared_secret()
    if isinstance(shared_secret, int):
        pytest.fail("Could not get shared secret to login to XML-RPC")
    token = remote.login("", shared_secret)
    if not token:
        pytest.fail("Could not get XML-RPC token!")
    return remote, token


def _new_cobblerd_log_lines(baseline_line_count: int) -> List[str]:
    """
    Return any lines appended to cobblerd's stderr log since ``baseline_line_count`` was captured.
    """
    if not COBBLERD_STDERR_LOG.exists():
        return []
    lines = COBBLERD_STDERR_LOG.read_text(
        encoding="utf-8", errors="replace"
    ).splitlines()
    return lines[baseline_line_count:]


def _cobblerd_log_line_count() -> int:
    if not COBBLERD_STDERR_LOG.exists():
        return 0
    return len(
        COBBLERD_STDERR_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    )


def test_concurrent_distro_create_rejects_duplicate_names(
    remote: CobblerXMLRPCInterface,
    token: str,
    images_fake_path: pathlib.Path,
):
    """
    Duplicate-name race regression test.

    ``Collection.add()`` (cobbler/cobbler_collections/collection.py ~538-634) runs its duplicate-name check
    (``check_for_duplicate_names``) *before* acquiring ``self.lock`` and inserting into ``self.listing``. This
    fires THREADS concurrent "new_distro + save_distro('new')" calls for the exact same name every round, and
    asserts that cobblerd never ends up with more than one distro carrying that name.
    """
    threads_n = 8
    rounds = 60
    kernel = str(images_fake_path / "vmlinuz")
    initrd = str(images_fake_path / "initramfs")

    incidents: List[str] = []

    for round_index in range(rounds):
        name = f"race-distro-{round_index}"
        barrier = threading.Barrier(threads_n)
        results: List[Any] = [None] * threads_n

        def worker(i: int) -> None:
            try:
                t_remote, t_token = _new_connection()
                did = t_remote.new_distro(t_token)
                t_remote.modify_distro(did, ["name"], name, t_token)
                t_remote.modify_distro(did, ["arch"], "x86_64", t_token)
                t_remote.modify_distro(did, ["kernel"], kernel, t_token)
                t_remote.modify_distro(did, ["initrd"], initrd, t_token)
                barrier.wait(timeout=30)
                ok = t_remote.save_distro(did, True, False, "new", t_token)
                results[i] = (ok, did, None)
            except Exception as error:  # pylint: disable=broad-except
                results[i] = (False, None, repr(error))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(threads_n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        survivors = [d for d in remote.get_distros() if d["name"] == name]

        # Clean up every survivor so the next round starts from a clean slate, regardless of outcome.
        for distro in survivors:
            remote.remove_distro(distro["uid"], token, True)

        if len(survivors) > 1:
            incidents.append(
                f"round {round_index}: {len(survivors)} distros named {name!r} survived "
                f"concurrent creation (thread results: {results})"
            )

    assert not incidents, (
        f"Duplicate-name race reproduced in {len(incidents)}/{rounds} rounds -- duplicate-named distros survived "
        f"concurrent creation:\n" + "\n".join(incidents)
    )


def test_concurrent_classic_edit_does_not_lose_updates(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
    images_fake_path: pathlib.Path,
):
    """
    Classic-edit lost-update race regression test (now exercising the fix).

    The classic (non-transaction) edit path -- ``modify_item``/``save_item`` in ``cobbler/remote.py`` -- used to
    call ``setattr()`` directly on the live, shared item object with no lock and no mtime/version check, so later
    writers silently clobbered earlier ones with no signal to either caller. It now clones the item per (token,
    object_id) edit and rejects a stale ``save_distro`` with an explicit conflict error instead. THREADS
    concurrent clients each read the current ``owners`` list, append their own unique marker, and race to save
    via ``save_distro(..., "bypass", ...)``.

    The invariant under test is the one the fix actually promises: a writer's save must never both (a) report
    success and (b) have its marker missing afterwards -- a losing writer must get an explicit, attributable
    conflict error instead of silent data loss. (Retrying after a conflict, and ending up with the retried value
    persisted, is covered separately and deterministically by
    ``tests/xmlrpcapi/distro_test.py::test_classic_edit_conflict_raises_and_allows_retry`` -- a dynamic test that
    has every losing thread retry independently and immediately, with no inter-thread coordination on the retry,
    would be testing a much stronger property than the fix promises: that a full read-modify-write, list-replace
    attribute converges losslessly under continuous multi-writer contention. That is a well-known limitation of
    optimistic concurrency control on whole-object/full-replace attributes, not a regression of this fix.)
    """
    threads_n = 6
    rounds = 50
    distro_id = create_distro(
        [
            (["name"], "race-owner-distro"),
            (["arch"], "x86_64"),
            (["kernel"], str(images_fake_path / "vmlinuz")),
            (["initrd"], str(images_fake_path / "initramfs")),
            (["owners"], []),
        ]
    )

    incidents: List[str] = []

    for round_index in range(rounds):
        markers = [f"r{round_index}-t{i}" for i in range(threads_n)]
        barrier = threading.Barrier(threads_n)
        outcomes: List[str] = [""] * threads_n

        def worker(i: int) -> None:
            try:
                t_remote, t_token = _new_connection()
                current = t_remote.get_distro(distro_id)["owners"]
                new_owners = list(current) + [markers[i]]
                t_remote.modify_distro(distro_id, ["owners"], new_owners, t_token)
                barrier.wait(timeout=30)
                t_remote.save_distro(distro_id, True, False, "bypass", t_token)
                outcomes[i] = "saved"
            except xmlrpc.client.Fault as conflict:
                outcomes[i] = (
                    "conflict" if "modified" in str(conflict) else repr(conflict)
                )
            except Exception as error:  # pylint: disable=broad-except
                outcomes[i] = repr(error)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(threads_n)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=60)

        final_owners = remote.get_distro(distro_id)["owners"]
        for i in range(threads_n):
            if outcomes[i] == "saved" and markers[i] not in final_owners:
                incidents.append(
                    f"round {round_index}: thread {i} reported a successful save but its marker "
                    f"{markers[i]!r} was lost silently (final owners: {final_owners})"
                )
            elif outcomes[i] not in ("saved", "conflict"):
                incidents.append(
                    f"round {round_index}: thread {i} got an unexpected error: {outcomes[i]}"
                )

        # Reset to a clean baseline for the next round.
        remote.modify_distro(distro_id, ["owners"], [], token)
        remote.save_distro(distro_id, True, False, "bypass", token)

    remote.remove_distro(distro_id, token, True)

    assert not incidents, (
        f"Classic-edit lost-update race regressed in {len(incidents)}/{rounds} rounds -- a concurrent "
        f"classic-path save reported success while its update was silently lost, or raised an unexpected error:\n"
        + "\n".join(incidents)
    )


def test_quick_sync_survives_concurrent_full_sync(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
    create_profile: Callable[[List[Tuple[List[str], Any]]], str],
    images_fake_path: pathlib.Path,
    wait_task_end: WaitTaskEndType,
):
    """
    Quick-sync/full-sync race regression test.

    ``Collection.add()``/``remove()`` -> ``add_quick_pxe_sync()``/``remove_quick_pxe_sync()`` never acquire
    ``/var/lib/cobbler/lock``, so a per-item "quick sync" can run concurrently with a full ``cobbler sync``, which
    holds that lock while ``clean_trees()`` ``rmtree()``s and recreates the shared ``pxelinux.cfg``/``grub``/
    ``images``/``ipxe``/``esxi`` directory trees. A sizeable inventory is pre-populated to widen that destructive
    window to multiple seconds, while a background thread continuously hammers ``save_profile`` on a working set
    of existing profiles for the full duration of several full-sync cycles.
    """
    kernel = str(images_fake_path / "vmlinuz")
    initrd = str(images_fake_path / "initramfs")
    inventory_size = 150
    hammer_set_size = 20
    sync_cycles = 10

    distro_id = create_distro(
        [
            (["name"], "race-sync-distro"),
            (["arch"], "x86_64"),
            (["kernel"], kernel),
            (["initrd"], initrd),
        ]
    )
    profile_ids = [
        create_profile(
            [
                (["name"], f"race-sync-profile-{i}"),
                (["distro"], distro_id),
            ]
        )
        for i in range(inventory_size)
    ]
    hammer_targets = profile_ids[:hammer_set_size]

    stop_event = threading.Event()
    hammer_errors: List[str] = []
    last_comment_sent: Dict[str, str] = {}
    results_lock = threading.Lock()

    def hammer() -> None:
        t_remote, t_token = _new_connection()
        counter = 0
        while not stop_event.is_set():
            for pid in hammer_targets:
                comment = f"hammer-{counter}"
                try:
                    t_remote.modify_profile(pid, ["comment"], comment, t_token)
                    ok = t_remote.save_profile(pid, True, True, "bypass", t_token)
                    if ok:
                        with results_lock:
                            last_comment_sent[pid] = comment
                except Exception as error:  # pylint: disable=broad-except
                    with results_lock:
                        hammer_errors.append(f"{pid}: {comment!r}: {error!r}")
                counter += 1

    log_baseline = _cobblerd_log_line_count()
    hammer_thread = threading.Thread(target=hammer, daemon=True)
    hammer_thread.start()

    try:
        for _cycle in range(sync_cycles):
            tid = remote.background_sync({}, token)
            wait_task_end(tid, remote)
    finally:
        stop_event.set()
        hammer_thread.join(timeout=30)

    mismatches: List[str] = []
    for pid, expected_comment in last_comment_sent.items():
        actual_comment = remote.get_profile(pid)["comment"]
        if actual_comment != expected_comment:
            mismatches.append(
                f"{pid}: expected last-saved comment {expected_comment!r}, found {actual_comment!r} on disk "
                "after the full sync completed"
            )

    new_log_lines = _new_cobblerd_log_lines(log_baseline)
    log_tracebacks = [
        line
        for line in new_log_lines
        if "Traceback" in line or "FileNotFoundError" in line or "OSError" in line
    ]

    assert not hammer_errors, (
        f"Quick-sync/full-sync race reproduced: {len(hammer_errors)} quick-sync write(s) raised an exception "
        f"while a concurrent full sync was running:\n" + "\n".join(hammer_errors[:20])
    )
    assert not mismatches, (
        "Quick-sync/full-sync race reproduced: quick-sync edits did not survive a concurrent full sync:\n"
        + "\n".join(mismatches)
    )
    assert not log_tracebacks, (
        "Quick-sync/full-sync race reproduced: cobblerd logged exception(s) during the concurrent "
        "quick-sync/full-sync window:\n" + "\n".join(log_tracebacks[:20])
    )


def test_quick_sync_with_attached_systems_survives_concurrent_full_sync(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
    create_profile: Callable[[List[Tuple[List[str], Any]]], str],
    create_system: Callable[[List[Tuple[List[str], Any]]], str],
    images_fake_path: pathlib.Path,
    wait_task_end: WaitTaskEndType,
):
    """
    Quick-sync/full-sync race regression test -- reentrancy variant.

    ``add_quick_pxe_sync()``'s ``Profile`` branch cascades into ``CobblerAPI.sync_systems()`` for every system
    attached to the profile being saved, and that method independently acquires the very same
    ``/var/lib/cobbler/lock``. The fix for the quick-sync/full-sync race makes ``utils.filelock()`` re-entrant for
    exactly this reason: without that, every hammered ``save_profile`` call below would self-deadlock while
    holding the lock (the second, nested acquisition would block forever on the first, which the very same
    thread can never get back around to releasing). A non-reentrant regression surfaces here as an ordinary,
    bounded test failure -- either the hammer thread never returns (detected via ``Thread.is_alive()`` after a
    bounded ``join``), or a concurrent full-sync cycle can no longer acquire the same lock and
    ``wait_task_end`` times out -- rather than the test process hanging forever.

    Unlike ``test_quick_sync_survives_concurrent_full_sync``, this is primarily a correctness/deadlock check, not a
    timing-window stress test, so a much smaller inventory and fewer sync cycles suffice: the nested-lock path just
    needs to be exercised at least once per hammer iteration, not widen a race window.
    """
    kernel = str(images_fake_path / "vmlinuz")
    initrd = str(images_fake_path / "initramfs")
    inventory_size = 20
    sync_cycles = 5

    distro_id = create_distro(
        [
            (["name"], "race-sync-reentrant-distro"),
            (["arch"], "x86_64"),
            (["kernel"], kernel),
            (["initrd"], initrd),
        ]
    )
    profile_ids: List[str] = []
    for i in range(inventory_size):
        pid = create_profile(
            [
                (["name"], f"race-sync-reentrant-profile-{i}"),
                (["distro"], distro_id),
            ]
        )
        create_system(
            [
                (["name"], f"race-sync-reentrant-system-{i}"),
                (["profile"], pid),
            ]
        )
        profile_ids.append(pid)

    stop_event = threading.Event()
    hammer_errors: List[str] = []
    last_comment_sent: Dict[str, str] = {}
    results_lock = threading.Lock()

    def hammer() -> None:
        t_remote, t_token = _new_connection()
        counter = 0
        while not stop_event.is_set():
            for pid in profile_ids:
                comment = f"hammer-{counter}"
                try:
                    t_remote.modify_profile(pid, ["comment"], comment, t_token)
                    ok = t_remote.save_profile(pid, True, True, "bypass", t_token)
                    if ok:
                        with results_lock:
                            last_comment_sent[pid] = comment
                except Exception as error:  # pylint: disable=broad-except
                    with results_lock:
                        hammer_errors.append(f"{pid}: {comment!r}: {error!r}")
                counter += 1

    log_baseline = _cobblerd_log_line_count()
    hammer_thread = threading.Thread(target=hammer, daemon=True)
    hammer_thread.start()

    try:
        for _cycle in range(sync_cycles):
            tid = remote.background_sync({}, token)
            wait_task_end(tid, remote)
    finally:
        stop_event.set()
        hammer_thread.join(timeout=30)

    assert not hammer_thread.is_alive(), (
        "Quick-sync/full-sync race reentrancy regression: the hammer thread never returned within the join "
        "timeout -- a save_profile call for a profile with an attached system self-deadlocked while holding "
        "/var/lib/cobbler/lock (Profile's add_quick_pxe_sync cascades into a nested, lock-acquiring "
        "sync_systems() call for every attached system)."
    )

    mismatches: List[str] = []
    for pid, expected_comment in last_comment_sent.items():
        actual_comment = remote.get_profile(pid)["comment"]
        if actual_comment != expected_comment:
            mismatches.append(
                f"{pid}: expected last-saved comment {expected_comment!r}, found {actual_comment!r} on disk "
                "after the full sync completed"
            )

    new_log_lines = _new_cobblerd_log_lines(log_baseline)
    log_tracebacks = [
        line
        for line in new_log_lines
        if "Traceback" in line or "FileNotFoundError" in line or "OSError" in line
    ]

    assert not hammer_errors, (
        f"Quick-sync/full-sync race reentrancy regression: {len(hammer_errors)} quick-sync write(s) raised an "
        f"exception while a concurrent full sync was running:\n"
        + "\n".join(hammer_errors[:20])
    )
    assert not mismatches, (
        "Quick-sync/full-sync race reentrancy regression: quick-sync edits did not survive a concurrent full sync:\n"
        + "\n".join(mismatches)
    )
    assert not log_tracebacks, (
        "Quick-sync/full-sync race reentrancy regression: cobblerd logged exception(s) during the concurrent "
        "quick-sync/full-sync window:\n" + "\n".join(log_tracebacks[:20])
    )


def test_transaction_add_batch_survives_concurrent_full_sync(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
    create_profile: Callable[[List[Tuple[List[str], Any]]], str],
    images_fake_path: pathlib.Path,
    wait_task_end: WaitTaskEndType,
):
    """
    Quick-sync/full-sync race regression test -- multi-item transaction variant.

    ``CobblerAPI.add_remove_items()`` (the transaction-commit path) used to acquire
    ``/var/lib/cobbler/lock`` separately for each added item's quick-sync, dropping and
    re-acquiring it between items of the very same transaction -- so, unlike a single ``save_*``
    call, a *multi-item* transaction commit could still have a concurrent full ``cobbler sync``'s
    ``clean_trees()`` interleave mid-batch even after the single-item quick-sync/full-sync race was
    fixed. It now holds one single, uninterrupted lock acquisition for the whole method - every
    item's add/remove and on-disk serialization, every added item's quick-sync, and the final menu
    rebuild. A background thread continuously commits small multi-system transactions (and cleans
    each batch up afterwards) for the full duration of several full-sync cycles.
    """
    kernel = str(images_fake_path / "vmlinuz")
    initrd = str(images_fake_path / "initramfs")
    sync_cycles = 10
    batch_size = 5

    distro_id = create_distro(
        [
            (["name"], "race-txn-distro"),
            (["arch"], "x86_64"),
            (["kernel"], kernel),
            (["initrd"], initrd),
        ]
    )
    profile_id = create_profile(
        [
            (["name"], "race-txn-profile"),
            (["distro"], distro_id),
        ]
    )

    stop_event = threading.Event()
    hammer_errors: List[str] = []
    batches_committed = 0
    results_lock = threading.Lock()

    def hammer() -> None:
        nonlocal batches_committed
        t_remote, t_token = _new_connection()
        counter = 0
        while not stop_event.is_set():
            system_ids: List[str] = []
            try:
                t_remote.transaction_begin(t_token)
                for i in range(batch_size):
                    sid = t_remote.new_system(t_token)
                    t_remote.modify_system(
                        sid, ["name"], f"race-txn-system-{counter}-{i}", t_token
                    )
                    t_remote.modify_system(sid, ["profile"], profile_id, t_token)
                    if not t_remote.save_system(sid, True, True, "new", t_token):
                        raise RuntimeError(f"save_system reported failure for {sid}")
                    system_ids.append(sid)
                if not t_remote.transaction_commit(t_token):
                    raise RuntimeError("transaction_commit reported failure")
                with results_lock:
                    batches_committed += 1
            except Exception as error:  # pylint: disable=broad-except
                with results_lock:
                    hammer_errors.append(f"batch {counter}: {error!r}")
            finally:
                for sid in system_ids:
                    try:
                        t_remote.remove_system(sid, t_token, True)
                    except Exception:  # pylint: disable=broad-except
                        pass
            counter += 1

    log_baseline = _cobblerd_log_line_count()
    hammer_thread = threading.Thread(target=hammer, daemon=True)
    hammer_thread.start()

    try:
        for _cycle in range(sync_cycles):
            tid = remote.background_sync({}, token)
            wait_task_end(tid, remote)
    finally:
        stop_event.set()
        hammer_thread.join(timeout=30)

    new_log_lines = _new_cobblerd_log_lines(log_baseline)
    log_tracebacks = [
        line
        for line in new_log_lines
        if "Traceback" in line or "FileNotFoundError" in line or "OSError" in line
    ]

    assert batches_committed > 0, (
        "the hammer thread never completed a single transaction commit -- the test setup itself is "
        "broken, independent of the race under test"
    )
    assert not hammer_errors, (
        f"Quick-sync/full-sync race (multi-item transaction variant) reproduced: "
        f"{len(hammer_errors)} transaction commit(s) raised an exception while a concurrent full "
        f"sync was running:\n" + "\n".join(hammer_errors[:20])
    )
    assert not log_tracebacks, (
        "Quick-sync/full-sync race (multi-item transaction variant) reproduced: cobblerd logged "
        "exception(s) during the concurrent transaction-commit/full-sync window:\n"
        + "\n".join(log_tracebacks[:20])
    )


def test_concurrent_system_save_does_not_drop_dhcp_entries(
    remote: CobblerXMLRPCInterface,
    token: str,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
    create_profile: Callable[[List[Tuple[List[str], Any]]], str],
    create_system: Callable[[List[Tuple[List[str], Any]]], str],
    create_network_interface: Callable[[str, List[Tuple[List[str], Any]]], str],
    images_fake_path: pathlib.Path,
    wait_task_end: WaitTaskEndType,
):
    """
    DHCP-manager race regression test.

    The active DHCP manager module (``cobbler/modules/managers/isc.py`` by default; ``dnsmasq.py`` if configured)
    mutates a shared, unlocked, process-wide ``self.config`` dict via a read-merge-write pattern in
    ``sync_single_system()``. Two concurrent ``save_system`` calls for two DIFFERENT systems can race: one
    thread's read-merge-write silently discards the other's not-yet-applied DHCP entry, with both XML-RPC calls
    still reporting success.
    """
    dhcp_module = (
        CobblerAPI().settings().modules.get("dhcp", {}).get("module", "managers.isc")
    )
    rounds = 50

    did = create_distro(
        [
            (["name"], "race-dhcp-distro"),
            (["arch"], "x86_64"),
            (["kernel"], str(images_fake_path / "vmlinuz")),
            (["initrd"], str(images_fake_path / "initramfs")),
        ]
    )
    pid = create_profile([(["name"], "race-dhcp-profile"), (["distro"], did)])

    # Prime the manager's incremental cache (a cold cache makes sync_single_system() fall back to a full,
    # non-racy self.sync() instead of exercising the read-merge-write path we're targeting).
    tid = remote.background_sync({"dhcp": True}, token)
    wait_task_end(tid, remote)

    def dhcp_config_text() -> str:
        if dhcp_module == "managers.dnsmasq":
            settings = CobblerAPI().settings()
            return pathlib.Path(settings.dnsmasq_hosts_file).read_text(
                encoding="utf-8", errors="replace"
            ) + pathlib.Path(settings.dnsmasq_ethers_file).read_text(
                encoding="utf-8", errors="replace"
            )
        return pathlib.Path(cobbler_utils.dhcpconf_location(enums.DHCP.V4)).read_text(
            encoding="utf-8", errors="replace"
        )

    incidents: List[str] = []

    for round_index in range(rounds):
        mac_a = f"aa:bb:cc:dd:{round_index:02x}:01"
        mac_b = f"aa:bb:cc:dd:{round_index:02x}:02"
        name_a = f"race-sys-a-{round_index}"
        name_b = f"race-sys-b-{round_index}"
        barrier = threading.Barrier(2)
        errors: List[Any] = [None, None]
        sids: List[Any] = [None, None]

        def worker(i: int, name: str, mac: str) -> None:
            try:
                t_remote, t_token = _new_connection()
                sid = t_remote.new_system(t_token)
                sids[i] = sid
                t_remote.modify_system(sid, ["name"], name, t_token)
                t_remote.modify_system(sid, ["profile"], pid, t_token)
                nid = t_remote.new_network_interface(sid, t_token)
                t_remote.modify_network_interface(nid, ["name"], "default", t_token)
                t_remote.modify_network_interface(nid, ["mac_address"], mac, t_token)
                t_remote.save_network_interface(nid, True, False, "bypass", t_token)
                barrier.wait(timeout=30)
                t_remote.save_system(sid, True, True, "new", t_token)
            except Exception as error:  # pylint: disable=broad-except
                errors[i] = repr(error)

        thread_a = threading.Thread(target=worker, args=(0, name_a, mac_a))
        thread_b = threading.Thread(target=worker, args=(1, name_b, mac_b))
        thread_a.start()
        thread_b.start()
        thread_a.join(timeout=60)
        thread_b.join(timeout=60)

        # Let any async DHCP config write triggered by the quick-sync settle before reading it back.
        config_text = dhcp_config_text()
        mac_a_present = mac_a in config_text
        mac_b_present = mac_b in config_text

        if not (mac_a_present and mac_b_present):
            incidents.append(
                f"round {round_index}: mac_a present={mac_a_present}, mac_b present={mac_b_present} "
                f"(errors: {errors})"
            )

        for sid in sids:
            if sid is None:
                continue
            try:
                remote.remove_system(sid, token, recursive=True)
            except Exception:  # pylint: disable=broad-except
                pass

    assert not incidents, (
        f"DHCP-manager race reproduced in {len(incidents)}/{rounds} rounds -- a concurrent save_system for a "
        f"different system silently dropped the other's DHCP entry (active module: {dhcp_module}):\n"
        + "\n".join(incidents)
    )
