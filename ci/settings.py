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
    ('', 'django-admin.py test projects --settings=ci.test_settings --failfast'),
)
IGNORE_EXTENSIONS = ('sqlite', 'sqlite-journal', 'css', 'scss')

# Disable template caching for development
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

# Enable django-debug-toolbar if installed
try:
    import debug_toolbar

    INTERNAL_IPS = ('127.0.0.1',)

    INSTALLED_APPS = INSTALLED_APPS + (
        'debug_toolbar',
    )

    MIDDLEWARE_CLASSES = MIDDLEWARE_CLASSES + (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
    )

    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
        'HIDE_DJANGO_SQL': False,
    }

    DEBUG_TOOLBAR_PANELS = (
        'debug_toolbar.panels.version.VersionDebugPanel',
        'debug_toolbar.panels.timer.TimerDebugPanel',
        'debug_toolbar.panels.settings_vars.SettingsVarsDebugPanel',
        'debug_toolbar.panels.headers.HeaderDebugPanel',
        'debug_toolbar.panels.request_vars.RequestVarsDebugPanel',
        'debug_toolbar.panels.template.TemplateDebugPanel',
        'debug_toolbar.panels.sql.SQLDebugPanel',
        'debug_toolbar.panels.signals.SignalDebugPanel',
        'debug_toolbar.panels.logger.LoggingPanel',
        'debug_toolbar.panels.cache.CacheDebugPanel',
    )
except ImportError:
    pass
