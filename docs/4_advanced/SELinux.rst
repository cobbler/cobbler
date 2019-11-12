*******
SELinux
*******

SELinux policies are typically provided by the upstream distribution (Fedora, Ubuntu, etc.). As new features are added
to cobbler (and we do add new features frequently), those policies may become out-of-date leading to AVC denials and
other problems. If you wish to run SELinux on your cobbler system, we expect you to know how to write policy and
resolve AVCs.

Below are some of the more common issues you may run into with this release.

ProtocolError: <ProtocolError for x.x.x.x:80/cobbler_api: 503 Service Temporarily Unavailable>
##############################################################################################

If you see this when you run "cobbler check" or any other cobbler command, it means SELinux is blocking httpd from
talking with cobblerd. The command to fix this is:

{% highlight bash %}
$ sudo setsebool -P httpd_can_network_connect true
{% endhighlight %}

Fedora 16 / RHEL6 / CentOS6 - Python MemoryError
################################################

When starting cobblerd for the first time (or after upgrading to 2.2.x), you may see a stack trace like the following:

{% highlight bash %}
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
{% endhighlight %}

This error is caused by SELinux blocking python ctypes. To resolve this, you can use audit2allow to enable the execution
of temp files or you can remove the authn_pam.py module from the site-packages/cobbler/modules directory (as long as
you're not using PAM authentication for the Web UI).
