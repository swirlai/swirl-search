---
layout: default
title: Installation - Community
nav_exclude: true
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# Installation Guide - Community Edition

{: .warning }
This document applies only to SWIRL AI Connect, Community Edition. 

{: .warning }
SWIRL's start-up process no longer starts `redis`.  You must now have `redis` installed *and running* before starting SWIRL. Refer to [Install Redis](https://redis.io/docs/latest/operate/oss_and_stack/install/install-redis/) for more information.

# System Requirements

* Platform - Ubuntu, RHEL, or OS/X; Microsfot Windows is *not* supported for local installation due to Celery support
* 8+ VCPU, 16+ GB of memory
* At least 500 GB of free disk space
* Python 3.11 or newer

## MacOS

* Python 3.12.x (or latest stable) with `pip`
    * If necessary, modify the system PATH so that Python runs when you type `python` at the Terminal (not `python3`)
    * [venv](https://docs.python.org/3/library/venv.html) (*optional*)
    * [pyenv](https://github.com/pyenv/pyenv) (*optional*)
* [Homebrew](https://brew.sh/) installed and updated
* Redis installed:
 ``` shell
 brew install redis
 ```
* jq installed:
``` shell
brew install jq
```

## Linux

* Python 3.12.x (or latest stable) with `pip`
* Redis and jq installed:
``` shell
sudo apt install jq redis-server -y
```

## PostgreSQL (optional)

If you wish to use PostgreSQL as a data source or as the SWIRL back-end database:

1. Install [PostgreSQL](https://www.postgresql.org/)

2. Modify the system PATH so that `pg_config` from the PostgreSQL distribution is accessible from the command line

3. Install `psycopg2` using `pip`:
``` shell
pip install psycopg2
```

## Installing SWIRL AI Connect

* Clone the repo:

``` shell
git clone https://github.com/swirlai/swirl-search
cd swirl-search
```

* To install SWIRL on MacOS, execute this command from the Console:

``` shell
./install.sh
```

* To install SWIRL on Linux, execute this command from the Console:

``` shell
apt-get update --allow-insecure-repositories -y && apt-get install apt-file -y && apt-file update && apt-get install -y python3-dev build-essential
./install.sh
```

* If there are problems running `install.sh`, proceed manually:

``` shell
pip install -r requirements.txt
python -m spacy download en_core_web_lg
python -m nltk.downloader stopwords
python -m nltk.downloader punkt
```

{: .warning }
Issues with certifications on OS/X? See: [urllib and "SSL: CERTIFICATE_VERIFY_FAILED" Error](https://stackoverflow.com/questions/27835619/urllib-and-ssl-certificate-verify-failed-error/42334357#42334357)

## Setup SWIRL

* Execute the following command from the Console to setup SWIRL:

``` shell
python swirl.py setup
```

## Setup RAG

* To enable SWIRL's Real-Time Retrieval Augmented Generation (RAG) on your `localhost`, run the following commands from the Console before installing the Galaxy UI:
``` shell
export MSAL_CB_PORT=8000
export MSAL_HOST=localhost
```

For more information, refer to the [RAG Configuration guide](RAG-Guide.html).

## Install the Galaxy UI

{: .warning }
To install the Galaxy UI, you must have the latest [Docker app](https://docs.docker.com/get-docker/) for MacOS or Linux installed and running locally.


* To install Galaxy, execute the following command the Console (with the Docker app running):

``` shell
./install-ui.sh
```

{: .highlight }
The Galaxy UI components should be installed only *after* running the `./install.sh` and `python swirl.py setup` commands.

## Start SWIRL

* Execute the following command from the Console to start SWIRL:

``` shell
python swirl.py start
```

## Open the SWIRL Homepage

* Enter this URL into a browser: <http://localhost:8000/swirl/>

The following page should appear:

![SWIRL Homepage](images/swirl_frontpage.png)

## Open the Galaxy UI

* Open this URL with a browser: <http://localhost:8000> (or <http://localhost:8000/galaxy/>)

If the search page appears, click `Log Out` at the top, right. The SWIRL login page will appear:

![SWIRL Login](images/swirl_login-galaxy_dark.png)

* Enter the username `admin` and password `password`, then click `Login`.

* Enter a search in the search box and press the `Search` button. Ranked results appear in just a few seconds:

![SWIRL Results](images/swirl_results_no_m365-galaxy_dark.png)

* Click the `Generate AI Insight` button to RAG using the most relevant results, if you have specified an OpenAI key as noted earlier.

![SWIRL Results with RAG](images/swirl_rag_pulmonary_1.png)

* Click the profile avatar in the upper right corner of the Galaxy UI. Then click [Manage SWIRL](http://localhost:8000/swirl/) to explore the rest of SWIRL's features.

* To view the raw result JSON, click `Search` under the API section of the `Manage SWIRL` page linked above, or open <http://localhost:8000/swirl/search/>

The most recent Search object will be displayed at the top. Click on the `result_url` link to view the full JSON Response. For example:

![SWIRL JSON response](images/swirl_results_mixed_1.png)

* Read the [SWIRL User Guide](User-Guide.html) for additional information.
