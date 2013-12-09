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

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
