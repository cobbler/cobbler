.. _kickstart-templating:

********************
Kickstart Templating
********************

Kickstarts automate Red Hat and Fedora based Linux installations. This document also pertains to templating as it
relates to other distributions, which also have similar answer files.

With any distribution if you are repeatedly installing a lot of different configurations, you can get into a scenario
where you have too many different answer files to maintain or the answer files get to be rather complex and unruly. A
kickstart templating system, such as Cobbler's, can help you keep these under control.

When cobbler profiles (created with ``cobbler profile add``) are created with the parameter ``--kickstart`` and the
kickstart lives on the filesystem, the file is treated as a kickstart template, not a raw kickstart. This means they
contain information about how to build a kickstart, but a given template might be modified by various variables on a per
profile or per system basis. This allows you to use the same source information (and maintain that), but have it work in
different ways for different profiles and different systems.

It also means that Cobbler, when you use ``cobbler import`` can assign kickstarts that work for fully automated installs
out of the box, but they are also easy to customize and change by manipulating settings on cobbler objects or editing
the global cobbler settings file.

The main feature in cobbler kickstart templating is the ability to declare variables on cobbler objects like
distributions, profiles, and systems. On the command line, this is the ``--ksmeta`` parameter. The same source templates
can result in different output based on different variables set in cobbler with ``--ksmeta``, which this document will
explain.

Down The Rabbit Hole
####################

Templating is very powerful, especially if you have a very large amount of profiles and/or systems to maintain.

Users can just treat templates like kickstarts, not explore this feature fully, or pretend this feature doesn't exist,
but if more customization is needed, the support is there.

This article will get into a lot of complicated (and optional) topics, so just take from it what you need. If this
sounds too complicated, it's not required that you understand all of it.

First off
#########

Cobbler uses `Cheetah <https://cheetahtemplate.org/>`_ for its kickstart templating engine. Read more at the Cheetah
page and you will learn a lot of advanced features you can employ in your kickstart templates. However, knowledge of all
parts of Cheetah are not required. Basic variable solution is automagic and doesn't require any advanced knowledge of
how the templating works.

Cheetah is nice in that most of the things you can do in the powerful Python programming language you can do in your
Cheetah templates, so it is very flexible. However some things do not look quite like Python, so you have to pay a
little attention to the syntax.

Hierarchy
#########

As with all things in cobbler, kickstart template variables (``--ksmeta``) take the following precendence:

* Distro parameters come first
* Profile parameters override Distro Parameters
* System parameters override Profile Parameters

If a distro has an attribute "bar" and the profile that is the child of the distro does not, the profile will still have
the value of "bar" accessible in the kickstart template. However, if the system then supplies it's own value for "bar",
the system value, not the distro value, will be used in rendering the kickstart for the system. This is what we mean by
"inheritance". It is a simple system of overriding things from the most specific (systems) to the least specific
(profiles, then distros) to allow for customizations.

Basic Variable substitution
###########################

Given the following commands

.. code-block:: bash

    cobbler profile add --name=foo --distro=RHEL-6-x86_64 --kickstart=/var/lib/cobbler/kickstarts/sample.ks
    cobbler profile edit --name=foo --ksmeta="noun=spot verb=run"
    cobbler system add --name=bar --profile=foo --ksmeta="verb=jump"

And the kickstart template ``/var/lib/cobbler/kickstarts/sample.ks``:

.. code-block:: bash

    See $noun $verb

The following file would be generated for profile foo:

.. code-block:: bash

    See spot run

And for the system, bar:

.. code-block:: bash

    See spot jump

This is of course very contrived, though you can imagine substituting in things like server locations, configuration
file settings, timezones, etc.

.. _kickstart-snippets:

Snippets
########

If you find yourself reusing a lot of pieces of code between several different kickstart templates, cobbler snippets are
for you.

Read more at :ref:`snippets`.

That page also includes some user contributed snippet examples -- some of which make some heavy use of the Cheetah
template engine. Snippets don't have to be complex, but you may find those examples educational.

Escaping
########

If your kickstart file contains any shell macros like ``$(list-harddrives)`` they should be escaped like this:

.. code-block:: bash

    $(list-harddrives)

This prevents Cheetah from trying to substitute something for ``$(list-harddrives)``, or worse, getting confused and
erroring out.

In general, escaping things doesn't hurt, even though in all cases, things don't have to be escaped.

Example:

.. code-block:: bash

    This is an $elephant

If there was no kickstart variable for "elephant", the kickstart templating engine would leave the string as is ...
``$elephant``

You should also be careful of the following stanza:

.. code-block:: bash

    #start some section (this is a comment)
    echo "doing stuff"
    #end some section (this is a comment)

if you want a comment to start with the word "end" place a space after the "\#" like this:

