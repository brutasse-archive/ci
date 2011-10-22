from default_settings import *

# Settings for development.
# Sane defaults are in default_settings, start from default_settings for
# production settings.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# Avoid parallel builds for easier debugging
CELERYD_CONCURRENCY = 1
