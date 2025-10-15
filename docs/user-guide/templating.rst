.. _templating:

**********
Templating
**********

Template Providers
##################

Cobbler is not using a single templating engine but has a small abstraction layer that allows for multiple template
engines. The default template engine is set via the setting ``default_template_type`` and currently has the value
``cheetah`` for backwards compatibility.

.. note:: While the default is Cheetah, new features will prefer Jinja 2 since the community and available resources
    are bigger than Cheetah.

Cheetah
=======

The Cheetah template engine allows you to embed Python-like expressions and logic directly in your templates. It is
traditionally used in Cobbler for generating configuration files and scripts. Cheetah templates use the ``$variable``
syntax and support control structures such as ``#if``, ``#for``, and ``#end if``.

Example (Cobbler Kickstart snippet):

.. code-block:: cheetah

    #if $system.gateway
    GATEWAY=$system.gateway
    #end if

    #for $iface in $system.interfaces
    DEVICE=$iface.name
    IPADDR=$iface.ip_address
    #end for

Explanation:

This example shows how to conditionally set the gateway if it is defined, and how to iterate over all network interfaces
of a Cobbler system object to render device and IP address information. The ``$system`` variable is provided by Cobbler
and exposes system attributes to the template.

More information:

* `Website <https://cheetahtemplate.org/>`__
* `User Guide <https://cheetahtemplate.org/users_guide/index.html>`__
* Useful community repository: `github.com/FlossWare/cobbler <https://github.com/FlossWare/cobbler>`__

Jinja
=====

Jinja is a modern templating engine with a clean syntax, supporting advanced features like filters and template
inheritance. Cobbler recommends Jinja for new templates due to its flexibility and strong community support. Jinja
templates use the ``{{ variable }}`` syntax for expressions and ``{% ... %}`` for control structures.

.. note:: Cobbler does not utilize the ``block`` feature from Jinja. Please stick to the ``include`` syntax.

Example (Cobbler Kickstart snippet):

.. code-block:: jinja

    {% if system.gateway %}
    GATEWAY={{ system.gateway }}
    {% endif %}

    {% for iface in system.interfaces %}
    DEVICE={{ iface.name }}
    IPADDR={{ iface.ip_address }}
    {% endfor %}

Explanation:

This example demonstrates how to use Jinja's conditional and loop syntax to render Cobbler system attributes. The
gateway is set only if present, and all network interfaces are listed with their device name and IP address. Jinja's
syntax is concise and supports powerful features for template logic and formatting.

More information:

* `Website <https://jinja.palletsprojects.com/en/stable/>`__
* `User Guide <https://jinja.palletsprojects.com/en/stable/templates/>`__

Available Variables inside the templates
########################################

Cobbler uses the method :meth:`cobbler.utils.blender` to generate the information that can be used inside a template.
The method internally combines the information from the settings and the to be rendered object and tweaks a few
variables so they can be used more easily. All variables from ``autoinstall_meta`` are being promoted to the top-level
of the generated information.

The Tag System
##############

The :class:`~cobbler.items.template.Template` class contains the property :meth:`~cobbler.items.template.Template.tags`.
This property is a Set of Python Strings which steers the selection for which a template is being used. A list of
well-known strings can be found in :class:`cobbler.enums.TemplateTag`.

Relevant XML-RPC API Calls
##########################

For detailed information, please check the docstrings of the linked XML-RPC API methods.

* :meth:`cobbler.remote.CobblerXMLRPCInterface.get_template`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.get_template_content`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.get_templates`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.find_template`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.get_template_handle`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.remove_template`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.copy_template`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.rename_template`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.new_template`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.modify_template`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.save_template`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.background_templates_refresh_content`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.get_template_file_for_profile`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.get_template_file_for_system`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.get_templates_since`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.get_template_as_rendered`
* :meth:`cobbler.remote.CobblerXMLRPCInterface.templates_refresh_content`

Changes for version 4.0.0
#########################

Cobbler 4.0.0 introduced the following changes that need to be accounted for inside the templates:

* Templates are now a dedicated item object.
* Templates are now internally selected via tags instead of filenames.
* Templates can now additionally be loaded from environment variables.
* Templates are now cached in-memory and have to be explicitly refreshed with an API call after being edited.
* Built-in templates are not stored in ``/var/lib/cobbler/templates`` anymore but are moved into the Python Package.
* Built-in templates can be references via ``built-in-<name>``.

Intended Workflow
#################

#. Write a template to disk underneath ``autoinstall_templates_dir`` or inside an environment variable which is
   accessible to the Cobbler Daemon.
#. Use :meth:`cobbler.remote.CobblerXMLRPCInterface.new_template` to create a new template object.
#. Use :meth:`cobbler.remote.CobblerXMLRPCInterface.modify_template` to modify the ``name``, ``template_type``,
   ``uri`` and ``tags`` of the object
#. Use :meth:`cobbler.remote.CobblerXMLRPCInterface.save_template` to persist the changes and make it available for use.
#. Optional: Set the UID/Name of the template as a value to ``autoinstall`` inside a Profile or System.
#. Optional: Execute a sync to update the affected configuration.

Usage Examples
##############

In the following, the built-in DHCP template is retrieved via the XML-RPC API, modified using Python Code and written to
disk. The result of the script is that the built-in template is not used anymore.

.. code:: python

    import xmlrpc.client

    # Connect to Cobbler XML-RPC API
    server = xmlrpc.client.ServerProxy("http://localhost/cobbler_api")

    # Authenticate and get a token
    token = server.login("username", "password")

    # 1. Retrieve the built-in DHCP template content
    built_in_template_uid = server.get_template_handle("built-in-dhcp")
    dhcp_content = server.get_template_content(built_in_template_uid, token)

    # 2. Modify the template (example: add a comment at the top)
    modified_content = "# Custom DHCP template\n" + dhcp_content

    # 3. Save the modified template to disk
    with open("/var/lib/cobbler/templates/dhcp.template", "w") as f:
        f.write(modified_content)

    # 4. Create a new Template object in Cobbler
    template_obj = server.new_template(token)

    # 5. Modify the Template object properties
    server.modify_template(
        template_obj,
        {
            "name": "custom-dhcp",
            "template_type": "cheetah",  # or "jinja" if using Jinja syntax
            "uri": "/var/lib/cobbler/templates/dhcp.template",
            "tags": ["dhcp", "active"],
        },
        token,
    )

    # 6. Save the Template object to make it available
    server.save_template(template_obj, token)

    # 7. Refresh templates cache
    server.background_templates_refresh_content({}, token)

Limitations and Suprises
########################

Before templates are passed to Jinja or Cheetah, there is a pre-processing of templates happening. During pre-processing
Cobbler replaces variables like ``@@my_key@@`` in the template. Those keys are currently limited by the regex of ``\S``,
which translates to ``[^ \t\n\r\f\v]``.
