***********************************
Cobbler CLI
***********************************

This page contains a description for commands which can be used from the CLI. Under this paragraph you can find the
current output of the CLI help.

Short Usage: ``cobbler command [subcommand] [--arg1=value1] [--arg2=value2]``

Long Usage:

.. code-block:: shell

    cobbler <distro|profile|system|repo|image|mgmtclass|package|file> ... [add|edit|copy|get-autoinstall*|list|remove|rename|report] [options|--help]
    cobbler <aclsetup|buildiso|import|list|replicate|report|reposync|sync|validate-autoinstalls|version|signature|get-loaders|hardlink> [options|--help]

cobbler distro
++++++++++++++

Example:

.. code-block:: shell

    $ cobbler distro

cobbler profile
+++++++++++++++

Example:

.. code-block:: shell

    $ cobbler profile

cobbler system
++++++++++++++

Example:

.. code-block:: shell

    $ cobbler system

cobbler repo
++++++++++++

Example:

.. code-block:: shell

    $ cobbler repo

cobbler image
+++++++++++++

Example:

.. code-block:: shell

    $ cobbler image

cobbler mgmtclass
+++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler mgmtclass

cobbler package
+++++++++++++++

Example:

.. code-block:: shell

    $ cobbler package

cobbler file
++++++++++++

Example:

.. code-block:: shell

    $ cobbler file

cobbler aclsetup
++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler aclsetup

cobbler buildiso
++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler buildiso

cobbler import
++++++++++++++

Example:

.. code-block:: shell

    $ cobbler import

cobbler list
++++++++++++

Example:

.. code-block:: shell

    $ cobbler list

cobbler replicate
+++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler replicate

cobbler report
+++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler report

cobbler reposync
++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler reposync

cobbler sync
++++++++++++

The sync command is very important, though very often unnecessary for most situations. It's primary purpose is to force
a rewrite of all configuration files, distribution files in the TFTP root, and to restart managed services. So why is it
unnecessary? Because in most common situations (after an object is edited, for example), Cobbler executes what is known
as a "lite sync" which rewrites most critical files.

When is a full sync required? When you are using manage_dhcpd (Managing DHCP) with systems that use static leases. In
that case, a full sync is required to rewrite the dhcpd.conf file and to restart the dhcpd service.

Example:

.. code-block:: shell

    $ cobbler sync

cobbler validate-autoinstalls
+++++++++++++++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler validate-autoinstalls

cobbler version
+++++++++++++++

Example:

.. code-block:: shell

    $ cobbler version

cobbler signature
+++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler signature

cobbler get-loaders
+++++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler get-loaders

cobbler hardlink
++++++++++++++++

Example:

.. code-block:: shell

    $ cobbler hardlink
