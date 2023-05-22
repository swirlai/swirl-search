<h1>&nbsp; Swirl MetasearchS 2.0<img alt='Swirl Metasearch Logo' src='https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl-logo-only-blue.png' width=38 align=left /></h1>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?color=blue&logoColor=blue&style=flat)](https://opensource.org/license/apache-2-0/)
[![GitHub Release](https://img.shields.io/github/v/release/swirlai/swirl-search?style=flat&label=Release)](https://github.com/swirlai/swirl-search/releases)
[![Docker Build](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml/badge.svg?branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml)
[![Tests](https://github.com/swirlai/swirl-search/actions/workflows/smoke-tests.yml/badge.svg?branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/smoke-tests.yml)
[![Built with spaCy](https://img.shields.io/badge/Built%20with-spaCy-09a3d5.svg?color=blue)](https://spacy.io)
[![Slack](https://img.shields.io/badge/Slack--channel-gray?logo=slack&logoColor=black&style=flat)](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)
[![Newsletter](https://img.shields.io/badge/Newsletter-gray?logo=revue&logoColor=black&style=flat)](https://groups.google.com/g/swirl-announce)
[![Twitter](https://img.shields.io/twitter/follow/SWIRL_SEARCH?label=Follow%20%40SWIRL_SEARCH&color=gray&logoColor=black&style=flat)](https://twitter.com/SWIRL_SEARCH)

Swirl Metasearch adapts and distributes queries to anything with a search API - search engines, databases, noSQL engines, cloud/SaaS services etc - and uses AI ([Large Language Models](https://techcrunch.com/2022/04/28/the-emerging-types-of-language-models-and-why-they-matter/)) to re-rank the unified results *without* extracting and indexing *anything*. It supports OAUTH2 integration with enterprise services including Microsoft 365, Atlassian, JetBrains YouTrack and more coming soon.

Using the updated Spyglass UI, knowledge workers can systematically review the best results from additional configured services including Apache [Solr](https://solr.apache.org/), [ChatGPT](https://openai.com/blog/chatgpt/), [Elastic](https://www.elastic.co/cn/downloads/elasticsearch), [OpenSearch](https://opensearch.org/downloads.html) | [PostgreSQL](https://www.postgresql.org/), [Google BigQuery](https://cloud.google.com/bigquery) plus generic HTTP/GET/JSON with configurations for premium services like [Google's Programmable Search Engine](https://programmablesearchengine.google.com/about/), [Miro](https://miro.com/app/) and [Northern Light Research](https://northernlight.com/).

![Metasearch diagram](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_arch_diagram.jpg)

Built on the Python/Django stack, Swirl is intended for use by search managers, developers, data scientists and engineers who want to solve multi-silo search problems - including notification services - without moving, re-indexing or re-permissioning sensitive information.

Learn more: [Documentation Wiki](https://github.com/swirlai/swirl-search/wiki)

<br/>

# Try SWIRL Now

* Download [https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml](https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml)

```
curl https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml -o docker-compose.yaml
```

* From the console:

```
docker compose up
```

After a few minutes the following or similar should appear:

```
ssdtest-app-1  | Command successful!
ssdtest-app-1  | __S_W_I_R_L__2_._0______________________________________________________________
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
```

* Open the following URL with a browser:

```
http://localhost:8000/spyglass/
```

The search page will appear. Click `Log Out` at top, right. The Swirl login page will appear:

![Swirl Login](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_login.png)

Enter username `admin` and password `password`. Then click Login.

* Enter a search in the search box and press the search button. Ranked results will appear in just a few seconds!

![Swirl Metasearch 2.0 Results](https://raw.githubusercontent.com/wiki/swirlai/swirl-search/images/swirl_metasearch_results.png)

:info: Swirl includes three (3) Google Programmable Search Engines (PSEs), complete with shared credentials, to get you up and running with right away. These credentials are shared with the SWIRL Community.

:info: Using Swirl with Microsoft 365 requires installation and approval by an authorized company administrator. For more information please review the [M365 Guide](https://github.com/swirlai/swirl-search/wiki/5.-M365-Guide) or [contact us](mailto:hello@swirl.today) for more information.

:Warning: The Docker version of SWIRL does *not* retain results or configuration when shut down!

Learn more: [Quick Start Guide](https://github.com/swirlai/swirl-search/wiki/1.-Quick-Start)

<br/>

# Try Swirl Cloud

### For information about Swirl as a managed service, please [contact us](mailto:hello@swirl.today)!

<br/>

# Download SWIRL

| Version                     | Date                        | Notes |
| --------------------------- | --------------------------- | ----- |
| [Swirl Metasearch 2.0](https://github.com/swirlai/swirl-search/releases/tag/v2.0) | 05-22-2023 | [Release 2.0](https://github.com/swirlai/swirl-search/releases) |

<br/>

# Documentation Wiki

### [Home](https://github.com/swirlai/swirl-search/wiki) | [Quick Start](https://github.com/swirlai/swirl-search/wiki/1.-Quick-Start) | [User Guide](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide) | [Developer Guide](https://github.com/swirlai/swirl-search/wiki/3.-Developer-Guide) | [Admin Guide](https://github.com/swirlai/swirl-search/wiki/4.-Admin-Guide) | [M365 Guide](https://github.com/swirlai/swirl-search/wiki/5.-M365-Guide)

<br/>

# Key Features

* [Microsoft 365 integration and OAUTH2 support](https://github.com/swirlai/swirl-search/wiki/5.-M365-Guide)

* [SearchProvider configurations](https://github.com/swirlai/swirl-search/tree/main/SearchProviders) for all included Connectors. They can be [organized with the active, default and tags properties](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide#organizing-searchproviders-with-active-default-and-tags).

* [Adaptation of the query for each provider](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide#search-syntax) such as rewriting `NOT term` to `-term`, removing NOTted terms from providers that don't support NOT, and passing down the AND, + and OR operators.

* [Synchronous or asynchronous search federation](https://github.com/swirlai/swirl-search/wiki/3.-Developer-Guide#architecture) via [APIs](http://localhost:8000/swirl/swagger-ui/)

* [Optional subscribe feature](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide#subscribing-to-a-search) to continuously monitor any search for new results

* Pipelining of [Processor](https://github.com/swirlai/swirl-search/wiki/3.-Developer-Guide#processors) stages for real-time adaptation and transformation of queries, responses and results

* [Results stored](https://github.com/swirlai/swirl-search/wiki/3.-Developer-Guide#result-object) in SQLite3 or PostgreSQL for post-processing, consumption and/or analytics

* Built-in [Query Transformation](https://github.com/swirlai/swirl-search/wiki/3.-Developer-Guide#query-transformations) support, including re-writing and replacement

* [Matching on word stems](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide#relevancy) and [handling of stopword](https://github.com/swirlai/swirl-search/wiki/3.-Developer-Guide#stopwords-language) via NLTK

* [Duplicate detection](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide#detecting-and-removing-duplicate-results) on field or by configurable Cosine Similarity threshold

* Re-ranking of unified results [using Cosine Vector Similarity](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide#relevancy) based on [spaCy](https://spacy.io/)'s large language model and [NLTK](https://www.nltk.org/)

* [Result mixers](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide#result-mixers) order results by relevancy, date or round-robin (stack) format, with optional filtering of just new items in subscribe mode

* Page through all results requested, re-run, re-score and update searches using URLs provided with each result set

* [Sample data sets](https://github.com/swirlai/swirl-search/tree/main/Data) for use with SQLite3 and PostgreSQL

* [Optional spell correction](https://github.com/swirlai/swirl-search/wiki/2.-User-Guide#spell-correction) using [TextBlob](https://textblob.readthedocs.io/en/dev/quickstart.html#spelling-correction)

* [Optional search/result expiration service](https://github.com/swirlai/swirl-search/wiki/4.-Admin-Guide#search-expiration-service) to limit storage use

* Easily extensible [Connector](https://github.com/swirlai/swirl-search/tree/main/swirl/connectors) and [Mixer](https://github.com/swirlai/swirl-search/tree/main/swirl/mixers) objects

<br/>

# Support

* [Join Swirl Metasearch on Slack!](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)

* [Create an Issue](https://github.com/swirlai/swirl-search/issues) if something doesn't work, isn't clear, or should be documented

* Email: [support@swirl.today](mailto:support@swirl.today) with issues, requests, questions, etc - we'd love to hear from you!

<br/>
