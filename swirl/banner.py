'''
@author:     Sid Probstein
@contact:    sid@swirl.today
'''

class bcolors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

SWIRL_VERSION = '1.6'

SWIRL_BANNER = f'__{bcolors.BOLD}S{bcolors.ENDC}_{bcolors.BOLD}W{bcolors.ENDC}_{bcolors.BOLD}I{bcolors.ENDC}_{bcolors.BOLD}R{bcolors.ENDC}_{bcolors.BOLD}L{bcolors.ENDC}__{bcolors.BOLD}{SWIRL_VERSION[:SWIRL_VERSION.find(".")]}{bcolors.ENDC}_{bcolors.BOLD}.{bcolors.ENDC}_{bcolors.BOLD}{SWIRL_VERSION[SWIRL_VERSION.find(".")+1:]}{bcolors.ENDC}______________________________________________________________'
SWIRL_BANNER_TEXT = "__S_W_I_R_L__1_._6______________________________________________________________"