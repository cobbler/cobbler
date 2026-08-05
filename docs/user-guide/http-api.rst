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

All endpoints on this page except ``tree`` (documented near the end of this page) follow the pattern
``http(s)://<fqdn>/cblr/svc/op/<endpoint>``. The ``tree`` endpoint has its own top-level path,
``http(s)://<fqdn>/cblr/svc/tree/<distro_name>/<relative_path>``, and is not found under ``op/``.

settings
========

Returns the currently loaded settings. For specific settings please see :ref:`the settings.yaml documentation <settings-ref>`.

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/setting

Example Output:

.. code-block:: text

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

.. code-block:: console

    curl http://localhost/cblr/svc/op/autoinstall/profile/example_profile

Example Output:

.. code-block:: yaml

   # this file intentionally left blank
   # admins:  edit it as you like, or leave it blank for non-interactive install

System
------

Example Call:

.. code-block:: console

   curl http://localhost/cblr/svc/op/autoinstall/system/example_system

Example Output:

.. code-block:: yaml

   # this file intentionally left blank
   # admins:  edit it as you like, or leave it blank for non-interactive install

ks
==

Autoinstallation files for either a profile or a system.
This is used only for backward compatibility with Cobbler 2.6.6 and lower, please use autoinstall if possible.

Profile
-------

Example Call:

.. code-block:: console

   curl http://localhost/cblr/svc/op/ks/profile/example_profile

Example Output:

.. code-block:: yaml

   # this file intentionally left blank
   # admins:  edit it as you like, or leave it blank for non-interactive install

System
------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/ks/system/example_system

Example Output:

.. code-block:: yaml

   # this file intentionally left blank
   # admins:  edit it as you like, or leave it blank for non-interactive install

iPXE
====

The iPXE configuration for a profile, an image or a system.

Profile
-------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/ipxe/profile/example_profile

Example Output:

.. code-block:: text

    :example_profile
    kernel /images/example_distro/vmlinuz
    initrd /images/example_distro/initramfs
    boot


.. warning:: If the specified profile doesn't exist there is currently no output.

Image
-----

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/ipxe/image/example_image

Example Output:

.. warning:: This endpoint is currently broken and will probably have no output.

System
------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/ipxe/system/example_system

Example Output:

.. code-block:: text

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

.. code-block:: console

    curl http://localhost/cblr/svc/op/bootcfg/profile/example_profile

Example Output:

.. code-block:: text

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

.. code-block:: console

    curl http://localhost/cblr/svc/op/bootcfg/system/example_system

Example Output:

.. code-block:: text

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

.. code-block:: console

    curl http://localhost/cblr/svc/op/script/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken and returns an Error 500.

System
------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/script/system/example_system

Example Output:

.. warning:: This endpoint is currently broken and returns an Error 500.

events
======

Returns events associated with the specified user, if no user is given returns all events.

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/events/user/example_user

Example Output:

.. code-block:: yaml

   []

.. warning:: If the specified user doesn't exist there is currently no output.

template
========

A rendered template for a system, or for a system linked to a profile.

Profile
-------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/template/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken.

System
------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/template/system/example_system

Example Output:

.. warning:: This endpoint is currently broken.

yum
===

Repository configuration for a profile or a system.

Profile
-------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/yum/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken and will probably have no output.

System
------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/yum/system/example_system

Example Output:

.. warning:: This endpoint is currently broken and will probably have no output.

trig
====

Hook to install triggers.

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/trig

Example Output:

.. code-block:: yaml

   False

Profile
-------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/trig/profile/example_profile

Example Output:

.. code-block:: yaml

   False

System
------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/trig/system/example_system

Example Output:

.. code-block:: yaml

   False

noPXE
=====

If network boot is enabled for specified system.

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/nopxe/system/example_system

Example Output:

.. code-block:: yaml

   True

list
====

Lists all instances of a specified type.
Currently the valid options are:
``systems, profiles, distros, images, repos, menus``
If no option is selected the endpoint will default to ``systems``.
If the selected option is not valid the endpoint will return ``?``.

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/list/what/profiles

Example Output:

.. code-block:: text

    example_profile
    example_profile2

.. warning:: currently no output if parameter has no instances.

autodetect
==========

Autodetects the system, returns an error if more than one system is found.

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/autodetect

Example Output:

