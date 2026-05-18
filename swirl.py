'''
@author:     Sid Probstein
@contact:    sid@swirl.today
@version:    Swirl 1.x
'''
import re
import argparse
from asyncio.subprocess import STDOUT
import sys
import os
import subprocess
from subprocess import SubprocessError
import json
import time
import signal
import glob
from datetime import datetime

from swirl_server import settings

module_name = 'swirl.py'

from swirl.banner import SWIRL_BANNER, bcolors, SWIRL_VERSION
from swirl.utils import is_running_celery_redis
from swirl.services import SWIRL_SERVICES_DEBUG, SWIRL_SERVICES_DEBUG_DICT, SERVICES, SERVICES_DICT

SWIRL_CORE_SERVICES = ['django', 'celery-worker']

# How long to poll after launch before declaring success (seconds).
# Increase only if a service needs more than 2 s to detect a bad config and exit.
EARLY_FAIL_WINDOW = 2.0
EARLY_FAIL_POLL   = 0.1   # seconds between polls during launch window

# How long to wait for a SIGTERM'd service to exit before giving up.
STOP_TIMEOUT      = 8.0
STOP_POLL         = 0.25

COMMAND_LIST = [ 'help', 'start', 'debug', 'start_sleep', 'stop', 'restart', 'migrate', 'setup', 'status', 'watch', 'logs' ]

def service_is_retired(service_name):
    ret = False
    try:
        for service in SERVICES:
            if service['name'] == service_name:
                if service['retired']:
                    print(f"{service_name} is retired, ignoring\n", end='')
                    ret = True
    except Exception as err:
        print(f"{err} checking retired service")
    finally:
        return ret


def check_pid(pid):
    proc = subprocess.run(['ps','-p',str(pid)], capture_output=True)
    result = proc.stdout.decode('UTF-8')
    return str(pid) in result

##################################################

def load_swirl_file():
    if os.path.exists('.swirl'):
        try:
            swirl_file = open('./.swirl', 'r')
            dict_pid = json.load(swirl_file)
            swirl_file.close()
        except OSError as err:
            print(f"Error: {err}")
            return False
        return dict_pid
    else:
        return {}

def write_swirl_file(dict_pid):
    try:
        swirl_file = open('./.swirl', 'w')
        result = swirl_file.write(json.dumps(dict_pid))
        swirl_file.close()
    except OSError as err:
        print(f"Error: {err}")
        return False

    return True

##################################################

def launch(name, path):
    """
    Start a service subprocess and poll for EARLY_FAIL_WINDOW seconds.
    Returns the pid (>0) on success, or -1 if the process exited early.
    """
    # prepare the path
    path_list = path.split()

    # create the log file
    try:
        f = open(f'./logs/{name}.log', 'ab')
    except OSError as err:
        print(f"Error: {err} creating: ./logs/{name}.log")
        return -1
    try:
        process = subprocess.Popen(path_list, stdout=f, stderr=subprocess.STDOUT)
    except Exception as err: # Broad exception okay here.
        print(f"Error: {err} creating process: {' '.join(path_list)}")
        return -1

    # do not close this file

    # Poll for EARLY_FAIL_WINDOW seconds to catch immediate exits (bad config, port in use, etc.)
    deadline = time.monotonic() + EARLY_FAIL_WINDOW
    while time.monotonic() < deadline:
        rc = process.poll()
        if rc is not None:
            # Process exited during the window
            if rc == 0:
                return process.pid   # clean daemonised exit — treat as success
            return -1                # non-zero exit = failure
        time.sleep(EARLY_FAIL_POLL)

    return process.pid

##################################################

def start(service_list, no_version_check=False):

    dict_pid = {}

    # check if .swirl exists
    dict_pid = load_swirl_file()
    if dict_pid:
        for service_name in dict_pid:
            if service_name in service_list:
                print(f"  {service_name} is already running — remove .swirl if this is incorrect")
                return False
        # end for
        # items in service_list are NOT in dict_pid, so continue and start them
    # end if

    if not os.path.exists('./logs'):
        print("  Creating logs/ directory")
        os.mkdir('./logs')

    if not is_running_celery_redis():
        print(f"  Redis is not running or unreachable ({settings.CELERY_BROKER_URL})")
        print( "  Start Redis before starting SWIRL — see https://docs.swirlaiconnect.com/Admin-Guide.html")
        return False

    # start service_list
    W = 16   # name column width
    print("Starting SWIRL:")
    flag = False
    for service_name in service_list:
        if service_name in SERVICES_DICT:
            if service_is_retired(service_name=service_name):
                continue
            print(f"  {service_name:<{W}} ...", end='', flush=True)
            result = launch(service_name, SERVICES_DICT[service_name])
            if result > 0:
                print(f'  started  (pid {result})')
                dict_pid[service_name] = result
            else:
                print(f'  error    — check logs/{service_name}.log')
                flag = True
            # end if
        else:
            print(f"  Unknown service '{service_name}' — ignored")
        # end if
    # end for

    if len(dict_pid) > 0:
        write_swirl_file(dict_pid)

    if flag:
        return False

    print(f"\nSWIRL {SWIRL_VERSION} is running.")
    return True

