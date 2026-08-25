"""
Tests for the ItemGroup abstract class.
"""

from typing import Any, Callable, List, Type

import pytest

from cobbler import enums
from cobbler.api import CobblerAPI
from cobbler.items.abstract.base_item import BaseItem
from cobbler.items.abstract.item_group import ItemGroup
from cobbler.items.distro import Distro


class DummyItemGroup(ItemGroup):
    """
    A concrete dummy class to instantiate the abstract ItemGroup class for testing.
    """

    COLLECTION_TYPE = "distro_group"

    def __init__(self, api: CobblerAPI, **kwargs: Any):
        super().__init__(api, **kwargs)

    def make_clone(self) -> "BaseItem":
        return self

    def _resolve(self, property_name: List[str]) -> Any:
        return None

    def _resolve_enum(
        self, property_name: List[str], enum_type: Type[enums.ConvertableEnum]
    ) -> Any:
        return None

    def _resolve_list(self, property_name: List[str]) -> Any:
        return []


def test_members_initialization(cobbler_api: CobblerAPI):
    """
    Test that members is initialized as an empty list.
    """
    group = DummyItemGroup(api=cobbler_api)
    assert getattr(group, "members") == []


def test_members_setter_valid(
    cobbler_api: CobblerAPI, create_distro: Callable[[str], Distro]
):
    """
    Test that the members setter works with a valid list of strings.
    """
    group = DummyItemGroup(api=cobbler_api)
    distro1 = create_distro("test_members_setter_valid_1")
    distro2 = create_distro("test_members_setter_valid_2")
    valid_members = [distro1.uid, distro2.uid]
    setattr(group, "members", valid_members)
    assert getattr(group, "members") == valid_members


def test_members_setter_invalid_type_not_list(cobbler_api: CobblerAPI):
    """
    Test that the members setter raises a TypeError if the value is not a list.
    """
    group = DummyItemGroup(api=cobbler_api)
    with pytest.raises(TypeError, match="members must be a list"):
        setattr(group, "members", "not a list")


def test_members_setter_invalid_member_type(cobbler_api: CobblerAPI):
    """
    Test that the members setter raises a TypeError if any member is not a string.
    """
    group = DummyItemGroup(api=cobbler_api)
    with pytest.raises(TypeError, match="All members must be of type string"):
        setattr(group, "members", ["member1", 123])


def test_from_dict_initialization(
    cobbler_api: CobblerAPI, create_distro: Callable[[str], Distro]
):
    """
    Test that passing a dict to __init__ correctly sets members via from_dict.
    """
    # Note: In from_dict, the keys correspond to properties.
    distro1 = create_distro("test_from_dict_initialization_1")
    distro2 = create_distro("test_from_dict_initialization_2")
    group = DummyItemGroup(api=cobbler_api, members=[distro1.uid, distro2.uid])
    assert getattr(group, "members") == [distro1.uid, distro2.uid]


def test_members_setter_nonexistent_uid_raises(cobbler_api: CobblerAPI):
    """
    Test that the members setter raises a ValueError if a uid does not reference an
    existing item.
    """
    group = DummyItemGroup(api=cobbler_api)
    with pytest.raises(ValueError, match="not an existing"):
        setattr(group, "members", ["does-not-exist"])


def test_members_setter_existing_uid_succeeds(
    cobbler_api: CobblerAPI, create_distro: Callable[[str], Distro]
):
    """
    Test that the members setter accepts a uid that references an existing item.
    """
    group = DummyItemGroup(api=cobbler_api)
    distro1 = create_distro("test_members_setter_existing_uid_succeeds")
    setattr(group, "members", [distro1.uid])
    assert getattr(group, "members") == [distro1.uid]
