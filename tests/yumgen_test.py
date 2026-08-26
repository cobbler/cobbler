import pathlib
from typing import Callable

import pytest

from cobbler import yumgen
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def test_joinpath_absolute_segment_resets_to_filesystem_root():
    """
    Characterization test for the bug fixed alongside this test: ``pathlib.Path.joinpath()`` treats an
    absolute-looking segment (``"/"``) as a full reset of the path, discarding everything that came before it.

    ``cobbler.yumgen.YumGen.get_yum_config()`` used to build its target path via
    ``pathlib.Path(webdir).joinpath("/", "/".join(...))`` which - due to the semantics demonstrated here - always
    collapsed back down to ``/...`` instead of staying rooted under ``webdir``. The fix simply drops the stray
    ``"/"`` argument.
    """
    webdir = "/var/www/cobbler"
    relative_fragment = "distro_mirror/config/testdistro-0.repo"

    # This is the buggy expression that used to be in get_yum_config().
    buggy_result = pathlib.Path(webdir).joinpath("/", relative_fragment)
    # This is the fixed expression that get_yum_config() uses now.
    fixed_result = pathlib.Path(webdir).joinpath(relative_fragment)

    assert str(buggy_result) == "/" + relative_fragment
    assert str(fixed_result) == webdir + "/" + relative_fragment
    assert fixed_result != buggy_result


def test_get_yum_config_source_repo_path_rooted_under_webdir(
    tmp_path: pathlib.Path,
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Regression test for the fix to ``YumGen.get_yum_config()``: the yum repo config file generated for a distro's
    ``source_repos`` entries must be read from underneath the configured ``webdir``, not from a path that got reset
    to the filesystem root.

    ``get_yum_config()`` is only ever called by ``CobblerAPI.get_repo_config_for_profile()`` /
    ``...for_system()`` (see ``cobbler/api.py``), always with a profile or system object - never a bare distro - so
    a profile is used here to match real usage. ``source_repos`` itself lives on the distro and is inherited by the
    profile via ``utils.blender()``.
    """
    # Arrange
    webdir = tmp_path / "webdir"
    webdir.mkdir()
    cobbler_api.settings().webdir = str(webdir)

    test_distro = create_distro()
    test_profile = create_profile(test_distro.name)
    # Shape mirrors what cobbler.modules.managers.import_signatures.py appends to distro.source_repos: a
    # [repo_config_url, repo_tree_url] pair where everything from the 5th "/"-separated segment onwards is the
    # path (relative to webdir) that get_yum_config() is supposed to read the rendered config file from.
    repo_config_url = "http://@@http_server@@/cobbler/distro_mirror/config/%s-0.repo" % test_distro.name
    repo_tree_url = "http://@@http_server@@/cobbler/distro_mirror/%s" % test_distro.name
    test_distro.source_repos = [[repo_config_url, repo_tree_url]]

    # Place the rendered repo config file exactly where it is expected to live once correctly rooted under webdir.
    correct_path = webdir / "distro_mirror" / "config" / ("%s-0.repo" % test_distro.name)
    correct_path.parent.mkdir(parents=True, exist_ok=True)
    repo_file_marker = "# yum repo config for %s" % test_distro.name
    correct_path.write_text(repo_file_marker + "\n")

    test_gen = yumgen.YumGen(cobbler_api)

    # Act
    result = test_gen.get_yum_config(test_profile, True)

    # Assert
    # If get_yum_config() were still building the buggy, filesystem-root-relative path, the file placed under
    # webdir would never be found, and the method would instead emit an "could not read repo source" error for a
    # path rooted at "/" (which does not contain our repo file).
    assert "error: could not read repo source" not in result
    assert repo_file_marker in result
