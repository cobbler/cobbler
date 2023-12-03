*******
SELinux
*******

Providing working policies for SELinux (and AppArmor) is the responsibility of downstream (e.g. your Linux or repo
vendor). Unfortunately, every now and then issues tend to pop up on the mailing lists or in the issue tracker. Since
we're really not in the position to resolve SELinux issues, all reported bugs will be closed. All we can do is try to
document these issues here, hopefully the community is able to provide some feedback/workarounds/fixes.

General Tips - Fedora
#####################

Service Specific Manpages
=========================

Manpages are automatically generated for SELinux, and many application that are restricted by SELinux. This
documentation is provided by the ``selinux-policy-devel`` package. For example, to see the SELinux restrictions on
cobbler, try:

.. code-block:: shell

    yum install selinux-policy-devel
    man cobblerd_selinux

Booleans
========

Many SELinux restrictions can easily be remedied by switching a boolean specifically designed for the purpose. For
example, many cobbler deployments require ``cobbler_can_network_connect`` to be true.

To find and set booleans that might affect the service you're working with, do:

.. code-block::

    getsebool -a|grep cobbler
    setsebool -P cobbler_can_network_connect 1

Context
=======

File context labelling is also addressed in ``man cobblerd_selinux``. Remember, ``mv`` will retain a file's current
context, and ``cp`` will make the file inherit the target directory's context. The first step and easiest step in
troubleshooting context denials is to simply ensure the default labels are applied:

.. code-block:: shell

    restorecon -R /var/lib/cobbler/

See the aforementioned manpage to learn of applying contexts to non-default paths.

Other policy issues
===================

SELinux denials can be caused by policies or labelling not applied (requiring admin action) or by improper default
policy (requiring developer action). You can create custom policy modules, if needed:

    yum install policycoreutils-python checkpolicy
    grep cobbler /var/log/audit/audit.log | audit2why
    # Read over the denials, check for booleans, labelling problems etc

Create a policy module for a specific denial:

.. code-block:: shell

    grep "audit(1388259039.970:1931)" /var/log/audit/audit.log | audit2allow -M sensible_module_name
    semodule -i sensible_module_name.pp

Custom Policy Best Practices
============================

Applying custom modules atomically ensures appropriate restrictions and helps to identify individual policy or
labelling issues. Some denials are caused by booleans or labelling that are not yet applied (requiring admin action);
some denials are caused by the default policy not matching the behaviour of the code (requiring developer action). By
providing feedback to both SELinux policy maintainers and application developers in bug reports, you can help make
secure use of cobbler (and other services) easier for everyone.


Fedora 16 / RHEL6 / CentOS6 - Python MemoryError
################################################

Obscure error message for which a solution is unknown. The workaround is to disable SELinux or build a custom SELinux
module to run cobbler unconfined. See also https://bugzilla.redhat.com/show_bug.cgi?id=816309

     Starting cobbler daemon: Traceback (most recent call last):
     File "/usr/bin/cobblerd", line 76, in main
     api = cobbler_api.BootAPI(is_cobblerd=True)
     File "/usr/lib/python2.6/site-packages/cobbler/api.py", line 127, in init
     module_loader.load_modules()
     File "/usr/lib/python2.6/site-packages/cobbler/module_loader.py", line 62, in load_modules
     blip = import("modules.%s" % ( modname), globals(), locals(), [modname])
     File "/usr/lib/python2.6/site-packages/cobbler/modules/authn_pam.py", line 53, in
     from ctypes import CDLL, POINTER, Structure, CFUNCTYPE, cast, pointer, sizeof
     File "/usr/lib64/python2.6/ctypes/init.py", line 546, in
     CFUNCTYPE(c_int)(lambda: None)
     MemoryError

To run cobbler unconfined, build the following SELinux module using the instructions http://www.city-fan.org/tips/BuildSeLinuxPolicyModules

.. code-block:: shell

     root@system # cat cobbler_unconfined.te
     policy_module(cobbler_unconfined, 1.0)
     gen_require('type cobblerd_t;')
     unconfined_domain(cobblerd_t)
     root@system # make -f /usr/share/selinux/devel/Makefile cobbler_unconfined.pp
     root@system # semodule -i cobbler_unconfined.pp
     root@system # semodule -l | grep cobbler
     cobbler	1.1.0
     cobbler_unconfined	1.0
     root@system #

Fedora 14
#########

While many users with SELinux distributions opt to turn SELinux off, you may wish to keep it on. For Fedora 14 you
might want to amend the SELinux policy settings:

.. code-block:: shell

       /usr/sbin/semanage fcontext -a -t public_content_rw_t "/var/lib/tftpboot/.*"
       /usr/sbin/semanage fcontext -a -t public_content_rw_t "/var/www/cobbler/images/.*"
       restorecon -R -v "/var/lib/tftpboot/"
       restorecon -R -v "/var/www/cobbler/images.*"
       # Enables cobbler to read/write public_content_rw_t
       setsebool cobbler_anon_write on
       # Enable httpd to connect to cobblerd (optional, depending on if web interface is installed)
       # Notice: If you enable httpd_can_network_connect_cobbler and you should switch httpd_can_network_connect off
       setsebool httpd_can_network_connect off
       setsebool httpd_can_network_connect_cobbler on
       #Enabled cobbler to use rsync etc.. (optional)
       setsebool cobbler_can_network_connect on
       #Enable cobbler to use CIFS based filesystems (optional)
       setsebool cobbler_use_cifs on
       # Enable cobbler to use NFS based filesystems (optional)
       setsebool cobbler_use_nfs on
       # Double check your choices
       getsebool -a|grep cobbler

The information suggested by ``cobbler check`` should be sufficient for older distributions. These is just a few
``fcontext`` commands and setting ``httpd_can_network_connect``.

ProtocolError: <ProtocolError for x.x.x.x:80/cobbler_api: 503 Service Temporarily Unavailable>
##############################################################################################

If you see this when you run ``cobbler check`` or any other Cobbler command, it means SELinux is blocking httpd from
talking with cobblerd. The command to fix this is:

``setsebool -P httpd_can_network_connect true``
