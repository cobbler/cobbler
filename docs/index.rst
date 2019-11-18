***********************************
Welcome to Cobbler's documentation!
***********************************

cobbler is a provisioning (installation) and update server. It supports deployments via PXE (network booting),
virtualization (Xen, QEMU/KVM, or VMware), and re-installs of existing Linux systems. The latter two features are
enabled by usage of 'koan' on the remote system. Update server features include yum mirroring and integration of those
mirrors with automated installation files.  Cobbler has a command line interface, Web UI, and extensive Python and
XMLRPC APIs for integration with external scripts and applications.

Here you should find a comprehensive overview about the usage of cobbler.

.. toctree::
   :maxdepth: 2
   :numbered:

   About Cobbler<about>
   Installing Cobbler<installation>
   General Topics<general>
   Advanced Topics<advanced>
   Web Interface<web-interface>
   Troubleshooting<troubleshooting>
   Appendix<appendix>

Indices and tables
##################

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
