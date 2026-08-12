"""
Process management module that restarts a Docker container, chosen by a label, instead of a local process. This is
useful when DHCP/DNS run as separate sidecar containers rather than inside the same process namespace as cobblerd.
"""

# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: Copyright 2006-2009, Red Hat, Inc and Others
# SPDX-FileCopyrightText: Michael DeHaan <michael.dehaan AT gmail>

import logging
from typing import TYPE_CHECKING, Any, Dict, List

if TYPE_CHECKING:
    from cobbler.api import CobblerAPI

try:
    # pylint: disable-next=ungrouped-imports
    import docker

    from docker.errors import DockerException  # type: ignore[assignment]

    DOCKER_SDK_LOADED = True
except ModuleNotFoundError:
    # pylint: disable=invalid-name
    docker = None  # type: ignore[assignment]

    class DockerException(Exception):  # type: ignore[no-redef]
        """
        Placeholder used only when the optional ``docker`` SDK isn't installed, so ``except DockerException`` below
        stays a valid exception handler (catching ``None`` would raise ``TypeError`` at runtime) instead of relying
        on an invariant static analysis can't verify. Never actually raised: the early ``DOCKER_SDK_LOADED`` guard
        in restart_service() means this branch's true fallback is never reached in practice.
        """

    # This is a constant! pyright just doesn't understand it.
    DOCKER_SDK_LOADED = False  # type: ignore

logger = logging.getLogger()

LABEL_KEY = "cobbler.io/managed-service"

# Mirrors the default for settings().modules["process_management"]["docker_service_labels"] defined in
# cobbler.settings.Settings.__init__() (and the V4_0_0 migration / shipped settings.yaml). Duplicated here - rather
# than imported - because it is a plain data literal, not something ``cobbler.settings`` exposes as a standalone
# constant, and importing the whole settings module here just for this one dict would be more awkward than helpful.
DEFAULT_DOCKER_SERVICE_LABELS: Dict[str, str] = {
    "dhcpd": "dhcp",
    "dhcpd4": "dhcp",
    "dhcpd6": "dhcp",
    "named": "dns",
    "dnsmasq": "dnsmasq",
}


def register() -> str:
    """
    The mandatory Cobbler module registration hook.

    :return: "process_management" if the optional ``docker`` Python package is available, else "".
    """
    if not DOCKER_SDK_LOADED:
        return ""
    return "process_management"


def restart_service(api_handle: "CobblerAPI", service_name: str) -> int:
    """
    Restart the Docker container labeled as responsible for ``service_name``.

    Exactly one container must be found carrying the label ``cobbler.io/managed-service=<value>``, where
    ``<value>`` is looked up from the ``docker_service_labels`` setting (falling back to the raw ``service_name``
    if it isn't mapped). Zero matches or more than one match is treated as a hard error - never a silent no-op and
    never a restart of more than one container.

    :param api_handle: The api instance to resolve settings.
    :param service_name: The name of the service to restart (e.g. "dhcpd", "named", "dnsmasq").
    :return: ``0`` on success, matching ``process_management.service.restart_service()``'s convention. Any other
             value indicates failure.
    """
    if not DOCKER_SDK_LOADED:
        logger.error(
            'Could not restart service "%s": the "docker" Python package is not installed',
            service_name,
        )
        return 1

    # Both keys are Optional in the settings schema, so a hand-edited settings.yaml that sets
    # modules.process_management.module to this module without also including the two companion keys would
    # otherwise validate fine and then raise an uncaught KeyError here. Fall back to the same defaults as the
    # settings scaffold instead.
    process_management_settings: Dict[str, Any] = api_handle.settings().modules.get(
        "process_management", {}
    )
    socket_path = process_management_settings.get(
        "docker_socket_path", "/var/run/docker.sock"
    )
    docker_service_labels: Dict[str, str] = process_management_settings.get(
        "docker_service_labels", DEFAULT_DOCKER_SERVICE_LABELS
    )
    label_value = docker_service_labels.get(service_name, service_name)

    client = None
    try:
        # DOCKER_SDK_LOADED being True at this point guarantees "docker" is the real module, not None -- pyright
        # cannot see that invariant across the early return above.
        client = docker.DockerClient(base_url=f"unix://{socket_path}")  # type: ignore[reportOptionalMemberAccess]
        containers: List[Any] = client.containers.list(
            all=True, filters={"label": f"{LABEL_KEY}={label_value}"}
        )
        if len(containers) == 0:
            logger.error(
                'Could not restart service "%s": no Docker container found with label "%s=%s"',
                service_name,
                LABEL_KEY,
                label_value,
            )
            return 1
        if len(containers) > 1:
            logger.error(
                'Could not restart service "%s": found %d Docker containers with label "%s=%s", expected exactly '
                "one",
                service_name,
                len(containers),
                LABEL_KEY,
                label_value,
            )
            return 1
        containers[0].restart()
        return 0
    except DockerException as error:
        logger.error(
            'Restarting the Docker container for service "%s" failed',
            service_name,
            exc_info=error,
        )
        return 1
    except Exception as error:  # pylint: disable=broad-except
        # Covers e.g. the Docker daemon not being reachable at all (socket missing, permission denied, ...), which
        # may not raise a DockerException depending on the underlying transport error.
        logger.error(
            'Restarting the Docker container for service "%s" failed unexpectedly (is the Docker daemon at "%s" '
            "reachable?)",
            service_name,
            socket_path,
            exc_info=error,
        )
        return 1
    finally:
        if client is not None:
            client.close()
