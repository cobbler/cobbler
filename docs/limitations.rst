*************************
Limitations and Surprises
*************************

Templating
##########

Before templates are passed to Jinja or Cheetah there is a pre-processing of templates happening. During pre-processing
Cobbler replaces variables like ``@@my_key@@`` in the template. Those keys are currently limited by the regex of ``\S``,
which translates to ``[^ \t\n\r\f\v]``.

Restarting the daemon
#####################

Once you have a Cobbler distro imported or manually added you have to make sure the source for the Kernel & initrd is
available all the time. Thus I highly recommend you to add the ISOs to your ``/etc/fstab`` to make them persistent
across reboots. If you forget to remount them the Cobbler daemon won't start!

Kernel options
##############

The user (so you) is responsible for generating the correct quoting of the Kernel Command Line. We manipulate the
arguments you give us in a way that we add wrapping double quotes around them when the value contains a space.

The Linux Kernel describes its quoting at:
`The kernel’s command-line parameters <https://www.kernel.org/doc/html/v5.15/admin-guide/kernel-parameters.html#the-kernel-s-command-line-parameters>`_

Consult the documentation of your operating system for how it deals with this if it is not Linux.

Special Case: Uyuni/SUSE Manager
################################

.. note:: SUSE Manager is a flavor of Uyuni. The term Uyuni refers to both pieces of software in this context.

Uyuni uses Cobbler for driving auto-installations. When using Cobbler in the context of Uyuni, you need to know that
Cobbler is not seen as the source of truth by Uyuni. This means, in case you don't have any auto-installation
configured in Uyuni, the content visible in Cobbler is deleted.

Because of the same reason, during the runtime of Cobbler you may see systems popping on and off as the content of
Cobbler is managed by Uyuni (in particular, the taskomatic task ``kickstart_cleanup`` executes cleanup on the Cobbler
content)
