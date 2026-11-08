"""
Test module to verify the built-in Windows startnet template's "net use" retry loop
distinguishes transient SMB failures from permanent ones, instead of retrying any
non-zero exit code the same way.
"""

from typing import Callable

import pytest

from cobbler import utils
from cobbler.api import CobblerAPI
from cobbler.items.distro import Distro
from cobbler.items.profile import Profile


def _render_startnet(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
) -> str:
    target_template = cobbler_api.find_template(False, False, name="built-in-startnet")
    if target_template is None or isinstance(target_template, list):
        pytest.fail("Could not find built-in template!")
    test_distro = create_distro()
    test_profile = create_profile(test_distro.uid)

    meta = utils.blender(cobbler_api, False, test_profile)
    autoinstall_meta = meta.get("autoinstall_meta", {})
    meta.update(autoinstall_meta)

    return cobbler_api.templar.render(target_template.content, meta, None)


def test_startnet_net_use_retry_only_retries_on_transient_error_53(
    cobbler_api: CobblerAPI,
    create_distro: Callable[[], Distro],
    create_profile: Callable[[str], Profile],
):
    """
    Regression test: "net use"'s exit code was captured but never inspected, so any non-zero
    result (including permanent failures like a bad share name or bad credentials) retried 5
    times the same way as the one documented transient case (error 53, "network path not
    found" before the SMB redirector has finished its post-DHCP handshake). The retry loop
    must fail fast on anything other than error 53 instead of burning all 5 retries on a
    permanent failure.
    """
    # Act
    result = _render_startnet(cobbler_api, create_distro, create_profile)

    # Assert
    assert "IF NOT %exit_code% EQU 53 GOTO NET_USE_FAILED" in result
