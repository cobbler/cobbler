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


def test_built_in_answerfile_has_modify_partitions_for_every_created_partition(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test-gap closure: CreatePartitions only creates raw, unformatted partitions -- without a
    matching ModifyPartitions entry for each one, Setup has nothing to install onto and aborts
    with a non-specific "DiskConfiguration setting... could not be applied" error. Every
    CreatePartition must have a corresponding ModifyPartition.
    """
    # Act
    result = _render_answerfile(cobbler_api, create_distro, create_profile)

    # Assert
    assert "<ModifyPartitions>" in result
    assert result.count('<CreatePartition wcm:action="add">') == result.count(
        '<ModifyPartition wcm:action="add">'
    )


def test_built_in_answerfile_respects_image_name_product_key_locale_overrides(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Test-gap closure: "image_name"/"product_key"/"locale" in autoinstall_meta must override the
    per-os_version defaults -- install.wim is frequently a multi-edition image whose index name
    doesn't match the generic default, and the generic/KMS product key is per-edition, not
    per-Windows-version, so setup.exe silently discards the whole unattend.xml if either mismatches
    the real image.
    """
    # Arrange
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)
    test_profile.autoinstall_meta = {
        "image_name": "Windows 11 Pro N",
        "product_key": "AAAAA-BBBBB-CCCCC-DDDDD-EEEEE",
        "locale": "de-DE",
    }
    meta = utils.blender(cobbler_api, False, test_profile)
    autoinstall_meta = meta.get("autoinstall_meta", {})
    meta.update(autoinstall_meta)
    target_template = cobbler_api.find_template(
        False, False, name="built-in-answerfile"
    )
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")

    # Act
    result = cobbler_api.templar.render(target_template.content, meta, None)

    # Assert
    assert "<Value>Windows 11 Pro N</Value>" in result
    assert "<Value>Windows 11 Pro</Value>" not in result
    assert "<Key>AAAAA-BBBBB-CCCCC-DDDDD-EEEEE</Key>" in result
    assert "<UILanguage>de-DE</UILanguage>" in result
