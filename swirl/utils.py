'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

from pathlib import Path
import os
import logging as logger

##################################################
##################################################

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