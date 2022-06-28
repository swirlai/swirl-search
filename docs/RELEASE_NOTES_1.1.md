![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL SEARCH 1.1

## New Features

* SearchProvider configurations for [Apache SOLR](https://solr.apache.org/) and [Northern Light's NLResearch.com service](https://www.nlresearch.com/) using the re-factored [requests_get connector](../swirl/connectors/requests_get.py)
* Added new command start_sleep to swirl.py for use in Docker

<br/>

## Key Features

* [Asynchronous search federation](DEVELOPER_GUIDE.md#workflow) via REST APIs
* Data landed in Sqlite for later consumption
* [Pre-built searchprovider definitions](../SearchProviders/) for HTTP/GET (with auth), google PSE, elastic, apache solr, sqlite3 and NLResearch.com
* [Sample data sources](../Data/) for use with sqlite3
* Sort results by provider date or relevancy, page through all results requested
* Result mixers operate on landed results and order results by relevancy, date, stack or round-robin
* [Cosine similarity relevancy using Spacy vectors](USER_GUIDE.md#understanding-relevancy) with field boosts and explanation
* Optional spell correction using TextBlob
* Optional search/result expiration service to limit storage use

<br/>

## Release Notes

:small_blue_diamond: The requests_get connector has been refactored to handle responses via configuration. 

This eliminated the opensearch connector; Google PSE is now supported by configuring requests_get, and all SearchProvider definitions have been updated to reflect this. Here is an example of the new Google PSE configuration:

```
        "query_mappings": "cx=some-google-pse-id,sort=date=DATE_SORT,start=RESULT_INDEX=PAGE",
        "result_mappings": "link=url,htmlSnippet=body,cacheId,NO_PAYLOAD,searchInformation.totalResults=FOUND,queries.request[0].count=RETRIEVED,items=RESULTS"
```

The [new mapping keys DATE_SORT, PAGE, FOUND, RETRIEVED and RESULTS are described in the User's Guide](../wiki/2.-User-Guide#query-mappings).

<br/>

:small_blue_diamond: [Apache SOLR](https://solr.apache.org/) is now supported by requests_get; this has tested against [8.1.1](https://solr.apache.org/downloads.html). 

Here's the [sample SearchProvider](../SearchProviders/solr_with_auth.json):

```
{
    "name": "techproducts (local/solr)",
    "connector": "requests_get",
    "url": "http://localhost:8983/solr/{collection}/select?wt=json",
    "query_template": "{url}&q={query_string}",
    "query_mappings": "collection=techproducts,start=RESULT_ZERO_INDEX=PAGE",
    "result_mappings": "name=title,response.numFound=FOUND,response.docs=RESULTS",
    "credentials": "HTTPBasicAuth('solr-username','solr-password')"
}
```

Remove the credentials item if using solr without security. 

<br/>

:small_blue_diamond: [NLResearch.com](https://www.nlresearch.com/) is now supported by requests_get; this has been tested as of June, 2022. 

Here's the sample SearchProvider:

```
{
    "name": "IT News (web/NLResearch.com)",
    "connector": "requests_get",
    "url": "https://nlresearch.com/results.php?datasource=BRECE&language=1&periodDate=-7&sort=1&resultsPerPage=10&micpr=0&extended=1&output=json",
    "query_template": "{url}&login={login}&password={password}&textQuery={query_string}",
    "query_mappings": "startNumber=RESULT_INDEX=PAGE,sort=2=DATE_SORT",
    "result_mappings": "summary=body,date=date_published,publisher=author,type,source,country,language,NO_PAYLOAD,header.@attributes.total_documents=FOUND,result_list.result=RESULTS,document=RESULT",
    "results_per_query": 10,
    "credentials": "login=nl-username,password=nl-password"
}
```

<br/>

## Known Issues

:small_blue_diamond: [](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide#creating-search-objects-with-a-url) can sometimes create two Search objects.

This may be because of browser pre-fetch, or simply because of hitting ENTER twice. Please [report issues](https://github.com/sidprobstein/swirl-search/issues/) with this or the [rerun function](USER_GUIDE.md#re-starting-re-running--re-trying-a-search).

<br/>

:small_blue_diamond: The [Django admin form for managing Result objects](http://localhost:8000/admin/swirl/result/) throws a 500 error. P2.

<br/>

:small_blue_diamond: Watch out for log files in logs/*.log. They'll need periodic purging. Rollover is planned for a future release.

<br/>

## For more information: 

* [Quick Start](https://github.com/sidprobstein/swirl-search/wiki/1.-Quick-Start)
* [User Guide](https://github.com/sidprobstein/swirl-search/wiki/2.-User-Guide)

<br/>

# Get Support

Please [report an issue](https://github.com/sidprobstein/swirl-search/issues/) or email [swirl-support@probstein.com](mailto:swirl-support@probstein.com) for support.

<br/>