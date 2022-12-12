*********************
Cobbler Configuration
*********************

.. toctree::
   :maxdepth: 2

   Configuration Migrations <cobbler-conf/migration>
   Configuration File Reference <cobbler-conf/settings-yaml>


The main configuration file is ``settings.yaml``. It is located per default at ``/etc/cobbler/``. The file is following
the `YAML <https://yaml.org/spec/1.2/spec.html>`_ specification.

.. warning:: If you are using ``allow_dynamic_settings`` or ``auto_migrate_settings``, then the comments in the YAML
             file will vanish after the first change due to the fact that PyYAML doesn't support comments
             (`Source <https://github.com/yaml/pyyaml/issues/90>`_)

Migration matrix
################

=======  ======   ======  ======  ======  ======  ======  ======  ======  ======  ======  ======  ======  ======  ======
To/From  <2.8.5   2.8.5   3.0.0   3.0.1   3.1.0   3.1.1   3.1.2   3.2.0   3.2.1   3.3.0   3.3.1   3.3.2   3.3.3   3.4.0
=======  ======   ======  ======  ======  ======  ======  ======  ======  ======  ======  ======  ======  ======  ======
2.8.5      x        o       --      --      --      --      --      --      --      --      --      --      --      --
3.0.0      x        x       o       --      --      --      --      --      --      --      --      --      --      --
3.0.1      x        x       x       o       --      --      --      --      --      --      --      --      --      --
3.1.0      x        x       x       x       o       --      --      --      --      --      --      --      --      --
3.1.1      x        x       x       x       x       o       --      --      --      --      --      --      --      --
3.1.2      x        x       x       x       x       x       o       --      --      --      --      --      --      --
3.2.0      x        x       x       x       x       x       x       o       --      --      --      --      --      --
3.2.1      x        x       x       x       x       x       x       x       o       --      --      --      --      --
3.3.0      x        x       x       x       x       x       x       x       x       o       --      --      --      --
3.3.1      x        x       x       x       x       x       x       x       x       x       o       --      --      --
3.3.2      x        x       x       x       x       x       x       x       x       x       x       o       --      --
3.3.3      x        x       x       x       x       x       x       x       x       x       x       x       o       --
3.4.0      x        x       x       x       x       x       x       x       x       x       x       x       x       o
main       --       --      --      --      --      --      --      --      --      --      --      --      --      --
=======  ======   ======  ======  ======  ======  ======  ======  ======  ======  ======  ======  ======  ======  ======

**Legend**: x: supported, o: same version, -: not supported

.. note::
   Downgrades are not supported!
