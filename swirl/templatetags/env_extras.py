'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

from django import template
from django.conf import settings

from swirl.banner import SWIRL_VERSION

register = template.Library()

@register.simple_tag
def get_swirl_version():
    return SWIRL_VERSION

@register.simple_tag
def get_swirl_url():
    return f"{settings.PROTOCOL}://{settings.HOSTNAME}:8000/"