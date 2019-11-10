*****
About
*****

.. toctree::
   :maxdepth: 2
   :numbered:

   Release Notes<1_about/release_notes>
   Distribution Support<1_about/distribution_support>
   Distribution Notes<1_about/distribution_notes>

Cobbler is a build and deployment system. The primary functionality of cobbler is to simplify the lives of
administrators by automating repetive actions, and to encourage reuse of existing work through the use of templating.

One of the primary tenets we follow is to provide options and flexibility rather than locking administrators into a
single way of doing things. As such, cobbler can be integrated with a growing number of configuration management systems
and remote scripting utilities while enabling deployment of many different operating system types.

Cobbler also provides a tool (koan) for simplifying virtualization deployments.

How We Model Things
###################

![object tree diagram](/images/how-we-do.png)