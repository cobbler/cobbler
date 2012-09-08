# Django settings for cobbler-web project.
import django

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

# Force Django to use the systems timezone
TIME_ZONE = None

# Language section
# TBD.
LANGUAGE_CODE = 'en-us'
USE_I18N = False

SITE_ID = 1

# not used
MEDIA_ROOT = ''
MEDIA_URL = ''
ADMIN_MEDIA_PREFIX = '/media/'

SECRET_KEY = ''

# code config

if django.VERSION[0] == 1 and django.VERSION[1] < 4:
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.load_template_source',
        'django.template.loaders.app_directories.load_template_source',
    )
else:
    TEMPLATE_LOADERS = (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )

if django.VERSION[0] == 1 and django.VERSION[1] < 2:
    # Legacy django had a different CSRF method, which also had 
    # different middleware. We check the vesion here so we bring in 
    # the correct one.
    MIDDLEWARE_CLASSES = (
        'django.middleware.common.CommonMiddleware',
        'django.contrib.csrf.middleware.CsrfMiddleware',
        'django.contrib.sessions.middleware.SessionMiddleware',
        'django.contrib.auth.middleware.AuthenticationMiddleware',
    )
else:
    MIDDLEWARE_CLASSES = (
        'django.middleware.common.CommonMiddleware',
        'django.middleware.csrf.CsrfViewMiddleware',
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

