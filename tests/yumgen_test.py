"""
Test module to verify the functionality of the yum repo configuration generator.
"""

import pathlib
from typing import Callable

from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile
from cobbler.modules.managers import import_signatures
from cobbler.yumgen import YumGen


def test_get_yum_config_resolves_source_repos_pair_to_config_file_path(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
    tmp_path: pathlib.Path,
):
    """
    Regression test: ``get_yum_config()``'s "tack on install source repos" logic indexes each
    ``source_repos`` entry as ``repo[0]`` -- the generated ``.repo`` config-file URL -- to resolve the local
    path of the repo config file to read and inline. This only resolves correctly if ``source_repos`` holds
    ``(config_url, baseurl)`` pairs as actually produced by ``import_signatures.py``'s
    ``yum_process_comps_file()``, confirming the whole producer-to-consumer pipeline still agrees on that
    shape after restoring ``Distro.source_repos``'s type.
    """
    # Arrange: populate source_repos via the real producer, exactly as `cobbler import` would.
    manager = import_signatures.get_import_manager(cobbler_api)
    manager.direct_source = False
    test_distro = create_distro()
    comps_path = tmp_path / "tree"
    (comps_path / "base").mkdir(parents=True)
    (comps_path / "base" / "comps.xml").write_text("<comps/>", encoding="UTF-8")
    manager.yum_process_comps_file(str(comps_path), test_distro)
    test_profile = create_profile(test_distro.uid)
    yumgen = YumGen(cobbler_api)

    # Act
    result = yumgen.get_yum_config(test_profile, True)

    # Assert: the config file written by yum_process_comps_file() at
    # "<webdir>/distro_mirror/config/<name>-0.repo" must be found and inlined, not reported as unreadable.
    assert f"could not read repo source" not in result
    assert "[core-0]" in result
