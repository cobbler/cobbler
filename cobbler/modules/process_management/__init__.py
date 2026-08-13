"""
This module represents all Cobbler methods of restarting the daemons (DHCP, DNS, ...) that Cobbler manages the
configuration of. All present modules may be used through the configuration file ``settings.yaml``, in the
``process_management`` section.

In the following the specification of a process management module is given:

#. The module must define a ``register() -> str`` function taking no arguments. It must return ``"process_management"``
   to be picked up as a member of this category, or ``""`` if an optional dependency required by the module (e.g. the
   ``docker`` Python package) is not available.
#. The module must define a ``restart_service(api_handle: "CobblerAPI", service_name: str) -> int`` function. It
   restarts the given service (for example ``"dhcpd"``, ``"named"`` or ``"dnsmasq"``) and returns ``0`` on success.
   Any other value indicates failure.
#. Errors should result in a log message to the standard Python logger obtained via ``logging.getLogger()`` in
   addition to a non-zero return code.

The list of currently known process management modules is:

- process_management.service
- process_management.systemd
- process_management.supervisor
- process_management.docker

``process_management.systemd``/``process_management.supervisor`` restart a service via systemd/supervisord
directly, with no auto-detection - select one of these explicitly when you already know which process manager
the host uses and want to skip the detection ``process_management.service`` performs (which delegates to these
same two modules for those cases, falling back to a SysV ``service`` invocation, or an error, if neither is
present).

``modules.process_management.module`` also accepts the special value ``"auto"``, which is not a real module in
this package - it is resolved by ``CobblerAPI.get_process_management_module()`` to ``process_management.docker``
or ``process_management.service`` depending on whether cobblerd is running inside a container (see
``process_management.detection.is_containerized()``). An explicit ``process_management.service``/
``process_management.docker`` setting is never overridden by container detection - only ``"auto"`` is affected.
"""
