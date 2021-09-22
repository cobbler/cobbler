"""
Migration from V3.3.0 to V3.3.1
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC


from schema import SchemaError

from cobbler.settings.migrations import V3_3_0

schema = V3_3_0.schema


def validate(settings: dict) -> bool:
    """
    Checks that a given settings dict is valid according to the reference V3.3.0 schema ``schema``.

    :param settings: The settings dict to validate.
    :return: True if valid settings dict otherwise False.
    """
    try:
        schema.validate(settings)
    except SchemaError:
        return False
    return True


def normalize(settings: dict) -> dict:
    """
    If data in ``settings`` is valid the validated data is returned.

    :param settings: The settings dict to validate.
    :return: The validated dict.
    """
    return schema.validate(settings)


def migrate(settings: dict) -> dict:
    """
    Migration of the settings ``settings`` to version V3.3.0 settings

    :param settings: The settings dict to migrate
    :return: The migrated dict
    """

    # rename keys and update their value
    # add missing keys
    # delete removed keys

    if not validate(settings):
        raise SchemaError("V3.3.0: Schema error while validating")
    return normalize(settings)
