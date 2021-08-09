"""
Tool to manage the Settings of Cobbler without the demon running.
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC


import argparse
import sys

from typing import List

# https://docs.python.org/3.6/howto/argparse.html#id1
# https://docs.python.org/3.6/library/argparse.html

# Desired usage, where [] means that the argument is optional and has a default (exception: automigrate, there it means
#     use one of the two):
# cobbler-settings [--config=/etc/cobbler/settings.yaml] validate
# cobbler-settings [--config=/etc/cobbler/settings.yaml] migrate [--diff] [--target=/etc/cobbler/cobbler-new.yaml]
# cobbler-settings [--config=/etc/cobbler/settings.yaml] automigrate [--enable] [--disable]
# cobbler-settings [--config=/etc/cobbler/settings.yaml] modify --key=name --value=value


parser = argparse.ArgumentParser(description='Manage the settings of Cobbler without a running demon.')
parser.add_argument('--config')
parser.add_argument('validate')
parser.add_argument('migrate')
parser.add_argument('automigrate')
parser.add_argument('modify')


def main(args: List[str]) -> int:
    parser.parse_args(args)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