.. warning:: This endpoint is currently broken.

find autoinstall
================

Find the autoinstallation file for a profile or system.

Profile
-------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/find_autoinstall/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken.

System
------

Example Call:

.. code-block:: console

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

.. code-block:: console

    curl http://localhost/cblr/svc/op/findks/profile/example_profile

Example Output:

.. warning:: This endpoint is currently broken.

System
------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/findks/system/example_system

Example Output:

.. warning:: This endpoint is currently broken.

puppet
======

Dump puppet data for specified hostname, returns yaml file for host.

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/op/puppet/hostname/example_hostname

Example Output:

.. warning:: This endpoint is currently broken.

.. _dynamic-httpd:

Dynamic (no-copy) distro tree serving
######################################

Everything documented above assumes the default ``managers.in_httpd`` module (see ``modules.httpd.module`` in
:ref:`settings-ref`), under which ``cobbler import`` copies a distro's source tree into
``webdir/distro_mirror/<name>`` so it can be served like any other file under ``webdir``.

Cobbler also ships a second module, ``managers.dynamic_httpd``, for when the import source is already a stable,
local, Cobbler-readable directory (for example a permanently mounted ISO, rather than a remote mirror or removable
media). When it is selected and that precondition holds, ``cobbler import`` skips the copy into ``distro_mirror``
entirely, and instead records the original location on the distro's ``source_tree_path`` property. The precondition
matters: if the source is later removed or becomes unreadable (e.g. the ISO gets unmounted), any install relying on
that distro's tree content will fail, since no copy was ever made to fall back on. ``cobbler check`` warns about
exactly this -- see below.

Tree content is then served from ``source_tree_path`` on demand, directly from disk, via a new endpoint:

.. code-block:: text

    http://<server>/cblr/svc/tree/<distro_name>/<relative_path>

Unlike ``dynamic_tftp`` (which resolves every request by calling back into Cobbler's XML-RPC API), this endpoint
reads file bytes straight from disk and never round-trips through XML-RPC per file. This is a deliberate
difference in design: distro trees (``repodata/``, ``Packages/``, etc.) are typically much larger than TFTP
payloads, so streaming every byte through XML-RPC would not scale the same way. XML-RPC is only used here for a
single, briefly-cached lookup that resolves a distro name to its ``source_tree_path``. The endpoint supports HTTP
``Range`` requests, so partial/resumable downloads work, and it returns a browsable directory listing when a
requested path resolves to a directory.

.. note:: Like every other ``/cblr/svc/`` endpoint documented on this page (autoinstall, ipxe, etc.), this endpoint
          is unauthenticated. Anyone who can reach ``/cblr/svc/`` can read any file under a distro's
          ``source_tree_path``. This is a deliberate design choice consistent with the rest of this API, not an
          oversight, but it is worth weighing before opting in.

tree
====

Serves a distro's tree content directly from its ``source_tree_path`` on disk (see
:ref:`dynamic-httpd`). Only available for distros that have a ``source_tree_path`` set; it does not serve repo
mirrors or any other ``/cblr/svc/`` content.

File
----

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/tree/example_distro/repodata/repomd.xml

Example Output:

The raw content of the requested file, streamed directly from disk (HTTP ``Range`` requests are honored).

Directory listing
-----------------

Example Call:

.. code-block:: console

    curl http://localhost/cblr/svc/tree/example_distro/repodata/

Example Output:

.. code-block:: html

    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><title>Directory listing</title></head>
    <body>
    <h1>Directory listing</h1>
    <ul>
    <li><a href="primary.xml.gz">primary.xml.gz</a></li>
    <li><a href="repomd.xml">repomd.xml</a></li>
    </ul>
    </body>
    </html>

.. note:: A request for a directory path without a trailing slash (e.g. ``.../repodata``) returns a ``301``
          redirect to the same path with a trailing slash appended, the same way ``Options Indexes`` behaves on a
          traditional web server.

.. note:: Unlike a typical Apache ``Options Indexes`` listing, generated directory listings hide dotfile entries
          (names starting with ``.``, e.g. ``.treeinfo``/``.discinfo``). This is deliberate. Dotfiles remain
          directly fetchable by their exact path regardless -- only the generated listing omits them.

Author
======

`Nico Krapp <https://github.com/tiltingpenguin>`_
