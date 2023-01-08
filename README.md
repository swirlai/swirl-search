<h1> &nbsp; SWIRL AI Federated Search Engine <img alt='SWIRL Logo' src='https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_logo_notext_200.jpg' width=38 align=left></h1>

SWIRL queries any number of data sources - search engines, databases, noSQL engines, cloud/SaaS services with APIs etc - and uses [Large Language Models](https://techcrunch.com/2022/04/28/the-emerging-types-of-language-models-and-why-they-matter/) to re-rank the unified results *without* extracting and indexing *anything*. 

![Federated search diagram](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/federation_diagram.png)

Built on the python/django/rabbit stack, SWIRL includes connectors to [elastic](https://www.elastic.co/cn/downloads/elasticsearch), apache [solr](https://solr.apache.org/), [PostgreSQL](https://www.postgresql.org/) and generic HTTP/GET/JSON with configurations for premium services like Google's Programmable Search Engine, NLResearch.com, newsdata.io and more. 

Learn more about [Federated Search](https://en.wikipedia.org/wiki/Federated_search) and 
[SWIRL SEARCH on the project WIKI...](https://github.com/sidprobstein/swirl-search/wiki)

<br/>

# How SWIRL Works

1. Create/load SearchProviders

![SWIRL SearchProviders](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_providers_focus.png)

2. Run a search:

```
http://localhost:8000/swirl/search/?q=your+query+here
```

3. Get unified, AI-ranked results:
![SWIRL Results](https://raw.githubusercontent.com/sidprobstein/swirl-search/main/docs/images/swirl_results_focus.png)

<br/>

# Try SWIRL Now!

```
docker pull sidprobstein/swirl-search
docker compose up
```

The container will start. Note the container name - for example ```swirl-search-app-1``` as shown below. 

After a minute or two you should see the following or similar:

```
swirl-search-app-1  | Command successful!
swirl-search-app-1  | 2022-10-01 17:06:50,295 INFO     Starting server at tcp:port=8000:interface=0.0.0.0
swirl-search-app-1  | 2022-10-01 17:06:50,295 INFO     HTTP/2 support not enabled (install the http2 and tls Twisted extras)
swirl-search-app-1  | 2022-10-01 17:06:50,295 INFO     Configuring endpoint tcp:port=8000:interface=0.0.0.0
swirl-search-app-1  | 2022-10-01 17:06:50,296 INFO     Listening on TCP address 0.0.0.0:8000
```

From the console, create a super user:

```
docker exec -it swirl-search-app-1 python manage.py createsuperuser --username admin
```

Enter a password, twice. It will be needed in the next step.

From the console, feed some search providers:

```
docker exec -it swirl-search-app-1 python swirl_load.py SearchProviders/google_pse.json -u admin -p <your-admin-password>
```

Be sure to replace ```<swirl-search-app-1``` if the container name is different for your installation, and ```<your-admin-password>``` with the password created earlier.

Now run a query from your browser:

```
http://localhost:8000/swirl/search/?q=enterprise+search
```

Results will appear in just a few seconds!

:star: For more information please review the [Quick Start Guide](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)

:warning: Please note the Docker version of SWIRL does not retain results or configuration when shut down.


<br/>

# Hosted SWIRL

If you are interested in a Docker w/PostgreSQL back-end, and/or a free trial of SWIRL as a managed service, please [contact support](#support)!

<br/>

# Download SWIRL

| Version                     | Date                        | Notes | 
| --------------------------- | --------------------------- | ----- |
| [SWIRL SEARCH 1.7](https://github.com/sidprobstein/swirl-search/releases/tag/v1.7) | 12-3-2022 | [Release 1.7](./docs/RELEASE_NOTES_1.7.md) |
| [Docker Image](https://hub.docker.com/r/sidprobstein/swirl-search) | * | [Setup Guide](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start#docker) - Note *does* *not* *persist* *data* after shutdown! | 

<br/>

# Documentation

* [Home](https://github.com/sidprobstein/swirl-search/wiki)
* [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)
* [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)
* [Developer Guide](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide)
* [Object Reference](https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference)
* [Admin Guide](https://github.com/sidprobstein/swirl-search/wiki/5.-Admin-Guide)

<br/>

# Key Features

* [Pre-built searchprovider definitions](https://github.com/sidprobstein/swirl-search/tree/main/SearchProviders) for apache solr, elastic, Sqlite3, PostgreSQL, generic http/get/auth/json and premium services like Google Programmable Search Engine, NLResearch.com and Newsdata.io that are configured - NOT coded - and easily [organized with properties and tags](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#organizing-searchproviders-with-active-default-and-tags)

* [Adaptation of the query for each provider](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#search-syntax) such as rewriting ```NOT term``` to ```-term```, removing NOTted terms from providers that don't support NOT, and passing down AND, + and OR.

* [Synchronous or asynchronous search federation](https://github.com/sidprobstein/swirl-search/wiki/3.-Developer-Guide#architecture) via [APIs](http://localhost:8000/swirl/swagger-ui/)

* Data landed in Sqlite3 or PostgreSQL for post-processing, consumption and analytics

* [Matching on word stems](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#relevancy) and [handling of stopword](https://github.com/sidprobstein/swirl-search/wiki/4.-Object-Reference#stopwords-language) via NLTK

* Re-ranking of unified results [using Cosine Vector Similarity](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#relevancy) based on [spaCy](https://spacy.io/)'s large language model and [NLTK](https://www.nltk.org/)

* [Result mixers](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#result-mixers) order results by relevancy, date, stack or round-robin

* Page through all results requested, re-run and re-score searches using URLs provided in each result set

* [Sample data sets](https://github.com/sidprobstein/swirl-search/tree/main/Data) for use with Sqlite3 and PostgreSQL

* [Optional spell correction](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#spell-correction) using TextBlob

* [Optional search/result expiration service](https://github.com/sidprobstein/swirl-search/wiki/5.-Admin-Guide#search-expiration-service) to limit storage use

* Easily extensible [Connector](https://github.com/sidprobstein/swirl-search/tree/main/swirl/connectors) and [Mixer](https://github.com/sidprobstein/swirl-search/tree/main/swirl/mixers) objects

* [Available under the Apache 2.0 License](./LICENSE)

<br/>

# Contributing

* Review the [help wanted list](docs/help_wanted.md)

* Submit a [pull request](https://github.com/sidprobstein/swirl-search/pulls) with changes

<br/>

# Support

:small_blue_diamond: [Create an Issue](https://github.com/sidprobstein/swirl-search/issues) if something doesn't work, isn't clear, or should be documented

:small_blue_diamond: Email: [support@swirl.today](mailto:support@swirl.today) with issues, requests, questions, etc - we'd love to hear from you!

<br/>

