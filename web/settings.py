# Django settings for cobbler-web project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = ''     # cobbler-web does not use a database
DATABASE_NAME = ''       
DATABASE_USER = ''       
DATABASE_PASSWORD = ''   
DATABASE_HOST = ''       
DATABASE_PORT = ''       

# this is not used by cobbler-web
TIME_ZONE = 'America/NewYork'

# Language section
# TBD.
LANGUAGE_CODE = 'en-us'
USE_I18N = False

SITE_ID = 1

# not used
MEDIA_ROOT = ''
MEDIA_URL = ''
ADMIN_MEDIA_PREFIX = '/media/'

# FIXME: ???
SECRET_KEY = 'w&x*74x-b=ycigsdya03699o!9kt4(z4wyx-us9q=--&7clv4='

# code config

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)
MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)
ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
    '/usr/share/cobbler/web/templates',
)
INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'cobbler_web',
)

from django.conf.global_settings import TEMPLATE_CONTEXT_PROCESSORS

TEMPLATE_CONTEXT_PROCESSORS += (
     'django.core.context_processors.request',
) 
     
SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = '/var/lib/cobbler/webui_sessions'

