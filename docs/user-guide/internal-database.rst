*****************
Internal Database
*****************

.. note:: This document describes advanced topics for system administrators.

The internal database of Cobbler is held at ``/var/lib/cobbler/collections``.

Items
#####

An item in Cobbler is a set of attributes grouped together and given a name. An example for this would be a ``distro``.
On disk those items are represented using JSON. By default, the JSON is minified, however you can make the serializer
produce "pretty" JSON files by changing ``serializer_pretty_json`` to ``true`` in the Cobbler Settings.

The name of the saved file is the name of the item.

Collections
###########

A collection in Cobbler is a number of ``n`` Cobbler items that are living inside the same folder.

Notes
#####

If you want to have a backup use the ``scm_track`` module of Cobbler.
It will use Git for version control of the complete ``/var/lib/cobbler/`` folder.

A rename operation does the following: Delete the item with the old name and create a new item with the new name. This is
reflected on disk and thus if Cobbler is being terminated at the wrong point in time, this specific item
can get lost. It's unlikely, but if you have items dependent onto that item you will receive errors on the
next Cobbler startup.

If you deem yourself a Cobbler expert you may edit the JSON files directly once Cobbler is not running. If Cobbler is
running you risk a corruption of the complete application. Please take all actions here with huge precautions and
only if you have backups!
