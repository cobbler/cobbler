****************
Autoinstallation
****************

Autoinstallation Support
########################

AutoYaST
========

Cobbler supports AutoYaST for automated installations of SUSE and openSUSE systems. You can provide an AutoYaST XML
profile to Cobbler, which will be served to clients during installation.

For more information about AutoYaST, see:

* https://documentation.suse.com/sles/15-SP7/html/SLES-all/Invoking.html
* https://github.com/yast/yast-autoinstallation

Kickstart
=========

Cobbler has built-in support for Kickstart guided autoinstallations. We supply a script called "Anamon" that sends
client side installation logs back to the Cobbler server.

To learn more about the installer used by Fedora, RedHat Enterprise Linux (RHEL) and other distributions please visit
one of the following websites:

* https://fedoraproject.org/wiki/Anaconda
* https://github.com/rhinstaller/anaconda
* https://anaconda-installer.readthedocs.io/en/latest/intro.html

Preseed
=======

Cobbler supports Preseed for automated installations of Debian and Ubuntu systems. You can provide a Preseed
configuration file to Cobbler, which will be delivered to clients during installation.

For more information about Preseed, see:

* https://wiki.debian.org/DebianInstaller/Preseed

Cloud-Init
==========

For the current status of cloud-init support please visit https://github.com/cobbler/cobbler/issues/3218

Ignition (and Combustion)
=========================

For the current status of Ignition support please visit:

* https://github.com/cobbler/cobbler/issues/3281
* https://github.com/cobbler/cobbler/issues/3282

Yomi
====

For the current status of Yomi support please visit https://github.com/cobbler/cobbler/issues/2209

Other auto-installation systems
===============================

To request a new type of auto-installation please open a feature request on GitHub: https://github.com/cobbler/cobbler/issues/new?assignees=&labels=enhancement&template=02_feature_request.md&title=

Automatic installation templating
#################################

The ``--autoinstall_meta`` options require more explanation.

If and only if ``--autoinstall`` options reference filesystem URLs, ``--autoinstall-meta`` allows for templating of the automatic
installation files to achieve advanced functions.  If the ``--autoinstall-meta`` option for a profile read
``--autoinstall-meta="foo=7 bar=llama"``, anywhere in the automatic installation file where the string ``$bar`` appeared would be
replaced with the string "llama".

To apply these changes, ``cobbler sync`` must be run to generate custom automatic installation files for each
profile/system.

For NFS and HTTP automatic installation file URLs, the ``--autoinstall_meta`` options will have no effect. This is a
good reason to let Cobbler manage your automatic installation files, though the URL functionality is provided for
integration with legacy infrastructure, possibly including web apps that already generate automatic installation files.

Templated automatic files are processed by the templating program/package Cheetah or Jinja. To learn more about
templating in Cobbler please visit the corresponding page in our doucmentation: :ref:`templating`

Automatic installation snippets
###############################

For Cheetah anywhere an automatic installation template mentions ``SNIPPET::snippet_name``, Cobbler will search for a
template with this name. This serves as a way to recycle frequently used automatic installation snippets without
duplication. Snippets can contain templating variables, and the variables will be evaluated according to the profile
and/or system as one would expect.

Snippets can also be overridden for specific profile names or system names. Do do this simply set a tag with
``per_<item type>`` and a second tag with the desired identifier (either name or UID) so the template qualifies as an
override.

Autoinstall validation
######################

To check for potential errors in auto-installation files, prior to installation, use ``cobbler validate-autoinstalls``.
This function will check all profile and system auto-installation files for detectable errors. Since ``pykickstart`` and
related tools are not future-version aware in most cases, there may be some false positives. It should be noted that
``cobbler validate-autoinstalls`` runs on the rendered autoinstall output, not autoinstall templates themselves.

Automatic installation tracking
###############################

Cobbler knows how to keep track of the status of automatic installation of machines.

.. code-block:: shell

    cobbler status

Using the status command will show when Cobbler thinks a machine started automatic installation and when it finished,
provided the proper snippets are found in the automatic installation template. This is a good way to track machines that
may have gone interactive (or stalled/crashed) during automatic installation.

Debugging of unattended installations
#####################################

There are different tools for debugging automatic installations. In general it is recommended to use something to record the
output of the screen, since some important information may only be visible for a short amount of time. Examples are
BMC (with IPMI SOL or HTML5 KVM), a dedicated serial console or a networked KVM.

Here is a short list of some important stages during automatic installations and the most frequently occuring errors there:

* Firmware/EFI:
  * Wrong boot device
* DHCP request:
  * Wrong VLAN/Network
  * Cable issues
  * Firewall issues
* TFTP request:
  * Typo in cobbler settings
  * inheritance issues
  * VM restarted with daemon started but not enabled
  * tftp timeout
* Kernel & Initrd:
  * Missing hardware drivers
* HTTP requests towards Cobbler:
  * Firewall/Proxy issues
  * Cobbler timeout
  * Cheetah templating errors
* Installation:
  * Incorrect escaping (syntax errors)
  * remote ressources unavailable
* Reboot:
  * Loop due to enabled netboot
