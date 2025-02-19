---
layout: default
title: Developer Reference
nav_order: 19
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# Developer Reference

{: .warning }
This document applies to all SWIRL Editions. 

# State Table

The following table describes in more detail all the steps in the federation process, with the associated `status` and other important state information.

| Action | Module | Status | Notes | 
| ---------- | ---------- | ---------- | ---------- | 
| Search object created | views.py SearchViewSet.list() | Search.status:<br/>NEW_SEARCH<br/>UPDATE_SEARCH | Required:<br/>`Search.query_string` |
| Pre-processing | search.py search() | Search.status:<br/>PRE_PROCESSING | Checks permissions<br/>Loads the Search object  |
| Pre-query processing | search.py search() | Search.status:<br/>PRE_QUERY_PROCESSING | Processes `Search.query_string` and updates `Search.query_string_processed` |
| Federation | search.py search() | Search.status:<br/>FEDERATING<br/>FEDERATING_WAIT_*<br/>FULL_RESULTS | Creates one Connector for each SearchProvider in the Search |
| Connector Init | connectors/connector.py<br/>connectors/db_connector.py | Connector.status:<br/>INIT<br/>READY | Loads the Search and SearchProvider | 
| Connector Federate | federate() | Connector.status:<br/>FEDERATING |  |
| Connector Query Processing|  process_query() | FEDERATING | Process `Search.query_string_processed` and store in `Connector.query_string_to_provider` |
| Connector Construct Query | construct_query() | FEDERATING | Take `Connector.query_string_to_provider` and create `Connector.query_to_provider` |
| Connector Validate Query | validate_query() | FEDERATING | Returns "False" if `Connector.query_to_provider` is empty |
| Connector Execute Search | execute_search () | FEDERATING | Connect to the SearchProvider<br/>Execute the search using `Search.query_to_provider`<br/>Store the response in `Connector.response` | 
| Connector Normalize Response | normalize_response() | FEDERATING | Transform `Connector.response` into JSON list of dicts<br/>Store it in `Connector.results` |
| Connector Process Results | process_results() | Connector.status:<br/>FEDERATING<br/>READY | Process `Connector.results` |
| Connector Save Results | save_results() | Connector.status:<br/>READY | Returns "True" |
| Post-result processing | search.py search() | Search.status:<br/>POST_RESULT_PROCESSING<br/>FULL_RESULTS_READY<br/>FULL_UPDATE_READY | Runs the `post_result_processors`<br/>Updates Result objects | 

# `Search.Status`

## Normal States

| Status | Meaning | 
| ---------- | ---------- |
| NEW_SEARCH | The search object is to be executed immediately |
| UPDATE_SEARCH | The search object is to be updated immediately |
| PRE_PROCESSING | SWIRL is performing pre-processing for this search |
| PRE_QUERY_PROCESSING | SWIRL is performing pre-query processing for this search |
| FEDERATING | SWIRL is provisioning Celery workers with Connectors and waiting for results |
| FEDERATING_WAIT_n | SWIRL has been waiting for the number of seconds indicated by `n` |
| FULL_RESULTS | SWIRL has received all results |
| NO_RESULTS | SWIRL received no results |
| PARTIAL_RESULTS | SWIRL has received results from some providers, but not all |
| POST_RESULT_PROCESSING | SWIRL is performing post-result processing |
| PARTIAL_RESULTS_READY | SWIRL has processed results from responding providers |
| PARTIAL_UPDATE_READY | SWIRL has processed updated results from responding providers  |
| FULL_RESULTS_READY | SWIRL has processed results for all specified providers  |
| FULL_UPDATE_READY | SWIRL has processed updated results for all specified providers |

## Error States

