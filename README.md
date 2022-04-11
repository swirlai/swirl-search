![SWIRL Logo](./docs/images/swirl_logo_notext_200.jpg)

# SWIRL FEDERATED SEARCH ENGINE

*SWIRL* is an open source, [Federated Search Engine](https://en.wikipedia.org/wiki/Federated_search) built on python, django, rabbit-mq and celery.

It exposes a set of RESTful APIs that make it quick and easy for search developers to build 
applications that incorporate searching and viewing results across any number of sources - without 
extracting or indexing ANYTHING. Want to learn more? [Contact SWIRL](mailto:swirl@probstein.com).

<br/>

# Releases

| Version | Date | Branch | Notes | 
| ------- | ---- | ------ | ----- |
| SWIRL SEARCH 1.0 | 04-07-2022 | Main | [Release Notes](./docs/RELEASE_NOTES_1.0.md) |

<br/>

# Documentation Wiki

:small_blue_diamond: [Home](https://github.com/sidprobstein/swirl-search/wiki)
:small_blue_diamond: [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)
:small_blue_diamond: [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)
:small_blue_diamond: [Developer Guide](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide)
:small_blue_diamond: [Object Reference](https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference)
:small_blue_diamond: [Admin Guide](https://github.com/sidprobstein/swirl-search/wiki/5.-Admin-Guide)

# Product Links

:warning: These links will only work if you have SWIRL installed!

:small_blue_diamond: [SWIRL Home](http://localhost:8000/swirl/index.html)
:small_blue_diamond: [SearchProviders](http://localhost:8000/swirl/searchproviders/) | [Search](http://localhost:8000/swirl/search/) | [Results](http://localhost:8000/swirl/results/)
:small_blue_diamond: [Swagger](http://localhost:8000/swirl/swagger-ui/) | [Schema](http://localhost:8000/swirl/openapi) | [PostMan](https://github.com/sidprobstein/swirl-search/blob/main/docs/SWIRL.postman_collection.json)) 

# Features

:small_blue_diamond: [Asynchronous search federation](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#architecture) via [REST APIs](http://localhost:8000/swirl/swagger-ui/)
:small_blue_diamond: Data landed in Sqlite for later consumption
:small_blue_diamond: [Pre-built searchprovider definitions](https://github.com/sidprobstein/swirl-search/tree/main/SearchProviders) for http_get, google PSE, elasticsearch and Sqlite
:small_blue_diamond: [Sample data sets](https://github.com/sidprobstein/swirl-search/tree/main/Data) for use with Sqlite
:small_blue_diamond: Sort results by provider date or relevancy, page through all results requested
:small_blue_diamond: [Result mixers](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#mixers) operate on landed results and order results by relevancy, date, stack or round-robin
:small_blue_diamond: [Cosine similarity relevancy](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#relevancy) using Spacy vectors with field boosts and explanation
:small_blue_diamond: [Optional spell correction](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#spell-correction) using TextBlob
:small_blue_diamond: [Optional search/result expiration service](https://github.com/sidprobstein/swirl-search/wiki/5.-Admin-Guide#search-expiration-service) to limit storage use

[Python CLI](./docs/USER_GUIDE.md#python-command-line-interface-cli)<br/>

# Get Support

Please email [swirl-support@probstein.com](mailto:swirl-support@probstein.com) for support.

