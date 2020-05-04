# Django settings for cobbler-web project.

# This is the list of http server request names the site is allowed to serve for
# Added for CVE-2016-9014
ALLOWED_HOSTS = ['*']

DEBUG = True

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

# Force Django to use a specific timezone and TZ
TIME_ZONE = 'UTC'
USE_TZ = True

# Language section
# TBD.
LANGUAGE_CODE = 'en-us'
USE_I18N = False

SITE_ID = 1

# not used
MEDIA_ROOT = ''
MEDIA_URL = ''

STATIC_URL = '/media/'

SECRET_KEY = ''

# code config

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            '/usr/share/cobbler/web/templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

MIDDLEWARE = (
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'cobbler.web.urls'

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'cobbler.web',
)

SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = '/var/lib/cobbler/webui_sessions'
