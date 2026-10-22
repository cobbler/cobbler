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

Agama
=====

Cobbler also supports `Agama <https://agama-project.github.io/docs/>`_, the installer that replaced AutoYaST as the
default for openSUSE Leap and SUSE Linux Enterprise starting with the 16.x generation. Unlike AutoYaST's XML
profiles, an Agama profile is a single JSON (or Jsonnet) document. Which installer a distro/profile/system actually
uses is decided by the ``AutoinstallerType`` tag (``autoyast`` vs. ``agama``) carried by its resolved autoinstall
template -- the same tagging mechanism used to distinguish Preseed from Cloud-Init, described in more detail in the
`Template selection via tags`_ section below.

How the install client finds its profile
------------------------------------------

Cobbler passes Agama the ``inst.auto=<url>`` kernel parameter, pointing at the rendered profile via the same
``/cblr/svc/op/autoinstall/<profile|system>/<name>/file/<template>`` URL used by every other autoinstall type (see
the :ref:`HTTP API documentation <http-api>`). Unlike Cloud-Init, an Agama profile is a single file -- there is no
``subfile`` concept here.

Building the JSON document
---------------------------

The built-in template, ``built-in-autoinst.json``, always includes a mandatory ``product`` section, followed by one
``built-in-agama-<module>`` snippet per entry in the ``agama_modules`` ``autoinstall_meta`` key (a list), each
contributing its own top-level JSON key:

.. code-block:: jinja

    {
        {% include "built-in-agama-product" %}{{ "," if agama_modules }}
    {%- for module in agama_modules %}
        {% include "built-in-agama-%s" % module %}{{ ", " if not loop.last }}
    {%- endfor %}
    }

Available modules (i.e. valid entries for ``agama_modules``) are: ``bootloader``, ``dasd`` (s390x), ``files``,
``hostname``, ``localization``, ``network``, ``questions``, ``root``, ``scripts``, ``security``, ``software``,
``storage``, ``storage-legacy`` (a simpler alternative to ``storage``) and ``user`` (s390x also adds ``zfcp``). Each
corresponds 1:1 to Agama's own `profile reference <https://agama-project.github.io/docs/user/reference/profile>`_
section of the same name -- consult that page for the exact JSON shape each module produces.

Most modules are driven by dedicated, flat ``agama_<module>_<field>`` ``autoinstall_meta`` keys, following the same
pattern as the ``product`` section (which is always rendered, independent of ``agama_modules``):

.. code-block:: text

    agama_product_id = "openSUSE_Leap"
    agama_root_password = "$6$rounds=..."
    agama_localization_language = "en_US"
    agama_localization_keyboard = "us"
    agama_localization_timezone = "UTC"

A few modules instead take one larger nested value (``agama_storage``, ``agama_scripts``, ``agama_files``,
``agama_security``, ``agama_questions``, ``agama_dasd``, ``agama_zfcp``) whose structure mirrors the corresponding
Agama profile section directly -- see the module reference linked above for their exact shape. ``network`` and
``hostname`` are the two exceptions that take no ``agama_*`` keys at all: they are instead derived automatically
from the system's actual configured :class:`~cobbler.items.network_interface.NetworkInterface` objects and
``hostname`` property respectively, the same metavariables every other autoinstall type uses.

If ``agama_root_password`` is left unset, the ``root`` module falls back to the global ``default_password_crypted``
setting (``/etc/cobbler/settings.yaml``), the same default every other autoinstall type uses.

.. note:: ``agama_modules`` is a list value, so -- as of this writing -- it needs to be set via the XML-RPC API
          directly rather than ``cobbler-cli``, for the same reason described for
          ``cloud_init_user_data_modules`` above: ``cobbler-cli``'s ``--autoinstall-meta`` flag can only represent
          flat ``key=value`` strings.

