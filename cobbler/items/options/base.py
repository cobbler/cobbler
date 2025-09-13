"""
Module for the base Option type. It represents an abstract type that cannot be directly used.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Dict, Generic, List, Type, TypeVar

from cobbler import enums
from cobbler.items.abstract import base_item

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI

ITEM = TypeVar("ITEM", bound=base_item.BaseItem)


class ItemOption(ABC, Generic[ITEM]):
    """
    The abstract base Option from which all other options inherit.
    """

    def __init__(self, api: "CobblerAPI", item: ITEM, **kwargs: Any) -> None:
        # pylint: disable=unused-argument
        self._api = api
        self._item = item

    def _resolve(self, property_name: List[str]) -> Any:
        """
        Logically identically to :func:`~cobbler.items.abstract.base_item.BaseItem._resolve`
        """
        # pylint: disable=protected-access
        return self._item._resolve(property_name)  # type: ignore[reportPrivateUsage]

    def _resolve_list(self, property_name: List[str]) -> Any:
        """
        Logically identically to :func:`~cobbler.items.abstract.base_item.BaseItem._resolve_list`
        """
        # pylint: disable=protected-access
        return self._item._resolve_list(property_name)  # type: ignore[reportPrivateUsage]

    def _resolve_enum(
        self, property_name: List[str], enum_type: Type[enums.ConvertableEnum]
    ) -> Any:
        """
        Logically identically to :func:`~cobbler.items.abstract.base_item.BaseItem._resolve_enum`
        """
        # pylint: disable=protected-access
        return self._item._resolve_enum(property_name, enum_type)  # type: ignore[reportPrivateUsage]

    @property
    @abstractmethod
    def parent_name(self) -> str:
        """
        The name of the object inside the parent class. This should be identical across all items where an option
        is used.

        :returns: The name of the parent attribute or property.
        """

    def serialize(self) -> Dict[str, Any]:
        """
        Logically identically to :func:`~cobbler.items.abstract.base_item.BaseItem.serialize`
        """
        return self.to_dict(resolved=False)

    def deserialize(self, dictionary: Dict[str, Any]):
        """
        Logically identically to :func:`~cobbler.items.abstract.base_item.BaseItem.deserialize`
        """
        self.from_dict(dictionary)

    def to_dict(self, resolved: bool = False) -> Dict[str, Any]:
        """
        Logically identically to :func:`~cobbler.items.abstract.base_item.BaseItem.to_dict`
        """
        result: Dict[str, Any] = {}
        for key, value in self.__dict__.items():
            if key in ("_api", "_item"):
                continue
            new_key = key[1:].lower()
            if isinstance(value, (str, bool, int, float)):
                if resolved and value == enums.VALUE_INHERITED:
                    result[new_key] = getattr(self, new_key)
                else:
                    result[new_key] = value
            elif isinstance(value, list):
                if resolved:
                    result[new_key] = getattr(self, new_key)
                else:
                    result[new_key] = value.copy()
            elif isinstance(value, enums.ConvertableEnum):
                if resolved:
                    result[new_key] = getattr(self, new_key).value
                else:
                    result[new_key] = value.value
            else:
                raise TypeError(f"Unsupported type {type(value)}!")
        return result

    def from_dict(self, dictionary: Dict[str, Any]) -> None:
        """
        Logically identically to :func:`~cobbler.items.abstract.base_item.BaseItem.from_dict`
        """
        for key, value in dictionary.items():
            if hasattr(self, f"_{key}"):
                setattr(self, key, value)
