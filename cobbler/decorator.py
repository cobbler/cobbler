"""
This module provides decorators that are required for Cobbler to work as expected.
"""
# The idea for the subclassed property decorators is from: https://stackoverflow.com/a/59313599/4730773


class InheritableProperty(property):
    """
    This property is supposed to provide a way to identify properties in code that can be set to inherit.
    """

    inheritable = True


class InheritableDictProperty(InheritableProperty):
    """
    This property is supposed to provide a way to identify properties in code that can be set to inherit.
    """
