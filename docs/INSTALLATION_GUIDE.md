![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL INSTALLATION GUIDE

## Table of Contents

:small_blue_diamond: [Assumptions](#assumptions)<br/>
:small_blue_diamond: [Install Packages](#install-packages)<br/>
:small_blue_diamond: [Start Services](#start-services): [OS/X and Linux](), [Windows]()<br/>
:small_blue_diamond: [Daemonization]()<br/>
:small_blue_diamond: [Get Support](#get-support)<br/>

<br/>

# Assumptions

:star: [Python 3.9 or later](https://www.python.org/) must be installed correctly. 

It should run if you type python in a terminal window. You should not have to run python3. Note that this is mostly an issue for OS/X users. 
For more information see: [The right and wrong way to set Python 3 as default on a Mac](https://opensource.com/article/19/5/python-3-default-mac) 

<br/>

# Install Packages:

:star: [Homebrew Installation](https://docs.brew.sh/Installation)

```
brew update
brew install rabbitmq
```

If you have issues this article may help [https://osxdaily.com/2021/02/13/how-update-homebrew-mac/](https://osxdaily.com/2021/02/13/how-update-homebrew-mac/)

<br/>

```
pip install requests
pip install django
pip install django_restframework
pip install django-celery-beat
pip install django-rest-swagger
pip install Celery
pip install pika
pip install elasticsearch
pip install --upgrade jsonpath-ng
pip install pyyaml
pip install whitenoise
pip install daphne
pip install textblob
pip install spacy
python -m spacy download en_core_web_md
```

:warning: Don't forget to restart your shell after all these installations.

<br/>

# Get SWIRL:

## Clone the SWIRL Repo https://github.com/sidprobstein/swirl-search 

This requires [git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git):

```
git clone https://github.com/sidprobstein/swirl-search
```

This should return:

```
Cloning into 'swirl-search'...
remote: Enumerating objects: 1118, done.
remote: Counting objects: 100% (1118/1118), done.
remote: Compressing objects: 100% (983/983), done.
remote: Total 1118 (delta 687), reused 543 (delta 121), pack-reused 0
Receiving objects: 100% (1118/1118), 37.80 MiB | 50.39 MiB/s, done.
Resolving deltas: 100% (687/687), done.
```

You can optionally specify the name of the subdirectory to clone into - otherwise it will default to swirl-search.

<br/>

You can also use various desktop apps to clone the report - here are a few:

* [Github Desktop](https://desktop.github.com/)
* [GitKraken](https://www.gitkraken.com/) - requires $, but is awesome

<br/>

:key: You will have to login with your github username and password.

<br />

:key: OS/X users should install [X-Code](https://apps.apple.com/us/app/xcode/id497799835?mt=12) to get git. 
Make sure you select the option to install command-line tools when prompted.

<br />

# Setup SWIRL

:warning: This step is required the first time you install SWIRL. 

```
python swirl.py setup
```

The output should be similar to this:

```
Setting Up SWIRL:
Checking Migrations:
No changes detected

Migrating:

Operations to perform:
  Apply all migrations: admin, auth, contenttypes, django_celery_beat, sessions, swirl
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  Applying admin.0002_logentry_remove_auto_add... OK
  Applying admin.0003_logentry_add_action_flag_choices... OK
  Applying contenttypes.0002_remove_content_type_name... OK
  Applying auth.0002_alter_permission_name_max_length... OK
  Applying auth.0003_alter_user_email_max_length... OK
  Applying auth.0004_alter_user_username_opts... OK
  Applying auth.0005_alter_user_last_login_null... OK
  Applying auth.0006_require_contenttypes_0002... OK
  Applying auth.0007_alter_validators_add_error_messages... OK
  Applying auth.0008_alter_user_username_max_length... OK
  Applying auth.0009_alter_user_last_name_max_length... OK
  Applying auth.0010_alter_group_name_max_length... OK
  Applying auth.0011_update_proxy_permissions... OK
  Applying auth.0012_alter_user_first_name_max_length... OK
  Applying django_celery_beat.0001_initial... OK
  Applying django_celery_beat.0002_auto_20161118_0346... OK
  Applying django_celery_beat.0003_auto_20161209_0049... OK
  Applying django_celery_beat.0004_auto_20170221_0000... OK
  Applying django_celery_beat.0005_add_solarschedule_events_choices... OK
  Applying django_celery_beat.0006_auto_20180322_0932... OK
  Applying django_celery_beat.0007_auto_20180521_0826... OK
  Applying django_celery_beat.0008_auto_20180914_1922... OK
  Applying django_celery_beat.0006_auto_20180210_1226... OK
  Applying django_celery_beat.0006_periodictask_priority... OK
  Applying django_celery_beat.0009_periodictask_headers... OK
  Applying django_celery_beat.0010_auto_20190429_0326... OK
  Applying django_celery_beat.0011_auto_20190508_0153... OK
  Applying django_celery_beat.0012_periodictask_expire_seconds... OK
  Applying django_celery_beat.0013_auto_20200609_0727... OK
  Applying django_celery_beat.0014_remove_clockedschedule_enabled... OK
  Applying django_celery_beat.0015_edit_solarschedule_events_choices... OK
  Applying sessions.0001_initial... OK
  Applying swirl.0001_initial... OK

Collecting Statics:

172 static files copied to '/Users/sid/Code/swirl_server/static'.
```
Report any errors [to support](mailto:swirl-support@probstein.com).

<br/>

## Create the Admin Account:

:warning: This step is required for your security, and should only take a minute. :-) 
You should only have to do it the first time you install SWIRL.

<br />

```
python manage.py createsuperuser --email admin@example.com --username admin
```

If the password you select is very simple, you will be asked to confirm it. 
We won't tell. :-)

<br />

:lock: Remember the password, you'll need it during the Quick Start. 
It's easy to [Reset the Admin Password](), if needed.

<br />

# Start Services

```
python swirl.py start
```

This should produce something similar to this:

```
##S#W#I#R#L##1#0################################################################

Starting: rabbitmq -> rabbitmq-server ... Ok, pid: 27434
Starting: django -> python manage.py runserver ... Ok, pid: 27482
Starting: celery-worker -> celery -A swirl_server worker --loglevel=info ... Ok, pid: 27515
Starting: celery-beats -> celery -A swirl_server beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler ... Ok, pid: 27542
Updating .swirl...Ok

  PID TTY           TIME CMD
27434 ttys000    0:00.00 /bin/sh /opt/homebrew/sbin/rabbitmq-server
27482 ttys000    0:00.29 python manage.py runserver
27515 ttys000    0:01.03 /Users/sid/.pyenv/versions/3.9.2/bin/python /Users/sid/.pyenv/versions/3.9.2/bin/celery -A swirl_server worker --loglevel=info
27542 ttys000    0:00.59 /Users/sid/.pyenv/versions/3.9.2/bin/python /Users/sid/.pyenv/versions/3.9.2/bin/celery -A swirl_server beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

# Go to http://localhost:8000/swirl/

<br />

![SWIRL Front Page](./images/swirl_frontpage.png)

<br />

### :1st_place_medal: Congratulations, you have successfully installed and started SWIRL!

<br />

<br />

# Microsoft Windows

## TO DO

### :1st_place_medal: Congratulations, you have successfully installed and started SWIRL!

<br/>

<br/>

# Further Reading

:small_blue_diamond: [Quick Start](QUICK_START.md) <br/>
:small_blue_diamond: [User Guide](USER_GUIDE.md))
:small_blue_diamond: [Developer Guide](DEVELOPER_GUIDE.md)
:small_blue_diamond: [Admin Guide](ADMIN_GUIDE.md)

<br/>

<br/>

# Get Support

Please email [swirl-support@probstein.com](mailto:swirl-support@probstein.com) for support.
