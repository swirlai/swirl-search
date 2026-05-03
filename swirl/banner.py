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

SWIRL_VERSION = '4.5-DEV'

SWIRL_BANNER_TEXT = f"SWIRL AI COMMUNITY {SWIRL_VERSION}"

SWIRL_LOGO = f"""
         .   o
        .        .   .  o
        .      .
  o        .  @ @   .            SWIRL AI COMMUNITY {SWIRL_VERSION}
    .        @ @  .    .         Apache 2.0 License
      .  . .   .     .    .
            .       .     o
     o  .       o .
"""

SWIRL_BANNER = f'{bcolors.BOLD}{SWIRL_LOGO}{bcolors.ENDC}'

#############################################

if __name__ == "__main__":
    print(SWIRL_BANNER)

# end