##################################################

def start_sleep (service_list, no_version_check=False):

    status = start(service_list, no_version_check=no_version_check)
    return status

##################################################

def debug(service_list, no_version_check=False):
    pass

##################################################

def watch(service_list, no_version_check=False):

    while 1:
        try:
            print(datetime.now())
            print()
            x = status(service_list)
            time.sleep(60)
        except KeyboardInterrupt:
            break

    return True

##################################################

def logs(service_list, no_version_check=False):

    log_files = sorted(glob.glob('logs/*.log'))
    if not log_files:
        print("No log files found in logs/")
        return True

    print(f"tail -f {' '.join(log_files)} - hit ^C to stop:")

    try:
        p = subprocess.Popen(['tail', '-f'] + log_files, stdout=subprocess.PIPE)

        while p.poll() is None:
            l = p.stdout.readline()
            print(l.decode("utf-8").replace('\n',''))
        p.kill()
        return True

    except KeyboardInterrupt:
        p.kill()
        return True

##################################################

def status(service_list, no_version_check=False):

    # check if .swirl exists
    dict_pid = load_swirl_file()

    if not dict_pid:
        print("  SWIRL is not running")
        return True

    W = 16   # name column width
    print("SWIRL status:")
    for service_name in dict_pid:
        if service_name in service_list:
            if service_is_retired(service_name=service_name):
                continue
            pid = dict_pid[service_name]
            if check_pid(pid):
                print(f"  {service_name:<{W}} running   pid {pid}")
            else:
                print(f"  {service_name:<{W}} unknown   pid {pid} not found")
        # end if
    # end for

    return True

##################################################

def migrate(service_list, no_version_check=False):

    print("Checking Migrations:")

    any_change = False

    proc = subprocess.run(['python','manage.py','makemigrations'], capture_output=True)
    if proc.returncode != 0:
        print(f"Error: {proc.stderr.decode('UTF-8')}")
        return False
    result = proc.stdout.decode('UTF-8')
    if not 'No changes detected' in result:
        any_change = True
    else:
        print(result)

    proc = subprocess.run(['python','manage.py','makemigrations','swirl'], capture_output=True)
    if proc.returncode != 0:
        print(f"Error: {proc.stderr.decode('UTF-8')}")
        return False
    result = proc.stdout.decode('UTF-8')
    if not 'No changes detected' in result:
        any_change = True
    else:
        print(result)

    print()
    print("Migrating:")
    print()

    proc = subprocess.run(['python','manage.py','migrate'], capture_output=True)
    if proc.returncode != 0:
        print(f"Error: {proc.stderr.decode('UTF-8')}")
        return False
    result = proc.stdout.decode('UTF-8')
    print(result)
    return True

##################################################

def _wait_for_pid_exit(pid):
    """Poll until the process is gone or STOP_TIMEOUT is reached. Returns True if gone."""
    deadline = time.monotonic() + STOP_TIMEOUT
    while time.monotonic() < deadline:
        if not check_pid(pid):
            return True
        time.sleep(STOP_POLL)
    return not check_pid(pid)

def stop(service_list, no_version_check=False):

    dict_pid = {}

    # check if .swirl exists
    dict_pid = load_swirl_file()

    if not dict_pid:
        print("  SWIRL is not running")
        return False

    W = 16   # name column width
    # stop service_list
    print("Stopping SWIRL:")
    stopped_names = []
    flag = False
    for service_name in dict_pid:
        # if in .swirl
        if service_name in service_list:
            if service_is_retired(service_name=service_name):
                continue
            # first listed service is stopped last
            if service_name == SERVICES[0]['name']:
                continue
            print(f"  {service_name:<{W}} (pid {dict_pid[service_name]}) ...", end='', flush=True)
            pid = int(dict_pid[service_name])
            try:
                os.kill(pid, 0)
                os.kill(pid, signal.SIGTERM)
            except OSError as err:
                print(f"  error    — {err}")
                flag = True
            if _wait_for_pid_exit(pid):
                print(f"  stopped")
                stopped_names.append(service_name)
            else:
                print(f"  error    — still running after {STOP_TIMEOUT:.0f}s")
                flag = True
            # end if
        # end if
    # end for

    # shut down the first service last
    if SERVICES[0]['name'] in dict_pid:
        if SERVICES[0]['name'] in service_list:
            svc = SERVICES[0]['name']
            print(f"  {svc:<{W}} (pid {dict_pid[svc]}) ...", end='', flush=True)
            pid = int(dict_pid[svc])
            try:
                pgrp = os.getpgid(pid)
                os.killpg(pgrp, signal.SIGTERM)
            except OSError as err:
                print(f"  error    — {err}")
                flag = True
            if _wait_for_pid_exit(pid):
                print(f"  stopped")
                stopped_names.append(svc)
            else:
                print(f"  error    — still running after {STOP_TIMEOUT:.0f}s")
                flag = True
            # end if
    # end if

    for service_name in stopped_names:
        del dict_pid[service_name]

    if dict_pid:
        write_swirl_file(dict_pid)

    if flag:
        print("  Warning: some services may still be running — check .swirl")
        return False

    if not dict_pid:
        try:
            os.remove('.swirl')
        except OSError as err:
            print(f"  error removing .swirl — {err}")
            return False

    print("\nSWIRL stopped.")
    return True

