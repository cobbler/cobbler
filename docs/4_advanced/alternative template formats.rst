.. _alternative-template-formats:

****************************
Alternative template formats
****************************

The default templating engine currently is Cheetah, as of cobbler 2.4.0 support for the Jinja2 templating engine has
been added.

The default template type to use in the absence of any other detected. If you do not specify the template with
``#template=<template_type>`` on the first line of your templates/snippets, cobbler will assume try to use the template
engine as specified in the settings file to parse the templates.

From ``/etc/cobbler/settings``:

.. code-block:: bash

    # Current valid values are: cheetah, jinja2
    default_template_type: "cheetah"
