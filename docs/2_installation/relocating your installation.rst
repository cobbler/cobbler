****************************
Relocating your installation
****************************

Often folks don't have a very large ``/var`` partition, which is what cobbler uses by default for mirroring install trees
and the like.

You'll notice you can reconfigure the webdir location just by going into ``/etc/cobbler/settings``, but it's not the
best way to do things -- especially as the RPM packaging does include some files and directories in the stock path. This
means that, for upgrades and the like, you'll be breaking things somewhat. Rather than attempting to reconfigure
cobbler, your Apache configuration, your file permissions, and your SELinux rules, the recommended course of action is
very simple.

1. Copy everything you have already in ``/var/www/cobbler`` to another location -- for instance, ``/opt/cobbler_data``
2. Now just create a symlink or bind mount at ``/var/www/cobbler`` that points to ``/opt/cobbler_data``.

Done. You're up and running.

.. note:: If you decided to access cobbler's data store over NFS (not recommended) you really want to mount NFS
   on <code>/var/www/cobbler</code> with SELinux context passed in as a parameter to mount versus the symlink. You may
   also have to deal with problems related to rootsquash. However if you are making a mirror of a Cobbler server for a
   multi-site setup, mounting read only is ok there.

.. warning:: ``/var/lib/cobbler`` can not live on NFS, as this interferes with locking ("flock") cobbler does around
   it's storage files.
