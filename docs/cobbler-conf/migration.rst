*********************************
Updates to the yaml-settings-file
*********************************

Starting with 3.4.0
###################

- TBD

Starting with 3.3.3
###################

- ``default_virt_file_size`` is now a float as intended.
- We added the ``proxies`` key for first-level Uyuni & SUSE Manager support. It is optional, so you can
  ignore it if you don't run one of the two solutions or a derivative of it.

Starting with 3.3.2
###################

- After community feedback we changed the default of the auto-migration to be disabled. It can be re-enabled via the
  already known methods ``cobbler-settings``-Tool, the settings file key ``auto_migrate_settings`` and the Daemon flag.
  We have decided to not change the flag for existing installations.

Starting with 3.3.1
###################

- There is a new setting ``bootloaders_shim_location``. For details please refer to the appropriate section below.

Starting with 3.3.0
###################

- The setting ``enable_gpxe`` was replaced with ``enable_ipxe``.

- The ``settings.d`` directory (``/etc/cobbler/settings.d/``) was deprecated and will be removed in the future.

- There is a new CLI tool called ``cobbler-settings`` which can be used to validate and migrate settings files from
  differente versions and to modify keys in the current settings file. Have a look at the migration matrix in the next
  paragraph to see the supported migration paths.
  Furthermore the auto migration feature can be enabled or disabled.

- A new settings auto migration feature was implemented which automatically updates the settings when installing a new
  version. A backup of the old settings file will be created in the same folder beforehand.

Starting with 3.2.1
###################

- We require the extension ``.yaml`` on our settings file to indicate the format of the file to editors and comply to
  standards of the YAML specification.
- We require the usage of booleans in the format of ``True`` and ``False``. If you have old integer style booleans with
  ``1`` and ``0`` this is fine but you may should convert them as soon as possible. We may decide in a future version to
  enforce our new way in a stricter manner. Automatic conversion is only done on a best-effort/available-resources
  basis.
- We enforce the types of values to the keys. Additional unexpected keys will throw errors. If you have those used in
  Cobbler please report this in our issue tracker. We have decided to go this way to be able to rely on the existence
  of the values. This gives us the freedom to write fewer access checks to the settings without losing stability.
