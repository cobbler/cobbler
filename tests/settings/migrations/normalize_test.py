"""
Tests for the Cobbler settings normalizations
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import yaml

from cobbler.settings.migrations import (
    V3_3_0,
    V3_2_1,
    V3_2_0,
    V3_1_2,
    V3_1_1,
    V3_1_0,
    V3_0_1,
    V3_0_0,
    V3_3_1,
    V3_3_2,
    V3_3_3,
    V3_3_4,
    V3_3_5,
)


def test_normalize_v3_0_0():
    # Arrange
    with open("/code/tests/test_data/V3_0_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_0_0.normalize(old_settings_dict)

    # Assert
    assert len(V3_0_0.normalize(new_settings)) == 111


def test_normalize_v3_0_1():
    # Arrange
    with open("/code/tests/test_data/V3_0_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_0_1.normalize(old_settings_dict)

    # Assert
    assert len(V3_0_1.normalize(new_settings)) == 111


def test_normalize_v3_1_0():
    # Arrange
    with open("/code/tests/test_data/V3_1_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_0.normalize(old_settings_dict)

    # Assert
    assert len(V3_1_0.normalize(new_settings)) == 111


def test_normalize_v3_1_1():
    # Arrange
    with open("/code/tests/test_data/V3_1_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_1.normalize(old_settings_dict)

    # Assert
    assert len(V3_1_1.normalize(new_settings)) == 111


def test_normalize_v3_1_2():
    # Arrange
    with open("/code/tests/test_data/V3_1_2/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_1_2.normalize(old_settings_dict)

    # Assert
    assert len(V3_1_2.normalize(new_settings)) == 110


def test_normalize_v3_2_0():
    # Arrange
    with open("/code/tests/test_data/V3_2_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_2_0.normalize(old_settings_dict)

    # Assert
    assert len(V3_2_0.normalize(new_settings)) == 112


def test_normalize_v3_2_1():
    # Arrange
    with open("/code/tests/test_data/V3_2_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_2_1.normalize(old_settings_dict)

    # Assert
    assert len(V3_2_1.normalize(new_settings)) == 111


def test_normalize_v3_3_0():
    # Arrange
    with open("/code/tests/test_data/V3_3_0/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_0.normalize(old_settings_dict)

    # Assert
    assert len(V3_3_0.normalize(new_settings)) == 121


def test_normalize_v3_3_1():
    # Arrange
    with open("/code/tests/test_data/V3_3_1/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_1.normalize(old_settings_dict)

    # Assert
    assert len(V3_3_1.normalize(new_settings)) == 129


def test_normalize_v3_3_2():
    # Arrange
    with open("/code/tests/test_data/V3_3_2/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_2.normalize(old_settings_dict)

    # Assert
    assert len(V3_3_2.normalize(new_settings)) == 129


def test_normalize_v3_3_3():
    # Arrange
    with open("/code/tests/test_data/V3_3_3/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_3.normalize(old_settings_dict)

    # Assert
    assert len(new_settings) == 130
    # Migration of default_virt_file_size to float is working
    assert isinstance(new_settings.get("default_virt_file_size", None), float)

def test_normalize_v3_3_4():
    # Arrange
    with open("/code/tests/test_data/V3_3_4/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_4.normalize(old_settings_dict)

    # Assert
    assert len(new_settings) == 130

def test_normalize_v3_3_5():
    # Arrange
    with open("/code/tests/test_data/V3_3_5/settings.yaml") as old_settings:
        old_settings_dict = yaml.safe_load(old_settings.read())

    # Act
    new_settings = V3_3_5.normalize(old_settings_dict)

    # Assert
    assert len(new_settings) == 131
