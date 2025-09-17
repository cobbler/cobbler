"""
This module provides decorators that are required for Cobbler to work as expected.
"""

# The idea for the subclassed property decorators is from: https://stackoverflow.com/a/59313599/4730773

from typing import Any, Optional

from cobbler.items.abstract import base_item
from cobbler.items.options import base


class LazyProperty(property):
    """
    This property is supposed to provide a way to override the lazy-read value getter.
    """

    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Any:
        if obj is None:
            return self
        if (
            isinstance(obj, base_item.BaseItem)
            and not obj.inmemory
            and obj._has_initialized  # pyright: ignore [reportPrivateUsage]
        ):
            obj.deserialize()
        if (
            isinstance(obj, base.ItemOption)
            and not obj._item.inmemory  # type: ignore
            and obj._item._has_initialized  # type: ignore
        ):
            obj._item.deserialize()  # type: ignore
        if self.fget is None:
            # This may occur if the functional way of using a property is used.
            raise ValueError("Property had no getter!")
        return self.fget(obj)


class InheritableProperty(LazyProperty):
    """
    This property is supposed to provide a way to identify properties in code that can be set to inherit.
    """

    inheritable = True


class InheritableDictProperty(InheritableProperty):
    """
    This property is supposed to provide a way to identify properties in code that can be set to inherit.
    """