.. code-block:: bash

    # start some section (this is a comment)
    echo "doing stuff"
    # end some section (this is a comment)

Built In Variables
##################

Cobbler includes a lot of built in kickstart variables.

What variables can I use?
*************************

Run this command to see all the templating variables at your disposal.

.. code-block:: bash

    cobbler system dumpvars --name=system

Some of the built in variables that can be useful include ``$mac_address``, ``$ip_address``, ``$distro``, ``$profile``,
``$hostname``, and so forth. You will recognize these as being commands that you would see in cobbler command line
options.

To make this a bit more clear, look at the following system add command:

.. code-block:: bash

    cobbler system add --name=spartacus --profile=f10webserver-i386 --ip-address=192.168.50.5 --mac=AA:BB:CC:DD:EE:FF --hostname=spartacus.example.org

For the above command, assuming the kickstart template for fc6webserver contained the following line:

.. code-block:: bash

    echo "I was installed from Cobbler server $server and my system name is $system_name" > /etc/motd

The above line would be rendered as:

.. code-block:: bash

    "I was installed from Cobbler server cobbler.example.org and my system name is spartacus"

Again, the examples above are a bit contrived, but you can see how every variable given to the command line is
accessible within templating. This is a rather useful feature and prevents having to specify a lot of additional
templating variables with ``--ksmeta``.

Checking For Variables That Might Not Exist
###########################################

Suppose you have some system objects that define a value for "foo", but sometimes they don't.

The following Cheetah templating trick can be used to access a variable if it exists, and assign a default value if it
doesn't exist.

.. code-block:: bash

    #set $selinux_mode = $getVar('selinux', 'enforcing')

or just

.. code-block:: bash

    $getVar('selinux', 'enforcing')

As a corollary, if you need to include a specific line in a kickstart file only if a variable is defined, that is also
doable.

.. code-block:: bash

    #if $foo
      this line will show $foo but only if it is defined, else there will be nothing here
    #end if

Networking
##########

Cobbler actually handles templating around network setup for you, via some rather clever snippets used in files such as
``/var/lib/cobbler/kickstarts/sample.ks``

However, if you need to access networking information from systems in Cobbler templating, you do it as follows:

.. code-block:: bash

    $system.interfaces['eth1']['mac_address']

This should also be apparent in the output from ``cobbler system dumpvars --name=foo``

Again, usually you should not have to access these directly, see :ref:`advanced-networking` for details about Cobbler
templates all the network info out for you.

Built-in functions and extensibility
####################################

