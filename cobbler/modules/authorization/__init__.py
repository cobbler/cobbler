"""
This module represents all Cobbler methods of authorization. All present modules may be used through the configuration
file ``modules.conf`` normally found at ``/etc/cobbler/``.

In the following the specification of an authorization module is given:

#. The name of the only public method - except the generic ``register()`` method -  must be ``authorize``
#. The attributes are - in exactly that order: ``api_handle``, ``user``, ``resource``, ``arg1``, ``arg2``
#. The ``api_handle`` must be the main ``CobblerAPI`` instance.
#. The ``user`` and ``resource`` attribute must be of type ``str``.
#. The attributes ``arg1`` and ``arg2`` are reserved for the individual use of your authorization module and may have
   any type and form your desire.
#. The method must return an integer in all cases.
#. The method should return ``1`` for success and ``0` for an authorization failure.
#. Additional codes can be defined, however they should be documented in the module description.
#. The values of additional codes should be positive integers.
#. Errors should result in the return of ``-1`` and a log message to the standard Python logger obtioned via
   ``logging.getLogger()``.
#. The return value of ``register()`` must be ``authz``.
"""
