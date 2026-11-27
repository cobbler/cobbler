"""
Migration from V4.0.0 to V4.0.1
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2026 Enno Gotthold <egotthold@suse.com
# SPDX-FileCopyrightText: Copyright SUSE LLC

from typing import Any, Dict

from schema import SchemaError  # type: ignore

from cobbler.settings.migrations import V4_0_0

# schema identical to V4_0_0 (4.0.1 is a re-release of 4.0.0)
schema = V4_0_0.schema


def validate(settings: Dict[str, Any]) -> bool:
    """
    Checks that a given settings dict is valid according to the reference V4.0.1 schema ``schema``.

    :param settings: The settings dict to validate.
    :return: True if valid settings dict otherwise False.
    """
    try:
        schema.validate(settings)  # type: ignore
    except SchemaError:
        return False
    return True


def normalize(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    If data in ``settings`` is valid the validated data is returned.

    :param settings: The settings dict to validate.
    :return: The validated dict.
    """
    return schema.validate(settings)  # type: ignore


def migrate(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migration of the settings ``settings`` to version V4.0.1 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """

    if not V4_0_0.validate(settings):
        raise SchemaError("V4.0.0: Schema error while validating")

    return normalize(settings)