You can optionally expose custom-written functions to all Cheetah templates. To see a list of these functions you have
configured for your site (Cobbler doesn't currently ship with any) and/or add new functions, see
:ref:`extending-cobbler`.

Raw Escaping
############

Cobbler uses `Cheetah <https://cheetahtemplate.org>` for kickstart templating. Since Cheetah sees "$" as "include this
variable", it is usually a good idea to escape dollar signs in kickstart templates with \\$. However, this gets to be
hard to read over time. It is easier to declare a block "raw", which means it will not be evaluated by Cheetah.

.. code-block:: bash

    #raw
    This $dollar sign will stay in the output regardless of what the --ksmeta metadata variables are
    #end raw

It is possible to cheat by assigning bash variables from the values of Cheetah variables, and use them inside raw
blocks. This is useful if you want your shell scripts to be able to access templating variables but don't really want
to make sure escaping is all super-correct.

.. code-block:: bash

    %pre
    foo = $foo
    #raw
    This $foo will be evaluated and will not appear with a dollar sign
    and if you included funky shell scripts here you wouldn't have to worry
    about escaping anything.  The $foo comes from bash and not Cheetah
    #end raw

Raw escaping and Snippets
*************************

Be aware: raw escaping also applies to SNIPPET directives. For example:

.. code-block:: bash

    #raw
    $SNIPPET('my_snippet')
    #end raw

Will not work as expected. The result will be:

.. code-block:: bash

    $SNIPPET('my_snippet')

Because ``$SNIPPET`` is inside ``#raw #end raw``, Cheetah ignores it, and the snippet is not included. Note this also
applies to the legacy ``SNIPPET::`` syntax.

The ``#raw`` ``#end raw`` directives should instead be placed inside of ``my_snippet``.

Conditionals
############

Cheetah supports looping and if statements. For more of this, see the `Cheetah <http://cheetahtemplate.org>`_ web page.

(This section needs to be expanded)

"Stanza" Support
################

Stanzas are the precursor to Cobbler snippets. Certain built-in complex pieces of code are auto-generated by Cobbler,
from within the Cobbler source code, that vary based upon the configuration of the cobbler object being rendered. These
sections are not user extensible, unlike the newer snippet support. These are being explained here to give folks an idea
of why they should leave these weird dollar sign variables in their kickstarts, but in general, more cobbler stanzas
will not be added. The new snippets are the user-extensible way to go.

Certain blocks of kickstart code are substituted for the following variables:

* ``$yum_repo_stanza`` -- this is replaced with the code neccessary to set up any repos that are associated with the
  given cobbler profile, for use during install time. This should be present towards the top of a kickstart, but only
  for kickstarts that are RHEL5 and later or FC6 and later. Before those versions, kickstart/Anaconda did not support
  the "repo" directive.
* ``$yum_config_stanza`` -- this is replaced with the code neccessary to configure the installed system to use the yum
  repos set up during install time for regular operation. In other words, it sets up ``/etc/yum.repos.d`` on the
  provisioned system. This works for all machines that can have yum installed. If the value in
  ``/var/lib/cobbler/settings`` for ``yum_post_install_mirror`` is set, in addition, the provisioned system will be
  pointed to the boot server as an install source for "core" packages as well as any additional repos.
* ``$kickstart_done`` -- this is replaced with a specially formatted ``wget``, that places an entry in the cobbler
  and/or Apache (depending on how implemented at the time) log file, allowing ``cobbler status`` to better tell when
  kickstarts are fully complete. The implementation of what ``kickstart_done`` means may vary depending on the cobbler
  version, but it should always be placed in a kickstart template as the last line in %post. Beware in version 2.2.0,
  ``$kickstart_done`` does not exist anymore. Use ``$SNIPPLET('kickstart_done')`` instead between a cheetah stanza.
* (there may be other :ref:`snippets` and macros used not listed above)

Over time these will become first class Cobbler snippets.

Validation
##########

Cobbler contains a command ``cobbler validateks`` that will run ksvalidator (part of the pykickstart package) against
all rendered kickstarts to see if Anaconda will likely like them. It should be noted that ksvalidator is not perfect,
and in some cases, it will report false positives and/or negatives. However, it is still useful to make sure that your
rendered output from the kickstart templates is still good.

Testing an install in a VM is often a better idea.

Looking at results
##################

As was said earlier, what is provided for ``--kickstart`` is a template, not a kickstart. Templates are used to generate
kickstarts. The actual contents of the files are served up dynamically from Python and Apache. If you would like to see
the output of cobbler first hand (for your own review), you can run the following commands:

For profiles: ``cobbler profile getks --name=profile-name``

For systems: ``cobbler system getks --name=system-name``

Calling Python Code
###################

Cheetah lets you use python modules from inside the templates.

Example:

.. code-block:: bash

    #import time
    $time.strftime('%m/%d/%Y')

However what modules you can import are very limited for security reasons. If you see a module cobbler won't let you
import, add it to the whitelist in ``/etc/cobbler/settings``.

Comments
########

Cheetah makes comments with double hash marks ``##``. Any line starting with ``##`` will not show up in the rendered
kickstart file at all.

Kickstart comments ``#`` will show up in the rendered output.

Both styles of comments may be mixed. You can use ``##`` to describe what you are doing in your templates, and those
``##`` comments won't show up when someone looks at the rendered kickstart file in ``/var/www/cobbler``.

If this sounds complicated, it is. It's even more complicated in that Cheetah has special meanings for some things
starting with ``#`` like ``#if`` or ``#include``. It's pretty much safe to just use the single ``#`` comment form
everywhere though.

Further info
############

_This was originally a separate section in "Advanced topics" (itself originally part of the original, oversized man
page. It has been moved here, but needs to be merged properly with the text above._

If and only if ``--kickstart`` options reference filesystem URLs, ``--ksmeta`` allows for templating of the kickstart
files to achieve advanced functions. If the ``--ksmeta`` option for a profile read ``--ksmeta="foo=7 bar=llama"``,
anywhere in the kickstart file where the string ``$bar`` appeared would be replaced with the string ``llama``.

To apply these changes, ``cobbler sync`` must be run to generate custom kickstarts for each profile/system.

For NFS and HTTP kickstart URLs, the ``--ksmeta`` options will have no effect. This is a good reason to let cobbler
manage your kickstart files, though the URL functionality is provided for integration with legacy infrastructure,
possibly including web apps that already generate kickstarts.

Other Resources
###############

* `Kickstart-list <http://www.redhat.com/mailman/listinfo/kickstart-list>`_ is a great mailing list for info
* `Cheetah web page <http://cheetahtemplate.org>`_
* `Article on some Cheetah features (devshed.com) <http://www.devshed.com/c/a/Python/Templating-with-Cheetah/3/>`_
* `RHEL 5 Install Guide (section on kickstart options) <http://www.redhat.com/docs/manuals/enterprise/RHEL-5-manual/Installation_Guide-en-US/s1-kickstart2-options.html>`_
