"""
Test module to verify that "cobblerd setup" creates every directory Cobbler expects at runtime.

Regression test for https://github.com/cobbler/cobbler/issues/3999: RPM/DEB builds invoke
"cobblerd setup --base-dir=<buildroot>" at package-build time, but the trigger and collection database
directories used to only be created lazily by "CobblerAPI.__init__" at runtime -- meaning the packages never
owned them.
"""

import pathlib

from cobbler.cobblerd.distro_options import DistroOptions
from cobbler.cobblerd.setup import setup_cobblerd


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
