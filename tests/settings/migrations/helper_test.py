"""
Tests for the Cobbler settings migration helpers
"""
# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2021 Dominik Gedon <dgedon@suse.de>
# SPDX-FileCopyrightText: 2021 Enno Gotthold <egotthold@suse.de>
# SPDX-FileCopyrightText: Copyright SUSE LLC

import copy
import pytest
from cobbler.settings.migrations import helper


@pytest.fixture
def example_dict():
    return {
    "a":{
        "r": 1,
        "s": 2,
        "t": 3
        },
    "b":{
        "u": 1,
        "v": {
            "x": 1,
            "y": 2,
            "z": 3
        },
        "w": 3
        }
}


def test_key_add(example_dict):
    # Arrange
    new = helper.Setting("c.a", 5)

    # Act
    helper.key_add(new, example_dict)

    # Assert
    assert example_dict["c"]["a"] == 5


def test_key_delete(example_dict):
    # Arrange
    # Act
    helper.key_delete("b.v.y", example_dict)

    # Assert
    print(example_dict)
    assert example_dict["b"]["v"].get("y") is None


def test_key_get(example_dict):
    # Arrange
    expected_result = helper.Setting("b.u", 1)
    # Act
    result = helper.key_get("b.u", example_dict)

    # Assert
    assert expected_result == result


def test_key_move(example_dict):
    # Arrange
    move = helper.Setting("b.u", 1)

    # Act
    helper.key_move(move, ["a", "a"], example_dict)

    # Assert
    assert example_dict["b"].get("u") is None
    assert example_dict["a"]["a"] == 1


def test_key_rename(example_dict):
    # Arrange
    rename = helper.Setting("b.u", 1)
    # Act
    helper.key_rename(rename, "a", example_dict)

    # Assert
    print(example_dict)
    assert example_dict["b"].get("u") is None
    assert example_dict["b"]["a"] == 1


def test_key_set_value(example_dict):
    # Arrange
    new = helper.Setting("b.u", 5)

    # Act
    helper.key_set_value(new, example_dict)

    # Assert
    assert example_dict["b"]["u"] == 5


def test_key_drop_if_default(example_dict):
    # Arrange

    # Act
    result = helper.key_drop_if_default(example_dict, example_dict)

    # Assert
    assert result == {}


def test_key_drop_if_default_2(example_dict):
    # Arrange
    value_dict = copy.deepcopy(example_dict)
    value_dict["a"]["r"] = 5

    # Act
    result = helper.key_drop_if_default(value_dict, example_dict)

    # Assert
    print(value_dict)
    assert result == {"a": {"r": 5}}
