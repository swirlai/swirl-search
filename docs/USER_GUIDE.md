![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL USER GUIDE

## Table of Contents

:small_blue_diamond: [What is Federated Search?](#what-is-federated-search) | [What is SWIRL?](#what-is-swirl) | [Glossary](#glossary)<br/>
:small_blue_diamond: [Managing Search Providers](#managing-searchproviders) | [Examples](#editing-searchproviders): [Mappings](#understanding-query-and-result-mappings) | [Credentials](#understanding-credentials) | [Develop Your Own](#develop-your-own) <br/>
:small_blue_diamond: [Running Searches](#running-searches) | [Examples](#example-searches) | [Managing Searches](#managing-searches)<br/>
:small_blue_diamond: [Managing Results](#managing-results) | [Viewing Unified Results](#viewing-unified-results)<br/>
:small_blue_diamond: [Swagger](http://localhost:8000/swirl/swagger-ui/) | [Schema](http://localhost:8000/swirl/openapi) | [Using Postman](#using-postman) | [swirl_load.py](#swirlloadpy-command-line-interface-cli)<br/>
:small_blue_diamond: [Get Support](#get-support)

<br/>

<br/>

------------

<br/>

<br/>

# Overview

## What is Federated Search?

[Federated search](https://en.wikipedia.org/wiki/Federated_search) is a technical approach in which one "search engine" accepts a search from some user or system and brokers (or "federates") the search - sending it to one or more other search engines, waiting for replies from all, and then returning a unified result set. 

Federated search is very different from traditional "enterprise" search which involves [extracting content from every source, mapping it to a new schema](https://en.wikipedia.org/wiki/Extract,_transform,_load) and then [indexing](https://en.wikipedia.org/wiki/Search_engine_indexing) it. That takes months and often costs millions of dollars. Federated search leaves the data where it is and relies on the silo's own search or query engine to get access. Federation takes a fraction of the time and cost, and the reality is, *users may not notice a difference in quality*. As a developer, data scientist or engineering manager who has worked with enterprise search beofre, you will notice how much more time you have to work on other things...

<br/>

## What is SWIRL?

[SWIRL](https://github.com/sidprobstein/swirl_server) is an open source, federated search engine, designed to make it quick and easy for developers and data scientists to add federated search to their applications, platforms or data science environments - with little or no code required, especially for common search engines like Elastic or SOLR. (And when you do have to write code, SWIRL makes it simple by providing examples you can copy and modify for your own purposes - all in python.)

<br/>

<br/>

# Glossary

| Term | Meaning | 
| ---- | ------- |
| SearchProvider | An object defining some searchable source. It includes metadata identifying the type of connector used to search the source and more. |
| Search | An object defining a query that some user or system desires to have run. It includes the query_string with the actual text, and metadata. Most of the metadata is optional.|
| Query | Search engines make a distinction between the act of searching, and what goes into a search. The user's keywords or other search terms are usually referred to as a query. SWIRL follows this convention whenever possible, but, at times, may refer to a search as a query. Sorry about that.|
| Connector | A SWIRL module that can connect to, and query, a particular type of source provider. Connectors are a wrapper around some existing python package such as request.get or elasticsearch.|
| Processors | a SWIRL module that can process search (query) or result content, in source-specific or generic format. They transform whatever they accept in various ways, for example removing control characters from a search, or spell checking it, re-mapping source provider result format's to SWIRL's, and much more.|
| Result | An object defining results from one SearchProvider during the federated search process in response to the creation of a Search object. It includes metadata about the SearchProvider. Much of the metadata is optional.|
| Mixer | A SWIRL module that organizes results from multiple SearchProviders into a unified result set. It includes metadata from all SearchProviders as well as the Search itself.| 

<br/>

<br/>

# Managing SearchProviders

SearchProviders are the essential element of SWIRL. They make it quick and easy to connect to, and search, many instances of the same
type of search engine - or very similar ones. 

<br/>

## Example SearchProviders

SearchProviders are JSON objects. Here are some you can get started with:

:star: [SearchProvider Examples](../SearchProviders/)

<br/>

The following table describes some of the more useful examples:

| SearchProvider | Description | Notes |
| -------------- | ----------- | ----- | 
| document_db.json | sqlite3 document database | [documents_db.csv](../Data/documents_db.csv) |
| funding_db.json  | sqlite3 funding database  | [funding_db.csv](../Data/funding_db.csv) |
| elasticsearch.json | elasticsearch, regular install | requires host, port, credentials | 
| elastic_cloud.json | elasticsearch, cloud version | requires cloud_id, credentials |
| google_pse.json | 3 google programmable search engines (PSE) based on OpenSearch | 
| http_get_with_auth.json | generic http query with basic authentication | requires url, credentials | 

 <br/>

## Creating SearchProviders

1. Go to http://127.0.0.1:8000/swirl/searchproviders/ 
2. Go the form at the bottom of the page, and click the "RAW" tab
3. Paste the SearchProvider JSON into the form and press the POST button.

<br/>

![SWIRL SearchProviders List - Google PSE Examples](./images/pse/swirl_spl_list.png)

4. Optionally, repeat steps 1-3 for each additional provider you want to search with SWIRL!

<br/>

:star: Refer to the [Quick Start](QUICK_START.md) for more detailed instructions.

<br/>

![SWIRL Search Provider List - Google PSE Examples](./images/pse/swirl_spl_list.png)

<br/>

## Viewing SearchProvider Objects & API as JSON

Add format=json to any API call to view it as a json string:

:star: http://127.0.0.1:8000/swirl/searchproviders/?format=json:

<br/>

## Editing SearchProviders

You can edit any SearchProvider by adding the id to the end of the /swirl/searchproviders URL. For example: http://127.0.0.1:8000/swirl/searchproviders/1/  

<br/>

![SWIRL Search Provider Instance - Google PSE Example](./images/pse/swirl_sp_instance.png)

<br/>

## From here, you can use the form to:

* DELETE it, forever
* Edit the body of the request and PUT it back

<br/>

# Understanding Query and Result Mappings 

This section explains Query and Result Mappings and how to use them with SearchProviders.

## Query Mappings

SearchProvider.query_mappings arekey/value pairs that are bound to the SearchProvider.query_template during Search Federation.
They must be in the form key=value. Each key placed in the query_mappings must appear in the query_template, wrapped in braces.

For example:

```
    "url": "https://www.googleapis.com/customsearch/v1",
    "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
    "query_mappings": "cx=0c38029ddd002c006",
```

At federation time, this query_template will be bound with the mappings, credentials and also reserved variables. 

<br/>

```
https://www.googleapis.com/customsearch/v1?cx=0c38029ddd002c006&q=your-query-here

```

Add as many fields as needed following this pattern - except as noted below. Don't use url, query_string, page or sort as these are reserved by SWIRL

A warning, at least, will be reported if any key is not bound to a template.

The following table explains the options available in query_mappings:

<br/>

| Mapping Format | Meaning | Example | 
| template_key = value | This maps a value to key in the provider.query_template. |  "query_template": "{url}?cx={cx}&key={key}&q={query_string}",<br/> "query_mappings": "cx=google-pse-key" |
| sort_by_date=provider-date-field | This identifies the date field for connectors where it may vary - like sqlite3 and elastic; if search.sort is set to 'date', it is automatically added to the query_to_provider | sort_by_date=date_published.keyword | 

:warning: Although result mappings support key only mappings, query mappings support only key=value.

<br/>

## Result Mappings

SearchProvider.result_mappings determine how source results are mapped to the SWIRL result schema. They are similar to query_mappings, but there are some important differences. Most singificantly, you can use json paths to access arbitrary json schemas that you may get back from SearchProviders. 

<br/>

:star: The SWIRL Result schema can be seen in [swirl/models.py](../swirl/models.py) or the create_result_dictionary() function in [swirl/processors/utils.py](../swirl/processors/utils.py).

<br/>

Here are three examples:

```
    "result_mappings": "link=url,snippet=body,cacheId,NO_PAYLOAD",
```

```
    "result_mappings": "_source.customer_full_name=title,_source.email=body,_source.manufacturer,_source.products,NO_PAYLOAD",
```

```
    "result_mappings": "company=title,'{city} {fundedDate}: {company} raised usd ${raisedAmt} series {round} funding'=body,fundedDate=date_published,NO_PAYLOAD"
```

<br/>

The following table explains the options available in result_mappings:

<br/>

| Mapping Format | Meaning | Example | 
| source_key = swirl_key | This maps a key from the source provider's raw format to SWIRL's result schema. Note that source_key may be a json path. |  link=url, _source.email=body |
| 'template {variable} etc'=swirl_key | This allows multiple provider raw format fields to be turned into a stringthat is then copied to SWIRL results or payload. Note you may not use a comma in the string, even though it is a field | '{x}: {y}'=title |
| source_key | This maps a key from the source provider's raw format to SWIRL's result payload. | cacheId, _source.products |
| NO_PAYLOAD | Without this directive, SWIRL copies all result keys from the searchprovider to the payload. If included, NO_PAYLOAD instructs SWIRL not to copy any field that is not explicitly mapped.| NO_PAYLOAD |

### Using the Payload

The payload is a JSON list structure that can hold arbitrary data structures. This is only meaningful if you also specify NO_PAYLOAD. If you don't specify this keyword, you will get all searchprovider raw data mapped into this field.

After you map the fields you want, the way you want them, then add the directive to the result_mappings so that you only get back what you want.

:key: To use NO_PAYLOAD most effectively, send your first query to a SearchProvider without it to see what you get back in the payload.

<br/>

# Understanding Credentials

The credentials property stores any required authentication information for the SearchProvider. It is expected to be in key=value format.

Here is an example from Google PSE which uses the [opensearch connector](#opensearch):

```
    "connector": "opensearch",
    "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
    "credentials": "key=your-google-api-key-here"
```

This connector binds the credentials directly to the URL. Other connectors may handle it differently. For example, here's one for the [requests_get connector](#requestget):

```
    "connector": "requests_get",
    "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
    "credentials": "HTTPDigestAuth('your-username-here', 'your-password-here')"
```

The credentials in this case are passed to the connector for use. Consult the specific [connector](#connector-modules) for more details.

<br/>

# Develop Your Own SearchProviders

This section details how to create your own provider definitions.

## Selecting Processors

The following table lists the processors included with SWIRL Preview 2:

| Processor | Description |
| --------- | ----------- |
| generic_query_processor | Removes whitespace from queries |
| generic_pre_query_processor | Cleans queries removing all characters but alphanumerics and +-"()_~ |
| spellcheck_query_processor | Corrects spelling errors in query_string and writes them into query_string_processed. Best deployed as a Search.pre_query_processor, but can be deployed as a SearchProvider query_processor. Experimental in SWIRL Preview 2. | 
| generic_result_processor | Searches result dictionary keys for SWIRL keys, and copies them, uses result_mappings if specified, mapping source_key to SWIRL_key as specified; aggegates remaining keys into the payload key |
| generic_post_result_processor | Intended for processing of multiple landed Result objects; nothing more than a stub as of Preview3 |
| relevancy_processor | Highlights and scores landed Results; must be configured as a post_result_processor |
| swirl_result_matches | Maps json results from sqlite3; experimental in SWIRL Preview 2. |

<br/>

## Adapting Existing Search Engines

The following sections explain how to adapt specific types of search engines for use with SWIRL. 
Have questions? [Get Support!](#get-support)

<br/>

## [Google Programmable Search Engines](https://programmablesearchengine.google.com/about/)

Google Programmable Search Engine (PSE) is a free web search service from Google you can set up and configure in minutes. You just need a gmail address.

:star: Learn more: https://programmablesearchengine.google.com/about/

<details><summary>Details</summary>
<p>

## Requirements

To use a Google PSE, you need the following:

### The *Google Search Engine ID* which is also the "cx" parameter in the PSE URL. 
If you created the PSE, you can find this in your [Google PSE console](https://programmablesearchengine.google.com/cse/all):

<br/>

![Google PSE Console](./images/google_pse_console.png)

<br/>

Click the name of the PSE to view the search engine id:

<br/>

![Google PSE Console Search Engine](./images/google_pse_console_pse.png)

<br/>

### The *Google API key*, which is the "key" parameter in the PSE URL

You can find this in the console entry for the search engine you want the key for, by scrolling down to "Custom Search python manage.py makemigrations API" and clicking the "Get started" button:

<br/>

![Google Custom Search JSON API](./images/google_pse_console_api.png)

<br/>

After creating a PSE you neeed to generate a free JSON API key here: https://developers.google.com/custom-search/v1/introduction 

<br/>

### Once you have these two pieces of information, plug them into the template below:

```
{
    "name": "<your-PSE-name>",
    "connector": "opensearch",
    "url": "https://www.googleapis.com/customsearch/v1",
    "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
    "query_mappings": "cx=your-google-search-engine-id",
    "result_mappings": "link=url,snippet=body,cacheId,NO_PAYLOAD",
    "credentials": "key=your-google-API-key"
}
```

<br/>

Then copy/paste this provider into the SearchProvider form http://127.0.0.1:8000/swirl/searchproviders/ as noted above.

<br/>

</p>
</details>

<br/>

<br/>

# Running Searches

There are two ways to run searches. 

<br/>

## Create a Search Object

Searches are JSON dictionaries that define a search that some user or system desires to have run. 

The only required property is some query_string with the actual text. All other properties are optional when creating a Search object. They will have the default values shown below.

<br/>

## Examples

:star: [Search JSON Examples](../Searches/)

<br/>

This query will run the default configuration, which will include 10 results and use of the relevancy_mixer.


```
{
    "query_string": "strategy"
}
```

<br/>

This is the same query, with spellcheck turned on:

```
{
    "query_string": "strategy",
    "pre_query_processor": "spellcheck_query_processor"
}
```

This causes the spellcheck_query_processor to run prior ("pre_query") to federation. 
The spell-corrected query is then sent to each provider.
Spellcheck is not recommended for use with Google PSE and shown here only as an example.

Here's the same query requesting 20 results from source provider 1 and 3 only, with round robin mixer instead of default (relevancy):

```
{
    "query_string": "strategy",
    "results_requested": 20,
    "searchprovider_list": [ 2 ],
    "result_mixer": "round_robin_mixer",
    "retention": 1 
}
```
Note the retention setting will cause the search to be deleted after 1 hour, assuming the [Search Expiration Service](#search-expiration-service) is running.

This variation requests date sorted results from all providers, and round robin mixing instead of relevancy.

```
{
    "query_string": "strategy",
    "sort": "date",
    "result_mixer": "round_robin_mixer"
}
```

You can use relevancy with date=sort just fine, it means you'll get the most relevant and freshest results.

<br/>

Once you have identified a Search definition:

1. Go to http://127.0.0.1:8000/swirl/search/
2. Go to the form at the bottom of the page
3. Change the form to "Raw data" mode and clear any pre-built input
4. Copy/paste the example 
5. Press the POST button

SWIRL will respond with the newly created Search Object, including the id for it:

<br/>

![SWIRL Search Created - Google PSE Example](./images/pse/swirl_search_created.png)

<br/>

## Important: note the id down. We'll use it in the next step to get results.

<br/>

:small_blue_star: To learn about the many options that can be specified as part of a Search, refer to the [Search](#search-object) Object Reference.

<br/>

## Using the OpenSearch Interface

You can also quickly run a search using the OpenSearch interface. This involves adding "?q=your-query-string" to the search URL. 
For example: http://127.0.0.1:8000/swirl/search?q=your-query-here

:stopwatch: SWIRL will not respond immediately when you request this URL. Be patient. 

After 5 or so seconds, SWIRL will redirect you to the fully mixed results page!!

![SWIRL Unified Results - Google PSE Example](./images/pse/swirl_results_mixed_1.png)

Note that are significant limitations to the OpenSearch interface:

* You must URL encode your query; for text queries, this mostly means turning spaces into + signs
* All configured SearchProviders are queried
* Error handling is limited; if no results appear, you should remove the ?q= from the URL and reload to get the list of search objects, and
see the Search.status.

<br/>

:star: Here's a free URL encoder you can use if hand querying: https://www.freeformatter.com/url-encoder.html

<br/>

:warning: There is some evidence that browser prefetching can sometimes send SWIRL a request before you type it
thus creating *two* swirl objects. 

Please [report this to suppport](#get-support) if it happens. We hope to resolve it in the next release.

<br/>

# Viewing Search Objects & API as JSON

Add format=json to any API call to view it as a json string instead of in the Django framework:

:star: http://127.0.0.1:8000/swirl/search/?format=json:

<br/>

# Managing Searches

You can edit any Search by adding the id to the end of the /swirl/search URL. For example: http://127.0.0.1:8000/swirl/search/1/  

![SWIRL Edit Search - Google PSE Example](./images/pse/swirl_search_edit_status_closeup.png)

## From here, you can use the form to:

* DELETE it, forever
* Edit the body of the request and PUT it back

<br/>

If you delete a Search, the associated Result objects are immediately deleted as well. This may be changed in a future release.

<br/>

## Re-Starting, Re-Running, Re-Scoring & Re-Trying a Search

The following options are available to handle failed searches, partial results, or changes to relevancy that you want to run without re-requesting results from searchproviders.

<br/>

| Method | Description | Example URL |
| ------ | ----------- | ----------- |
| Re-start | Edit the query, change Search.status to 'NEW_SEARCH' and PUT to update the object; old result sets are retained and may become duplicates, but [they can be manually removed](#deleting-a-result) first, or you can edit the searchprovider_list | http://127.0.0.1:8000/swirl/search/1/ (then edit and PUT) |
| Re-run | Discards any partial results, resets search status, starts over | http://127.0.0.1:8000/swirl/search?rerun=1 |
| Re-score | Repeats post-result-processing for the specified search; after 7s it redirects to the mixer view | http://127.0.0.1:8000/swirl/search?rescore=1 |

<br/>

## Enabling Spell Correction

To specify spelling correction for the Search.query_string, add this option to the Search object:

```
    "pre_query_processor": "spellcheck_query_processor"
```

Don't forget the comma :-)

Corrections are provided by [TextBlob](https://textblob.readthedocs.io/en/dev/quickstart.html#spelling-correction). It is claimed to be at most ~70% accurate. 

If you want to apply spellcheck to a single provider, put it in the SearchProvider.query_processor property, instead of the Search.pre_query_processor. 

:warning: Use Spellcheck cautiously as it tends to cause a lack of results from sources that have sparse indexes, i.e. not a lot of results. 
It is likely not necessary to use at all with Google PSE, since they already correct the query. (It probably doesn't hurt in this scenario, though.)

<br/>

## Search Expiration

If your SWIRL installation is using the [Search Expiration Service](#search-expiration-service), then users can specify the retention setting for each Search. 

The following table describes the Search.retention field:

<br/>

| Retention Value | Meaning | 
| --------------- | ------- |
| 0 | Retain indefinitely, do not expire |
| 1 | Retain for 1 hour | 
| 2 | Retain for 1 day | 
| 3 | Retain for 1 month |

<br/>

The exact time of expiration is determined by the [Celery Beat Configuration](#configuring-celery-beats--rabbitmq) and the [Search Expiration Service](#search-expiration-service) configuration. 

<br/>

# Managing Results

A Result object is the clean, normalized result for a single Search, from a single SearchProvider. It includes metadata about the SearchProvider.

<br/>

![SWIRL Result Object - Google PSE Example](./images/pse/swirl_result_individual.png)

<br/>

If you want to review all the results from a Search, use a [Result Mixer](#result-mixer-modules) instead.

They are created asynchronously during the federation process. They become available for retrival by search id as soon as a Search.status ends in _READY. HTTP/503 will occur if they are requested prior to this.

<br/>

It is not typical for a user to create a Result object. SWIRL creates them as the result of federated search. 

<br/>

## Viewing Result Objects & API as JSON

Add format=json to any API call to view it as a json string:

:star: http://127.0.0.1:8000/swirl/searchproviders/?format=json:

<br/>

## Deleting a Result

To delete a result Object - for example if you re-run a Search - add the id of the Result to the Result URL. For example: http://127.0.0.1:8000/swirl/results/1

<br/>

## From here, you can use the form to:

* DELETE it, forever
* Edit the body of the request and PUT it back

<br/>

If you delete a Result set, it will not delete the associated Search.

<br/>

# Viewing Unified Results

The main goal of SWIRL specifically, and [federated search](#what-is-federated-search) in general is to see unified results - from all sources. 

Result Mixers are SWIRL modules that do exactly that - organizing results from multiple SearchProviders into a unified result set, including metadata. 
Mixers operate on landed Result data. They can be run again and again and reflect any changes in Result Data. 

To retrieve the default unified results for a Search, add ?search_id= and the id of the Search to the Result URL.

<br/>

:star: For example: http://127.0.0.1:8000/swirl/results?search_id=1

<br/>

SWIRL will respond by having the result_mixer specified in the Search object present the unified results.

![SWIRL Unified Results - Google PSE Examples](./images/pse/swirl_results_mixed_1.png)
![SWIRL Unified Results - Google PSE Examples](./images/pse/swirl_results_mixed_2.png)

<br/>

## Specifying a Different Mixer

You can specify a different Mixer on-the-fly by adding the URL parameter result_mixer. 
The following table presents the current mixer options:

| Mixer | Description | Notes |
| ----- | ----------- | ----- | 
| relevancy_mixer | Organizes results by [relevancy](#understanding-relevancy) score (descending), then rank (ascending) | The default; depends on relevancy_processor being installed as the search.post_result_processor (also the default) |
| round_robin_mixer | Organizes results by taking 1 result from each responding source, alternating | Good for searches with search.sort set to 'date' or anytime you want a cross section of results instead of just the ones with the most evidence | 
| stack_mixer | Organizes results by taking n results from each responding source, where n is results_requested / number of sources | Good for cross section of data |
| stack_2_mixer | Organizes results by taking 2 from each responding source, alternating | Good for cross sections of data with 4-6 providers |
| stack_3_mixer | Organizes results by taking 3 from each responding source, alternating | Good for cross sections of data with few providers | 

<br/>

:star: For example: http://127.0.0.1:8000/swirl/results?search_id=1&result_mixer=stack_2_mixer

<br/>

![SWIRL Unified Results - Stack Mixer - Google PSE Examples](./images/pse/swirl_results_mixer_change_1.png)
![SWIRL Unified Results - Stack Mixer - Google PSE Examples](./images/pse/swirl_results_mixer_change_2.png)

<br/>

SWIRL will respond by having the specified mixer present the unified results.

<br/>

## Understanding Relevancy

When the result_mixer is set to relevancy_mixer, and the search.post_result_processor is set to cosine_relevancy_processor - the defaults - SWIRL will return a result set that features the most relevant responses to the search, across all sources.

```
{
    "messages": [
        "##S#W#I#R#L##1#0################################################################",
        "Retrieved 0 of 0 results from: Funding DB Search",
        "Retrieved 1 of 3 results from: Document DB Search",
        "Retrieved 10 of 38 results from: Enron Email ES Local",
        "Retrieved 10 of 407,000 results from: Enterprise Search PSE",
        "Retrieved 10 of 13,300,000,000 results from: Strategy Consulting PSE",
        "Retrieved 10 of 14,600 results from: Mergers and Acquisitions PSE",
        "Post processing of results by cosine_relevancy_processor updated 41 results",
        "Results ordered by: relevancy_mixer"
    ],
    "info": {
        "Funding DB Search": {
            "found": 0,
            "retrieved": 0,
            "query_to_provider": "select * from funding where city like '%%strategy%%' or company like '%%strategy%%';",
            "result_processor": "generic_result_processor"
        },
        "Document DB Search": {
            "found": 3,
            "retrieved": 1,
            "query_to_provider": "select * from documents where title like '%%strategy%%' or body like '%%strategy%%' limit 10;",
            "result_processor": "generic_result_processor"
        },
        "Enron Email ES Local": {
            "found": 38,
            "retrieved": 10,
            "query_to_provider": "index='email', query={'query_string': {'query': 'strategy', 'default_field': 'content'}}",
            "result_processor": "generic_result_processor"
        },
        "Enterprise Search PSE": {
            "found": 407000,
            "retrieved": 10,
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=0c38029ddd002c006&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&start=1&q=strategy",
            "result_processor": "generic_result_processor"
        },
        "Strategy Consulting PSE": {
            "found": 13300000000,
            "retrieved": 10,
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=7d473806dcdde5bc6&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&start=1&q=strategy",
            "result_processor": "generic_result_processor"
        },
        "Mergers and Acquisitions PSE": {
            "found": 14600,
            "retrieved": 10,
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=b384c4e79a5394479&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&start=1&q=strategy",
            "result_processor": "generic_result_processor"
        },
        "search": {
            "query_string": "strategy",
            "query_string_processed": "strategy"
        },
        "results": {
            "next_page": "/swirl/results/?search_id=14&result_mixer=round_robin_mixer&page=2",
            "retrieved": 10
        }
    },
    "results": [
        {
            "rank": 7,
            "score": 1.0,
            "title": "Your *Strategy* Needs a *Strategy*",
            "url": "https://www.bcg.com/publications/collections/your-strategy-needs-strategy/intro",
            "body": "This new book from BCG's *Strategy* Lab cuts through the clutter of *strategy* frameworks and provides clarity on which approach to *strategy* and execution—or which ...",
            "date_published": "unknown",
            "date_retrieved": "2022-04-10 00:06:37.079250",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "1VfUY4PbJP8J"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ],
                    "body": [
                        "strategy"
                    ]
                },
                "similarity": 0.8,
                "boosts": [
                    "term_match 0.2"
                ]
            }
        },
        {
            "rank": 9,
            "score": 1.0,
            "title": "*Strategy*",
            "url": "https://www2.deloitte.com/us/en/insights/topics/strategy.html",
            "body": "Consulting. Innovation, transformation and leadership occur in many ways. At Deloitte, our ability to help solve clients' most complex issues is distinct.",
            "date_published": "unknown",
            "date_retrieved": "2022-04-10 00:06:37.114367",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "6fGaLtBaraUJ"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ]
                },
                "similarity": 1.0,
                "boosts": []
            }
        },
        {
            "rank": 2,
            "score": 0.95,
            "title": "*Strategy*& - the global *strategy* consulting team at PwC",
            "url": "https://www.strategyand.pwc.com/",
            "body": "From the start, *Strategy*& creates a *strategy* for you that works today and delivers into tomorrow. We make *strategy* real.",
            "date_published": "unknown",
            "date_retrieved": "2022-04-10 00:06:36.978837",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "iygA_Hu_O24J"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ],
                    "body": [
                        "strategy"
                    ]
                },
                "similarity": 0.75,
                "boosts": [
                    "term_match 0.2"
                ]
            }
        },
        {
            "rank": 5,
            "score": 0.95,
            "title": "Business Growth *Strategy* Consulting | BCG",
            "url": "https://www.bcg.com/capabilities/corporate-finance-strategy/business-strategy",
            "body": "BCG focuses on three critical deliverables to develop winning business growth strategies. Learn more about our business *strategy* consulting approach.",
            "date_published": "unknown",
            "date_retrieved": "2022-04-10 00:06:37.042919",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "emuJsOnOzwwJ"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ],
                    "body": [
                        "strategy"
                    ]
                },
                "similarity": 0.75,
                "boosts": [
                    "term_match 0.2"
                ]
            }
        },
        {
            "rank": 1,
            "score": 0.89,
            "title": "*Strategy* Consulting Services & Solutions | Accenture",
            "url": "https://www.accenture.com/us-en/about/strategy-index",
            "body": "Accenture *Strategy* enables clients to thrive by combining technology fluency with industry expertise for solutions that master competitive agility.",
            "date_published": "unknown",
            "date_retrieved": "2022-04-10 00:06:36.956630",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "zOUsVXwN5V0J"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ],
                    "body": [
                        "strategy"
                    ]
                },
                "similarity": 0.69,
                "boosts": [
                    "term_match 0.2"
                ]
            }
        },
        {
            "rank": 3,
            "score": 0.89,
            "title": "How Customer Expansion *Strategy* Catapults Business Growth",
            "url": "https://www.searchunify.com/blog/how-customer-expansion-strategy-catapults-business-growth/",
            "body": "Sep 28, 2021 <b>...</b> An effective customer expansion <b>*strategy*</b> understands customers &amp; their expectations. Then, accordingly provides relevant offers to upsell&nbsp;...",
            "date_published": "unknown",
            "date_retrieved": "2022-04-10 00:06:36.986653",
            "author": "",
            "searchprovider": "Enterprise Search PSE",
            "payload": {
                "cacheId": "9Zr6Xx7VclIJ"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ],
                    "body": [
                        "strategy"
                    ]
                },
                "similarity": 0.69,
                "boosts": [
                    "term_match 0.2"
                ]
            }
        },
        {
            "rank": 6,
            "score": 0.85,
            "title": "Western *Strategy* Summaries",
            "url": "allen-p/_sent_mail/305.",
            "body": "Message-ID: <13777999.1075855691899.JavaMail.evans@thyme>\nDate: Fri, 3 Mar 2000 04:33:00 -0800 (PST)\nFrom: phillip.allen@enron.com\nTo: mike.grigsby@enron.com\nSubject: Western *Strategy* Summaries\nMime-Version: 1.0\nContent-Type: text/plain; charset=us-ascii\nContent-Transfer-Encoding: 7bit\nX-From: Phillip K Allen\nX-To: Mike Grigsby\nX-cc: \nX-bcc: \nX-Folder: \\Phillip_Allen_Dec2000\\Notes Folders\\'sent mail\nX-Origin: Allen-P\nX-FileName: pallen.nsf\n\n---------------------- Forwarded by Phillip K Allen/HOU/ECT on 03/03/2000 \n12:30 PM ---------------------------\n\n\nTim Heizenrader\n03/03/2000 07:25 AM\nTo: James B Fallon/HOU/ECT@ECT, Phillip K Allen/HOU/ECT@ECT\ncc:  \nSubject: Western *Strategy* Summaries\n\nSlides from yesterday's meeting are attached: \n",
            "date_published": "2000-03-03 04:33:00",
            "date_retrieved": "2022-04-10 00:06:35.640365",
            "author": "Phillip K Allen",
            "searchprovider": "Enron Email ES Local",
            "payload": {
                "_source.to": "Mike Grigsby"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ],
                    "body": [
                        "strategy"
                    ]
                },
                "similarity": 0.65,
                "boosts": [
                    "term_match 0.2"
                ]
            }
        },
        {
            "rank": 8,
            "score": 0.85,
            "title": "*Strategy* consulting services | EY - US",
            "url": "https://www.ey.com/en_us/strategy-transactions/strategy-services",
            "body": "EY-Parthenon *strategy* consulting services can develop growth, transaction or turnaround strategies to help organizations increase profitability and ...",
            "date_published": "unknown",
            "date_retrieved": "2022-04-10 00:06:37.097333",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "BuVvBXcmGawJ"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ],
                    "body": [
                        "strategy"
                    ]
                },
                "similarity": 0.65,
                "boosts": [
                    "term_match 0.2"
                ]
            }
        },
        {
            "rank": 10,
            "score": 0.85,
            "title": "Western *Strategy* Summaries",
            "url": "allen-p/all_documents/305.",
            "body": "Message-ID: <5105744.1075855672142.JavaMail.evans@thyme>\nDate: Fri, 3 Mar 2000 04:33:00 -0800 (PST)\nFrom: phillip.allen@enron.com\nTo: mike.grigsby@enron.com\nSubject: Western *Strategy* Summaries\nMime-Version: 1.0\nContent-Type: text/plain; charset=us-ascii\nContent-Transfer-Encoding: 7bit\nX-From: Phillip K Allen\nX-To: Mike Grigsby\nX-cc: \nX-bcc: \nX-Folder: \\Phillip_Allen_Dec2000\\Notes Folders\\All documents\nX-Origin: Allen-P\nX-FileName: pallen.nsf\n\n---------------------- Forwarded by Phillip K Allen/HOU/ECT on 03/03/2000 \n12:30 PM ---------------------------\n\n\nTim Heizenrader\n03/03/2000 07:25 AM\nTo: James B Fallon/HOU/ECT@ECT, Phillip K Allen/HOU/ECT@ECT\ncc:  \nSubject: Western *Strategy* Summaries\n\nSlides from yesterday's meeting are attached: \n",
            "date_published": "2000-03-03 04:33:00",
            "date_retrieved": "2022-04-10 00:06:35.778476",
            "author": "Phillip K Allen",
            "searchprovider": "Enron Email ES Local",
            "payload": {
                "_source.to": "Mike Grigsby"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ],
                    "body": [
                        "strategy"
                    ]
                },
                "similarity": 0.65,
                "boosts": [
                    "term_match 0.2"
                ]
            }
        },
        {
            "rank": 7,
            "score": 0.83,
            "title": "Western *Strategy* Briefing",
            "url": "allen-p/_sent_mail/317.",
            "body": "Message-ID: <10110194.1075855692193.JavaMail.evans@thyme>\nDate: Fri, 11 Feb 2000 07:39:00 -0800 (PST)\nFrom: phillip.allen@enron.com\nTo: mike.grigsby@enron.com\nSubject: Western *Strategy* Briefing\nMime-Version: 1.0\nContent-Type: text/plain; charset=us-ascii\nContent-Transfer-Encoding: 7bit\nX-From: Phillip K Allen\nX-To: Mike Grigsby\nX-cc: \nX-bcc: \nX-Folder: \\Phillip_Allen_Dec2000\\Notes Folders\\'sent mail\nX-Origin: Allen-P\nX-FileName: pallen.nsf\n\n---------------------- Forwarded by Phillip K Allen/HOU/ECT on 02/11/2000 \n03:38 PM ---------------------------\n\n\nTim Heizenrader\n02/10/2000 12:55 PM\nTo: James B Fallon/HOU/ECT@ECT, Phillip K Allen/HOU/ECT@ECT\ncc: Tim Belden/HOU/ECT@ECT \nSubject: Western *Strategy* Briefing\n\nSlides for today's meeting are attached: \n",
            "date_published": "2000-02-11 07:39:00",
            "date_retrieved": "2022-04-10 00:06:35.674315",
            "author": "Phillip K Allen",
            "searchprovider": "Enron Email ES Local",
            "payload": {
                "_source.to": "Mike Grigsby"
            },
            "explain": {
                "matches": {
                    "title": [
                        "strategy"
                    ],
                    "body": [
                        "strategy"
                    ]
                },
                "similarity": 0.63,
                "boosts": [
                    "term_match 0.2"
                ]
            }
        }
    ]
}
```

Note that SWIRL also provides the rank value, which is the result number assigned by the responding source. This allows you to see what SWIRL thought was relevant vs what the sources thought.

Relevancy scores are actually assigned during post-result processing by the [cosine_relevancy_processor](../swirl/processors/relevancy.py). This processor scores each result using [weighted cosine similarity](https://en.wikipedia.org/wiki/Cosine_similarity) between the query and the matching result fields. 

It also boosts results based on:

* Each query terms matched 
* Each two-word phrase from the query matched
* Each field that matches all query terms

If you want to configure the weights, modify the RELEVANCY_CONFIG dictionary in the relevancy.py module linked above.

<br/>

## Paging Through Results

Get more results by adding a page parameter. For example:

:star: For example: http://127.0.0.1:8000/swirl/results?search_id=1&page=2

:warning:  For SWIRL Preview 2, will only page through saved Results and won't request more pages from a provider.

If you need more mixed results, increase the results_per_query value in your searchproviders. A setting of 20 or 50 or 100 
will ensure that you have lots of results to page through with the mixer.

<br/>

# Using Postman

[Postman](https://learning.postman.com/docs/getting-started/introduction/) is a powerful API client you can use to manipulate SWIRL via the APIs.

:star: Download and import the [SWIRL Postman Collection](SWIRL.postman_collection.json) 

<br/>

Prior to placing any requests, you have to authenticate using the admin password you created during [installation](INSTALLATION_GUIDE.md#create-the-admin-account).

Click on the elipsis menu to the right of the collection name and select Edit, then Authentication to reach this page.

<br/>

![Postman with SWIRL Collection in Authentication mode](./images/postman_2.png)

<br/>

![Postman with SWIRL Collection](./images/postman_1.png)

<br/>

# swirl_load.py Command Line Interface CLI

You can use swirl_load.py to bulk-load SearchProvider, Search or even Result objects. 

```
cd scripts
python swirl_load.py ../SearchProviders/enterprise_search_pse.json
```

You can use swirl_load to load single dictionary objects, or lists of them. It automatically detects the type of object based on the keys. Use the --debug option to see the items and URLs as they go out.

:warning: Be careful bulk-loading Search objects; if they have status=NEW_SEARCH, they will begin executing simultaneously!

<br/>

<br/>

# Further Reading

:small_blue_diamond: [Developer Guide](DEVELOPER_GUIDE.md)
:small_blue_diamond: [Admin Guide](ADMIN_GUIDE.md)

<br/>

<br/>

# Get Support

Please email [swirl-support@probstein.com](mailto:swirl-support@probstein.com) for support.

<br/>