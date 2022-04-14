********
HTTP API
********

Error codes
###########

=========== ============== ===========
status code status message Description
=========== ============== ===========
200         ok
404         not found
500         server error
=========== ============== ===========

Http endpoints
##############

All Http endpoints are found at ``http(s)://<fqdn>/cblr/svc/op/<endpoint>``

settings
========

Returns the currently loaded settings. For specific settings please see :ref:`the settings.yaml documentation <settings-ref>`.

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/setting

Example Output:

.. code-block::

    #{
        "allow_duplicate_hostnames": false,
        "allow_duplicate_ips": false,
        "allow_duplicate_macs": false,
        "allow_dynamic_settings": false
    ...
            "gcry_sha1",
            "gcry_sha256"
        ],
        "grub2_mod_dir": "/usr/share/grub2"
    }

autoinstall
===========

Autoinstallation files for either a profile or a system.

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/autoinstall/profile/example_profile

Example Output:

.. code-block::

    # this file intentionally left blank
    # admins:  edit it as you like, or leave it blank for non-interactive install

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/autoinstall/system/example_system

Example Output:

.. code-block::

    # this file intentionally left blank
    # admins:  edit it as you like, or leave it blank for non-interactive install

ks
==

Autoinstallation files for either a profile or a system.
This is used only for backward compatibility with Cobbler 2.6.6 and lower, please use autoinstall if possible.

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/ks/profile/example_profile

Example Output:

.. code-block::

    # this file intentionally left blank
    # admins:  edit it as you like, or leave it blank for non-interactive install

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/ks/system/example_system

Example Output:

.. code-block::

    # this file intentionally left blank
    # admins:  edit it as you like, or leave it blank for non-interactive install

iPXE
====

The iPXE configuration for a profile, an image or a system.

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/ipxe/profile/example_profile

Example Output:

.. code-block::

    :example_profile
    kernel /images/example_distro/vmlinuz   initrd=initrd.magic
    initrd /images/example_distro/initramfs
    boot


.. warning:: If the specified profile doesn't exist there is currently no output.

Image
-----

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/ipxe/image/example_image

Example Output:

.. warning:: This endpoint is currently broken and will probably have no output.

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/ipxe/system/example_system

Example Output:

.. code-block::

    #!ipxe
    iseq ${smbios/manufacturer} HP && exit ||
    sanboot --no-describe --drive 0x80


.. warning:: If the specified system doesn't exist there is currently no output.

bootcfg
=======

boot.cfg configuration file for either a profile or a system.

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/bootcfg/profile/example_profile

Example Output:

.. code-block::

    bootstate=0
    title=Loading ESXi installer
    prefix=/images/example_distro
    kernel=b.b00
    kernelopt=runweasel ks=http://192.168.1.1:80/cblr/svc/op/ks/profile/example_profile
    modules=$esx_modules
    build=
    updated=0

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/bootcfg/system/example_system

Example Output:

.. code-block::

    bootstate=0
    title=Loading ESXi installer
    prefix=/images/example_distro
    kernel=b.b00
    kernelopt=runweasel ks=http://192.168.1.1:80/cblr/svc/op/ks/system/example_system
    modules=$esx_modules
    build=
    updated=0

script
======

A generated script based on snippets.

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/script/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken and returns an Error 500.

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/script/system/example_system

Example Output:

.. warning:: This endpoint is currently broken and returns an Error 500.

events
======

Returns events associated with the specified user, if no user is given returns all events.

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/events/user/example_user

Example Output:

.. code-block::

    []

.. warning:: If the specified user doesn't exist there is currently no output.

template
========

A rendered template for a system, or for a system linked to a profile.

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/template/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken.

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/template/system/example_system

Example Output:

.. warning:: This endpoint is currently broken.

yum
===

Repository configuration for a profile or a system.

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/yum/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken and will probably have no output.

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/yum/system/example_system

Example Output:

.. warning:: This endpoint is currently broken and will probably have no output.

trig
====

Hook to install triggers.

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/trig

Example Output:

.. code-block::

    False

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/trig/profile/example_profile

Example Output:

.. code-block::

    False

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/trig/system/example_system

Example Output:

.. code-block::

    False

noPXE
=====

If network boot is enabled for specified system.

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/nopxe/system/example_system

Example Output:

.. code-block::

    True

list
====

Lists all instances of a specified type.
Currently the valid options are:
``systems, profiles, distros, images, repos, mgmtclasses, packages, files, menus``
If no option is selected the endpoint will default to ``systems``.
If the selected option is not valid the endpoint will return ``?``.

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/list/what/profiles

Example Output:

.. code-block::

    example_profile
    example_profile2

.. warning:: currently no output if parameter has no instances.

autodetect
==========

Autodetects the system, returns an error if more than one system is found.

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/autodetect

Example Output:

.. warning:: This endpoint is currently broken.

find autoinstall
================

Find the autoinstallation file for a profile or system.

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/find_autoinstall/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken.

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/find_autoinstall/system/example_system

Example Output:

.. warning:: This endpoint is currently broken.

find ks
=======

Find the autoinstallation files for either a profile or a system.
This is used only for backward compatibility with Cobbler 2.6.6 and lower, please use ``find autoinstall`` if possible.

Profile
-------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/findks/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken.

System
------

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/findks/system/example_system

Example Output:

.. warning:: This endpoint is currently broken.

puppet
======

Dump puppet data for specified hostname, returns yaml file for host.

Example Call:

.. code-block::

    curl http://localhost/cblr/svc/op/puppet/hostname/example_hostname

Example Output:

.. warning:: This endpoint is currently broken.

Author
======

`Nico Krapp <https://github.com/tiltingpenguin>`_
