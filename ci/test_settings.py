from default_settings import *

# Don't break the local workspace
WORKSPACE = os.path.join(HERE, 'test_workspace')

# Make tasks synchronous
CELERY_ALWAYS_EAGER = True

# Silent CI logs
LOGGING['handlers']['null'] = {
    'level': 'DEBUG',
    'class': 'django.utils.log.NullHandler',
}
LOGGING['loggers']['ci']['handlers'] = ['null']
