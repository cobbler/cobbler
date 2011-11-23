import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['PYTHON_EGG_CACHE'] = '/var/lib/cobbler/webui_cache'
sys.path.append('/usr/share/cobbler/web')
sys.path.append('/usr/share/cobbler/web/cobbler_web')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
