# Only add standard python modules here. When running under a virtualenv other modules are not
# available at this point.
import inspect
import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['PYTHON_EGG_CACHE'] = '/var/lib/cobbler/webui_cache'

# chdir resilient solution
script_path = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
if script_path not in sys.path:
    sys.path.insert(0, script_path)
    sys.path.insert(0, os.path.join(script_path, 'cobbler_web'))


def application(environ, start_response):
    if 'VIRTUALENV' in environ and environ['VIRTUALENV'] != "":
        # VIRTUALENV Support
        # see http://code.google.com/p/modwsgi/wiki/VirtualEnvironments
        import site
        import distutils.sysconfig
        site.addsitedir(distutils.sysconfig.get_python_lib(prefix=environ['VIRTUALENV']))
        # Now all modules are available even under a virtualenv

    from django.core.wsgi import get_wsgi_application
    _application = get_wsgi_application()
    return _application(environ, start_response)
