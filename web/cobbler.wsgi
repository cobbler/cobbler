import os
import sys

os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'
os.environ['PYTHON_EGG_CACHE'] = '/tmp'
sys.path.append('/usr/share/cobbler/web')
sys.path.append('/usr/share/cobbler/web/cobbler_web')

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