| Status | Meaning | 
| ---------- | ---------- |
| ERR_DUPLICATE_RESULT_OBJECTS | More than one Result object was found; [contact support](#support) for assistance. |
| ERR_NEED_PERMISSION | The Django User did not have sufficient permissions to perform the requested operation. More: [Permissioning Normal Users](Admin-Guide.html#permissioning-normal-users) | 
| ERR_NO_ACTIVE_SEARCHPROVIDERS | Search failed because no specified SearchProviders were active |
| ERR_NO_RESULTS | SWIRL has not received results from any source |
| ERR_NO_SEARCHPROVIDERS | Search failed because no SearchProviders were specified |
| ERR_RESULT_NOT_FOUND | A Result object that was expected to be found, was not; [contact support](#support) for assistance. |
| ERR_RESULT_PROCESSING | An error occurred during Result processing - check the `logs/celery-worker.log` for details | 
| ERR_SUBSCRIBE_PERMISSIONS | The user who created the Search object lacks permission to enable `subscribe` mode |

# Key Module List

* ### [View Controller](https://github.com/swirlai/swirl-search/tree/main/swirl/views.py)
* ### [Search Workflow](https://github.com/swirlai/swirl-search/tree/main/swirl/search.py)
* ### [Connectors](https://github.com/swirlai/swirl-search/tree/main/swirl/connectors)
* ### [Processors](https://github.com/swirlai/swirl-search/tree/main/swirl/processors)
* ### [Mixers](https://github.com/swirlai/swirl-search/tree/main/swirl/mixers)
* ### [Query Transforms](https://github.com/swirlai/swirl-search/tree/main/swirl/processors/transform_query_processor.py)

# SearchProvider Object

A SearchProvider defines some searchable source. It includes metadata identifying the type of connector used to search the source and much more. Many properties are optional when creating a SearchProvider object. They will have the default values shown below.

## Properties

| Property | Description | Default Value (`Example Value`) | 
| ---------- | ---------- | ---------- |
| id | Unique identifier for the SearchProvider | Automatic (`1`) |
| name | Human-readable name for the source | "" (`"Enterprise Search PSE"`) |
| owner | The username of the Django user that owns the object | Logged-in user (`"admin"`) |
| shared | Boolean setting: if `true` the SearchProvider can be searched by other users, if `false` it is only available to the `owner` | true (`false`) |
| date_created | The time and date at which the SearchProvider was created | Automatic (`2022-02-28T17:55:04.811262Z`) |
| date_updated | The time and date at which the SearchProvdier was updated  | Automatic (`2022-02-29T18:03:02.716456Z`) |
| active | Boolean setting: if `true` the SearchProvider is used, if `false` it is ignored when federating | false (`true`) |
| default | Boolean setting: if `true` the SearchProvider will be queried for searches that don't specify a `searchprovider_list`; if `false`, the SearchProvider must be specified in the `searchprovider_list` | false (`true`) |
| connector | Name of the Connector to use for this source | "" (`"RequestsGet"`) | 
| url | The URL or other string including file path needed by the Connector for this source; not validated | "" (`"https://www.googleapis.com/customsearch/v1"`) |
| query_template | A string with optional variables in form `{variable}`; the Connector will bind the `query_template` with required data including the `url` and `query_string`, as well as any `query_mappings` or `credentials`, at runtime. Note this format is not yet used by the [Sqlite3 Connector](#sqlite3). | "" (`"{url}?q={query_string}"`) |
| post_query_template | For the RequestsPost Connector: valid JSON and a marker for the query text which then sent as the POST body | "" (`"query": "{query_string}","limit": "100"`) |
| http_request_headers | A string for passing custom HTTP Request Header values to the source along with query| "" (`"Accept": "application/vnd.github.text-match+json"`) |
| query_processors | A list of processors to use to prepare the query for this source | "" (`"AdaptiveQueryProcessor"`) |
| query_mappings | A string defining the mappings for the query. Depends on the Connector used. | "" (`"cx=your-google-search-engine-key"`) |
| result_grouping_field | Used with the `DedupeByFieldResultProcessor` result processor, this string defines the specific source field to use for duplicate suppression. | "" (`"resource.conversationId"`) |
| result_processors | A list of processors to use to normalize results from this source | "CosineRelevancyResultProcessor" (`"MappingResultProcessor","CosineRelevancyResultProcessor"`) |
| response_mappings | List of response keys and JSONPaths to transform this providers response into a JSON result set | "" (`"FOUND=searchInformation.totalResults, RETRIEVED=queries.request[0].count, RESULTS=items"`) |
| result_mappings | List of keys, optionally with values; see [SP Guide, Result Mappings](SP-Guide.html#result-mappings) for more information| "" (`"url=link,body=snippet,cacheId,NO_PAYLOAD"`) |
| results_per_query | The number of results to request from this source for each query | 10 (`20`) |
| credentials | The credentials to use for this source. Dependent on the source. | "" (`"key=your-google-json-api-key"`) |
| eval_credentials | A credential variable set in the session and then be used in the SearchProvider. | "" (`"session["my-connector-token"]"`) |
| tags | List of strings that organize SearchProviders into groups. | "" (`"News", "EnterpriseSearch"`) |

{: .warning }
The `CosineRelevancyResultProcessor` must be after the `MappingResultProcessor` in the default list of `result_processors`.

## APIs

| URL | Explanation |
| ---------- | ---------- |
| /swirl/searchproviders/      | List SearchProvider objects, newest first; create a new one using the POST button and the form at the bottom |
| /swirl/searchproviders/id/ | Retrieve a specific SearchProvider object; destroy it using the DELETE button; edit it using the PUT button and the form at the bottom  |

# Search Object

Search objects are JSON dictionaries that define the searches some user or system desires to have run. They have unique IDs. They may be linked to by Result objects.

The only required property is a `query_string` with the actual text to be searched. All other properties are optional when creating a Search object, and they will have default values shown below. As SWIRL executes a search, asynchronously, it will update properties of the Search object like `status` and `result_url` in real-time.

## Properties

| Property | Description | Default Value (`Example Value`) | 
| ---------- | ---------- | ---------- |
| id | Unique identifier for the Search | Automatic (`search_id=1`) |
| owner | The username of the Django user that owns the object | logged-in user (`admin`) |
| date_created | The time and date at which the Search was created | Automatic (`2022-02-28T17:55:04.811262Z`) |
| date_updated | The time and date at which the Search was updated  | Automatic (`2022-02-28T17:55:07.811262Z`) |
| query_string | The query to be federated - the only required field! | "" (`knowledge management`) | 
| query_string_processed | The Search query, modified by any pre-query processing | "" ("") |
| sort | The type of search to be run | relevancy (`date`) | 
| results_requested | The number of results, overall, the user has requested | 10 (`25`) | 
| searchprovider_list | A list of the SearchProviders to search for this query; an empty list, the default, searches all sources | [] (`[ "Enterprise Search Engines - Google PSE" ]`) |
| subscribe | If `True`, SWIRL will update this Search as per the Celery-Beats schedule | False (`True`) |
| status | The execution status of this search (see below) | NEW_SEARCH (`FULL_RESULTS_READY`) |
| pre_query_processors | A list of processors to apply to the query before federation starts | "" (`[ "SpellcheckQueryProcessor" ]`) |
| post_result_processors | A list of result processors to apply to the results after federation is complete | "" (`[ "DedupeByFieldPostResultProcessor", "CosineRelevancyPostResultProcessor" ]`) |
| result_url | Link to the initial Result object for the Search which uses the `RelevancyMixer` | Automatic (`"http://localhost:8000/swirl/results?search_id=17&result_mixer=RelevancyMixer"`) |
| new_result_url | Link to the updated Result object for the search which uses the `RelevancyNewItemsMixer` | Automatic (`"http://localhost:8000/swirl/results?search_id=17&result_mixer=RelevancyNewItemsMixer"`) | 
| messages | Messages from SearchProviders | "" (`Retrieved 1 of 1 results from: Document DB Search`) | 
| result_mixer | The name of the Mixer object (see below) to use for ordering results | RoundRobinMixer (`Stack2Mixer`) | 
| retention | The retention setting for this object; `0` = retain indefinitely; see [Search Expiration Service](Admin-Guide.html#search-expiration-service) for details | 0 (`2` for daily deletion) | 
| tags | Parameter (string) that can be passed into a search and will be attached to the Search object that is stored in SWIRL | "" (`{ "query_string": "knowledge management", "tags": ["max_length:50"] }`) |

{: .highlight }
There are some special Search tags that control query processing.  For example, the `SW_RESULT_PROCESSOR_SKIP` Search tag can be used to skip a processor for the Search it is specified for:  `SW_RESULT_PROCESSOR_SKIP:DedupeByFieldResultProcessor`

## APIs

| URL | Explanation |
| ---------- | ---------- |
| /swirl/search/      | List Search objects, newest first; create a new one using the form at the bottom and the POST button |
| /swirl/search/id/ | Retrieve a specific Search object; destroy it using the DELETE button; edit it using the form at the bottom and the  PUT button |
| /swirl/search/?q=some+query | Create a Search object with default values except for `query_string` which is set to the `q=` parameter value; return redirects to result set; also accepts `providers` parameter |
| /swirl/search/?qs=some+query | Create Search object as above, but return results synchronously; also accepts `providers` and `result_mixer` parameters |
| /swirl/search/?rerun=id | Re-run a Search, deleting any previously stored Results |
| /swirl/search/?update=id | [Update a Search](Developer-Guide.html#update-a-search) with new results since the last time you ran it |

# Result Objects

A Result object is the normalized, re-ranked result for a single Search, from a single SearchProvider. They are created at the end of the federated search process in response to the creation of a Search object.  They are the only SWIRL object that has a foreign key (`search.id`).

Only Connectors should create Result objects. 

Developers are free to operate on individual Results as needed for their application. 

However, the [goal of SWIRL](index.html) (and federated search in general) is to provide unified results from all sources. SWIRL uses Mixers to make this quick and easy.

## Properties

| Property | Description | `Example Value` | 
| ---------- | ---------- | ---------- | 
| id | Unique identifier for the Result | `1` |
| owner | The username of the Django user that owns the object | `admin` |
| date_created | The time and date at which the Result was created. | `2022-02-28T17:55:04.811262Z` |
| date_updated | The time and date at which the Result was updated  | `2022-02-28T19:55:02.752962Z` |
| search_id | The `id` of the associated Search; there may be many Result objects with this `id` | `18` | 
| searchprovider | The name value of the SearchProvider that provided this result list | `"OneDrive Files - Microsoft 365"` |
| query_to_provider | The exact query sent to the SearchProvider | `https://www.googleapis.com/customsearch/v1?cx=google-search-engine-id&key=google-json-api-key&q=strategy` |
| query_processors | The names of the Processors, specified in the SearchProvider, that processed the query | `"AdaptiveQueryProcessor"` |
| result_processors | The names of the Processors, specified in the SearchProvider, that normalized the results | `"MappingResultProcessor","CosineRelevancyResultProcessor"` |
| result_processor_json_feedback | A list of processors that responded | (*See a full result object*) |
| messages | A list of any messages (strings) from the SearchProvider | `Retrieved 10 of 249 results from: OneDrive Files - Microsoft 365` |
| status | The readiness of the result set | `READY` |
| retrieved | The number of results SWIRL retrieved from this SearchProvider for this query | `10` |
| found | The total number of results reported by the SearchProvider for this query | `2309` |
| time | The time it took for the SearchProvider to create this result set, in seconds | `1.9` |
| json_results | The normalized JSON results from this SearchProvider | (*See below*) | 

## `json_results`

| Field | Description | Example |
| ---------- | ---------- | ---------- |
| swirl_rank | SWIRL's relevancy ranking for this result | `1` |
| swirl_score | A metric showing the relevancy of the result to the query. It is not meant to be meaningful as a number otherwise. It is only shown if [&explain=True](Developer-Guide.html#understand-the-explain-structure) is set. | `1890.6471312936828` |
| searchprovider | The human-readable name for the SearchProvider | `"OneDrive Files - Microsoft 365"` |
| searchprovider_rank | The SearchProvider's ranking of this result | `3`
| title | The source-reported title for this result, with search term matches highlighted | `German car industry to invest in <em>electric</em> <em>vehicles</em> ...` |
| url | The URL for this result; may be reported by the source and/or calculated by SWIRL | `http://pwc.com/etc` |
| body | The source-reported result snippet(s), with search term matches highlighted | `<em>Technology</em> strategy encompasses a full set of Consulting capabilities ...` |
| date_published | The source-reported time and date of publication of this result, when available (`unknown` if not). This is the field used by the [DateMixer](#mixers-1) | `unknown` |
| date_published_display | Optional SearchProvider field for mapping a different publish date value for display purposes. | `... date_published=foo.bar.date1,date_published_display=foo.bar.date2 ...` |
| date_retrieved | The time and date at which SWIRL received this result from the source | `2022-02-20 03:45:03.207909` |
| author | The source-reported author of this result, when available | `"CNN staff"` |
| title_hit_highlights | A list of highlights found in title |  |
| body_hit_highlights | A list of highlights found in the body |  |
| payload | A dictionary of all remaining keys in the SearchProvider's response | `{}` |
| explain | A dictionary containing (a) the matching word stems, (b) similarity scores for each match in each field, (c) length adjustments and other metadata, (d) `hits` information. It is only shown if [&explain=True](Developer-Guide.html#understand-the-explain-structure) is set. | `{}` |

{: .highlight }
Note that PAYLOAD can be totally different from SearchProvider to SearchProvider. It is up to the caller to access the PAYLOAD and extract whatever is needed, generally by making a new Processor (see below) or adding `result_mappings`.

## APIs

| URL | Explanation |
| ---------- | ---------- |
| /swirl/results/      | List Result objects, newest first; create a new one using the POST button and form at bottom |
| /swirl/results/id/ | Retrieve a specific Result object; destroy it using the DELETE button; edit it using the PUT button and form at bottom  |
| /swirl/results/?search_id=search_id | Retrieve unified Results for a specific Search, ordered by the Mixer specified; also accepts `result_mixer` and `page` parameters|

# Connectors

Connectors are objects responsible for searching a specific type of SearchProvider, retrieving the results and normalizing them to the SWIRL format. This includes calling query and result processors.

Both [`connector.py`](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/connector.py) and [`db_connectory.py`](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/db_connector.py) are base classes from which other connector classes are derived.  While [`requests.py`](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/requests.py) is a wrapper called by `RequestsGet`.  Two utility functions, [`mappings.py`](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/mappings.py) and [`utils.py`](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/utils.py), can be used by other Connectors.

{: .highlight }
Note that the [`requests.py`](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/requests.py) connector automatically converts XML responses to JSON for mapping in SearchProvider configurations.

The following table describes the included source Connectors:

| Connector | Description | Inputs |
| ---------- | ---------- | ---------- |
| BigQuery | Searches Google BigQuery | `query_template`, `credentials` (project JSON token file) |
| GenAI | Asks LLM questions for direct answer | `credentials` |
| Elastic | Searches Elasticsearch | `url` or `cloud_id`, `query_template`, `index_name`, `credentials` |
| Microsoft Graph | Uses the Microsoft Graph API to search M365 content | `credentials` |
| Mongodb | Searches a Mongodb Atlas search index | `mongo_uri`, `database_name`, `collection_name`, `credentials` |
| OpenSearch | Searches OpenSearch | `url`, `query_template`, `index_name`, `credentials` |
| Oracle | Tested against 23c Free (and presumably supporting earlier versions) | `credentials` |
| PostgreSQL | Searches PostgreSQL database | `url` (connection parameters), `query_template`, `credentials` |
| RequestsGet | Searches any web endpoint using HTTP/GET with JSON response, including Google PSE, SOLR, Northern Light and more (see below) | `url`, `credentials` |
| RequestsPost | Searches any web endpoint using HTTP/POST with JSON response, including M365 | `url`, `credentials` |
| Snowflake | Searches Snowflake datasets | `credentials`, `database`, `warehouse` |
| Sqlite3 | Searches SQLite3 databases | `url` (database file path), `query_template` |

Connectors are specified in, and configured by, SearchProvider objects. 

## BigQuery

The [BigQuery connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/bigquery.py) uses the Google Cloud Python package. 

The included [BigQuery SearchProvider](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/funding_db_bigquery.json) is intended for use with the [Funding Data Set](#funding-data-set) but can be adapted to most any configuration.

``` json
{
    "name": "Company Funding Records - BigQuery",
    "active": false,
    "default": false,
    "connector": "BigQuery",
    "query_template": "select {fields} from `{table}` where search({field1}, '{query_string}') or search({field2}, '{query_string}');",
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "fields=*,sort_by_date=fundedDate,table=funding.funding,field1=company,field2=city",
    "result_processors": [
        "MappingResultProcessor",	
        "CosineRelevancyResultProcessor"
    ],
    "result_mappings": "title='{company}',body='{company} raised ${raisedamt} series {round} on {fundeddate}. The company is located in {city} {state} and has {numemps} employees.',url=id,date_published=fundeddate,NO_PAYLOAD",
    "credentials": "/path/to/bigquery/token.json",
    "tags": [
        "Company",
        "BigQuery",
        "Internal"
    ]
}
```

More information: [BigQuery Documentation](https://cloud.google.com/bigquery/docs)

## GenAI


The [GenAI Connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/gen_ai.py) makes use of the OpenAI chat completion API. It will return at most one result.

LLM responses usually rank highly since they are written on-the-fly in response to the user's query, reflect the terminology associated with that query, and are titled for the query.

The included [SearchProvider](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/gen_ai.json) is pre-configured with a "Tell me about: ..." prompt.  The [`GenAIQueryProcessor`](https://github.com/swirlai/swirl-search/blob/main/swirl/processors/gen_ai_query.py) also contains other query options for using LLMs that follow the OpenAI standard.

``` json
{
    "name": "GenAI - OpenAI",
    "active": false,
    "default": true,
    "connector": "GenAI",
    "url": "",
    "query_template": "",
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "PROMPT='Tell me about: {query_to_provider}'",
    "result_processors": [
        "GenericResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "response_mappings": "",
    "result_mappings": "",
    "results_per_query": 10,
    "credentials": "your-openai-API-key-here",
    "tags": [
        "GenAI",
        "Question"
    ]
}
```

The `Question` and `GenAI` SearchProvider Tags make it easy to target the LLM by starting a query with either of them. For example:

``` shell
Question: Tell me about knowledge management software?
```

### GenAI SearchProvider Tags

The following three Tags are available for use in the GenAI SearchProvider to help shape the Prompt or Default Role passed to GenAI along with the user's query.  To utilize these options:
1. Add a valid OpenAI API Key to SWIRL's `.env` file (found in the `swirl-home` directory), and then restart the SWIRL for it to take effect.
2. Add the `GenAIQueryProcessor` to the SearchProvider query_processors list:
``` json
    "query_processors": [
        "AdaptiveQueryProcessor",
        "GenAIQueryProcessor"
    ],
```

#### Available Tags

* `CHAT_QUERY_REWRITE_PROMPT`: Override the default Prompt used to rewrite the query.
``` json
"CHAT_QUERY_REWRITE_PROMPT:Write a more precise query of similar length to this : {query_string}"
```

* `CHAT_QUERY_REWRITE_GUIDE`:  Override the `system` role passed to the LLM.
``` json
"CHAT_QUERY_REWRITE_GUIDE:You are a helpful assistant that responds like a pirate captain"
```

* `CHAT_QUERY_DO_FILTER`: Turn on or off the default internal filter of LLM responses. 
``` json
"CHAT_QUERY_DO_FILTER:false"
```

### GenAI `query_mapping`

The following `query_mapping` is also available for use in the GenAI SearchProvider to help shape the Default Role passed to GenAI along with the user's query. To utilize this `query_mapping`, add a valid OpenAI API Key to SWIRL's `.env` file (found in the `swirl-home` directory) and then restart the SWIRL for it to take effect.

* `CHAT_QUERY_REWRITE_GUIDE`:  Override the `system` role passed to GenAI.
``` shell
"query_mappings": "PROMPT='Tell me about: {query_to_provider}',CHAT_QUERY_REWRITE_GUIDE='You are a helpful assistant that responds like a pirate captain'",
```

### Other GAI/LLMs

The Community Edition of SWIRL supports OpenAI and Azure/OpenAI for LLMs. The [Enterprise Edition supports additional platforns](https://swirlaiconnect.com/connectors). Please [contact SWIRL](mailto:hello@swirlaiconnect.com) for more information. 

## Elastic & OpenSearch

The [Elastic](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/elastic.py) and [OpenSearch](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/opensearch.py) Connectors make use of each engine's Python client.

Here is an example of a SearchProvider to connect to ElasticCloud using the `cloud_id`:

``` json
{
    "name": "ENRON Email - Elastic Cloud",
    "connector": "Elastic",
    "url": "your-cloud-id-here",
    "query_template": "index='{index_name}', query={'query_string': {'query': '{query_string}', 'default_field': '{default_field}'}}",
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "index_name=email,default_field=content,sort_by_date=date_published.keyword,NOT=true,NOT_CHAR=-",
    "result_processors": [
        "MappingResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "result_mappings": "url=_source.url,date_published=_source.date_published,author=_source.author,title=_source.subject,body=_source.content,_source.to,NO_PAYLOAD",
    "credentials": "verify_certs=[True|False],ca_certs=/path/to/cert/file.crt,username:password",
    "tags": [
        "Enron",
        "Elastic",
        "Internal"
    ]
}
```

This is the default OpenSearch SearchProvider that connects to a local instance of the engine:

``` json
{
    "name": "ENRON Email - OpenSearch",
    "active": false,
    "default": false,
    "connector": "OpenSearch",
    "url": "https://localhost:9200/",
    "query_template": "{\"query\":{\"query_string\":{\"query\":\"{query_string}\",\"default_field\":\"{default_field}\",\"default_operator\":\"and\"}}}",
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "index_name=email,default_field=content,sort_by_date=date_published.keyword,NOT=true,NOT_CHAR=-",
    "result_processors": [
        "MappingResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "result_mappings": "url=_source.url,date_published=_source.date_published,author=_source.author,title=_source.subject,body=_source.content,_source.to,NO_PAYLOAD",
    "credentials": "verify_certs=[True|False],ca_certs=/path/to/cert/file.crt,username:password",
    "tags": [
        "Enron",
        "OpenSearch",
        "Internal"
    ]
}
```

Note the use of JSONPaths in the `result_mappings`. This is essential for Elastic and OpenSearch since they embed results in a `_source` field unless otherwise configured. 

For more details consult the [SearchProvider Guide, Result Mappings](SP-Guide.html#result-mappings) section.

Use the [Payload Field](SP-Guide.html#payload-field) to store extra content that doesn't map to an existing item.

## Microsoft Graph

The [Microsoft Graph connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/microsoft_graph.py) uses the Microsoft Graph API to query M365 content.  The user must authenticate via OAuth2 in order to enable searching of their M365 content.

There are 5 pre-configured SearchProviders for querying the authenticated user's M365 content:
* Outlook Messages
* Calendar Events
* OneDrive Files
* SharePoint Sites
* Teams Chat

``` json
{
        "name": "Outlook Messages - Microsoft 365",
        "active": false,
        "default": true,
        "connector": "M365OutlookMessages",
        "url": "",
        "query_template": "{url}",
        "query_processors": [
            "AdaptiveQueryProcessor"
        ],
        "query_mappings": "NOT=true,NOT_CHAR=-",
        "result_grouping_field": "conversationId",
        "result_processors": [
            "MappingResultProcessor",
            "DedupeByFieldResultProcessor",
            "CosineRelevancyResultProcessor"
        ],
        "response_mappings": "",
        "result_mappings": "title=resource.subject,body=summary,date_published=resource.createdDateTime,author=resource.sender.emailAddress.name,url=resource.webLink,resource.isDraft,resource.importance,resource.hasAttachments,resource.ccRecipients[*].emailAddress[*].name,resource.replyTo[*].emailAddress[*].name,NO_PAYLOAD",
        "results_per_query": 10,
        "credentials": "",
        "eval_credentials": "",
        "tags": [
            "Microsoft",
            "Email"
        ]
    }
```

## Mongodb

The [Mongodb connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/mongodb.py) uses the `pymongo` package to connect to an [Atlas Search](https://www.mongodb.com/docs/atlas/atlas-search/atlas-search-overview/) index.

The included [IMDB Movie Samples](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/movies_mongodb.json) SearchProvider is configured to search the `sample_mflix` collection, `movies` sample table.

``` json
{
    "name": "IMDB Movie Samples - MongoDB",
    "active": false,
    "default": false,
    "authenticator": "",
    "connector": "MongoDB",
    "url": "sample_mflix:movies",
    "query_template": "{'$text': {'$search': '{query_string}'}}",
    "post_query_template": {},
    "http_request_headers": {},
    "page_fetch_config_json": {},
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "DATE_SORT=year,NOT_CHAR=-",
    "result_grouping_field": "",
    "result_processors": [
        "MappingResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "response_mappings": "",
    "result_mappings": "title=name,body=fullplot,date_published=released,date_published_display=year,author=directors[*],url=poster,lastupdated,genres[*],rated,runtime,languages[*],cast[*],writers[*],awards.text,imdb.rating,tomatoes.viewer.rating,tomatoes.critic.rating,NO_PAYLOAD",
    "results_per_query": 10,
    "credentials": "mongodb+srv://<mongodb-username>:<mongodb-password>@<mongdb-cluster>.mongodb.net/?retryWrites=true&w=majority",
    "eval_credentials": "",
    "tags": [
        "Movies",
        "MongoDB",
        "Internal"
    ]
}
```

The MongoDB SearchProvider is configured with `MATCH_ALL` by default, which requires that all search terms be present in a result (similar to a Boolean `AND` operator). This can be changed to `MATCH_ANY`, which would only require one search term be present in a result (similar to a Boolean `OR` operator). There are two way to change the default behavior.

* Update the `query_mappings` of the SP:
```
"query_mappings": "DATE_SORT=year,NOT_CHAR=-,MATCH_ANY",
```
* Add a Search Tag (not a SearchProvider Tag).

## Oracle

The [Oracle connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/oracle.py) use the `oracledb` package to connect to an Oracle instance.

The included [Free Public DB](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/oracle.json) SearchProvider has tested against 23c Free and presumably supports earlier versions. 

## PostgreSQL

The [PostgreSQL connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/postgresql.py) uses the [psycopg2](https://pypi.org/project/psycopg2/) driver. 

### Installing the PostgreSQL Driver

To use PostgreSQL with SWIRL:

* Install [PostgreSQL](https://www.postgresql.org/) 
* Modify the system PATH so that `pg_config` from the PostgreSQL distribution runs from the command line
* Install `psycopg2` using `pip`:

``` shell
pip install psycopg2
```

* Uncomment the PostgreSQL Connector in the following modules:
  * [swirl.connectors.__init__.py](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/__init__.py)
```
# uncomment this to enable PostgreSQL
# from swirl.connectors.postgresql import PostgreSQL
```
  * [swirl.models.py](https://github.com/swirlai/swirl-search/blob/main/swirl/models.py)
``` python
    CONNECTOR_CHOICES = [
        ('RequestsGet', 'HTTP/GET returning JSON'),
        ('Elastic', 'Elasticsearch Query String'),
        # Uncomment the line below to enable PostgreSQL
        # ('PostgreSQL', 'PostgreSQL'),
        ('BigQuery', 'Google BigQuery'),
        ('Sqlite3', 'Sqlite3')
    ]
```

* Run SWIRL setup:

``` shell
python swirl.py setup
```

* Restart SWIRL:

``` shell
python swirl.py restart
```

* Add a PostgreSQL SearchProvider like the one provided with the [Funding Dataset](#funding-data-set)

{: .highlight }
Suggestions on how to improve this process are [most welcome](#support)!

Here is an example of a basic SearchProvider using PostgreSQL:

``` json
{
    "name": "Company Funding Records - PostgreSQL)",
    "default": false,
    "connector": "PostgreSQL",
    "url": "host:port:database:username:password",
    "query_template": "select {fields} from {table} where {field1} ilike '%{query_string}%' or {field2} ilike '%{query_string}%';",
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "fields=*,sort_by_date=fundedDate,table=funding,field1=city,field2=company",
    "result_processors": [
        "MappingResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "result_mappings": "title='{company} series {round}',body='{city} {fundeddate}: {company} raised usd ${raisedamt}\nThe company is headquartered in {city} and employs {numemps}',date_published=fundeddate,NO_PAYLOAD",
    "tags": [
        "Company",
        "PostgreSQL",
        "Internal"
    ]
}
```

Note: Putting a fixed SQL query in the `query_template` is perfectly acceptable. Anything that doesn't change in the URL can be stored here.

## RequestsGet

The [RequestsGet connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/requestsget.py) uses HTTP/GET to fetch URLs. It supports optional authentication. Here is a generic SearchProvider based on RequestsGet:

``` json
{
    "name": "Sample HTTP GET Endpoint",
    "connector": "RequestsGet",
    "url": "http://hostname/site/endpoint",
    "query_template": "{url}&textQuery={query_string}",
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "PAGE=start=RESULT_INDEX,DATE_SORT=sort=date",
    "result_processors": [
        "MappingResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "response_mappings": "FOUND=count,RESULTS=results",
    "result_mappings": "body=content,date_published=date,author=creator",
    "credentials": "HTTPBasicAuth('your-username-here', 'your-password-here')",
    "tags": [
        "News"
    ]
}
```

Here is the same connector, configured for three different Google Programmable Search Engines:

``` json
[
    {
        "name": "Enterprise Search Engines - Google PSE",
        "active": true,
        "default": true,
        "connector": "RequestsGet",
        "url": "https://www.googleapis.com/customsearch/v1",
        "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
        "post_query_template": "{}",
        "http_request_headers": {},
        "page_fetch_config_json": {
            "cache": "false",
            "headers": {
                "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
            },
            "www.businesswire.com": {
                "timeout": 60
            },
            "www.linkedin.com": {
                "timeout": 5
            },
            "rs.linkedin.com": {
                "timeout": 5
            },
            "uk.linkedin.com": {
                "timeout": 5
            },
            "au.linkedin.com": {
                "timeout": 5
            },
            "timeout": 30
        },
        "query_processors": [
            "AdaptiveQueryProcessor"
        ],
        "query_mappings": "cx=0c38029ddd002c006,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-",
        "result_processors": [
            "MappingResultProcessor",
            "DateFinderResultProcessor",
            "CosineRelevancyResultProcessor"
        ],
        "response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
        "result_mappings": "url=link,body=snippet,author=displayLink,cacheId,pagemap.metatags[*].['og:type'],pagemap.metatags[*].['og:site_name'],pagemap.metatags[*].['og:description'],NO_PAYLOAD",
        "credentials": "key=AIzaSyDvVeE-L6nCC9u-TTGuhggvSmzhtiTHJsA",
        "tags": [
            "News",
            "EnterpriseSearch"
        ]
    },
    {
        "name": "Strategy Consulting - Google PSE",
        "active": true,
        "default": true,
        "connector": "RequestsGet",
        "url": "https://www.googleapis.com/customsearch/v1",
        "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
        "post_query_template": "{}",
        "http_request_headers": {},
        "page_fetch_config_json": {
            "cache": "false",
            "headers": {
                "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
            },
            "www.businesswire.com": {
                "timeout": 60
            },
            "www.linkedin.com": {
                "timeout": 5
            },
            "rs.linkedin.com": {
                "timeout": 5
            },
            "uk.linkedin.com": {
                "timeout": 5
            },
            "au.linkedin.com": {
                "timeout": 5
            },
            "timeout": 30
        },
        "query_processors": [
            "AdaptiveQueryProcessor"
        ],
        "query_mappings": "cx=7d473806dcdde5bc6,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-",
        "result_processors": [
            "MappingResultProcessor",
            "DateFinderResultProcessor",
            "CosineRelevancyResultProcessor"
        ],
        "response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
        "result_mappings": "url=link,body=snippet,author=pagemap.metatags[*].['authors-name'],cacheId,pagemap.metatags[*].['articletype'],pagemap.metatags[*].['practice-name'],pagemap.metatags[*].['searchresults-tags'],pagemap.metatags[*].['site_name'],pagemap.metatags[*].['twitter:description'],NO_PAYLOAD",
        "credentials": "key=AIzaSyDvVeE-L6nCC9u-TTGuhggvSmzhtiTHJsA",
        "tags": [
            "News",
            "StrategyConsulting"
        ]
    },
    {
        "name": "Mergers & Acquisitions - Google PSE",
        "active": true,
        "default": true,
        "connector": "RequestsGet",
        "url": "https://www.googleapis.com/customsearch/v1",
        "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
        "post_query_template": "{}",
        "http_request_headers": {},
        "page_fetch_config_json": {
            "cache": "false",
            "headers": {
                "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
            },
            "www.businesswire.com": {
                "timeout": 60
            },
            "www.linkedin.com": {
                "timeout": 5
            },
            "rs.linkedin.com": {
                "timeout": 5
            },
            "uk.linkedin.com": {
                "timeout": 5
            },
            "au.linkedin.com": {
                "timeout": 5
            },
            "timeout": 30
        },
        "query_processors": [
            "AdaptiveQueryProcessor"
        ],
        "query_mappings": "cx=b384c4e79a5394479,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX,NOT_CHAR=-",
        "result_processors": [
            "MappingResultProcessor",
            "DateFinderResultProcessor",
            "CosineRelevancyResultProcessor"
        ],
        "response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
        "result_mappings": "url=link,body=snippet,author=pagemap.metatags[*].['article:publisher'],cacheId,pagemap.metatags[*].['og:type'],pagemap.metatags[*].['article:tag'],pagemap.metatags[*].['og:site_name'],pagemap.metatags[*].['og:description'],NO_PAYLOAD",
        "credentials": "key=AIzaSyDvVeE-L6nCC9u-TTGuhggvSmzhtiTHJsA",
        "tags": [
            "News",
            "MergersAcquisitions"
        ]
    }
]
```

And here it is again, configured for SOLR with the [tech products example collection](https://solr.apache.org/guide/solr/latest/getting-started/tutorial-techproducts.html) installed:

``` json
{
    "name": "techproducts - Apache Solr",
    "active": false,
    "default": false,
    "connector": "RequestsGet",
    "url": "http://localhost:8983/solr/{collection}/select?wt=json",
    "query_template": "{url}&q={query_string}",
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "collection=techproducts,PAGE=start=RESULT_ZERO_INDEX,NOT=True,NOT_CHAR=-",
    "result_processors": [
        "MappingResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "response_mappings": "FOUND=numFound,RESULTS=response.docs",
    "result_mappings": "title=name,body=features,response",
    "credentials": "",
    "tags": [
        "TechProducts",
        "Solr",
        "Internal"
    ]
}
```

To adapt RequestsGet for your JSON response, just replace the JSONPaths on the right of the `FOUND`, `RETRIEVED`, and `RESULT` configurations in `response_mappings`, following the left-to-right format of `swirl_key=source-key`. If the response provides a dictionary wrapper around each result, use the RESULT path to extract it.

From there, map results fields to SWIRL's schema as described in the [SearchProvider Guide, Result Mapping](SP-Guide.html#result-mappings) section. Use the [PAYLOAD Field](SP-Guide.html#payload-field) to store any extra content from SearchProviders that doesn't map to an existing SWIRL field.

Add additional required `key/value` parameters to the `url` - if they won't change from SearchProvider to SearchProvider - or by adding a mapping in the `query_template` and a default or guide value in the `query_mappings`. (See `{collection}` in the SOLR example above.)

## RequestsPost

The [RequestsPost connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/requestspost.py) uses HTTP/POST to submit search forms to configured URLs. It supports optional authentication. RequestsPost is used by M365 connectors and is now available for other sources.  Here is a generic SearchProvider based on RequestsPost:

``` json
{
    "name": "Sample HTTP POST Endpoint",
    "active": false,
    "default": false,
    "connector": "RequestsPost",
    "url": "https://xx.apis.it.h.edu/ats/person/v3/search",
    "query_template": "{url}?Query={query_string}",
    "query_processor": "",
    "post_query_template": {
        "fields": [
          "names.personNameKey",
          "names.firstName",
          "names.lastName"
        ],
        "conditions": {
          "names.name": "*{query_string}*"
        }
    },
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "NOT=true,NOT_CHAR=-",
    "result_processor": "",
    "result_processors": [
        "MappingResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "response_mappings": "FOUND=count,RESULTS=results",
    "result_mappings": "titles=names[0].name,url=names[0].personNameKey,body='{names[0].name} ID#: {names[*].personNameKey}'",
    "results_per_query": 10,
    "credentials": "X-Api-Key=<your-api-key>",
    "eval_credentials": "",
    "tags": [
        "People"
    ]
}
```

[Contact Support](#support) for help getting started.

## Snowflake

The [Snowflake connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/snowflake.py) uses the `snowflake-connector-python` package to connect to a Snowflake instance.

The included [Free Company Records](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/company_snowflake.json) SearchProvider is configured to search the `FreeCompanyResearch` dataset available in the Snowflake Marketplace.

``` json
{
    "name": "Free Company Records - Snowflake",
    "active": false,
    "default": false,
    "authenticator": "",
    "connector": "Snowflake",
    "url": "<snowflake-instance-address>",
    "query_template": "SELECT {fields} FROM {table} WHERE {field1} ILIKE '%{query_string}%' AND NULLIF(TRIM(founded), '') IS NOT NULL ORDER BY TRY_TO_NUMBER(REGEXP_REPLACE(SPLIT_PART(size, '-', 1), '[^0-9]', '')) DESC;",
    "post_query_template": {},
    "http_request_headers": {},
    "page_fetch_config_json": {},
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "fields=*,sort_by_date=founded,table=FREECOMPANYDATASET,field1=name",
    "result_grouping_field": "",
    "result_processors": [
        "MappingResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "response_mappings": "",
    "result_mappings": "title='{name}  ({founded})',body='{name} was founded in {founded} in {country}. It has {size} employees and operates in the {industry} industry.',url='https://{linkedin_url}',date_published=founded,NO_PAYLOAD",
    "results_per_query": 10,
    "credentials": "<username>:<password>:FREE_COMPANY_DATASET:COMPUTE_WH",
    "eval_credentials": "",
    "tags": [
        "Company",
        "Snowflake"
    ]
}
```

Note: Putting a fixed SQL query in the `query_template` is perfectly acceptable. Anything that doesn't change in the URL can be stored here.

## SQLite3

The [SQLite3 Connector](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/sqlite3.py) uses the SQLite3 driver built-in to Python.

Here is an example of a SearchProvider using SQLite3:

``` json
{
    "name": "Company Funding Records - SQLite3",
    "active": false,
    "default": false,
    "connector": "Sqlite3",
    "url": "db.sqlite3",
    "query_template": "select {fields} from {table} where {field1} like '%%{query_string}%%' or {field2} like '%%{query_string}%%';",
    "query_processors": [
        "AdaptiveQueryProcessor"
    ],
    "query_mappings": "fields=*,sort_by_date=fundeddate,table=funding,field1=city,field2=company",
    "result_processors": [
        "MappingResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
    "result_mappings": "title='{company} series {round}',body='{city} {fundeddate}: {company} raised usd ${raisedamt}\nThe company is headquartered in {city} and employs {numemps}',date_published=fundeddate,NO_PAYLOAD",
    "tags": [
        "Company",
        "SQLite3",
        "Internal"
    ]
}
```

Note: Putting a fixed SQL query in the `query_template` is perfectly acceptable. Anything that doesn't change in the URL can be specified here.

# Processing Pipelines

![SWIRL Processing Pipelines](images/swirl_architecture_1.png)

Processors are intended to be single purpose and executed in a sequence called a "pipeline". Pipelines are specified as JSON lists in their respective properties.  There are four processing pipelines in SWIRL:
* `Search.pre_query_processors`
* `SearchProvider.query_processors`
* `SearchProvider.result_processors`
* `Search.post_result_processors`

For example, the default `Search.post_result_processors` pipeline is:

``` json
"post_result_processors": [
            "DedupeByFieldPostResultProcessor",
            "CosineRelevancyPostResultProcessor"
        ],
```

This pipeline removes duplicates from the result set prior to relevancy ranking.

## Query Processors

Query Processors operate queries. The exact field they operate on depends on how they are deployed.

| Pipeline | Reads | Updates |
| ---------- | ---------- | ---------- | 
| Search.pre_query_processors | `Search.query_string` | `Search.query_string_processed` | 
| SearchProvider.query_processors | `Search.query_string_processed` | `<Connector>.query_string_to_provider` | 

This table describes the query processors included in SWIRL:

| Processor | Description | Notes | 
| ---------- | ---------- | ---------- | 
| AdaptiveQueryProcessor | Rewrites queries based on the `query_mappings` for a given SearchProvider | Should not be used as `pre_query_processor` |
| GenAIQueryProcessor | This query processor asks an LLM to rewrite queries based on a configurable prompt. For example it can rewrite queries to be fuzzier, broader, more specific, boolean, or in another language. | Experimental |
| GenericQueryProcessor | Removes special characters from the query |  |
| SpellcheckQueryProcessor | Uses [TextBlob](https://textblob.readthedocs.io/en/dev/quickstart.html#spelling-correction) to predict and fix spelling errors in `query_string` | Best deployed in a `SearchProvider.query_processor` for sources that need it; not recommended with Google PSEs | 
| NoModQueryProcessor |  Only removes leading SearchProvider Tags and does not modify the query terms in any way. | It is intended for repositories that allow non-search characters (such as brackets). |
| RemovePIIQueryProcessor | Removes PII entities from the query. It does not replace them. | | 

## Result Processors

Result Processors transform source results into the SWIRL format defined in [swirl/processors/utils.py](https://github.com/swirlai/swirl-search/blob/main/swirl/processors/utils.py).

The following table lists the Result Processors included with SWIRL:

| Processor | Description | Notes | 
| ---------- | ---------- | ---------- | 
| GenericResultProcessor | Copies results from source format to SWIRL format by exact match on name | Recommended for sources that don't need mapping |
| MappingResultProcessor | Transforms results from source format to SWIRL format, using `SearchProvider.result_mappings` | Default |
| LenLimitingResultProcessor | Checks if the `title` and `body` responses from a source exceed a configurable length (set in `swirl_server/settings.py`: `SWIRL_MAX_FIELD_LEN = 512`), truncates anything after that value, and adds an ellipsis ("..."). If the `body` field has been truncated, the processor reports the entire response in a new `body_full` field in the Payload. The default truncation length for can be overridden for a specific SearchProvider using a new Tag value (e.g. `max_length:256`). | Recommended for sources that consistently return lengthy title or body fields; should follow the `MappingResultProcessor`. |
| CleanTextResultProcessor | Removes non-alphanumeric characters from the source response. It should be considered for lengthy responses where URLs or other HTML or Markdown syntax appear in results. | Should be installed before the `LenLimitingResultProcessor` when both are used. |
| DateFinderResultProcessor | Looks for a date in any a number of formats in the body field of each result item. Should it find one, and the `date_published` for that item is `'unknown'`, it replaces `date_published` with the date extracted from the body, and notes this in the `result.messages`. | This processor can detect the following date formats:<br/> `06/01/23`<br/>`06/01/2023`<br/>`06-01-23`<br/>`06-01-2023`<br/>`jun 1, 2023`<br/>`june 1, 2023` |
| AutomaticPayloadMapperResultProcessor | Profiles response data to find good strings for SWIRL's `title`, `body`, and `date_published` fields. It is intended for SearchProviders that would otherwise have few (or no) good `result_mappings` options. | It should be place after the `MappingResultProcessor`. The `result_mappings` field should be blank, except for the optional DATASET directive, which will return only a single SWIRL response for each provider response, with the original response in the `payload` field under the `dataset` key. |
| RequireQueryStringInTitleResultProcessor | Drops results that do not contain the `query_string_to_provider` in the result `title` field. | It should be added after the `MappingResultProcessor` and is now included by default in the "LinkedIn - Google PSE" SearchProvider. | 
| RemovePIIResultProcessor | Redacts PII entries in all result fields for configured SearchProviders, including payload string fields, with a generic tag showing the entity type. For example "James T. Kirk" -> "<PERSON>". | This processor may be installed before or after the CosineRelevancyResultProcessor. If it runs before, query terms which are PII entities will not be used in relevancy ranking, since they will be redacted. More information: [https://microsoft.github.io/presidio/](https://microsoft.github.io/presidio/) |

## Post Result Processors

`PostResultProcessors` operate only on processed result data and are saved to the SWIRL database by each connector. They operate on Result objects.

### `CosineRelevancyPostResultProcessor`

SWIRL includes a cosine vector similarity relevancy model based on [spaCy](https://spacy.io/). The source code is found in: [swirl/processors/relevancy.py](https://github.com/swirlai/swirl-search/blob/main/swirl/processors/relevancy.py)

The relevancy model is as follows:

* Matches on word stems from [nltk](https://www.nltk.org/howto/stem.html)

* Scores the fields configured in `SWIRL_RELEVANCY_CONFIG` in [swirl_server/settings.py](https://github.com/swirlai/swirl-search/blob/main/swirl_server/settings.py)

* Aggregates the similarity of:

    * the entire query and the field, with the score being the highest in any single sentence (if any), 
    
    * the entire query and a window of text around the field match

    * the 1 and 2 word combinations in the query (if long enough), and a window of text around the field match

* Weights these fields as defined in  `SWIRL_RELEVANCY_CONFIG`, a dictionary structure in [swirl_server/settings.py](https://github.com/swirlai/swirl-search/blob/main/swirl_server/settings.py)

* Further weights the window-text matches with the length of the match

* Gives a small boost based on the original SearchProvider's rank, equal to $1/(1+\sqrt{SearchProvider.rank})$

* Normalizes the length of the result against the median length of all results in the set - this is reflected in the `result_length_adjust` in the `explain` structure.

* Normalizes the query executed by this SearchProvider vs. all the other queries in the set - this is reflected in the `query_length_adjust` in the `explain` structure.

The SWIRL score is just that: a score. The higher a score is, the more contextually relevant the result is. Scores aren't comparable between queries or results.

*Tip: to translate a result score to a confidence score, take the #1 result as 1.0, and then divide subsequent results by the score for that result to calculate the confidence.*

SWIRL reports the `swirl_rank`, from 1 to N, where N is the total number of results. SWIRL also includes the `searchprovider_rank`, which is the result rank assigned by the source. This makes it easy to compare what SWIRL viewed as relevant compared to what each SearchProvider did.

In the event of a relevancy tie, the `date_published` and `search_provider` rank are used as additional sorts, to break it.

{: .highlight }
Note that there are two steps to Relevancy ranking: 
1. `SearchProvider.result_processors` processes the results from each configured SearchProvider, asynchronously
2. `Search.post_result_processors` makes a final pass over the results, adjusting for length and finalizing the score for each item.  

For this to work, the `CosineRelevancyPostResultProcessor` must be added in the `Search.post_result_processors` list. It should be after any result mappings, but before any other stages you add that depend on a finished `swirl_score`.

For example:

``` json
    "result_processors": [
        "MappingResultProcessor",
        "DateFinderResultProcessor",
        "CosineRelevancyResultProcessor"
    ],
```

### `DropIrrelevantPostResultProcessor`

The `DropIrrelevantPostResultProcessor` drops results with `swirl_score < settings.MIN_SWIRL_SCORE` (which is set to 500 by default) and results with no `swirl_score`.  This processor is available for use but not enabled by default.

{: .highlight }
The Galaxy UI will not display the correct number of results if this ResultProcessor is deployed. 

### `RemovePIIPostResultProcessor`

This processor is identical in most respects to the [RemovePIIResultProcessor](#result-processors), except that it operates on all results in a result set, not just a single SearchProvider. 

# Mixers

The following table details the Result Mixers included with SWIRL:

| Mixer | Description | Notes |
| ---------- | ---------- | ---------- | 
| RelevancyMixer | Organizes results by [relevancy](User-Guide.html#relevancy-ranking) score (descending), then source rank (ascending) | The default; depends on `relevancy_processor` being installed as the `search.post_result_processors` (also the default) |
| RelevancyNewItemsMixer | Organizes results as above, but hiding results that don't have the `new` field as [created during Search updates](Developer-Guide.html#update-a-search) | This is the default for `search.new_result_url`|
| DateMixer | Organizes results by `date_published`. Results with "unknown" for `date_published` are omitted | Use when you want date sorted results | 
| DateNewItemsMixer | Organizes results as above, but hiding results that don't have the `new` field as [created during Search updates](Developer-Guide.html#update-a-search) | This is the default for `search.new_result_url` when `search.date` is set to `sort` |     
| RoundRobinMixer | Organizes results by taking 1 result from each responding SearchProvider, alternating; actually calls `Stack1Mixer` (see below) | Good for searches with `search.sort` set to "date" or anytime you want a cross-section of results instead of just the ones with the most evidence | 
| Stack1Mixer | Organizes results by taking 1 result from each responding SearchProvider, alternating | Good for cross-sections of data |
| Stack2Mixer | Organizes results by taking 2 from each responding SearchProvider, alternating | Good for cross-sections of data with 4-6 sources |
| Stack3Mixer | Organizes results by taking 3 from each responding SearchProvider, alternating | Good for cross-sections of data with few sources | 
| StackNMixer | Organizes results by taking `N` from each responding source, where `N` if not specified is the number of results requested divided by the number of SearchProviders reporting at least 1 result | Good for cross-sections of data with few providers | 

## Date Mixer

If you want results sorted by `date_published`, descending, use the Date Mixer.

![SWIRL Results, Date Mixer](images/swirl_results_mixed_2_date_sort.png)


{: .highlight }
For example: [http://localhost:8000/swirl/results?search_id=1&result_mixer=DateMixer](http://localhost:8000/swirl/results?search_id=1&result_mixer=DateMixer)

## NewItems Mixers

The two NewItems mixers automatically filter results to items with the `new` field present. Both will report the number of results hidden because they do not have this field. 

To remove the `new` field from all results in a search, add `&mark_all_as_read=1` to the `result_mixer` URL property. For example:

``` shell
http://localhost:8000/swirl/results/?search_id=1&result_mixer=DateNewItemsMixer&mark_all_as_read=1
```

The Mixer will then return 0 results. But it will return results if the Search is updated.

Mixer objects combine separate `Result` objects for a given `Search`, wrap them in metadata, and order them. For example, a Mixer might alternate from each source (`Stack1Mixer`), or sort results by `date_published` (`DateMixer`)

To invoke the mixer specified using the `result_mixer` property of the Search object, specify the `search_id` as shown in APIs, above:

``` shell
http://localhost:8000/swirl/results/?search_id=1
```

If you use the SWIRL defaults, a search will produce a JSON result that is relevancy ranked.

To specify a different Mixer, add `&result_mixer=mixer-name` to the URL.

``` shell
http://localhost:8000/swirl/results/?search_id=1&result_mixer=Stack1Mixer
```

The following table describes the Mixer wrapper in more detail:

| Field | Description |
| ---------- | ---------- |
| messages | All messages from the Search and all SearchProviders |
| info | A dictionary of Found and Retrieved counts from each SearchProvider | 
| info - search | Information about the Search, including the processed query, and links to re-run and re-score Searches |
| info - results | Information about the Results, including the number retrieved and the URL of the next (and previous) pages of results |
| results | Mixed Results from the specified Search |

# Sample Data Sets

## Funding Data Set

The TechCrunch Continental USA funding data set was taken from [Insurity SpatialKey](https://support.spatialkey.com/spatialkey-sample-csv-data/). It is included with SWIRL in [Data/funding_db.csv](https://github.com/swirlai/swirl-search/blob/main/Data/funding_db.csv)
This file was processed with [scripts/fix_csv.py](https://github.com/swirlai/swirl-search/blob/main/DevUtils/fix_csv.py) prior to loading into SQLite3. 

### Loading into SQLite3 

1. Activate [sqlite_web](Admin-Guide.html#sqlite-web)
Then, from the swirl-home directory:
``` shell
sqlite_web db.sqlite3
```

2. A browser window should open automatically; if not go to [http://localhost:8080/](http://localhost:8080/)
3. Enter "funding" in the text box in the upper right of the screen and press the `Create` button
![Sqlite loading funding dataset](images/sqlite_import_funding_1.png)

4. Click `Choose File` and select [Data/funding_db.csv](https://github.com/swirlai/swirl-search/blob/main/Data/funding_db.csv)

5. Leave "Yes" in the box below.

6. Click `Import`.
![Sqlite loading funding dataset](images/sqlite_import_funding_2.png)

7. Load the [Funding DB SQLite3](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/funding_db_sqlite3.json) SearchProvider as [described in the SearchProvider Guide](SP-Guide.html#copypaste-install).

### Loading into PostgreSQL

* Create a table following the structure in the CSV using SQL or something like [Postico](https://eggerapps.at/postico/)

``` shell
-- DDL generated by Postico 1.5.21
-- Table Definition ----------------------------------------------

CREATE TABLE funding (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    permalink text,
    company text,
    numemps text DEFAULT '0'::numeric,
    category text,
    city text,
    state text,
    fundeddate date,
    raisedamt numeric DEFAULT '0'::numeric,
    raisedcurrency text,
    round text
);

-- Indices -------------------------------------------------------

CREATE UNIQUE INDEX funding_pkey ON funding(id int4_ops);
```

* Run this SQL to ingest the CSV:

``` shell
COPY funding(permalink,company,numemps,category,city,state,fundeddate,raisedamt,raisedcurrency,round) FROM '/path/to/Data/funding_db.csv' DELIMITER ',' CSV HEADER;
```

* Load the [Funding DB PostgreSQL](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/funding_db_postgres.json) SearchProvider as [described in the SearchProvider Guide, SearchProvider](SP-Guide.html#copypaste-install) section.

### Loading into BigQuery

* Create a table with a schema like so:

![BigQuery Funding DB Schema in Console](images/funding_bigquery_schema.png)

* Load the CSV file into this table: [Loading CSV data into a table](https://cloud.google.com/bigquery/docs/loading-data-cloud-storage-csv#loading_csv_data_into_a_table)

* Load the [Funding DB BigQuery](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/funding_db_bigquery.json) SearchProvider as [described in the User Guide, SearchProvider](SP-Guide.html#copypaste-install) section.

## Enron Email Data Set

This data set consists of 500,000+ emails from 150 employees of the former Enron Corporation. It's available from Kaggle: [https://www.kaggle.com/datasets/wcukierski/enron-email-dataset](https://www.kaggle.com/datasets/wcukierski/enron-email-dataset) among [other places](https://www.cs.cmu.edu/~./enron/).

### Loading into Elastic or OpenSearch

* Download the Enron email data set.

* Unzip and untar the download and place the `email.csv` file in your swirl-home directory

* Create a new Elastic/OpenSearch index named 'email' using the [development console](http://localhost:5601/app/dev_tools#/console):

``` shell
PUT /email
```

{: .highlight }
To index the Enron data into Elastic, you must first update the load script with the path to a certificate, as required by Elastic.

* Add the path to a valid certificate as the value in `scripts/index_email_elastic.py`, line 37, and save the change.

``` shell
# Insert path to Elastic cert below
ca_certs = "<PATH-TO-CERT>"
```

* Index the `emails.csv` from the SWIRL directory:

For Elastic:
``` shell
python scripts/index_email_elastic.py emails.csv -p elastic-password
```

For OpenSearch:
``` shell
python scripts/index_email_opensearch.py emails.csv -p admin-password
```

The script will report progress every 100 rows. Hit `Ctrl-C` to stop it if desired.

* Verify that the messages have been indexed by Elastic/OpenSearch by querying in the [development console](http://localhost:5601/app/dev_tools#/console):

``` shell
GET _search
{
  "query": {
    "match_all": {}
  }
}
```

Results should appear in the right-hand pane:

``` shell
{
  "took" : 38,
  "timed_out" : false,
  "_shards" : {
    "total" : 6,
    "successful" : 6,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 6799,
      "relation" : "eq"
    },
    "max_score" : 1.0,
    "hits" : [
      ...
      {
        "_index" : "email",
        "_id" : "c13MwoUBmlIzd81ioZ7H",
        "_score" : 1.0,
        "_source" : {
          "url" : "allen-p/_sent_mail/118.",
          "date_published" : "2000-09-26 09:26:00.000000",
          "author" : "Phillip K Allen",
          "to" : "pallen70@hotmail.com",
          "subject" : "Investment Structure",
          "content" : """---------------------- Forwarded by 
          
    ...
```
