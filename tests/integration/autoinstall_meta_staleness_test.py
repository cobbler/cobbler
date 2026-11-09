"""
Integration test for the Release Blocker found during 4.0.0 validation attempt 3: editing a
profile's "autoinstall_meta" through the live cobblerd does not reliably propagate to a child
system's rendered autoinstall file, even after an explicit save (and even after a plain
"cobbler sync").
"""

import pathlib
from typing import Any, Callable, List, Tuple

import pytest

from cobbler.remote import CobblerXMLRPCInterface


@pytest.mark.integration
def test_autoinstall_meta_edit_is_reflected_without_cobblerd_restart(
    remote: CobblerXMLRPCInterface,
    token: str,
    images_fake_path: pathlib.Path,
    create_distro: Callable[[List[Tuple[List[str], Any]]], str],
    create_profile: Callable[[List[Tuple[List[str], Any]]], str],
    create_system: Callable[[List[Tuple[List[str], Any]]], str],
):
    """
    A profile's "autoinstall_meta" is edited and saved twice in a row, through the same live
    cobblerd a plain "cobbler profile edit" would hit. Each edit's rendered autoinstall file (for
    a child system inheriting the value) must reflect that edit's value, not a previous one.
    """
    # Arrange
    did = create_distro(
        [
            (["name"], "fake"),
            (["arch"], "x86_64"),
            (["breed"], "redhat"),
            (["kernel"], str(images_fake_path / "vmlinuz")),
            (["initrd"], str(images_fake_path / "initramfs")),
        ]
    )
    pid = create_profile(
        [
            (["name"], "fake"),
            (["distro"], did),
            (["autoinstall"], "built-in-sample.ks"),
            (["autoinstall_meta"], "use_disk=vda"),
        ]
    )
    create_system(
        [
            (["name"], "fake"),
            (["profile"], pid),
        ]
    )

    def render_ignoredisk_line() -> str:
        rendered = remote.generate_autoinstall("fake", "system", "name", "", "")
        (line,) = [l for l in rendered.splitlines() if "ignoredisk" in l]
        return line

    # Act / Assert: initial value renders correctly.
    assert "vda" in render_ignoredisk_line()

    # Act: edit the profile's autoinstall_meta again, through the same live cobblerd, and save --
    # exactly what a plain "cobbler profile edit --autoinstall-meta=..." does. with_sync=False
    # since a full DHCP/DNS sync is irrelevant to this bug and isn't set up in this test environment.
    remote.modify_profile(pid, ["autoinstall_meta"], "use_disk=vdz", token)
    remote.save_profile(pid, False, False, "bypass", token)

    # Assert: the system's rendered autoinstall file must reflect the new value immediately --
    # no cobblerd restart should be required.
    line = render_ignoredisk_line()
    assert "vdz" in line, (
        f"expected the re-rendered autoinstall file to use the just-saved value 'vdz', "
        f"but got: {line!r} -- the profile's resolved/blended autoinstall_meta is stale"
    )
