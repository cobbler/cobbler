*******
Scripts
*******

.. warning:: All execution examples are not meant to be copy&pasted! Cobbler instances are very custom and each command
             needs to be adjusted to your environment.

settings-migration-v1-to-v2.sh
##############################

Description
===========

This script will try to replace your old ``modules.conf`` file (< 3.0.1) to a new one (>= 3.0.1).

Execution examples
==================

.. code-block:: shell

   ./settings-migration-v1-to-v2.sh -h
   ./settings-migration-v1-to-v2.sh -r -f /etc/cobbler/modules.conf
   ./settings-migration-v1-to-v2.sh -n -f /etc/cobbler/modules.conf
   ./settings-migration-v1-to-v2.sh -s -f /etc/cobbler/modules.conf

Author
======

`Enno Gotthold <https://github.com/SchoolGuy>`_

cobbler-settings
################

Description
===========

This script will enable you to manage the settings of Cobbler.

Execution examples
==================

.. code-block:: shell

   cobbler-settings -c /etc/cobbler/settings migrate # Prints updated settings file to stdout
   cobbler-settings -c /etc/cobbler/settings.yaml migrate -t /etc/cobbler/settings.new.yaml # Writes migrated result to file
   cobbler-settings validate # Validates the file at /etc/cobbler/settings.yaml
   cobbler-settings automigrate --enable # Enables settings auto-migration
   cobbler-settings automigrate # Disables settings auto-migration
   cobbler-settings modify --key="next_server_v4" --value="127.0.0.1" # Changes the key to the new value

Author
======

`Enno Gotthold <https://github.com/SchoolGuy>`_ & `Dominik Gedon <https://github.com/nodeg>`_
