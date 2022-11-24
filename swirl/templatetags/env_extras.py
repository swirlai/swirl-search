'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import os
from django import template
from swirl.banner import SWIRL_VERSION

register = template.Library()

@register.simple_tag
def get_swirl_version():
    return SWIRL_VERSION