<h1> &nbsp; SWIRL SEARCH <img alt='SWIRL Logo' src='https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_logo_notext_200.jpg' width=38 align=left /></h1>

[![GitHub Release](https://img.shields.io/github/v/release/sidprobstein/swirl-search?style=flat)](https://github.com/sidprobstein/swirl-search/releases)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?color=blue&logoColor=blue&style=flat)](https://opensource.org/licenses/Apache-2.0)
[![Docker Build Status](https://img.shields.io/docker/cloud/build/sidprobstein/swirl-search?style=flat)](https://hub.docker.com/repository/docker/sidprobstein/swirl-search/builds) 
[![Slack](https://img.shields.io/badge/slack--channel-gray?logo=slack&logoColor=black&style=flat)](https://join.slack.com/t/swirlsearch/shared_invite/zt-1n7xophls-F4SzYecGniOFB95xI6WlAw)
[![Newsletter](https://img.shields.io/badge/newsletter-gray?logo=revue&logoColor=black&style=flat)](https://groups.google.com/g/swirl-announce)
[![Twitter](https://img.shields.io/twitter/follow/SWIRL_SEARCH?color=gray&logoColor=black&style=flat)](https://twitter.com/SWIRL_SEARCH)
 

SWIRL adapts and distributes queries to anything with a search API - search engines, databases, noSQL engines, cloud/SaaS services etc - and uses AI ([Large Language Models](https://techcrunch.com/2022/04/28/the-emerging-types-of-language-models-and-why-they-matter/)) to re-rank the unified results *without* extracting and indexing *anything*. It's intended for use by developers and data scientists who want to solve multi-silo search problems from enterprise search to new monitoring & alerting solutions that push information to users continuously.

![Federated search diagram](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/federation_diagram.png)

Built on the Python/Django/RabbitMQ stack, SWIRL includes connectors to [Elastic](https://www.elastic.co/cn/downloads/elasticsearch), Apache [Solr](https://solr.apache.org/), [PostgreSQL](https://www.postgresql.org/), [Google BigQuery](https://cloud.google.com/bigquery) plus generic HTTP/GET/JSON with configurations for premium services like [Google's Programmable Search Engine](https://programmablesearchengine.google.com/about/) and [NLResearch.com](https://northernlight.com/). 

:star: Learn more: [Documentation Wiki](https://github.com/sidprobstein/swirl-search/wiki)

<br/>

# Try SWIRL Now:

* Download [https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docker-compose.yaml](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docker-compose.yaml)

```
curl https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docker-compose.yaml -o docker-compose.yaml
```

* From the console:

```
docker compose up
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
```

* Open the following URL with a browser: 

```
http://localhost:8000/swirl/search/
```

The search page will appear. Login with username `admin` and password `password`. 

* Open the following URL with a browser: 

```
http://localhost:8000/swirl/search/?q=enterprise+search 
```

Ranked results will appear in just a few seconds!

```

    "messages": [
        "__S_W_I_R_L__1_._8______________________________________________________________",
        "[2023-01-21 15:02:53.696346] Retrieved 10 of 3530 results from: Mergers & Acquisitions (web/Google PSE)",
        "[2023-01-21 15:02:53.731620] Retrieved 10 of 2070000000 results from: Strategy Consulting (web/Google PSE)",
        "[2023-01-21 15:02:53.854734] Retrieved 10 of 120000 results from: Enterprise Search (web/Google PSE)",
        "[2023-01-21 15:02:54.228330] DedupeByFieldPostResultProcessor updated 1 results",
        "[2023-01-21 15:02:55.203736] CosineRelevancyPostResultProcessor updated 29 results",
        "[2023-01-21 15:02:59.241287] Results ordered by: RelevancyMixer"
    ],
    "info": {
        "Enterprise Search (web/Google PSE)": {
            "found": 120000,
            "retrieved": 10,
            "filter_url": "http://localhost:8000/swirl/results/?search_id=2&provider=1",
            "query_string_to_provider": "enterprise search",
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=0c38029ddd002c006&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&q=enterprise+search",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "result_processors": [
                "MappingResultProcessor"
            ],
            "search_time": 1.7
        },
        "Strategy Consulting (web/Google PSE)": {
            "found": 2070000000,
            "retrieved": 10,
            "filter_url": "http://localhost:8000/swirl/results/?search_id=2&provider=2",
            "query_string_to_provider": "enterprise search",
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=7d473806dcdde5bc6&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&q=enterprise+search",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "result_processors": [
                "MappingResultProcessor"
            ],
            "search_time": 1.6
        },
        "Mergers & Acquisitions (web/Google PSE)": {
            "found": 3530,
            "retrieved": 10,
            "filter_url": "http://localhost:8000/swirl/results/?search_id=2&provider=3",
            "query_string_to_provider": "enterprise search",
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=b384c4e79a5394479&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&q=enterprise+search",
            "query_processors": [
                "AdaptiveQueryProcessor"
            ],
            "result_processors": [
                "MappingResultProcessor"
            ],
            "search_time": 1.6
        },
        "search": {
            "query_string": "enterprise search",
            "query_string_processed": "enterprise search",
            "rescore_url": "http://localhost:8000/swirl/search/?rescore=2",
            "rerun_url": "http://localhost:8000/swirl/search/?rerun=2"
        },
        "results": {
            "retrieved_total": 29,
            "retrieved": 10,
            "federation_time": 3.0,
            "next_page": "http://localhost:8000/swirl/results/?search_id=2&page=2"
        }
    },
    "results": [
        {
            "swirl_rank": 1,
            "swirl_score": 8641.028729276184,
            "searchprovider": "Enterprise Search (web/Google PSE)",
            "searchprovider_rank": 1,
            "title": "*Enterprise* *search* - Wikipedia",
            "url": "https://en.wikipedia.org/wiki/Enterprise_search",
            "body": "*Enterprise* *search* is the practice of making content from multiple *enterprise-type* sources, such as databases and intranets, *searchable* to a defined audience ...",
            "date_published": "unknown",
            "date_retrieved": "2023-01-21 15:02:53.854964",
            "author": "",
            "payload": {
                "cacheId": "D6cJRzESeEoJ"
            },
            "explain": {
                "stems": "enterpris search",
                "title": {
                    "enterprise_search_*": 0.9434668430078893,
                    "Enterprise_search_0": 0.9434668430078893,
                    "Enterprise_0": 0.6651386968008296,
                    "search_1": 0.9049768381205389,
                    "result_length_adjust": 2.3333333333333335,
                    "query_length_adjust": 1.0
                },
                "body": {
                    "enterprise_search_*": 0.6018024110405671,
                    "Enterprise_search_0": 0.571031804774827,
                    "search_1": 0.5442048484158057,
                    "result_length_adjust": 1.0,
                    "query_length_adjust": 1.0
                }
            }
        },
        {
            "swirl_rank": 2,
            "swirl_score": 7348.585219407358,
            "searchprovider": "Strategy Consulting (web/Google PSE)",
            "searchprovider_rank": 6,
            "title": "Intelligent *Enterprise* *Search*",
            "url": "https://www.accenture.com/dk-en/services/applied-intelligence/intelligent-enterprise-search",
            "body": "Accenture helps clients implement intelligent *enterprise* *search* solutions using AI technologies, such as natural language processing and machine learning.",
            "date_published": "unknown",
            "date_retrieved": "2023-01-21 15:02:53.780191",
            "author": "",
            "payload": {},
            "explain": {
                "stems": "enterpris search",
                "title": {
                    "enterprise_search_*": 0.9608442937138034,
                    "Enterprise_Search_1": 1.0,
                    "Enterprise_1": 0.7935776562186374,
                    "Search_2": 1.0,
                    "result_length_adjust": 2.3333333333333335,
                    "query_length_adjust": 1.0
                },
                "body": {
                    "enterprise_search_*": 0.7308253502908216,
                    "enterprise_search_5": 0.7899886473674567,
                    "enterprise_5": 0.8224356551634711,
                    "search_6": 0.6706759394116855,
                    "result_length_adjust": 1.1578947368421053,
                    "query_length_adjust": 1.0
                }
            }
        },
        {
            "swirl_rank": 3,
            "swirl_score": 6636.90423527112,
            "searchprovider": "Strategy Consulting (web/Google PSE)",
            "searchprovider_rank": 2,
            "title": "Intelligent *Enterprise* *Search* | Accenture",
            "url": "https://www.accenture.com/us-en/services/applied-intelligence/intelligent-enterprise-search",
            "body": "Intelligent *enterprise* *search* uses AI technologies, such as Natural Language Processing (NLP), semantic search, and Machine Learning (ML), to provide an engaged ...",
            "date_published": "unknown",
            "date_retrieved": "2023-01-21 15:02:53.745475",
            "author": "",
            "payload": {},
            "explain": {
                "stems": "enterpris search",
                "title": {
                    "enterprise_search_*": 0.9294430473589433,
                    "Enterprise_Search_1": 0.9505501863924661,
                    "Enterprise_1": 0.8166240031067878,
                    "Search_2": 0.8792733859459471,
                    "result_length_adjust": 1.75,
                    "query_length_adjust": 1.0
                },
                "body": {
                    "enterprise_search_*": 0.7327504309736037,
                    "enterprise_search_1": 0.6809326651912151,
                    "enterprise_1": 0.6592383943038718,
                    "search_2": 0.5937011247188788,
                    "search_13": 0.6189125063789584,
                    "result_length_adjust": 1.0,
                    "query_length_adjust": 1.0
                }
            }
        }, 
        ...etc...
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
| [SWIRL SEARCH 1.8.2](https://github.com/sidprobstein/swirl-search/releases/tag/v1.8.2) | 01-22-2023 | [Release 1.8.2](./docs/RELEASE_NOTES_1.8.2.md) |
| [SWIRL SEARCH 1.8.1](https://github.com/sidprobstein/swirl-search/releases/tag/v1.8.1) | 01-21-2023 | [Release 1.8.1](./docs/RELEASE_NOTES_1.8.1.md) |
| [SWIRL SEARCH 1.7](https://github.com/sidprobstein/swirl-search/releases/tag/v1.7) | 12-03-2022 | [Release 1.7](./docs/RELEASE_NOTES_1.7.md) |

<br/>

# Documentation Wiki

### [Home](https://github.com/sidprobstein/swirl-search/wiki) | [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start) | [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide) | [Developer Guide](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide) | [Admin Guide](https://github.com/sidprobstein/swirl-search/wiki/4.-Admin-Guide)

<br/>

# Key Features

* [SearchProvider configurations](https://github.com/sidprobstein/swirl-search/tree/main/SearchProviders) for all included Connectors. They can be [organized with the active, default and tags properties](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#organizing-searchproviders-with-active-default-and-tags).

* [Adaptation of the query for each provider](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#search-syntax) such as rewriting `NOT term` to `-term`, removing NOTted terms from providers that don't support NOT, and passing down the AND, + and OR operators.

* [Synchronous or asynchronous search federation](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#architecture) via [APIs](http://localhost:8000/swirl/swagger-ui/)

* [Optional subscribe feature](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#subscribing-to-a-search) to continuously monitor any search for new results 

* Pipelining of [Processor](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#processors) stages for real-time adaptation and transformation of queries, responses and results 

* [Results stored](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#result-object) in SQLite3 or PostgreSQL for post-processing, consumption and/or analytics

* [Matching on word stems](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#relevancy) and [handling of stopword](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#stopwords-language) via NLTK

* [Duplicate detection](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#detecting-and-removing-duplicate-results) on field or by configurable Cosine Similarity threshold

* Re-ranking of unified results [using Cosine Vector Similarity](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#relevancy) based on [spaCy](https://spacy.io/)'s large language model and [NLTK](https://www.nltk.org/)

* [Result mixers](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#result-mixers) order results by relevancy, date or round-robin (stack) format, with optional filtering of just new items in subscribe mode

* Page through all results requested, re-run, re-score and update searches using URLs provided with each result set

* [Sample data sets](https://github.com/sidprobstein/swirl-search/tree/main/Data) for use with SQLite3 and PostgreSQL

* [Optional spell correction](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#spell-correction) using [TextBlob](https://textblob.readthedocs.io/en/dev/quickstart.html#spelling-correction)

* [Optional search/result expiration service](https://github.com/sidprobstein/swirl-search/wiki/4.-Admin-Guide#search-expiration-service) to limit storage use

* Easily extensible [Connector](https://github.com/sidprobstein/swirl-search/tree/main/swirl/connectors) and [Mixer](https://github.com/sidprobstein/swirl-search/tree/main/swirl/mixers) objects

<br/>

# Support

* [Join SWIRL SEARCH #support on Slack!](https://join.slack.com/t/swirlsearch/shared_invite/zt-1n7xophls-F4SzYecGniOFB95xI6WlAw)

* [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented

* Email: [support@swirl.today](mailto:support@swirl.today) with issues, requests, questions, etc - we'd love to hear from you!

<br/>

