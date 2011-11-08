from django import template

register = template.Library()


@register.filter
def truncatechars(value, chars):
    chars = int(chars)
    return value[:chars]
