"""
Migration from V3.3.5 to V3.3.6
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2024 Enno Gotthold <egotthold@suse.com
# SPDX-FileCopyrightText: Copyright SUSE LLC

from schema import SchemaError  # type: ignore

from cobbler.settings.migrations import V3_3_5

# schema identical to V3_3_5
schema = V3_3_5.schema


def validate(settings: dict) -> bool:
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


def normalize(settings: dict) -> dict:
    """
    If data in ``settings`` is valid the validated data is returned.

    :param settings: The settings dict to validate.
    :return: The validated dict.
    """
    return schema.validate(settings)  # type: ignore


def migrate(settings: dict) -> dict:
    """
    Migration of the settings ``settings`` to version V3.3.4 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """

    if not V3_3_5.validate(settings):
        raise SchemaError("V3.3.5: Schema error while validating")

    # rename keys and update their value
    # add missing keys
    # name - value pairs

    return normalize(settings)
