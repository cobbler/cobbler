.. Cobbler documentation master file, created by
   sphinx-quickstart on Sat Aug 23 06:59:22 2014.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

***********************************
Welcome to Cobbler's documentation!
***********************************

Cobbler is a provisioning (installation) and update server. It supports deployments via PXE (network booting),
virtualization (Xen, QEMU/KVM, or VMware), and re-installs of existing Linux systems. The latter two features are
enabled by usage of 'Koan' on the remote system. Update server features include yum mirroring and integration of those
mirrors with automated installation files. Cobbler has a command line interface, WebUI, and extensive Python and
XML-RPC APIs for integration with external scripts and applications.

If you want to explore tools or scripts which are using Cobbler please use the GitHub Topic:
https://github.com/topics/cobbler

Here you should find a comprehensive overview about the usage of Cobbler.

.. toctree::
   :maxdepth: 2
   :numbered:

   Quickstart Guide <quickstart-guide>
   Install Guide <installation-guide>
   Cobbler CLI <cobbler>
   Cobbler Server <cobblerd>
   Cobbler Configuration <cobbler-conf>
   User Guide <user-guide>
   Developer Guide <developer-guide>
   Cobbler-Code Documentation<code-autodoc/cobbler>
   Release Notes <release-notes>
   Limitations and Surprises <limitations>

Indices and tables
##################

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

