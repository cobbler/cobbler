"""
This module contains extensions for services Cobbler is managing. The services are restarted via the ``service`` command
or alternatively through the server executables directly. Cobbler does not announce the restarts but is expecting to be
allowed to do this on its own at any given time. Thus all services managed by Cobbler should not be touched by any
other tool or administrator.
"""
