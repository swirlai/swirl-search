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

SWIRL_VERSION = '2.1'

SWIRL_BANNER_TEXT = "__S_W_I_R_L__M_E_T_A_S_E_A_R_C_H__2_._1_________________________________________"
SWIRL_BANNER = f'{bcolors.BOLD}{SWIRL_BANNER_TEXT}{bcolors.ENDC}'

#############################################

if __name__ == "__main__":
    print(SWIRL_BANNER)

# end
