"""
Helper module which contains shared logic for adjusting the settings.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import datetime
import os
from shutil import copytree
from typing import Any, Dict, List, Union


class Setting:
    """
    Specifies a setting object
    """

    def __init__(self, location: Union[str, List[str]], value: Any):
        """
        Conutructor
        """
        if isinstance(location, str):
            self.location = self.split_str_location(location)
        elif isinstance(location, list):  # type: ignore
            self.location = location
        else:
            raise TypeError("location must be of type str or list.")
        self.value = value

    def __eq__(self, other: Any) -> bool:
        """
        Compares 2 Setting objects for equality. Necesarry for the tests.
        """
        if not isinstance(other, Setting):
            return False
        return self.value == other.value and self.location == other.location

    @property
    def key_name(self) -> str:
        """
        Returns the location.
        """
        return self.location[-1]

    @staticmethod
    def split_str_location(location: str) -> List[str]:
        """
        Split the given location at "."
        Necessary for nesting in our settings file

        :param location: Can be "manage.dhcp_v4" or "restart.dhcp_v4" for example.
        """
        return location.split(".")


# Some algorithms taken from https://stackoverflow.com/a/14692746/4730773


def key_add(new: Setting, settings: Dict[str, Any]) -> None:
    """
    Add a new settings key.

    :param new: The new setting to add.
    :param settings: [description]
    """
    nested = new.location
    for key in nested[:-1]:
        if settings.get(key) is None:
            settings[key] = {}
        settings = settings[key]
    settings[nested[-1]] = new.value


def key_delete(delete: str, settings: Dict[str, Any]) -> None:
    """
    Deletes a given setting

    :param delete: The name of the setting to be deleted.
    :param settings: The settings dict where the key should be deleted.
    """
    delete_obj = Setting(delete, None)
    if len(delete_obj.location) == 1:
        del settings[delete_obj.key_name]
    else:
        del key_get(".".join(delete_obj.location[:-1]), settings).value[
            delete_obj.key_name
        ]


def key_get(key: str, settings: Dict[str, Any]) -> Setting:
    """
    Get a key from the settings

    :param key: The key to get in the form "a.b.c"
    :param settings: The dict to operate on.
    :return: The desired key from the settings dict
    """
    # TODO: Check if key does not exist

    if not key:
        raise ValueError("Key must not be empty!")
    new = Setting(key, None)
    nested = new.location
    for keys in nested[:-1]:
        settings = settings[keys]
    new.value = settings[nested[-1]]
    return new


def key_move(move: Setting, new_location: List[str], settings: Dict[str, Any]) -> None:
    """
    Delete the old setting and create a new key at ``new_location``

    :param move: The name of the old key which should be moved.
    :param new_location: The location of the new key
    :param settings: The dict to operate on.
    """
    new_setting = Setting(new_location, move.value)
    key_delete(".".join(move.location), settings)
    key_add(new_setting, settings)


def key_rename(old_name: Setting, new_name: str, settings: Dict[str, Any]) -> None:
    """
    Wrapper for key_move()

    :param old_name: The old name
    :param new_name: The new name
    :param settings:
    """
    new_location = old_name.location[:-1] + [new_name]
    key_move(old_name, new_location, settings)


def key_set_value(new: Setting, settings: Dict[str, Any]) -> None:
    """
    Change the value of a setting.

    :param new: A Settings object with the new information.
    :param settings: The settings dict.
    """
    nested = new.location
    for key in nested[:-1]:
        settings = settings[key]
    settings[nested[-1]] = new.value


def key_drop_if_default(
    settings: Dict[str, Any], defaults: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Drop all keys which values are identical to the default ones.

    :param settings: The current settings read from an external source
    :param defaults: The full settings with default values
    """
    for key in list(settings.keys()):
        if isinstance(settings[key], dict):
            settings[key] = key_drop_if_default(settings[key], defaults[key])
            if len(settings[key]) == 0:
                del settings[key]
        else:
            if settings[key] == defaults[key]:
                settings.pop(key)
    return settings


def backup_dir(dir_path: str) -> None:
    """
    Copies the directory tree and adds a suffix ".backup.XXXXXXXXX" to it.

    :param dir_path: The full path to the directory which should be backed up.
    :raises FileNotFoundError: In case the path specified was not existing.
    """
    src = os.path.normpath(dir_path)
    now_iso = datetime.datetime.now().isoformat()
    copytree(dir_path, f"{src}.backup.{now_iso}")