.. note:: ``agama_product_id`` has no reliable default -- the built-in template falls back to ``"Tumbleweed"`` if
          unset, which is wrong for any other product. The value is Agama's own internal product identifier, not a
          distribution or codename string: for example, openSUSE Leap's correct value is ``"openSUSE_Leap"`` --
          values like ``"Leap"`` or ``"Leap_16.1"`` are rejected by Agama as unknown products. Consult the
          ``products.d`` definitions shipped by the target media/product (or Agama's own documentation) for the
          correct value of any other product.

For more information about Agama, see:

* https://agama-project.github.io/docs/overview/unattended
* https://agama-project.github.io/docs/user/profile
* https://agama-project.github.io/docs/user/reference/profile

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

Cobbler supports `cloud-init <https://cloud-init.io/>`_'s ``NoCloud`` datasource, used by modern Ubuntu releases
(24.04 and newer) that install via Subiquity instead of the classic debian-installer/Preseed used by older
Ubuntu releases and by Debian. Which of the two mechanisms is used for a given distro/profile/system is decided by
the ``AutoinstallerType`` tag (``cloud-init`` vs. ``preseed``) carried by its resolved autoinstall template, not by
breed alone -- see `Template selection via tags`_ below.

How the install client finds its data
--------------------------------------

Cobbler passes cloud-init a kernel parameter of the form ``ds=nocloud;s=<seed-url>``. The ``NoCloud`` datasource
then fetches its data by directly concatenating that seed URL with each file name it needs -- see `cloud-init's
NoCloud datasource reference <https://docs.cloud-init.io/en/latest/reference/datasources/nocloud.html>`_ for the
exact protocol. Cobbler's generated seed URL always ends in ``/subfile/``, so appending e.g. ``user-data`` produces
a clean, unambiguous path such as:

.. code-block:: text

    http://<server>/cblr/svc/op/autoinstall/system/<name>/file/<template>/subfile/user-data

See the :ref:`HTTP API documentation <http-api>`'s ``autoinstall`` endpoint section for the full URL format,
including why sub-file selection only ever works through this path segment and never through a query string.

The four sub-files
-------------------

A cloud-init install is made up of up to four separate files, all requested against the same seed URL:

* ``user-data``: the main cloud-config document (packages, users, ``runcmd``, ...). Built-in template:
  ``built-in-user-data``.
* ``meta-data``: minimal per-instance metadata, currently just an ``instance-id``. Built-in template:
  ``built-in-meta-data``.
* ``network-config``: static network configuration for first boot. Built-in template:
  ``built-in-network-config``.
* ``vendor-data``: not used by Cobbler's built-in templates -- always rendered as an empty string, since all
  provisioning data is folded into ``user-data``/``meta-data`` instead.

Template selection via tags
----------------------------

As described in :ref:`templating`, every :class:`~cobbler.items.template.Template` carries a set of tags that steer
which template gets used for what. For cloud-init, two layers of tagging are involved:

#. Every cloud-init template is tagged with the :class:`cobbler.enums.AutoinstallerType` value ``cloud-init`` (this
   is what makes Cobbler emit a ``ds=nocloud;s=...`` kernel parameter instead of a Preseed ``url=...`` one in the
   first place) and with the specific :class:`cobbler.enums.CloudInitFileTypes` it implements (``user-data``,
   ``meta-data``, ``vendor-data`` or ``network-config``).
#. Each built-in template is additionally cross-tagged with its *siblings'* ``built-in-<name>`` identifiers. For
   example, the ``built-in-meta-data`` template also carries the tag ``built-in-user-data``, and vice versa. This
   is what lets Cobbler resolve ``meta-data`` for a profile/system whose ``autoinstall`` property only ever points
   at ``built-in-user-data``: when a sub-file other than the one already assigned is requested, Cobbler searches
   for a template tagged with that sub-file type *and* tagged with the originally assigned template's name or UID,
   and uses that one instead.

In practice this means you only need to assign the ``user-data`` template to a profile/system's ``autoinstall``
property, exactly as you would for any other autoinstall type (this is also what every shipped
``default_autoinstall`` value for cloud-init-based distros already points at) -- Cobbler resolves ``meta-data`` and
``network-config`` from there automatically.

Customizing generated output with modules
-------------------------------------------

The built-in ``user-data`` template does not hardcode any cloud-config modules. Instead, it includes a configurable
list of them:

.. code-block:: jinja

    #cloud-config
    {%- for module in cloud_init_user_data_modules %}
    {% include "built-in-cloud-init-module-%s" % module %}
    {%- endfor %}

Set which modules to include via the ``cloud_init_user_data_modules`` ``autoinstall_meta`` key (a list of module
names, hyphenated to match cloud-init's own module names, e.g. ``set-hostname``, ``ssh``, ``packages``), then
configure each selected module's values via a further ``autoinstall_meta`` key named ``cloud_init_<module name,
with underscores instead of hyphens>`` (a dict). Both of these are non-flat (list/dict) values, so -- as of this
writing -- they need to be set via the XML-RPC API directly rather than ``cobbler-cli``, whose ``--autoinstall-meta``
flag can only represent flat ``key=value`` strings. For example, to set a hostname and an SSH authorized key:

.. code:: python

    import xmlrpc.client

    server = xmlrpc.client.ServerProxy("http://localhost/cobbler_api")
    token = server.login("username", "password")

    profile_uid = server.get_profile_handle("example_profile")
    server.modify_profile(
        profile_uid,
        "autoinstall_meta",
        {
            "cloud_init_user_data_modules": ["set-hostname", "ssh"],
            "cloud_init_set_hostname": {"hostname": "example-host"},
            "cloud_init_ssh": {"ssh_authorized_keys": ["ssh-ed25519 AAAA..."]},
        },
        token,
    )
    server.save_profile(profile_uid, True, True, "bypass", token)

Cobbler ships one module snippet per `cloud-init module
<https://cloudinit.readthedocs.io/en/latest/reference/modules.html>`_ under
``cobbler/data/templates/jinja/autoinstall/snippets/cloud-init/``; each snippet's expected ``autoinstall_meta``
shape follows that module's entry in the linked cloud-init module reference directly.

``network-config`` does not have a configurable module list -- it always renders the ``network-v1`` module
snippet.

.. note:: ``libcobblersignatures``' shipped ``supported_arches`` for the ``ubuntu``/``debian`` breeds use Debian's
          own architecture names (e.g. ``amd64``), but :class:`cobbler.enums.Archs` only knows ``x86_64`` -- pass
          ``--arch=x86_64`` to ``cobbler import`` for these distros rather than ``--arch=amd64``.

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
