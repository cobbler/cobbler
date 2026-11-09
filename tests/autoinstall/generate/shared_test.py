"""
Test module to verify the functionality shared by multiple per-breed auto-installation generators.
"""

from typing import Callable

from cobbler.api import CobblerAPI
from cobbler.autoinstall.generate.shared import generate_repo_stanza
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def test_generate_repo_stanza_renders_source_repos_baseurl_from_pair(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Regression test: ``distro.source_repos`` holds one ``(config_url, baseurl)`` pair per split-tree repo
    (e.g. RHEL5-style imports) -- ``config_url`` points at a generated ``.repo`` config file that no current
    code path deploys as a drop-in file, ``baseurl`` is the real mirror directory. ``generate_repo_stanza()``
    must render a ``repo --baseurl=...`` line using the baseurl (the pair's second element), not the config
    file URL, and must not emit a stanza for the config-file entry itself.
    """
    # Arrange
    test_distro = create_distro()
    test_distro.source_repos = [  # type: ignore[method-assign]
        (
            "http://server/cobbler/distro_mirror/config/test-0.repo",
            "http://server/cobbler/distro_mirror/testtree",
        )
    ]
    test_profile = create_profile(test_distro.uid)
    test_profile.repos = []  # type: ignore[method-assign]

    # Act
    result = generate_repo_stanza(cobbler_api, test_profile, True)

    # Assert
    assert (
        "repo --name=source-1 --baseurl=http://server/cobbler/distro_mirror/testtree"
        in result
    )
    assert "test-0.repo" not in result
