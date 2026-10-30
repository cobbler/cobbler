"""
Test module to verify that "cobblerd setup" creates every directory Cobbler expects at runtime.

Regression test for https://github.com/cobbler/cobbler/issues/3999: RPM/DEB builds invoke
"cobblerd setup --base-dir=<buildroot>" at package-build time, but the trigger and collection database
directories used to only be created lazily by "CobblerAPI.__init__" at runtime -- meaning the packages never
owned them.
"""

import json
import pathlib

from cobbler.cobblerd.distro_options import DistroOptions
from cobbler.cobblerd.setup import setup_cobblerd, signatures_seed_needed


def test_setup_cobblerd_creates_trigger_and_collection_dirs(tmp_path: pathlib.Path):
    """
    Test that "setup_cobblerd()" materializes the trigger and collection database directory trees under the given
    base directory, so that packaging (which invokes this at build time) ends up owning them too.
    """
    # Arrange
    distro_options = DistroOptions()
    var_path = tmp_path / "var" / "lib" / "cobbler"

    # Act
    setup_cobblerd(tmp_path, distro_options, ["core"])

    # Assert - a representative sample of the collection database directories
    for collection in (
        "distros",
        "images",
        "profiles",
        "repos",
        "systems",
        "menus",
        "network_interfaces",
        "templates",
        "distro_groups",
        "profile_groups",
        "system_groups",
    ):
        assert (var_path / "collections" / collection).is_dir()

    # Assert - a representative sample of the trigger directories
    for trigger in (
        "add/distro/pre",
        "add/distro/post",
        "delete/system/pre",
        "install/firstboot",
        "sync/pre",
        "change",
        "task/repo/post",
    ):
        assert (var_path / "triggers" / trigger).is_dir()


class TestSignaturesSeedNeeded:
    """
    Regression tests for the distro_signatures.json seeding check.

    An RPM/DEB upgrade can leave behind a zero-byte or truncated ``distro_signatures.json`` (e.g. if a
    packaging scriptlet race clobbers the file after it was created but before its content was fully
    written). The old check only looked at ``Path.exists()``, so a present-but-empty-or-corrupt file was
    mistaken for "an admin already has one" and never got repaired. These tests pin the corrected
    behavior: only a file that exists AND parses as non-empty JSON should be left alone.
    """

    def test_missing_file_needs_seeding(self, tmp_path: pathlib.Path):
        # Arrange
        signatures_path = tmp_path / "distro_signatures.json"

        # Act / Assert
        assert signatures_seed_needed(signatures_path) is True

    def test_empty_file_needs_seeding(self, tmp_path: pathlib.Path):
        # Arrange
        signatures_path = tmp_path / "distro_signatures.json"
        signatures_path.write_text("", encoding="utf-8")

        # Act / Assert
        assert signatures_seed_needed(signatures_path) is True

    def test_whitespace_only_file_needs_seeding(self, tmp_path: pathlib.Path):
        # Arrange
        signatures_path = tmp_path / "distro_signatures.json"
        signatures_path.write_text("   \n", encoding="utf-8")

        # Act / Assert
        assert signatures_seed_needed(signatures_path) is True

    def test_corrupt_json_file_needs_seeding(self, tmp_path: pathlib.Path):
        # Arrange
        signatures_path = tmp_path / "distro_signatures.json"
        signatures_path.write_text("{not valid json!!", encoding="utf-8")

        # Act / Assert
        assert signatures_seed_needed(signatures_path) is True

    def test_valid_json_file_does_not_need_seeding(self, tmp_path: pathlib.Path):
        # Arrange
        signatures_path = tmp_path / "distro_signatures.json"
        signatures_path.write_text(json.dumps({"breeds": {}}), encoding="utf-8")

        # Act / Assert
        assert signatures_seed_needed(signatures_path) is False


def test_setup_cobblerd_reseeds_empty_signatures_file(tmp_path: pathlib.Path):
    """
    Regression test: an existing-but-empty distro_signatures.json (as could be left behind by a
    packaging-scriptlet race around an RPM/DEB upgrade) must be reseeded, not silently left empty.
    """
    # Arrange
    distro_options = DistroOptions()
    var_path = tmp_path / "var" / "lib" / "cobbler"
    var_path.mkdir(parents=True)
    signatures_path = var_path / "distro_signatures.json"
    signatures_path.write_text("", encoding="utf-8")

    # Act
    setup_cobblerd(tmp_path, distro_options, ["core"])

    # Assert
    content = signatures_path.read_text(encoding="utf-8")
    assert content.strip() != ""
    json.loads(content)  # must parse as valid JSON


def test_setup_cobblerd_does_not_touch_valid_existing_signatures_file(
    tmp_path: pathlib.Path,
):
    """
    A valid, already-seeded (or admin-customized) distro_signatures.json must be left untouched.
    """
    # Arrange
    distro_options = DistroOptions()
    var_path = tmp_path / "var" / "lib" / "cobbler"
    var_path.mkdir(parents=True)
    signatures_path = var_path / "distro_signatures.json"
    sentinel_content = json.dumps({"sentinel": "admin-customized"})
    signatures_path.write_text(sentinel_content, encoding="utf-8")

    # Act
    setup_cobblerd(tmp_path, distro_options, ["core"])

    # Assert
    assert signatures_path.read_text(encoding="utf-8") == sentinel_content
