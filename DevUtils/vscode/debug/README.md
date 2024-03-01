# README

This README outlines the steps required to configure Visual Studio Code for debugging Django and Celery applications. Follow these instructions to setup your development environment for effective debugging.

## Configure VS Code

To get started, you need to add specific configurations to your `.vscode/launch.json` file to enable attaching the debugger to Django and Celery processes. Create a new `.vscode/launch.json` in the `swirl-home` directory with the following configuration and restart VS Code if it's running. *Note, you may need to create the .vscode directory first, then add a new launch.json file to it.*  Alter these port numbers below to suite your needs:

```
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Attach to Django",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 7029
      }
    },
    {
      "name": "Attach to Celery",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 7030
      }
    }
  ]
}
```

## Install `debugpy`
From a Terminal in the `swirl-home` directory, run:

```
pip install debugpy
```

## Run Django in Debug Mode
From a Terminal in the `swirl-home` directory, run:

```
# Uncomment to change the debug port for Django
# export SWIRL_DJANGO_DEBUG_PORT=<port-number>
export SWIRL_ENABLE_DEBUGPY=True
python -Xfrozen_modules=off manage.py runserver
```

## Run Celery in Debug Mode
From a second Terminal in the `swirl-home` directory, run:

```
python -m debugpy --listen 7030 --wait-for-client -m celery -A swirl_server worker --loglevel=info -P solo
```
Note:  Swap `7030` for a port of your choice, if desired.

## Attach the VS Code Debugger to the Running Processes

With both the Django and Celery running Terminal windows above running, launch VS Code. Navigate to the Run/Debug
menu and attach the debugger to both Django and Celery.

1. Attach to Django by selecting `Attach to Django` from the debug configurations.
2. Attach to Celery by selecting `Attach to Celery`.

You are now ready to set breakpoints in your code that runs in either Django or Celery. Debugging can be started and managed from the Run/Debug menu in VS Code.