##################################################

def restart(service_list, no_version_check=False):

    result = stop(service_list)
    if not result:
        return result

    print()
    result = start(service_list, no_version_check=no_version_check)
    return result

##################################################

def help(service_list, no_version_check=False):
    # Filter out the retired services
    active_services = [service for service in service_list if not SERVICES[service].get('retired', False)]

    print("Usage: python swirl.py <command> [<service-list>]\n")

    # Now use the active_services list to print the available services
    print(f"Available commands: {', '.join(COMMAND_LIST)}")
    print(f"Available services: {', '.join(active_services)}, core ({', '.join(SWIRL_CORE_SERVICES)})\n")
    print("The start, status, stop and restart commands default to all Swirl services.")
    print("Most optionally accept one or more Swirl service names, separated by spaces.")
    print()

    result = True

##################################################

def setup(service_list, no_version_check=False):

    print("Setting Up Swirl:")

    result = migrate(service_list)
    if not result:
        print(f"Error: error during migration, check console output")
        return False

    if not os.path.exists(os.getcwd() + '/static'):
        # collect statics
        print()
        print(f"Collecting Statics:")
        print()
        proc = subprocess.run(['python','manage.py','collectstatic'], capture_output=True)
        if proc.returncode != 0:
            print(f"Error: {proc.stderr.decode('UTF-8')}")
            return False
        result = proc.stdout.decode('UTF-8')
        print(result)
        if 'static files copied' in result:
            print("Ok")
            return True
        else:
            return False
    else:
        return True

##################################################
##################################################

def main(argv):
    global SERVICES
    global SERVICES_DICT

    print(f"{SWIRL_BANNER}")
    print()

    parser = argparse.ArgumentParser(description="Manage the Swirl server")
    parser.add_argument('command', nargs='+', help="Specify 'help' to get a list of available commands")
    parser.add_argument('-d', '--debug', action="store_true", help="start Swirl in debug mode")
    parser.add_argument('--no-version-check', action="store_true", dest="no_version_check",
                        help="skip the external version check on startup")
    args = parser.parse_args()

    if args.debug:
        SERVICES = SWIRL_SERVICES_DEBUG
        SERVICES_DICT = SWIRL_SERVICES_DEBUG_DICT

    # check to see that we are in a directory with swirl under it, and manage.py in it
    dir = os.getcwd()
    if not os.path.exists(dir + '/swirl'):
        print(f"  Error: swirl subdirectory is missing — is '{dir}' the right directory?")
    if not os.path.exists(dir + '/manage.py'):
        print(f"  Error: manage.py is missing — is '{dir}' the right directory?")

    if not args.command[0] in COMMAND_LIST:
        print(f"  Unknown command: '{args.command[0]}'")
        print(f"  Available commands: {', '.join(COMMAND_LIST)}")
        return 0
    else:
        service_list = args.command[1:]
        if service_list == [] or service_list[0].lower() == 'all':
            service_list = []
            for service in SERVICES:
                # only add default services, since none was specified
                if 'default' in service:
                    if service['default']:
                        service_list.append(service['name'])
        elif service_list[0].lower() == 'core':
            service_list = SWIRL_CORE_SERVICES
        else:
            for service in service_list:
                if not service in SERVICES_DICT:
                    active = [s['name'] for s in SERVICES if not s.get('retired', False)]
                    print(f"  Unknown service: '{service}'")
                    print(f"  Available services: {', '.join(active)}")
                    return False
                # end if
            # end for
        # run the command
        command = args.command[0]
        result = COMMAND_DISPATCH.get(command)(service_list=service_list, no_version_check=args.no_version_check)
    # end if

    if result == False:
        return 1
    else:
        if args.command[0] == 'start_sleep':
            while 1:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    return 0
        else:
            return 0
    # end if

COMMAND_DISPATCH = {
     'help': help,
     'start': start,
     'debug': debug,
     'start_sleep': start_sleep,
     'stop' : stop,
     'restart': restart,
     'migrate': migrate,
      'setup' : setup,
      'status': status,
      'watch':watch,
      'logs': logs
}

#############################################

if __name__ == "__main__":
    main(sys.argv)

# end
