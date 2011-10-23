from default_settings import *

# Settings for development.
# Sane defaults are in default_settings, start from default_settings for
# production settings.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Avoid parallel builds for easier debugging
CELERYD_CONCURRENCY = 1

# gorun configuration -- https://github.com/peterbe/python-gorun
# We don't care about everything in INSTALLED_APPS, just the ci.* tests.
DIRECTORIES = (
    ('', 'django-admin.py test projects --settings=ci.test_settings'),
)
