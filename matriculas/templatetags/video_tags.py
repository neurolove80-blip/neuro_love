import re
from django import template
from django.template.defaultfilters import stringfilter

register = template.Library()

@register.filter
@stringfilter
def youtube_thumbnail(value):
    match = re.search(r'(?:v=|youtu\.be/|/embed/|shorts/|live/)([a-zA-Z0-9_-]{11})', value)
    if match:
        return f'https://img.youtube.com/vi/{match.group(1)}/hqdefault.jpg'
    return ''
