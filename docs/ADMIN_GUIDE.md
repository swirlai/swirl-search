![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL ADMIN GUIDE

## Table of Contents

:small_blue_diamond: [Search Expiration Service](#search-expiration-service)<br/>
:small_blue_diamond: [Service Startup & Daemonization](#service-startup--daemonization)<br/>
:small_blue_diamond: [Management Tools](#management-tools)<br/>
:small_blue_diamond: [Database Migration](#database-migration)<br/>
:small_blue_diamond: [Configuring Django](#configuring-django)<br/>
:small_blue_diamond: [Configuring Celery, Beats & RabbitMQ](#configuring-celery-beats--rabbitmq)<br/>
:small_blue_diamond: [Security](#security)<br/>
:small_blue_diamond: [Troubleshooting](#troubleshooting)<br/>
:small_blue_diamond: [Get Support](#get-support)

<br/>

<br/>

------------

<br/>

<br/>

# Search Expiration Service

SWIRL can automatically expire Search and their associated (linked) Result objects, to ensure you don't end up storing everything anyone has ever searched for. (Unless you want to, of course.)

To learn more about this feature, refer to the [Using SWIRL - Search Expiration & Retention](#search-expiration)

To enable this feature you must start the [Celery Beats](INSTALLATION_GUIDE.md#7-start-celery-beats) service as described in the Installation Guide.

<br/>

```
celery -A swirl_server beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

<br/>

By default, the service runs every hour. You can change this in the [Django settings](../swirl_server/settings.py):

<br/>

```
CELERY_BEAT_SCHEDULE = {
    # Executes every hour
    'expire': { 
         'task': 'expirer', 
         'schedule': crontab(minute=0,hour='*'),
        },          
}
```

<br/>

You can also change it using the Django Console here: http://127.0.0.1:8000/admin/django_celery_beat/crontabschedule/ 

<br/>

![Django console crontab page](./images/django_admin_console_crontab.png)

:warning: If you change the crontab entry in the database, and don't change the CELERY_BEAT_SCHEDULE as well, that schedule will be restored
if/when you restart SWIRL.

For more information on Celery consult [Configuring Celery, Beats and RabbitMQ](#configuring-celery-beats--rabbitmq)

<br/>

# Service Startup & Daemonization

## Using swirl.py

For most normal operation, use swirl.py to start, stop or restart services. 
It is located in the swirl_server directory, along with manage.py.

* To start services:

```
python swirl.py start
```

One or more services may be specified, e.g.:

```
python swirl.py start celery-beats
```

* To check the status of SWIRL:

```
python swirl.py status
```

SWIRL will report the current running services, and their pid:

```
##S#W#I#R#L##1#0################################################################

Service: rabbitmq...RUNNING, pid:27434
Service: django...RUNNING, pid:27482
Service: celery-worker...RUNNING, pid:27515
Service: celery-beats...RUNNING, pid:27542

  PID TTY           TIME CMD
27434 ttys000    0:00.00 /bin/sh /opt/homebrew/sbin/rabbitmq-server
27482 ttys000    0:00.29 python manage.py runserver
27515 ttys000    0:01.05 /Users/sid/.pyenv/versions/3.9.2/bin/python /Users/sid/.pyenv/versions/3.9.2/bin/celery -A swirl_server worker --loglevel=info
27542 ttys000    0:00.60 /Users/sid/.pyenv/versions/3.9.2/bin/python /Users/sid/.pyenv/versions/3.9.2/bin/celery -A swirl_server beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

* To terminate services:

```
python swirl.py stop
```

* To restart services:

```
python swirl.py restart
```

```
python swirl.py restart celery-worker consumer
```

* To get help:

```
python swirl.py help
```

<br/>

### Troubleshooting

Note that swirl.py writes the list of services and their associated pids to a file, .swirl. 

Here is an example of a .swirl file for a fully running system:

```
{"rabbitmq": 27434, "django": 27482, "celery-worker": 27515, "celery-beats": 27542}
```

This file is read by the status and stop commands. Note that both commands invoke ps -p with the pids
for the services to determine if they are actually running, and displays this information for you.

If you start or stop individual services, the .swirl file should only have the name and pid for running
services. 

In the event that the .swirl file is out of sync with the running processes, you may delete it, or edit it to match the
actual running processes. Be sure to manually delete any running processes. You can find them as follows:

On OS/X or Linux:

```
ps -ef | grep python
ps -ef | grep celery
ps -ef | grep rabbit
```

Note that there will be at least two rabbit processes, when killing them manually.

### Helpful Hints

* When troubleshooting swirl.py be sure to look at logs/*.log. Live services will continue writing to the appropriately
named logfile. 

* If a service starts and then isn't running a short time later, check the log files there is likely an exception occuring.

<br/>

### Changing Startup Configuration

To change startup incantations for any service, or change the service names, 
edit the SWIRL_SERVICES variable at the top of swirl.py:

```
SWIRL_SERVICES = [
    {
        'name': 'rabbitmq',
        'path': 'rabbitmq-server'
    },
    {
        'name': 'django',
        'path': 'python manage.py runserver' # this might be different
    },
    {
        'name': 'celery-worker',
        'path': 'celery -A swirl_server worker --loglevel=info'
    },
    {
        'name': 'celery-beats',
        'path': 'celery -A swirl_server beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler'
    }
]
```

Note that swirl.py starts the services in the order specified, but terminates the first service last - with a longer delay and using a group signal to shut down. It is intended to be used by rabbitmq.

<br/>

### Manually Starting Services

The exact incantations to start the services varies by Operating System. 
The following sections present them along with the expected output.

[Mac OS/X or Linux](#mac-osx-or-linux) | [Microsoft Windows](#microsoft-windows)

<br/>

#### Mac OS/X or Linux

Run each command shown below in a separate terminal window, in the directory where you installed SWIRL, 
e.g. swirl_server, in the order specified below.

*Don't* run these commands in the swirl_server subdirectory. 
They won't work anyway; if you aren't sure, check that manage.py is there.

<br/>

#### 1. RabbitMQ
```
cd swirl_server
rabbitmq-server
```
<details><summary>Expected Output</summary>
<p>

```
2022-02-28 12:54:27.502241-05:00 [info] <0.227.0> Feature flags: list of feature flags found:
2022-02-28 12:54:27.505744-05:00 [info] <0.227.0> Feature flags:   [x] implicit_default_bindings
2022-02-28 12:54:27.505769-05:00 [info] <0.227.0> Feature flags:   [x] maintenance_mode_status
2022-02-28 12:54:27.505785-05:00 [info] <0.227.0> Feature flags:   [x] quorum_queue
2022-02-28 12:54:27.505801-05:00 [info] <0.227.0> Feature flags:   [x] stream_queue
2022-02-28 12:54:27.505813-05:00 [info] <0.227.0> Feature flags:   [x] user_limits
2022-02-28 12:54:27.505822-05:00 [info] <0.227.0> Feature flags:   [x] virtual_host_metadata
2022-02-28 12:54:27.505833-05:00 [info] <0.227.0> Feature flags: feature flag states written to disk: yes
2022-02-28 12:54:27.611037-05:00 [noti] <0.44.0> Application syslog exited with reason: stopped
2022-02-28 12:54:27.611087-05:00 [noti] <0.227.0> Logging: switching to configured handler(s); following messages may not be visible in this log output

  ##  ##      RabbitMQ 3.9.13
  ##  ##
  ##########  Copyright (c) 2007-2022 VMware, Inc. or its affiliates.
  ######  ##
  ##########  Licensed under the MPL 2.0. Website: https://rabbitmq.com

  Erlang:      24.2.1 [emu]
  TLS Library: OpenSSL - OpenSSL 1.1.1m  14 Dec 2021

  Doc guides:  https://rabbitmq.com/documentation.html
  Support:     https://rabbitmq.com/contact.html
  Tutorials:   https://rabbitmq.com/getstarted.html
  Monitoring:  https://rabbitmq.com/monitoring.html

  Logs: /opt/homebrew/var/log/rabbitmq/rabbit@localhost.log
        /opt/homebrew/var/log/rabbitmq/rabbit@localhost_upgrade.log
        <stdout>

  Config file(s): (none)

  Starting broker... completed with 7 plugins.
```
</p>
</details>

<br />

#### 2. Setup Django

Note: this should not be necessary unless you are installing for the first time.

Please report any need to run these commands to [support](#get-support).
Thank you.

``` 
python swirl.py start rabbitmq
python manage.py collectstatic
python swirl.py stop rabbitmq
``` 

``` 
python manage.py makemigrations
python manage.py makemigrations swirl
python manage.py migrate
```

Refer to the [Installation Guide](INSTALLATION_GUIDE.md#setup-django) for more information.

<br/>

#### 3. Start Django Server

```
cd swirl_server
python manage.py runserver
```
<details><summary>Expected Output</summary>
<p>

```
Watching for file changes with StatReloader
Performing system checks...
System check identified some issues:
System check identified 3 issues (0 silenced).
February 20, 2022 - 22:51:48
Django version 4.0.1, using settings swirl_server.settings
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```
</p>
</details>

<br />

If using ASGI:

```
cd swirl_server
daphne swirl_server.asgi:application
```

<details><summary>Expected Output</summary>
<p>

```
2022-02-20 22:55:19,969 INFO     Starting server at tcp:port=8000:interface=127.0.0.1
2022-02-20 22:55:19,969 INFO     HTTP/2 support not enabled (install the http2 and tls Twisted extras)
2022-02-20 22:55:19,969 INFO     Configuring endpoint tcp:port=8000:interface=127.0.0.1
2022-02-20 22:55:19,969 INFO     Listening on TCP address 127.0.0.1:8000
```
</p>
</details>

<br />

Once you have started django, you should be able to request a SWIRL object:

:star: [http://localhost:8000/swirl/](http://localhost:8000/swirl/)

<br/>

![SWIRL Front Page](./images/swirl_frontpage.png)

<br/>

<br/>

### 4. Start Celery Worker
```
cd swirl_server
celery -A swirl_server worker --loglevel=info 

```
<details><summary>Expected Output</summary>
<p>

```
 -------------- celery@Tenet1.cable.rcn.com v5.2.3 (dawn-chorus)
--- ***** ----- 
-- ******* ---- macOS-12.1-arm64-arm-64bit 2022-02-28 17:54:34
- *** --- * --- 
- ** ---------- [config]
- ** ---------- .> app:         swirl_server:0x104ea0100
- ** ---------- .> transport:   amqp://guest:**@localhost:5672//
- ** ---------- .> results:     rpc://
- *** --- * --- .> concurrency: 10 (prefork)
-- ******* ---- .> task events: ON
--- ***** ----- 
 -------------- [queues]
                .> celery           exchange=celery(direct) key=celery
                

[tasks]
  . federate
  . swirl_server.celery.debug_task

[2022-02-28 17:54:35,179: INFO/MainProcess] Connected to amqp://guest:**@127.0.0.1:5672//
[2022-02-28 17:54:35,184: INFO/MainProcess] mingle: searching for neighbors
[2022-02-28 17:54:36,218: INFO/MainProcess] mingle: all alone
[2022-02-28 17:54:36,240: WARNING/MainProcess] /Users/sid/.pyenv/versions/3.9.2/lib/python3.9/site-packages/celery/fixups/django.py:203: UserWarning: Using settings.DEBUG leads to a memory
            leak, never use this setting in production environments!
  warnings.warn('''Using settings.DEBUG leads to a memory

[2022-02-28 17:54:36,240: INFO/MainProcess] celery@Tenet1.cable.rcn.com ready.
```
</p>
</details>

<br />

### 5. Start Celery Beats 

You only need to star this if you want to use the [Search Expiration Service](#search-expiration-service). You don't need to start this service if you don't want to use it.
```
celery -A swirl_server beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```
<details><summary>Expected Output</summary>
<p>

```
celery beat v5.2.3 (dawn-chorus) is starting.
LocalTime -> 2022-03-03 14:43:11
Configuration ->
    . broker -> amqp://guest:**@localhost:5672//
    . loader -> celery.loaders.app.AppLoader
    . scheduler -> django_celery_beat.schedulers.DatabaseScheduler

    . logfile -> [stderr]@%INFO
    . maxinterval -> 5.00 seconds (5s)
[2022-03-03 14:43:11,798: INFO/MainProcess] beat: Starting...
```
</p>
</details>

<br/>

<br/>

# Management Tools

## django console

Django has a built-in web UI for managing users, groups, crontabs, and more. 

<br/>

![Django console ](./images/django_admin_console.png)

<br/>

You can access it here anytime Django is running:

:star: http://127.0.0.1:8000/admin/ 

<br/>

## django dbshell

Django has a built-in shell for managing the database. You can run it in the swirl_server directory as follows:

```
./manage.py dbshell
```

## Wiping the Database

```
python manage.py flush
```

All SWIRL objects will be deleted, once you confirm.

:warning: You must create a new [SWIRL Super User](#creating-a-swirl-super-user) after doing this. 

## sqlite-web

The open source sqlite-web project offers a solid web GUI!
 
```
pip install sqlite-web
sqlite_web my_database.db                   # makes it run locally http://127.0.0.1:8080/
sqlite_web --host 0.0.0.0 my_database.db    # run it on the lan
```

Don't forget to give it the path to db.sqlite3 in swirl_server when you invoke it. 

## RabbitMQ

Rabbit comes with a built-in [web-based management UI](http://localhost:15672/#/):

:star: http://localhost:15672/#/ 

<br/>

# Database Migration

If you change most anything in swirl/models.py, you will have to perform [database migration](https://docs.djangoproject.com/en/4.0/topics/migrations/).

Detailing this process is beyond the scope of this document. For the most part all you have to do is:

```
python swirl.py migrate
```

:star: For more information: [https://docs.djangoproject.com/en/4.0/topics/migrations/](https://docs.djangoproject.com/en/4.0/topics/migrations/)

<br/>

## Notes

* Migration is usually simple/easy if you are just adding fields or changing defaults 
* It's a good idea to delete existing data before doing anything drastic like changing the name of an id or relationship - use [sqlite-web](#sqlite-web)!
* If things go wrong, delete db.sqlite3, all /migrations/, then do python manage.py flush and then repeat this process. 

:warning: Don't forget to [Create a SWIRL Super User](#creating-a-swirl-super-user) after flushing the database!

<br/>

# Configuring Django

There are many values you can configure in [swirl_server/settings.py](../swirl_server/settings.py). These include:

* Time Zone

```
TIME_ZONE = 'US/Eastern'
...
CELERY_TIMEZONE = "US/Eastern"
CELERY_TIME_ZONE = "US/Eastern"

```

* Language Settings

```
LANGUAGE_CODE = 'en-us'
```

The configuration for Celery-Beats is also here, in case you are using the [Search Expiration Service](#search-expiration-service):

```
CELERY_BEAT_SCHEDULE = {
    # Executes every hour
    'expire': { 
         'task': 'expirer', 
         'schedule': crontab(minute=0,hour='*'),
        },          
}
```

<br/>

# Configuring Celery, Beats & RabbitMQ

Celery is used to execute SWIRL federated search. It uses RabbitMQ as a result back-end for asynchronous operation. 
Both of these systems must be configured correctly.

:warning: Celery is configured in at least three locations. They must be the same! 

<br/>

1. [swirl_server/celery.py](../swirl_server/celery.py)

```
app = Celery('swirl_server', backend='rpc://', ampq='amqp://guest:guest@localhost:5672//')
```

If this is setup correctly, you should see the backend setting appear when you run Celery from the command line:

```
> transport:   amqp://guest:**@localhost:5672//
- ** ---------- .> results:     rpc://
```

2. [Django Settings](../swirl_server/settings.py):
```
CELERY_BROKER_URL = 'amqp://guest:guest@localhost:5672//'
# Celery Configuration Options
CELERY_TIMEZONE = "US/Eastern"
CELERY_TIME_ZONE = "US/Eastern"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULE = {
    # Executes every hour
    'expire': { 
         'task': 'expirer', 
         'schedule': crontab(minute=0,hour='*'),
        },          
}
```

The settings.py file also has configuration for the [Search Expiration Service](#search-expiration-service).

<br/>

# Security

## Creating a SWIRL Super User

Use the following incantation to create a super user:

```
python manage.py createsuperuser --email admin@example.com --username admin
```

If you already have an admin user, =change the password like this:

```
python manage.py changepassword admin
```

If you select a password that is too simple, Django will object. 
For more information see: [django-admin and manage.py](https://docs.djangoproject.com/en/4.0/ref/django-admin/)

:warning: SWIRL does not recommend using an easily guessable password for any production use.

<br/>

## The Django Secret Key

In swirl_server/settings.py there is a config item for a SECRET_KEY. It's not really a big deal.
If you change it, active users will have to login again. That's it.

If you want to change the one that is in the repo, do this:

```
python -c "import secrets; print(secrets.token_urlsafe())"
```

<br/>

## SWIRL User & Group Support

You can use Django's built-in authentication support, which adds User and Group objects, or implement your own. The following sections detail how to access these.

<br/>

| URL | Explanation |
| ---------------------------- | -------------------------------------------------------------------------------------- |
| /swirl/users/      | List user objects; create a new one using the form at bottom |
| /swirl/users/id/ | Retrieve user object; destroy it using the delete button; edit it using the form at bottom  |

| URL | Explanation |
| ---------------------------- | -------------------------------------------------------------------------------------- |
| /swirl/groups/      | List group objects; create a new one using the form at bottom |
| /swirl/groups/id/ | Retrieve group object; destroy it using the delete button; edit it using the form at bottom  |

<br/>

You can edit these tables using [Django Console](#django-console):

![Django console user object](./images/django_admin_console_user.png)

<br/>

For more information see: [User authentication in Django](https://docs.djangoproject.com/en/4.0/topics/auth/)

<br/>

## Securing RabbitMQ

As shown in the previous section "Configuring Celery & RabbitMQ", the Celery configuration files specify the username and password of the RabbitMQ user to use when connecting. By default, it is set to guest:guest.

<br/>

To secure RabbitMQ:

* Create a new RabbitMQ user with rights to access virtually, and an appropriately secure password
* Enter this in form username:password in [swirl_server/swirl_server/celery.py](../swirl_server/celery.py) and [swirl_server/swirl/tasks.py](../swirl/tasks.py)
* Restart Rabbit, Celery and Producer as described in the [Installation Guide](INSTALLATION_GUIDE.md#start-services)

<br/>

# Troubleshooting

## Debug Mode

By default, SWIRL ships in production mode. 
To put Django into debug mode, modify [swirl_server/settings.py](../swirl_server/settings.py), changing:

```
DEBUG = False
```

...to...

```
DEBUG = True
```

Then restart django. Debug mode provides far more debugging information.

<br/>

## Log Information

All SWIRL services write log files in the logs folder under swirl_server. 

Here's what to expect in each:

<br/>

| Logfile | Details | Notes | 
| ----------- | -------- | ----- |
| logs/rabbit.log | Contains infrastructural issues, not often useful | Advanced users try the [rabbitmq web UI](#1-rabbitmq) |
| logs/django.log | Contains the log of the django container, which includes all http activity API calls. | Not involved in federation |
| logs/consumer.log | Contains the log of the swirl consumer | Very involved in federation, look here first if there are errors in search.status | 
| logs/celery-worker.log | Contains the log of celery taskss | Very involved in federation, look for detailed info regarding errors in search.status or partial results |
| logs/celery-beat.log | Contains the log of the celery beat service, which is only used by the [Search Expiration Service](#search-expiration-service) | Look here for issues with expiration not working | 

<br/>

:key: From the SWIRL root directory, try running:

```
tail -f logs\*.log
```

This will show you the collected, latest output of all logs, continuously.

<br/>

<br/>

# Further Reading

:small_blue_diamond: [User Guide](USER_GUIDE.md))
:small_blue_diamond: [Developer Guide](DEVELOPER_GUIDE.md)

<br/>

<br/>

# Get Support

Please email [swirl-support@probstein.com](mailto:swirl-support@probstein.com) for support.

<br/>