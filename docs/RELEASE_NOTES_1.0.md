![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.0

## Key Features

* [Asynchronous search federation](DEVELOPER_GUIDE.md#workflow) via REST APIs
* Data landed in Sqlite for later consumption
* [Pre-built searchprovider definitions](../SearchProviders/) for http_get, google PSE, elasticsearch and Sqlite
* [Sample data sources](../Data/) for use with Sqlite
* Sort results by provider date or relevancy, page through all results requested
* Result mixers operate on landed results and order results by relevancy, date, stack or round-robin
* [Cosine similarity relevancy using Spacy vectors](USER_GUIDE.md#understanding-relevancy) with field boosts and explanation
* Optional spell correction using TextBlob
* Optional search/result expiration service to limit storage use

<br/>

## Release Notes

:small_blue_diamond: The [Installation Guide](INSTALLATION_GUIDE.md) has been tested for Mac OS/X (Intel, M1) and Centos. It has not been tested on Microsoft Windows.

<br/>

:small_blue_diamond: There are reports that using [OpenSearch](USER_GUIDE.md#using-the-opensearch-interface) sometimes creates two Search objects.

This may be because of browser pre-fetch, or simply because of hitting ENTER twice.<br/>Please report issues with this or the [rerun function](USER_GUIDE.md#re-starting-re-running--re-trying-a-search).

<br/>

:small_blue_diamond: The [Django admin form for managing Result objects](http://localhost:8000/admin/swirl/result/) throws a 500 error. P2.

<br/>

:small_blue_diamond: Watch out for the log files in logs/*.log. They'll need periodic rollover.

<br/>

## How to Help

- [ ] Test the [Installation Guide](INSTALLATION_GUIDE.md) and [Quick Start](QUICK_START.md)
- [ ] Test and document the [installation procedure for Microsoft Windows](INSTALLATION_GUIDE.md#microsoft-windows)
- [ ] Email [support@swirl.today](mailto:support@swirl.today) for support, or please [open a ticket in Github](https://github.com/sidprobstein/swirl-search/issues)

<br/>

## For more information: 

* [Installation Guide](INSTALLATION_GUIDE.md)
* [Quick Start](QUICK_START.md)
* [User Guide](USER_GUIDE.md)

<br/>

# Get Support

Please email [support@swirl.today](mailto:support@swirl.today) for support.

<br/>