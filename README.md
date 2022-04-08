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

# Documentation

### [Installation Guide](./docs/INSTALLATION_GUIDE.md)

:small_blue_diamond: Steps: [Install Packages](./docs/INSTALLATION_GUIDE.md#install-packages) | [Setup SWIRL](./docs/INSTALLATION_GUIDE.md#setup-swirl) | [Start Services](./docs/INSTALLATION_GUIDE.md#start-services)

### [Quick Start](./docs/QUICK_START.md)

:small_blue_diamond: Steps: [Create SearchProviders](./docs/QUICK_START.md#create-searchproviders) | [Run a Search](./docs/QUICK_START.md#run-a-search) | [Get Results](./docs/QUICK_START.md#get-results) 

### [User Guide](./docs/USER_GUIDE.md)

:small_blue_diamond: [What is Federated Search?](./docs/USER_GUIDE.md#what-is-federated-search) | [What is SWIRL?](./docs/USER_GUIDE.md#what-is-swirl) | [Glossary](./docs/USER_GUIDE.md#glossary)<br/>
:small_blue_diamond: [Managing Search Providers](./docs/USER_GUIDE.md#managing-searchproviders) | [Examples](./docs/USER_GUIDE.md#editing-searchproviders): [Mappings](./docs/USER_GUIDE.md#understanding-query-and-result-mappings) | [Credentials](./docs/USER_GUIDE.md#understanding-credentials) | [Develop Your Own](./docs/USER_GUIDE.md#develop-your-own) <br/>
:small_blue_diamond: [Running Searches](./docs/USER_GUIDE.md#running-searches) | [Examples](./docs/USER_GUIDE.md#example-searches) | [Managing Searches](./docs/USER_GUIDE.md#managing-searches)<br/>
:small_blue_diamond: [Managing Results](./docs/USER_GUIDE.md#managing-results) | [Viewing Unified Results](./docs/USER_GUIDE.md#viewing-unified-results)<br/>
:small_blue_diamond: [Swagger](http://localhost:8000/swirl/swagger-ui/) | [Schema](http://localhost:8000/swirl/openapi) | [PostMan Collection](./docs/SWIRL.postman_collection.json)) | [Python CLI](./docs/USER_GUIDE.md#python-command-line-interface-cli)<br/>

### [Developer Guide](./docs/DEVELOPER_GUIDE.md)

:small_blue_diamond: [Architecture](./docs/DEVELOPER_GUIDE.md#architecture) | [Workflow](./docs/DEVELOPER_GUIDE.md#workflow) | [Search Status](./docs/DEVELOPER_GUIDE.md#search-status)<br/>
:small_blue_diamond: [Object Reference](./docs/DEVELOPER_GUIDE.md#object-reference)

### [Admin Guide](./docs/ADMIN_GUIDE.md)

:small_blue_diamond: [Search Expiration Service](./docs/ADMIN_GUIDE.md#search-expiration-service)<br/>
:small_blue_diamond: [Service Startup & Daemonization](#./docs/ADMIN_GUIDE.mdservice-startup--daemonization)<br/>
:small_blue_diamond: [Management Tools](./docs/ADMIN_GUIDE.md#management-tools)<br/>
:small_blue_diamond: [Database Migration](./docs/ADMIN_GUIDE.md#database-migration)<br/>
:small_blue_diamond: [Configuring Django](./docs/ADMIN_GUIDE.md#configuring-django)<br/>
:small_blue_diamond: [Configuring Celery, Beats & RabbitMQ](./docs/ADMIN_GUIDE.md#configuring-celery-beats--rabbitmq)<br/>
:small_blue_diamond: [Security](./docs/ADMIN_GUIDE.md#security)<br/>
:small_blue_diamond: [Troubleshooting](./docs/ADMIN_GUIDE.md#troubleshooting)<br/>

<br/>

# Get Support

Please email [swirl-support@probstein.com](mailto:swirl-support@probstein.com) for support.

