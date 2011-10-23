from django.template.loader import add_to_builtins

# i18n is everywhere.
# Opting in for the future, too.

add_to_builtins('django.templatetags.i18n')
add_to_builtins('django.templatetags.future')
