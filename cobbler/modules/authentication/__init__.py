"""
This module represents all Cobbler methods of authentication. All present modules may be used through the configuration
file ``modules.conf`` normally found at ``/etc/cobbler/``.

In the following the specification of an authentication module is given:

#. The name of the only public method - except the generic ``register()`` method -  must be ``authenticate``
#. The attributes are - in exactly this order: ``api_handle``, ``username``, ``password``
#. The username and password both must be of type ``str``.
#. The ``api_handle`` must be the main ``CobblerAPI`` instance.
#. The return value of the module must be a ``bool``.
#. The method should only return ``True`` in case the authentication is successful.
#. Errors should result in the return of ``False`` and a log message to the standard Python logger obtioned via
   ``logging.getLogger()``.
#. The return value of ``register()`` must be ``authn``.

The list of currently known authentication modules is:

- authentication.configfile
- authentication.denyall
- authentication.ldap
- authentication.pam
- authentication.passthru
- authentication.spacewalk
"""
