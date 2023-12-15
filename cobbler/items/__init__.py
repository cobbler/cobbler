"""
This package contains all data storage classes. The classes are responsible for ensuring that types of the properties
are correct but not for logical checks. The classes should be as stupid as possible. Further they are responsible for
returning the logic for serializing and deserializing themselves.

Cobbler has a concept of inheritance where an attribute/a property may have the value ``<<inherit>>``. This then takes
over the value of the parent item with the exception of dictionaries. Values that are of type ``dict`` are always
implicitly inherited, to remove a key-value pair from the dictionary in the inheritance chain prefix the key with ``!``.
"""
