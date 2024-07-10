"""
This module provides decorators that are required for Cobbler to work as expected.
"""
# The idea for the subclassed property decorators is from: https://stackoverflow.com/a/59313599/4730773

from typing import Any, Optional

from cobbler.items.abstract import base_item


class LazyProperty(property):
    """
    This property is supposed to provide a way to override the lazy-read value getter.
    """

    def __get__(self, obj: Any, objtype: Optional[type] = None):
        if obj is None:
            return self
        if (
            isinstance(obj, base_item.BaseItem)
            and not obj.inmemory
            and obj._has_initialized  # pyright: ignore [reportPrivateUsage]
        ):
            obj.deserialize()
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
