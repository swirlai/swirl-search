<h1> &nbsp; SWIRL SEARCH <img alt='SWIRL Logo' src='https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_logo_notext_200.jpg' width=38 align=left /></h1>

[![Slack](https://img.shields.io/badge/slack--channel-blue?logo=slack)](https://join.slack.com/t/swirlsearch/shared_invite/zt-1n7xophls-F4SzYecGniOFB95xI6WlAw)
[![Newsletter](https://img.shields.io/badge/newsletter-blue?logo=revue)](https://groups.google.com/g/swirl-announce)


SWIRL adapts and distributes queries to any data source with searchable API - search engines, databases, noSQL engines, cloud/SaaS services etc - and uses AI ([Large Language Models](https://techcrunch.com/2022/04/28/the-emerging-types-of-language-models-and-why-they-matter/)) to re-rank the unified results *without* extracting and indexing *anything*. It's intended for use by developers and data scientists who want to solve multi-silo search problems from enterprise search to new monitoring & alerting solutions that push information to users continuously.

![Federated search diagram](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/federation_diagram.png)

Built on the python/django/rabbit stack, SWIRL includes connectors to [elastic](https://www.elastic.co/cn/downloads/elasticsearch), apache [solr](https://solr.apache.org/), [PostgreSQL](https://www.postgresql.org/), [Google BigQuery](https://cloud.google.com/bigquery) plus generic HTTP/GET/JSON with configurations for premium services like [Google's Programmable Search Engine](https://programmablesearchengine.google.com/about/) and [NLResearch.com](https://northernlight.com/). 

:star: Learn more: [Documentation Wiki](https://github.com/sidprobstein/swirl-search/wiki)

<br/>

# Use SWIRL:

1. Load [SearchProviders](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#searchproviders) as described in the [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start#install-searchproviders):

![SWIRL SearchProviders](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_providers_focus.png)

2. [Run a search](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#creating-a-search-object-with-the-q-url-parameter):

```
http://localhost:8000/swirl/search/?q=knowledge+management
```

3. Get unified, AI-ranked results:

![SWIRL Results](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_results_focus.png)

<br/>

# Try SWIRL Now:

* Download [https://github.com/sidprobstein/swirl-search/blob/main/docker-compose.yaml](https://github.com/sidprobstein/swirl-search/blob/main/docker-compose.yaml) into a folder

* From the console:

```
docker-compose up
```

After a few minutes the following or similar should appear:

```
ssdtest-app-1  | Command successful!
ssdtest-app-1  | __S_W_I_R_L__1_._8______________________________________________________________
ssdtest-app-1  | 
ssdtest-app-1  | Warning: logs directory does not exist, creating it
ssdtest-app-1  | Start: rabbitmq -> rabbitmq-server ... Ok, pid: 53
ssdtest-app-1  | Start: celery-worker -> celery -A swirl_server worker ... Ok, pid: 577
ssdtest-app-1  | Start: celery-beats -> celery -A swirl_server beat --scheduler django_celery_beat.schedulers:DatabaseScheduler ... Ok, pid: 609
ssdtest-app-1  | Updating .swirl... Ok
ssdtest-app-1  | 
ssdtest-app-1  |   PID TTY          TIME CMD
ssdtest-app-1  |    53 ?        00:00:00 rabbitmq-server
ssdtest-app-1  |   577 ?        00:00:11 celery
ssdtest-app-1  |   609 ?        00:00:06 celery
ssdtest-app-1  | 
ssdtest-app-1  | Command successful!
ssdtest-app-1  | 2023-01-21 13:16:11,070 INFO     Starting server at tcp:port=8000:interface=0.0.0.0
ssdtest-app-1  | 2023-01-21 13:16:11,074 INFO     HTTP/2 support not enabled (install the http2 and tls Twisted extras)
ssdtest-app-1  | 2023-01-21 13:16:11,075 INFO     Configuring endpoint tcp:port=8000:interface=0.0.0.0
ssdtest-app-1  | 2023-01-21 13:16:11,079 INFO     Listening on TCP address 0.0.0.0:8000
ssdtest-app-1  | 2023-01-21 13:18:43,470 WARNING  Forbidden: /swirl/search/
```

* Open the following with a browser: 

```
http://localhost:8000/swirl/search/?q=enterprise+search
```

Login with username `admin` and password `password`. Ranked results will appear in just a few seconds!

```
TO DO
```

<br/>

:warning: Warning: The Docker version of SWIRL does *not* retain results or configuration when shut down!

:star: Learn more: [Quick Start Guide](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)

<br/>

# Try Hosted SWIRL

### If interested in a free trial of SWIRL as a managed service, please [contact support](#support)!

<br/>

# Download SWIRL

| Version                     | Date                        | Notes | 
| --------------------------- | --------------------------- | ----- |
| [SWIRL SEARCH 1.8.1](https://github.com/sidprobstein/swirl-search/releases/tag/v1.8.1) | 1-21-2022 | [Release 1.8.1](./docs/RELEASE_NOTES_1.8.1.md) |
| [SWIRL SEARCH 1.7](https://github.com/sidprobstein/swirl-search/releases/tag/v1.7) | 12-3-2022 | [Release 1.7](./docs/RELEASE_NOTES_1.7.md) |
| [Docker Image](https://hub.docker.com/r/sidprobstein/swirl-search) | * | [Setup Guide](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start#docker) - Note *does* *not* *persist* *data* after shutdown! | 

<br/>

# Documentation Wiki

### [Home](https://github.com/sidprobstein/swirl-search/wiki) | [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start) | [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide) | [Developer Guide](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide) | [Admin Guide](https://github.com/sidprobstein/swirl-search/wiki/4.-Admin-Guide)

<br/>

# Key Features

* [Pre-built searchprovider definitions](https://github.com/sidprobstein/swirl-search/tree/main/SearchProviders) for apache solr, elastic, Sqlite3, PostgreSQL, generic http/get/auth/json and premium services like Google Programmable Search Engine, NLResearch.com and Newsdata.io that are configured - NOT coded - and easily [organized with properties and tags](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#organizing-searchproviders-with-active-default-and-tags)

* [Adaptation of the query for each provider](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#search-syntax) such as rewriting ```NOT term``` to ```-term```, removing NOTted terms from providers that don't support NOT, and passing down AND, + and OR.

* [Synchronous or asynchronous search federation](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#architecture) via [APIs](http://localhost:8000/swirl/swagger-ui/)

* [Optional subscribe feature](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#subscribing-to-a-search) to continuously monitor any search for new results 

* Pipelining of [Processor](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#processors) stages for real-time adaptation and transformation of queries, responses and results 

* [Results landed](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#result-object) in Sqlite3 or PostgreSQL for post-processing, consumption and/or analytics

* [Matching on word stems](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#relevancy) and [handling of stopword](https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference#stopwords-language) via NLTK

* [Duplicate detection](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#detecting-and-removing-duplicate-results) on field or by configurable Cosine Similarity threshold

* Re-ranking of unified results [using Cosine Vector Similarity](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#relevancy) based on [spaCy](https://spacy.io/)'s large language model and [NLTK](https://www.nltk.org/)

* [Result mixers](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#result-mixers) order results by relevancy, date or round-robin (stack) format, with optional filtering of just new items in subscribe modes

* Page through all results requested, re-run, re-score and update searches using URLs provided with each result set

* [Sample data sets](https://github.com/sidprobstein/swirl-search/tree/main/Data) for use with Sqlite3 and PostgreSQL

* [Optional spell correction](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#spell-correction) using TextBlob

* [Optional search/result expiration service](https://github.com/sidprobstein/swirl-search/wiki/5.-Admin-Guide#search-expiration-service) to limit storage use

* Easily extensible [Connector](https://github.com/sidprobstein/swirl-search/tree/main/swirl/connectors) and [Mixer](https://github.com/sidprobstein/swirl-search/tree/main/swirl/mixers) objects

* [Source code & docker images provided under the Apache 2.0 License](./LICENSE)

<br/>

# Support

* [Join SWIRL SEARCH #support on Slack!](https://join.slack.com/t/swirlsearch/shared_invite/zt-1n7xophls-F4SzYecGniOFB95xI6WlAw)

* [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented

* Email: [support@swirl.today](mailto:support@swirl.today) with issues, requests, questions, etc - we'd love to hear from you!

<br/>

