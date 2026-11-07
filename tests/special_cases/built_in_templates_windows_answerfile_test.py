"""
Test module to verify the built-in Windows answerfile template respects the configured
autoinstall scheme (http/https) for its post-install-script download, instead of
hardcoding http like startnet.template's sibling download used to before being fixed.
"""

from typing import Callable

import pytest

from cobbler import utils
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def _render_answerfile(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
) -> str:
    """
    Mirrors cobbler.modules.sync_post_wingen.run()'s rendering of the answerfile:
    blender() output with autoinstall_meta flattened on top, rendered directly via the
    templar - not cobbler.autoinstall.manager.generate_autoinstall(), which pops
    "autoinstall_meta" instead of merely flattening it and is not how this template is
    actually rendered in production.
    """
    target_template = cobbler_api.find_template(
        False, False, name="built-in-answerfile"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)

    meta = utils.blender(cobbler_api, False, test_profile)
    autoinstall_meta = meta.get("autoinstall_meta", {})
    meta.update(autoinstall_meta)

    return cobbler_api.templar.render(target_template.content, meta, None)


def test_built_in_answerfile_download_uses_default_http_scheme(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    By default (no autoinstall_scheme override) the post_install.cmd download must use http.
    """
    # Act
    result = _render_answerfile(cobbler_api, create_distro, create_profile)

    # Assert
    assert "DownloadFile('http://" in result
    assert "DownloadFile('https://" not in result


def test_built_in_answerfile_download_respects_https_scheme(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    When the server is configured for HTTPS-only autoinstall delivery, the post_install.cmd
    download in the answerfile must not silently fall back to plain HTTP.
    """
    # Arrange
    cobbler_api.settings().autoinstall_scheme = "https"

    # Act
    result = _render_answerfile(cobbler_api, create_distro, create_profile)

    # Assert
    assert "DownloadFile('https://" in result
    assert "DownloadFile('http://" not in result
