'''
@author:     Sid Probstein
@contact:    sidprobstein@gmail.com
@version:    SWIRL 1.x
'''

import argparse
from asyncio.subprocess import STDOUT
import sys
import os
import subprocess
from subprocess import SubprocessError
import json
import time
import signal
from datetime import datetime

module_name = 'install.py'
g_debug = False

class bcolors:
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# NOTE: ORDER BELOW IS IMPORTANT
# NOTE: FIRST IN LIST IS FIRST STARTED
# NOTE: FIRST IN LIST IS LAST STOPPED 

##################################################

def install():

    print("Installing SWIRL dependencies:")

    err = 0

    proc = subprocess.run(['pip','install','-r','requirements.txt'], capture_output=True)
    if proc.returncode != 0:
        print(f"Error: {proc.stderr.decode('UTF-8')}")
        return False
    result = proc.stdout.decode('UTF-8')
    print(result)
    if 'error' in result:
        return False

    print("Ok")
    print()
    print("Now run python swirl.py setup")

    return True

##################################################
##################################################

def main(argv):

    print(f"{bcolors.BOLD}##S#W#I#R#L##1#.#5##############################################################{bcolors.ENDC}")
    print()

    parser = argparse.ArgumentParser(description="Install swirl packages")
    parser.add_argument('command', nargs='+', help="Specify 'help' to get a list of available commands")
    parser.add_argument('-d', '--debug', action="store_true", help="provide debugging information")
    args = parser.parse_args()

    # check to see that we are in a directory with swirl under it, and manage.py in it
    dir = os.getcwd()
    if not os.path.exists(dir + '/swirl'):
        print(f"{bcolors.FAIL}Error: swirl subdirectory is missing, are you sure '{dir}' is the right directory?{bcolors.ENDC}")
    if not os.path.exists(dir + '/manage.py'):
        print(f"{bcolors.FAIL}Error: manage.py is missing, are you sure '{dir}' is the right directory?{bcolors.ENDC}")

    result = install()

    if result == False:
        print(f"{bcolors.FAIL}Command {args.command[0]} reported an error{bcolors.ENDC}")
        return False
    else:
        print(f"{bcolors.OKGREEN}Command successful!{bcolors.ENDC}")
        
    return True
    
#############################################    
    
if __name__ == "__main__":
    main(sys.argv)

# end
