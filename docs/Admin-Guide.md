---
layout: default
title: Admin Guide
nav_order: 11
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# Admin Guide 

{: .warning }
This document applies to all SWIRL Editions. 

# Configuring SWIRL AI Connect

## Configuring the Environment

SWIRL uses `django-environ` to load important values such as hostname from a file called `.env`.

The file `.env.dist` contains expected defaults. If no `.env` file is created, then the `install.sh` script copy this file to `.env` prior to startup.

``` shell
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost
PROTOCOL=http
SWIRL_EXPLAIN=True
SQL_ENGINE=django.db.backends.sqlite3
SQL_DATABASE=db.sqlite3
SQL_USER=user
SQL_PASSWORD=password
SQL_HOST=localhost
SQL_PORT=5432
MICROSOFT_CLIENT_ID=''
MICROSOFT_CLIENT_SECRET=''
MICROSOFT_REDIRECT_URI=''
OPENAI_API_KEY=
```

To configure a SWIRL server to listen on a particular port, hostname, via HTTPS, etc., modify the `.env` file and then restart SWIRL. There should never be a `.env` file in the SWIRL repo, and when updating SWIRL to a new version, no migration of these settings should be needed. They remain in `.env`.

The `SWIRL_EXPLAIN` item determines if SWIRL will show the [explain structure](Developer-Guide.html#understand-the-explain-structure) or not.

The `SECRET_KEY` is actually a [salt](https://en.wikipedia.org/wiki/Salt_(cryptography)) used by Django. SWIRL recommends [generating a new one](https://docs.djangoproject.com/en/4.1/topics/signing/) for production use.

## Creating a SWIRL Super User

To start over with a new database, delete or rename the `db.sqlite3` file. Then run this command:

``` shell
python swirl.py setup
```

This will create a new, blank database. To create a Super User, run the following command:

``` shell
python manage.py createsuperuser --email admin@example.com --username admin
```

## Changing the Super User Password

If you already have an `admin` user, you can change the password with this command:

``` shell
python manage.py changepassword admin
```

If you select a password that is too simple, Django will object. 
For more information see: [django-admin and manage.py](https://docs.djangoproject.com/en/4.0/ref/django-admin/)

### Using the Django Admin

To use the Django Admin to change the Super User Password:

1. Go to the SWIRL homepage. For example [http://localhost:8000/swirl](http://localhost:8000/swirl)

2. Click the `CHANGE PASSWORD` link at the top left:

![Django Admin Change Password](images/try-it-adm-pwd-3.png)

3. This should bring up the password change screen:

![Django Admin Change Password](images/try-it-adm-pwd-4.png)

Don't forget to click `CHANGE MY PASSWORD` at the end.

## Adding Normal Users

You may use the Django Admin UI to add users:

```
http://localhost:8000/admin/
```

![Django Admin - Users](images/django_admin_console_user.png)

This isn't necessary if using OpenID Connect to provision users. Please refer to the [AI Connect Guide](AI-Connect.html#openid-connect) for more information.

## Permissioning Normal Users

There are four permissions -- `add`, `change`, `delete`, and `view` -- for each of the core SWIRL objects: `SearchProviders`, `Search`, `Result`, and `Query Transform`.

![Django Admin - Permissions](images/django_admin_console_permissions.png)

<br/>

The following table shows how to configure these for various scenarios:

| Scenario | SearchProvider | Search | Results | Query Transform |
| ---------- | ---------- | ---------- | ---------- | ---------- |
| Admin       | ALL            | ALL    | ALL     | ALL |
| Search ONLY | NONE           | Add    |         |     | 
| Result ONLY | NONE           | NONE   | View    |     | 
| Search & View Results | NONE | Add, View | Add, View | Add, View |
| Manage Search including re-run | NONE | ALL | ALL | ALL |
| SearchProvider Admin | ALL | Add | View | View |

## Object Ownership

SearchProvider, Search, Result, and Query Transform objects are owned by, and private to, the Django user who creates them.

## Shared SearchProviders and Query Transformations

SWIRL supports shared SearchProviders (v. 1.7) and Query Transformations (v. 2.0). These defaults to "false" for all Users, except the Django Super User (`admin`) which defaults to "true". This makes it easy to add users without having to duplicate SearchProviders or Query Transformations. 
  
For installations with a large number of users, create groups with the desired permissions first, then assign each User to the appropriate group.

# Deploying SWIRL for Production Use

The SWIRL application is designed to be deployed behind a reverse-proxy. There are many reasons for this:

* Scalability: a reverse-proxy allows for the horizontal scaling of SWIRL. By deploying multiple SWIRL application VMs behind a reverse-proxy, the incoming connection demands can be handled by the reverse-proxy then disseminated to a pool of backend SWIRL servers. If demand for SWIRL increases, additional VMs can be provisioned on-demand. These VMs can also be turned down when the traffic drops below certain thresholds to save on hosting costs.

* Security: Offloading the SSL/TLS overhead to a dedicated public endpoint such as a reverse-proxy alleviates the CPU load on the application server that serves up SWIRL.

* Performance: Using a reverse-proxy separates the task of serving up static content from the application server. This makes it possible to deploy SWIRL with a content delivery network (CDN) which places static content close to the end user for a faster SWIRL experience.

* Availability: a reverse-proxy adds resiliency to any setup by spreading traffic across a backend pool of SWIRL servers. The reverse-proxy monitors the pool of available backend servers and detects and removes failed servers from a pool of available ones.

Popular reverse-proxy projects/products include [HA Proxy](https://www.haproxy.org/), [Nginx](https://nginx.org/en/), [Azure Application Gateway](https://azure.microsoft.com/en-us/products/application-gateway) and [AWS Application Load Balancer](https://aws.amazon.com/elasticloadbalancing/application-load-balancer/). 

[Contact support](#support) to discuss this topic anytime.

# Upgrading SWIRL

{: .warning }
Please [contact support](#support) for instructions on upgrading Docker containers!

1. Update the `swirl-search` repository:
``` shell
git pull
```

2. Run the install script:
``` shell
./install.sh
```

3. Setup SWIRL:
``` shell
python swirl.py setup
```

4. If upgrading Galaxy UI, execute:
``` shell
./install-ui.sh
```

4. Restart SWIRL:
``` shell
python swirl.py restart
```

{: .highlight }
Consult the [release notes](https://github.com/swirlai/swirl-search/releases) for more information on each release.

## Resetting Prompts

To reset AI prompts to their default state, run the following command:

`python swirl.py reload_ai_prompts`

This will restore the system prompts to the "factory" settings. New prompts are not impacted.

# Configuring SWIRL

SWIRL uses the following configuration items, defined in the [`swirl_server/settings.py`](https://github.com/swirlai/swirl-search/blob/main/swirl_server/settings.py):

| Configuration Item | Explanation | Example |
| ---------- | ---------- | ---------- |
| CELERY_BEATS_SCHEDULE | Defines the schedule for the [Search Expiration Service](#search-expiration-service) and [Search Subscriber Service](#search-subscriber-service) | See the linked sections. |
| SWIRL_DEFAULT_QUERY_LANGUAGE | Determines which stopword dictionary is loaded | `SWIRL_DEFAULT_QUERY_LANGUAGE = 'english'` | 
| SWIRL_TIMEOUT | The number of seconds to wait until declaring federation complete, and terminating any connectors that haven't responded | `SWIRL_TIMEOUT = 10` |
| SWIRL_SUBSCRIBE_WAIT | The number of seconds to wait before timing out and reporting an error when [updating a search](Developer-Guide.html#update-a-search) | `SWIRL_SUBSCRIBE_WAIT = 20` |
| SWIRL_DEDUPE_FIELD | The field to use when [detecting and removing duplicates](Developer-Guide.html#detect-and-remove-duplicate-results) with the `DedupeByFieldPostResultProcessor` | `SWIRL_DEDUPE_FIELD = 'url'` |
| SWIRL_DEDUPE_SIMILARITY_MINIMUM | The minimum similarity score that constitutes a duplicate, when [detecting and removing duplicates](Developer-Guide.html#detect-and-remove-duplicate-results) with the `DedupeBySimilarityPostResultProcessor` | `SWIRL_DEDUPE_SIMILARITY_MINIMUM = 0.95` |
| SWIRL_DEDUPE_SIMILARITY_FIELDS | A list of the fields to use when determining the similarity between documents when [detecting and removing duplicates](Developer-Guide.html#detect-and-remove-duplicate-results) with the `DedupeBySimilarityPostResultProcessor` | `SWIRL_DEDUPE_SIMILARITY_FIELDS = ['title', 'body']` | 
| SWIRL_RELEVANCY_CONFIG | Defines the relevancy score weights for important fields | See below |
| SWIRL_MAX_MATCHES | Configures the maximum number of matches for any given result, before being cut-off. This helps protect against favoring very long articles. | `SWIRL_MAX_MATCHES = 5` |
| SWIRL_MIN_SIMILARITY | Configures the minimum threshold at which a query hit in a result will be scored. Lower values will increase recall but lower precision. | `SWIRL_MIN_SIMILARITY = 0.54` |
| SWIRL_EXPLAIN | Configures the delivery of relevancy explain structures, in Mixed responses | `SWIRL_EXPLAIN = false` | 

### Example SWIRL_RELEVANCY_CONFIG

``` shell
SWIRL_RELEVANCY_CONFIG = {
    'title': {
        'weight': 1.5
    },
    'body': {
        'weight': 1.0
    },
    'author': {
        'weight': 1.0
    }
}
``` 

Note that all configuration names must be UPPER_CASE per the [django settings convention](https://docs.djangoproject.com/en/4.1/topics/settings/).

# Search Expiration Service

The [Expirer](https://github.com/swirlai/swirl-search/blob/main/swirl/expirer.py) service can automatically delete Search and their associated (linked) Result objects after a specified period of time - to ensure SWIRL doesn't retain everything ever searched.

## Service Frequency

Although you may specify various expiration settings for SWIRL Search and associated Result objects, the service to expire them runs on a regular schedule. 

By default, this service runs every hour. The frequency is defined in the [Django settings](https://github.com/swirlai/swirl-search/blob/main/swirl_server/settings.py):

``` shell
CELERY_BEAT_SCHEDULE = {
    # Executes every hour
    'expire': { 
         'task': 'expirer', 
         'schedule': crontab(minute=0,hour='*'),
        },          
}
```

Temporary changes can also be made via the Django Console here:

```
http://localhost:8000/admin/django_celery_beat/crontabschedule/ 
```
![Django console crontab page](images/django_admin_console_crontab.png)

{: .warning }
SWIRL AI Connect, Enterprise Edition, supports a 5 minute service expiration schedule. Please [contact support](#support) for more information.

{: .warning }
If you change the `crontab` entry in the database and don't change the `CELERY_BEAT_SCHEDULE` as well, that schedule will be restored if/when you restart SWIRL.

# Search Subscriber Service

When one or more Search objects [have the subscribe property set to True](Developer-Guide.html#subscribe-to-a-search), SWIRL will periodically [update that Search](Developer-Guide.html#update-a-search).

By default, the Subscriber service runs every four hours. The frequency is defined in the [Django settings](https://github.com/swirlai/swirl-search/blob/main/swirl_server/settings.py):

``` shell
CELERY_BEAT_SCHEDULE = {
    # Executes every four hours
    'subscribe': { 
         'task': 'subscriber', 
         'schedule': crontab(minute=0,hour='*/4'),   # minute='*/10'
        },          
}
```

Temporary changes can also be made via the Django Console here:

```
http://localhost:8000/admin/django_celery_beat/crontabschedule/
```

![Django console crontab page](images/django_admin_console_crontab.png)

{: .warning }
If you change the `crontab` entry in the database and don't change the `CELERY_BEAT_SCHEDULE` as well, that schedule will be restored if/when you restart SWIRL.

# Service Startup & Daemonization

## Using `swirl.py`

For normal operations, use `swirl.py` to start, stop or restart services. It is located in SWIRL's install directory (along with `manage.py`).

* To start services:

``` shell
python swirl.py start
```

One or more services may be specified, e.g.:

``` shell
python swirl.py start celery-beats
```

* To check the status of SWIRL:

``` shell
python swirl.py status
```

SWIRL will report the current running services, and their pids:

``` shell
__S_W_I_R_L__2_._6______________________________________________________________

Service: django...RUNNING, pid:1620
Service: celery-worker...RUNNING, pid:1625

  PID TTY           TIME CMD
 1620 ttys000    0:13.26 /Users/erikspears/.pyenv/versions/3.11.5/bin/python3.11 /Users/erikspears/.pyenv/versions/3.11.5/bin/daphne -b 0.0.0.0 -p 8000 swirl_server.asgi:application
 1625 ttys000    0:40.70 /Users/erikspears/.pyenv/versions/3.11.5/bin/python3.11 /Users/erikspears/.pyenv/versions/3.11.5/bin/celery -A swirl_server worker --loglevel INFO

Command successful!
```

* To terminate services:

``` shell
python swirl.py stop
```

* To restart services:

``` shell
python swirl.py restart
```

One or more services may be specified, e.g.:

``` shell
python swirl.py restart celery-worker consumer
```

* To get help:

``` shell
python swirl.py help
```

## Customizing

The services invoked by `swirl.py` are defined in [swirl/services.py](https://github.com/swirlai/swirl-search/blob/main/swirl/services.py). 

Modify the list to start celery-beats automatically.

# Changing the Galaxy Logos and Branding

To change the logo in SWIRL Galaxy, for both the search and chat pages, along with other control labels:

* Go to [the SWIRL home page](http://localhost:8000/admin/)

![SWIRL home page](./images/admin.png)

* Click the "admin" link as shown. This will take you to the admin UI:

![SWIRL admin UI](./images/admin_branding.png)

* Click "Upload a Branding Configuration" as shown. This will take you to the Branding Configuration page:

![SWIRL branding configuration](./images/branding_config.png)

* Fill out the form. "Name" is required, in addition to at least one other item. To change the logo, upload a light mode image. 

The following table describes the remaining options:

| Item | Galaxy Location | Default | 
| ---- | --------------- | ------- | 
| Name | Not shown | N/A | 
| Search button label | On the button | SEARCH |
| Search bar placeholder | In the search box | What are you searching for today? |
| AI Response label | Below the search box | Generate AI Response |  
| Select items label | Below the paging control | Select Items | 

* Click the "Submit" button to save the branding configuration.

* Refresh your browser to see the changes in Galaxy.

Note that this may launch a new RAG or chat session.

### Logo File Requirements

* Image file format: png
* Dimensions: 818 x 214
* At least 30 px whitespace around the margin of the logo

Note also that only one branding configuration can be active at a time.

# Managing Django Users

## Django Admin

Most users can be managed through the Django Admin, which is located here:

```
http://localhost:8000/admin/
```

View this [Youtube Video on Django Administration](https://youtu.be/jCihWwrwS-w?si=QVtZXR7j9PRszQW1&t=174) for more information.

## To Change a User's Password

``` shell
python manage.py changepassword <user_name>
```

# Management Tools

## Django Console

Django has a built-in web UI for managing users, groups, crontabs, and more. 

![Django console ](images/django_admin_console.png)

The URL is: [http://localhost:8000/admin/](http://localhost:8000/admin/) 

View these [YouTube Videos on how to use Django Admin](https://www.youtube.com/watch?v=c_S0ZQs81XQ&list=PLOLrQ9Pn6cazhaxNDhcOIPYXt2zZhAXKO) for more information.

## Django dbshell

Django has a built-in shell for managing the database. You can run it in the `swirl-search` directory as follows:

``` shell
./manage.py dbshell
```

## Wiping the Database

``` shell
python manage.py flush
```

All SWIRL objects will be deleted, once you confirm.

{: .warning }
You must create a new [SWIRL Super User](#creating-a-swirl-super-user) after doing this.

## `sqlite-web`

The open source `sqlite-web` project offers a solid web GUI!
 
``` shell
pip install sqlite-web
sqlite_web my_database.db                   # makes it run locally http://localhost:8080/
sqlite_web --host 0.0.0.0 my_database.db    # run it on the lan
```

Don't forget to give it the path to `db.sqlite3` in `swirl-search` when you invoke it.

# Database Migration

If you change most anything in `swirl/models.py`, you will have to perform a database migration. Detailing this process is beyond the scope of this document. For the most part, all you have to do is:

``` shell
python swirl.py migrate
```

For more information: [https://docs.djangoproject.com/en/4.0/topics/migrations/](https://docs.djangoproject.com/en/4.0/topics/migrations/)

* Migration is usually simple/easy if you are just adding fields or changing defaults 
* It's a good idea to delete existing data before doing anything drastic like changing the name of an `id` or relationship - use `sqlite-web` (see above)!
* If things go wrong:
    * Delete `db.sqlite3`
    * Delete all `swirl/migrations/`
    * Run: `python manage.py flush`
    * Then, repeat this process

{: .warning }
Don't forget to [create a SWIRL Super User](#creating-a-swirl-super-user) after flushing the database!

# Configuring Django

There are many values you can configure in [`swirl_server/settings.py`](https://github.com/swirlai/swirl-search/blob/main/swirl_server/settings.py). 

These include:
* Hostname
* Protocol

``` shell
# PUT the FQDN first in the list below
ALLOWED_HOSTS = ['localhost']
HOSTNAME = ALLOWED_HOSTS[0]
PROTOCOL = 'http'
```

{: .highlight }
The FQDN that SWIRL should listen on must be the first entry in the `ALLOWED_HOST` list.

* Time Zone

``` shell
TIME_ZONE = 'US/Eastern'
...
CELERY_TIMEZONE = "US/Eastern"
CELERY_TIME_ZONE = "US/Eastern"
```

* Celery Beats

The configuration for Celery-Beats is also here, in case you are using the [Search Expiration Service](#search-expiration-service) or the [Search Subscription Service](#search-subscriber-service):

``` shell
CELERY_BEAT_SCHEDULE = {
    # Executes every hour
    'expire': { 
         'task': 'expirer', 
         'schedule': crontab(minute=0,hour='*'),
        },          
}
```

* Database Provider

``` shell
DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE", "django.db.backends.sqlite3"),
        "NAME": os.environ.get("SQL_DATABASE", BASE_DIR / "db.sqlite3"),
        "USER": os.environ.get("SQL_USER", "user"),
        "PASSWORD": os.environ.get("SQL_PASSWORD", "password"),
        "HOST": os.environ.get("SQL_HOST", "localhost"),
        "PORT": os.environ.get("SQL_PORT", "5432"),
    }
}
```

To configure PostgreSQL as the Django back-end:

1. Install PostgreSQL (if not already installed)
2. Ensure that `pg_config` from the PostgreSQL distribution is in the `PATH` and runs from the command line
3. Install the `psycopg2` driver:
``` shell
pip install psycopg2
```
Then follow the appropriate section of [Configuring Django Database Back-Ends](https://docs.djangoproject.com/en/4.1/ref/databases/).

4. Uncomment the PostgreSQL Connector in the following modules:
* [`swirl.connectors.__init__.py`](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/__init__.py)
``` shell
# uncomment this to enable PostgreSQL
# from swirl.connectors.postgresql import PostgreSQL
```
* [`swirl.models.py`](https://github.com/swirlai/swirl-search/blob/main/swirl/models.py)
``` shell
CONNECTOR_CHOICES = [
    ('ChatGPT', 'ChatGPT Query String'),
    ('RequestsGet', 'HTTP/GET returning JSON'),
    ('RequestsPost', 'HTTP/POST returning JSON'),
    ('Elastic', 'Elasticsearch Query String'),
    ('OpenSearch', 'OpenSearch Query String'),
    # Uncomment the line below to enable PostgreSQL
    # ('PostgreSQL', 'PostgreSQL'),
    ('BigQuery', 'Google BigQuery'),
    ('Sqlite3', 'Sqlite3'),
    ('M365OutlookMessages', 'M365 Outlook Messages'),
    ('M365OneDrive', 'M365 One Drive'),
    ('M365OutlookCalendar', 'M365 Outlook Calendar'),
    ('M365SharePointSites', 'M365 SharePoint Sites'),
    ('MicrosoftTeams', 'Microsoft Teams'),
]
```

# Configuring Celery & Redis

Celery is used to execute a SWIRL metasearch. It uses Redis as a result back-end for asynchronous operation. Both of these systems must be configured correctly.

{: .warning }
Celery is configured in at least three locations. They must be the same! 

1. [`swirl_server/celery.py`](https://github.com/swirlai/swirl-search/blob/main/swirl_server/celery.py)
``` shell
app = Celery('swirl_server', 
             broker='redis://localhost:6379/0', 
             backend='redis://localhost:6379/0')
```
If this is setup correctly, you should see the backend setting appear when you run Celery from the command line:
``` shell
> transport:   amqp://guest:**@localhost:6379//
- ** ---------- .> results:     rpc://
```

2. [`swirl_server/settings.py`](https://github.com/swirlai/swirl-search/blob/main/swirl_server/settings.py) (Django settings):

``` shell
# Celery Configuration Options
CELERY_TIMEZONE = 'US/Eastern'
CELERY_TIME_ZONE = 'US/Eastern'
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BEAT_SCHEDULE = {
    # Executes every hour
    'expire': {
         'task': 'expirer',
         'schedule': crontab(minute=0,hour='*'),
        },
    # Executes every four hours
    'subscribe': {
         'task': 'subscriber',
         'schedule': crontab(minute=0,hour='*/4'),   # minute='*/10'
        },
}
CELERY_BROKER_URL = 'redis://localhost:6379/0'
# CELERY_BROKER_URL = 'amqp://guest:guest@localhost:6379//'

CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
# CELERY_RESULT_BACKEND='rpc://'
```

The `settings.py` file also contains the configuration for the [Search Expiration Service](#search-expiration-service) and the [Search Subscription Service](#search-subscriber-service).

# Security

## The Django Secret Key

In `swirl_server/settings.py`, there is a configuration item for a `SECRET_KEY`. This is not really a big deal. If you change it, active users will have to login again. That's it.

To change the one that is in the repo:

``` shell
python -c "import secrets; print(secrets.token_urlsafe())"
```

Read [more about the Django Secret Key](https://stackoverflow.com/questions/7382149/whats-the-purpose-of-django-setting-secret-key)

## SWIRL User & Group Support

You can use Django's built-in authentication support, which adds User and Group objects, or implement your own. The following sections detail how to access these.

| URL | Explanation |
| ---------- | ---------- |
| /swirl/users/      | List User objects; create a new one using the form at bottom |
| /swirl/users/id/ | Retrieve a User object; destroy it using the Delete button; edit it using the form at bottom  |

| URL | Explanation |
| ---------- | ---------- |
| /swirl/groups/      | List Group objects; create a new one using the form at bottom |
| /swirl/groups/id/ | Retrieve a Group object; destroy it using the Delete button; edit it using the form at bottom  |

You can also edit these tables using the [Django Console](#django-console):

![Django console user object](images/django_admin_console_user.png)

For more information, see: [User authentication in Django](https://docs.djangoproject.com/en/4.0/topics/auth/)