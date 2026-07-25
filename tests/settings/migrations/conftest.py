"""
Shared fixtures for the Cobbler settings migration tests.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC
import pathlib

import pytest


@pytest.fixture(scope="function", autouse=True)
def delete_modules_conf():
    """
    Removes /etc/cobbler/modules.conf and /etc/cobbler/mongodb.conf after every
    test, since several migration versions read (and then delete) these files as
    part of migrate().
    """
    yield
    modules_conf_path = pathlib.Path("/etc/cobbler/modules.conf")
    if modules_conf_path.exists():
        modules_conf_path.unlink()
    mongodb_conf_path = pathlib.Path("/etc/cobbler/mongodb.conf")
    if mongodb_conf_path.exists():
        mongodb_conf_path.unlink()
