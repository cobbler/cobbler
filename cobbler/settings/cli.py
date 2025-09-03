"""
Tool to manage the settings of Cobbler without the daemon running.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: 2022 Pablo Suárez Hernández <psuarezhernandez@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC


import argparse
from typing import Any, Dict, List
from typing import Optional as TOptional

import yaml
from schema import Optional, SchemaError  # type: ignore

from cobbler import settings
from cobbler.settings import migrations
from cobbler.settings.migrations import EMPTY_VERSION, helper
from cobbler.utils import input_converters


# TODO: Transform this into a lamda/list comprehension
def __generate_version_choices() -> List[str]:
    versions = migrations.VERSION_LIST.keys()
    result: List[str] = []
    for version in versions:
        result.append(f"{version.major}.{version.minor}.{version.patch}")

    return result


def __check_settings(filepath: str, settings_to_preserve: List[str]) -> Dict[str, Any]:
    try:
        result = settings.read_yaml_file(filepath)
    except (FileNotFoundError, yaml.YAMLError) as error:
        print(str(error))
        return {}

    settings_version = migrations.get_settings_file_version(
        result, settings_to_preserve
    )
    if settings_version == EMPTY_VERSION:
        print("Error detecting settings file version!")
        return {}
    print(f"The following version was detected: {settings_version}")
    return result


def __update_settings(
    yaml_dict: Dict[str, Any], filepath: str, settings_to_preserve: List[str]
) -> int:
    if not settings.update_settings_file(yaml_dict, filepath, settings_to_preserve):
        print("Modification would make settings invalid!")
        return 1
    print("Updated settings file successfully!")
    return 0


def validate(args: argparse.Namespace) -> int:
    """
    TODO
    """
    try:
        result = settings.read_yaml_file(args.config)
    except (FileNotFoundError, yaml.YAMLError) as error:
        print(str(error))
        return 1

    # Exclude settings to preserve from the list of settings to migrate
    result, _ = migrations.filter_settings_to_validate(result, args.preserve_settings)

    version_split = args.version.split(".")
    version = migrations.CobblerVersion(*version_split)

    try:
        migrations.VERSION_LIST[version].normalize(result)
    except SchemaError as error:
        print("Settings file invalid!")
        print(str(error))
        return 1
    print("Settings file successfully validated!")
    return 0


def migrate(args: argparse.Namespace) -> int:
    """
    TODO
    """
    settings_dict = __check_settings(args.config, args.preserve_settings)
    if not settings_dict:
        print("Settings file invalid!")
        return 1

    old = migrations.get_settings_file_version(settings_dict, args.preserve_settings)
    if old == migrations.EMPTY_VERSION:
        print("Settings file version could not be discovered!")
        return 1

    new_list = args.new.split(".")
    new = migrations.CobblerVersion(*new_list)

    result_settings = migrations.migrate(
        settings_dict, args.config, old, new, args.preserve_settings
    )

    # only if --target supplied
    if args.target is not None:
        return __update_settings(result_settings, args.target, args.preserve_settings)

    # if --target not supplied
    print(yaml.dump(result_settings))
    return 0


def automigrate(args: argparse.Namespace) -> int:
    """
    TODO
    """
    settings_dict = __check_settings(args.config, args.preserve_settings)
    if not settings_dict:
        print("Settings file invalid!")
        return 1
    setting_obj = helper.Setting("auto_migrate_settings", args.enable_automigration)
    helper.key_set_value(setting_obj, settings_dict)

    return __update_settings(settings_dict, args.config, args.preserve_settings)


def modify(args: argparse.Namespace) -> int:
    """
    TODO
    """
    # pylint: disable=protected-access
    # Disable protected-access because we can't use the property that is available in newer versions of the schema
    # library.
    settings_dict = __check_settings(args.config, args.preserve_settings)
    if not settings_dict:
        print("Settings file invalid!")
        return 1
    schema = migrations.get_schema(migrations.get_installed_version())
    setting_obj = helper.Setting(args.key, args.value)
    # _schema used due to old version of python3-schema in Leap
    try:
        key_type = schema._schema[setting_obj.key_name]  # type: ignore
    except KeyError:
        try:
            key_type = schema._schema[Optional(setting_obj.key_name)]  # type: ignore
        except KeyError:
            print("Requested key not found in the settings!")
            return 1
    if key_type not in (bool, int, float, str, dict, list):
        if isinstance(key_type, list):
            key_type = list
        elif isinstance(key_type, dict):
            key_type = dict
        else:
            print("Unsupported type!")
    if isinstance(Optional, key_type):
        key_type = schema._schema[setting_obj.key_name].name  # type: ignore
    if key_type == bool:
        setting_obj.value = input_converters.input_boolean(setting_obj.value)
    elif key_type == int:
        setting_obj.value = int(setting_obj.value)
    elif key_type == float:
        setting_obj.value = float(setting_obj.value)
    elif key_type == list:
        setting_obj.value = input_converters.input_string_or_list(setting_obj.value)
    elif key_type == dict:
        setting_obj.value = input_converters.input_string_or_dict(setting_obj.value)
    elif key_type == str:
        setting_obj.value = setting_obj.value
    else:
        print("Unsupported type!")
        return 1
    helper.key_set_value(setting_obj, settings_dict)

    return __update_settings(settings_dict, args.config, args.preserve_settings)


parser = argparse.ArgumentParser(
    description="Manage the settings of Cobbler without a running daemon."
)
parser.add_argument(
    "-c",
    "--config",
    help="The location of the Cobbler configuration file.",
    default="/etc/cobbler/settings.yaml",
)
parser.add_argument(
    "--preserve-settings",
    help="Comma separeted list of custom settings to preserve during migration",
    dest="preserve_settings",
    type=lambda arg: arg.split(","),
    default=[],
)
subparsers = parser.add_subparsers(
    title="Subcommands", help="One of these commands is required."
)
parser_validate = subparsers.add_parser(
    "validate",
    description="Validates if Cobbler would start with the current settings file.",
)
parser_validate.set_defaults(func=validate)
parser_validate.add_argument(
    "-v",
    "--version",
    help="The version to validate against.",
    choices=sorted(__generate_version_choices()),
    default=sorted(__generate_version_choices())[-1],
)
parser_migrate = subparsers.add_parser(
    "migrate",
    description="Migrates from the current version to the version provided with "
    '"--new".',
)
parser_migrate.set_defaults(func=migrate)
# TODO: Implement in the future
# parser_migrate.add_argument("--diff", "-d",
#                            help="Whether to produce a diff output or not.",
#                            action="store_true",
#                            default=False)
parser_migrate.add_argument(
    "-t",
    "--target",
    help="Write the resulting settings to the target path given in this argument.",
)
parser_migrate.add_argument(
    "--new",
    help="The new version to migrate to, e.g. 3.3.0",
    dest="new",
    choices=sorted(__generate_version_choices()),
    default=sorted(__generate_version_choices())[-1],
)
parser_automigrate = subparsers.add_parser(
    "automigrate",
    description="Enables or disables the automigration on startup of the daemon. "
    'If no flag is provided, the default is "--disable".',
)
parser_automigrate.set_defaults(func=automigrate)
parser_automigrate.add_argument(
    "-e",
    "--enable",
    help="Enables settings automigration.",
    dest="enable_automigration",
    action="store_true",
)
parser_automigrate.add_argument(
    "-d",
    "--disable",
    help="Disables settings automigration.",
    dest="enable_automigration",
    action="store_false",
)
parser_modify = subparsers.add_parser(
    "modify", description="Modify the value of a key in the config file."
)
parser_modify.set_defaults(func=modify)
parser_modify.add_argument(
    "-k",
    "--key",
    help="The name of the key in file to edit. If the key is nested use the format "
    '"parent_key.key".',
    required=True,
)
parser_modify.add_argument(
    "-v", "--value", help="The new value of the key.", required=True
)


def main(args: TOptional[List[str]] = None) -> int:
    """
    Main entrypoint for the the ``cobbler-settings`` script.
    """
    parsed_args = parser.parse_args(args=args)
    if hasattr(parsed_args, "func"):
        return parsed_args.func(parsed_args)
    parser.print_help()
    return 0
