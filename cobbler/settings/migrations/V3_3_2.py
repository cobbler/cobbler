"""
Migration from V3.3.1 to V3.3.2
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2022 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

from typing import Any, Dict

from schema import SchemaError  # type: ignore

from cobbler.settings.migrations import V3_3_1

schema = V3_3_1.schema


def validate(settings: Dict[str, Any]) -> bool:
    """
    Checks that a given settings dict is valid according to the reference V3.3.1 schema ``schema``.

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
    # We are aware of our schema and thus can safely ignore this.
    return schema.validate(settings)  # type: ignore


def migrate(settings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migration of the settings ``settings`` to version V3.3.1 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """

    if not V3_3_1.validate(settings):
        raise SchemaError("V3.3.1: Schema error while validating")

    # rename keys and update their value
    # add missing keys
    # name - value pairs

    return normalize(settings)
