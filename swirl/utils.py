'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

import os
import logging as logger
import json
from pathlib import Path
from django.core.paginator import Paginator

##################################################
##################################################

def is_valid_json(j):
    try:
        json.loads(j)
    except ValueError:
        return False
    return True

def swirl_setdir():
    # Get the current path and append it to the path
    this_file = str(Path(__file__).resolve())
    # /Users/sid/Code/swirl_server/swirl/utils.py
    # C:\Users\sid\Code\swirl_server\swirl\utils.py
    slash = '\\'
    if '/' in this_file:
        slash = '/'
    this_path = this_file[:this_file.rfind(slash)]
    this_folder = this_path[this_path.rfind(slash)+1:]
    append_path = ""
    if this_folder == "swirl":
        # chop off the swirl
        swirl_server_path = this_path[:this_path.rfind(slash)]
        append_path = swirl_server_path + slash + 'swirl_server' + slash + 'settings.py'
    # end if
    if append_path == "":
        logger.error("swirl_setdir(): error: append_path is empty string!!")
    if not os.path.exists(append_path):
       logger.error("swirl_setdir(): error: append_path does not exist!!")
    return(append_path)

def is_int(value):
    try:
        if not value:
            return False
        int_value = int(value)
        if int_value > 0:
            return True
        return False
    except ValueError:
        return False

def paginate(data, request):
    page = request.GET.get('page')
    items = request.GET.get('items')
    if data and is_int(page) and is_int(items):
        paginator = Paginator(data, items)
        page_obj = paginator.get_page(page)
        return page_obj.object_list
    return data