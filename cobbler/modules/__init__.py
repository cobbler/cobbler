"""
This part of Cobbler may be utilized by any plugins which are extending Cobbler and core code which can be exchanged
through the ``modules.conf`` file.

A Cobbler module is loaded if it has a method called ``register()``. The method must return a ``str`` which represents
the module category.
"""
