![SWIRL Logo](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_logo_1024.jpg)

# SWIRL FEDERATED SEARCH ENGINE

SWIRL is the first open source, [Federated Search Engine](https://en.wikipedia.org/wiki/Federated_search)! 

SWIRL makes it easy for search developers, data scientists and power users to search multiple search engine silos at once and quickly receive unified results *without* extracting and indexing *anything*. It includes connectors to elastic, solr, Google PSE, NLResearch.com, generic HTTP/GET/JSON and Sqlite3 that are easy to configure, without writing code. Then use SWIRL's simple REST APIs to run searches and quickly retrieve unified results, re-ranked by SWIRL using built-in cosine-vector similarity plus term, phrase and freshness boosts. 

SWIRL is available under the [Apache 2.0 license](https://github.com/sidprobstein/swirl-search/blob/main/LICENSE), and leans heavily on the popular python/django/celery/rabbit-mq stack - a universe of plug-ins that can extend and integrate SWIRL with a range of existing systems.

<br/>

# Releases

| Version | Date | Branch | Notes | 
| ------- | ---- | ------ | ----- |
| [SWIRL SEARCH 1.3](https://github.com/sidprobstein/swirl-search/releases/tag/v1.3) | 09-23-2022 | Main | [Release Notes](./docs/RELEASE_NOTES_1.3.md) - recommended for ALL USERS |
| [DOCKER CONTAINER](https://hub.docker.com/r/sidprobstein/swirl-search) | 09-24-2022 | Main | For demo/trial only; does not persist data! | 

<br/>

# Screen Shots

### Google PSE Search Providers
![SWIRL SearchProviders](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_providers_focus.png)

### Relevancy Ranked Results
![SWIRL Results](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_results_focus.png)

<br/>

# Features

* [Pre-built searchprovider definitions](https://github.com/sidprobstein/swirl-search/tree/main/SearchProviders) for apache solr, elastic, Sqlite3, http/get/auth/json and NLResearch.com

* [Asynchronous search federation](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#architecture) via [REST APIs](http://localhost:8000/swirl/swagger-ui/)

* Data landed in Sqlite3 for post-processing, later consumption

* [Cosine similarity relevancy](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#relevancy) using Spacy vectors with term, phrase and freshness boosts with full explanation

* [Result mixers](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#mixers) operate on landed results and order results by relevancy, date, stack or round-robin

* Sort results by provider date or relevancy

* Page through all results requested

* [Optional spell correction](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#spell-correction) using TextBlob

* [Sample data sets](https://github.com/sidprobstein/swirl-search/tree/main/Data) for use with Sqlite3

* [Optional search/result expiration service](https://github.com/sidprobstein/swirl-search/wiki/5.-Admin-Guide#search-expiration-service) to limit storage use

* Easily extensible [Connector](https://github.com/sidprobstein/swirl-search/tree/main/swirl/connectors) and [Mixer](https://github.com/sidprobstein/swirl-search/tree/main/swirl/mixers) objects

<br/>

# Documentation

* [Home](https://github.com/sidprobstein/swirl-search/wiki)
* [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)
* [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)
* [Developer Guide](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide)
* [Object Reference](https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference)
* [Admin Guide](https://github.com/sidprobstein/swirl-search/wiki/5.-Admin-Guide)

<br/>

# Contributing

* Review the [to-do list](docs/TO_DO.md)

* Submit a [pull request](https://github.com/sidprobstein/swirl-search/pulls) with changes

<br/>

# Support

* [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented - we'd love to hear from you!

* Paid support and consulting are available... [contact SWIRL](mailto:swirl@probstein.com) for more information.

<br/>



