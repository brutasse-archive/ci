import os
HERE = os.path.abspath(os.path.dirname(__file__))

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ()
MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(HERE, 'db.sqlite'),
    }
}

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True
USE_L10N = True

MEDIA_ROOT = os.path.join(HERE, 'media')
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(HERE, 'static')
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

# CachedStaticFilesStorage recommended for production
STATICFILES_STORAGE = 'staticfiles.storage.StaticFilesStorage'

STATICFILES_FINDERS = (
    'staticfiles.finders.FileSystemFinder',
    'staticfiles.finders.AppDirectoriesFinder',
)

# XXX people need to change this for deployments
SECRET_KEY = 'CHANGEME'

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',
    )),
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'ci.urls'

TEMPLATE_DIRS = (
    os.path.join(HERE, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',

    'djcelery',
    'floppyforms',
    'staticfiles',

    'ci.projects',
)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '%(asctime)s %(levelname)s: %(message)s'
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
        'ci': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Redis for celery
REDIS_HOST = "localhost"
REDIS_PORT = 6379

CELERY_RESULT_BACKEND = "redis"
CELERY_REDIS_HOST = REDIS_HOST
CELERY_REDIS_PORT = REDIS_PORT
CELERY_REDIS_DB = 2

BROKER_TRANSPORT = "redis"
BROKER_HOST = REDIS_HOST
BROKER_PORT = REDIS_PORT
BROKER_VHOST = "3"

import djcelery
djcelery.setup_loader()

# CI-specific settings
WORKSPACE = os.path.join(HERE, 'workspace')
