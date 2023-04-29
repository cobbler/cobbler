****************
Autoinstallation
****************

Autoinstallation Support
########################

AutoYaST
========

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

Templated automatic files are processed by the templating program/package Cheetah, so anything you can do in a Cheetah
template can be done to an automatic installation template.  Learn more at https://cheetahtemplate.org/users_guide/intro.html

When working with Cheetah, be sure to escape any shell macros that look like ``$(this)`` with something like
``\$(this)`` or errors may show up during the sync process.

The Cobbler Wiki also contains numerous Cheetah examples that should prove useful in using this feature.

Also useful is the following repository: https://github.com/FlossWare/cobbler

Automatic installation snippets
###############################

Anywhere a automatic installation template mentions ``SNIPPET::snippet_name``, the file named
``/var/lib/cobbler/snippets/snippet_name`` (if present) will be included automatically in the automatic installation
template. This serves as a way to recycle frequently used automatic installation snippets without duplication. Snippets
can contain templating variables, and the variables will be evaluated according to the profile and/or system as one
would expect.

Snippets can also be overridden for specific profile names or system names. This is described on the Cobbler Wiki.

Autoinstall validation
######################

To check for potential errors in auto-installation files, prior to installation, use ``cobbler validate-autoinstalls``.
This function will check all profile and system auto-installation files for detectable errors. Since ``pykickstart`` and
related tools are not future-version aware in most cases, there may be some false positives. It should be noted that
``cobbler validate-autoinstalls`` runs on the rendered autoinstall output, not autoinstall templates themselves.
