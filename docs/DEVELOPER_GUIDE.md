![SWIRL Logo](./images/swirl_logo_notext_200.jpg)

<br/>

# SWIRL DEVELOPER GUIDE

## Table of Contents

:small_blue_diamond: [Architecture](#architecture) | [Workflow](#workflow) | [Search Status](#search-status)<br/>
:small_blue_diamond: [SearchProvider](#searchprovider-object) | [Search](#search-object) | [Result](#result-object)<br/>

:small_blue_diamond: [Connector Modules](#connector-modules):<br/>
&nbsp;&nbsp; [elastic](#elastic) | [requests_get](#requestget) [opensearch](#opensearch) | [sqlite3](#sqlite3)<br/>

:small_blue_diamond: [Processor Modules](#processor-modules):<br/>
&nbsp;&nbsp; Query: [spellcheck_query_processor](#spellcheck-query-processor)<br/>
&nbsp;&nbsp; Results: [generic_result_processor](#result-processors) | [elastic_result_processor](#result-processors)<br/>
&nbsp;&nbsp; Post-Result: [cosine_relevancy_processor](#cosine-post-result-processor) | [generic_relevancy_processor](#relevancy-post-result-processor)<br/>

:small_blue_diamond: [Result Mixer Modules](#result-mixer-modules): <br/>
&nbsp;&nbsp; [relevancy_mixer](#result-mixer-modules) [round_robin_mixer](#result-mixer-modules) | [stack_mixer](#result-mixer-modules) <br/>

:small_blue_diamond: [Changing Defaults](#changing-defaults) | [Get Support](#get-support)

<br/>

<br/>

------------

<br/>

<br/>

# System Reference

![SWIRL Federated Search Architecture](/docs/images/swirl_arch.png)

## SWIRL Federated Search Architecture

The diagram above presents the SWIRL Federated Search Architecture. The following sections explain how SWIRL works.

<br/>

## Workflow

1. Create a Search using http://127.0.0.1:8000/swirl/search/

A POST to /swirl/search creates a new Search object. This invokes the create method in [swirl/views.py](../swirl/views.py):

```
        serializer = SearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        search_task.delay(serializer.data['id'])
        return Response(serializer.data, status=status.HTTP_201_CREATED)
```

This code creates the object, then invokes Celery task search_task, defined in [swirl/tasks.py](../swirl/tasks.py). This method executes the federated search, asychronously. 

2. SWIRL responds immediately with the id of the newly created Search object. 

```
    {
        "id": 56,
        "date_created": "2022-03-04T17:50:04.283994-05:00",
        "date_updated": "2022-03-04T17:50:06.317787-05:00",
        "query_string": "<your-query-terms>"
        ...
```

It is up to developer to poll this object using the returned id until Search.status ends in _READY. 
As a guideline, this generally takes 5 seconds.

For more information refer to the section on [Search Status](#search-status).

3. Asynchronously, a celery worker executes search_task(). 

```
from .search import search

@shared_task(name='search', ignore_result=True)
def search_task(search_id):
    logger.info(f'{module_name}: search_task: {search_id}')  
    return search(search_id)
```

4. search_task calls [swirl/search.py's search function](../swirl/search.py) which:

* Executes pre-query processing, using the specified Search.pre_query_processor. This is intended to occur before provider specific federation.
* Executes the federation process by creating one Celery task for each SearchProvider specified in the Search.searchprovider_list; the task calls the SearchProvider federate method:

```
@shared_task(name='federate', ignore_result=True)
def federate_task(provider_id, provider_name, provider_connector, search_id):
    logger.info(f'{module_name}: federate_task: {provider_name}.{provider_connector}')  
    return eval(provider_connector).search(provider_id, search_id)
```

* Search.py then waits for all federate tasks to report success by polling the Search and Result objects in the database:

```
    while 1:        
        # get the list of result objects
        results = Result.objects.filter(search_id=search.id)
        if len(results) == len(providers):
            break
        if len(results) > 0:
            at_least_one = True
        ticks = ticks + 1
        search.status = f'FEDERATING_WAIT_{ticks}'
        search.save()    
        time.sleep(1)
        if ticks > 5:
            error_flag = True
            failed_providers = []
            responding_provider_names = []
            for result in results:
                responding_provider_names.append(result.searchprovider)
            for provider in providers:
                if not provider.name in responding_provider_names:
                    failed_providers.append(provider.name)
            logger.warning(f"{module_name}: timeout waiting for: {failed_providers}")
            break
    # end while
```

:key: SWIRL uses the sqlite database to manage federation because we weren't able to get Celery to work properly :\

If you want to help with that please [contact support](#get-support)!

---------- 

:clock1: Everything after this proceeds asynchronously...

---------- 

5. While search.py waits for results, each federate_task calls the search() method of the associated connector. 

```
from .connectors import *

@app.task(name='federate')
def federate_task(provider_id, provider_name, provider_connector, data):
    return eval(provider_connector).search(provider_id, data)
```

Each connector search() method:

* Prepares the query by applying the specified Search.query_processor which updates Search.query_string_processed

SWIRL processors are invoked using an eval function:

```
    processed_query = eval(provider.query_processor)(search.query_string_processed)
```

* Prepares the query by binding SearchProvider and Search items like the url or the query_string with the 
specified query_template. Templates use python {} variable format. 

Here is an example taken from a Google PSE provider:

```
    "url": "https://www.googleapis.com/customsearch/v1",
    "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
    "query_mappings": "cx=0c38029ddd002c006",

```

Query construction involves parsing the query_template and replacing variables from the SearchProvider and Search objects. 
Currently url and query_string are hard wired replacements, while others are taken from the SearchProvider.query_mappings and credentials.

The function bind_query_mappings in [swirl/connectors/utils.py](../swirl/connectors/utils.py) is used for this.

* Connects to the SearchProvider as configured 
* Executes the query and gathers results

The query is sent using the method embedded in the connector code - for example, from the [OpenSearch connector](../swirl/connectors/opensearch.py):

```
    response = requests.get(query_to_provider)
    if response.status_code != HTTPStatus.OK:
        message = f"Error: request.get returned: {response.status_code} {response.reason}"
        logger.error(f'{module_name}: {message}')
        return message
```

* Prepares the 'retrieved' and 'found' counts
* Normalizes results to the SWIRL schema using the specified Search.result_processor

This follows the same invokation  as with query_processors above. Result_processors differ from query_processors in that they accept a single provider's raw result list and return a set of normalized SWIRL result dictionaries, ready to be stored. 

From [swirl/connectors/generic.py](../swirl/processors/elastic.py):

```
        for result in json_results:
            swirl_result = create_result_dictionary()
```

Thereafter processors handle mappings of keys & values from the raw results, to the SWIRL result schema. 

Consult the Object Reference for [Processors](#processors) for more information.

* Stores the normalized results in the SWIRL database, as Result objects - it is possible to retrieve them individually immediately using R

Storing results is the last step for search() methods:

```
        result = save_result(search=search, provider=provider, query_to_provider=query_to_provider, messages=messages, found=found, retrieved=retrieved, provider_results=provider_results) 
```

---------- 

:clock1: Everything after this proceeds synchronously again...

---------- 

6. When all federate_tasks are complete, search.py calls the specified Search.post_result_processor to highlight and score results.

7. When post-result processing is completed, search.py sets the Search.status to PARTIAL_RESULTS_READY or FULL_RESULTS_READY, depending on provider
responses. 

At this point, a mixed result set is available using a [result mixer](#mixers). 

This involves a URL like: http://127.0.0.1:8000/swirl/results/?search_id=1

[swirl/view.py](../swirl/views.py) resolves the URL request to retrieve results using the module [swirl/urls.py](../swirl/urls.py) which maps the URL to a ViewSet. 
In this case, it is the Result view set. Users can retrieve individual result sets by adding the id of the result set to the url. 

Adding search_id to the Result URL invokes the result_mixer specified in the Search, which serves up unified results:

```
            if Search.objects.filter(id=search_id).exists():
                search = Search.objects.get(id=search_id)
                if search.status.endswith('_READY'):
                    finished_results = Result.objects.filter(search_id=search_id)
                    if otf_result_mixer:
                        # call the specifixed mixer on the fly otf
                        results = eval(otf_result_mixer)(finished_results, search.results_requested)
                    else:
                        # call the mixer for this search provider
                        results = eval(search.result_mixer)(finished_results, search.results_requested)
```

Mixers read all the Result objects from a single Search, since they are linked by search_id, and organizes them in various ways, before returning a JSON structure that the Result View handles from there. 

<br/>

:1st_place_medal: Congratulations, you read the entire SWIRL Workflow description! :-) 

<br/>

<br/>

## Search Status

While SWIRL asychnronously executes a bunch of search() tasks, the Search Status - Search.status, more precisely - is updated in real time. 
The following table explains the different status messages that may be observed.

<br/>

| Status | Meaning | 
| ------ | ------- |
| DRAFT | Search is stored, but not to be run |
| NEW_SEARCH | Search is to be run immediately upon creation; this is the default |
| PRE_PROCESSING | SWIRL is preparing to federate the query |
| ERR_NO_PROVIDERS | Search failed because no SearchProviders were defined or specified (perhaps in Search.searchprovider_list?) |
| PRE_QUERY_PROCESSING | SWIRL is running the specified processor prior to federating the query |
| FEDERATING | SWIRL is federating the query - provisioning Celery workers with Connectors etc |
| FEDERATING_WAIT_n | SWIRL has been waiting for at least 3 seconds, plus 1 for every n in the status |
| POST_RESULT_PROCESSING | SWIRL is running the specified processor after federating the query |
| RESCORING | SWIRL is re-running the post-result processor for this query to re-score existing (saved) results |
| PARTIAL_RESULTS | SWIRL has received results from some providers, but not all, and those providers will not or cannot reply |
| ERROR_NO_RESULTS | SWIRL has not received results from any provider |
| FULL_RESULTS | SWIRL has received all results from all providers |
| PARTIAL_RESULTS_READY | SWIRL has finished processing results from providers who responded |
| FULL_RESULTS_READY | SWIRL has finished processing results from all providers | 

<br/>

<br/>

------------

<br/>

<br/>

# Object Reference

## SearchProvider Object

A SerchProvider defines some searchable source. It includes metadata identifying the type of connector used to search the source and much more.  

Many properties are optional when creating a SearchProvider object. They will have the default values shown below.

<br/>

### Properties

<br/>

| Property | Description | Default | Value/Example | 
| ------------------ | -----------------------------------------------------------------| -------------- | -----------------------------|
| id | Unique identifier for the SearchProvider | Integer, automatic | 1 |
| active | Boolean setting, if true the SearchProvider is used, if false it is ignored when federating | true | true, false |
| date_created | The time & date at which the Search was created | Automatic | 2022-02-28T17:55:04.811262Z |
| date_updated | The time & date at which the Search was updated  | Automatic | 2022-02-28T17:55:07.811262Z |
| name | Human-readable name for the source | "" | Enterprise Search PSE |
| connector | Name of the Connector to use for this source, see below | "requests_get" | "opensearch" | 
| url | The URL or other string including file path needed by the Connector for this source; not validated | "" | https://www.googleapis.com/customsearch/v1 |
| query_template | A string with optional variables in form {variable}; the Connector will bind the query_template with required data including the url and query_string, as well as any query_mappings or credentials, at runtime. Note this format is not yet used by the [Sqlite3 Connector](#sqlite3). | "" | {url}?cx={cx}&key={key}&q={query_string} |
| query_processor | The name of the Processor to use to prepare the query for this source | generic_query_processor | spellcheck_query_processor |
| query_mappings | A string defining the mappings for the query. Depends on the connector used. | "" | cx=your-google-search-engine-key |
| result_processor | The name of the Processor to use to normalize results from this source | generic_result_processor | |
| result_mappings | list of keys, optionally with values; there is one special key NO_PAYLOAD | "" | link=url,snippet=body,cacheId,NO_PAYLOAD |
| results_per_query | The number of results to request from this source for each query | Yes | 10 |
| credentials | The credentials to use for this source. Dependent on the source. | Yes | "" | key=your-google-json-api-key |
 
<br/>

### APIs

| URL | Explanation |
| ---------------------------- | -------------------------------------------------------------------------------------- |
| /swirl/searchproviders/      | List SearchProvider objects, newest first; create a new one using POST button and the form at bottom |
| /swirl/searchproviders/id/ | Retrieve SearchProvider object; destroy it using the DELETE button; edit it using the PUT button and the form at bottom  |

<br/>

## Search Object

Search objects define a search that some user or system desires to have run. They have unique id's. 
They may be linked to by Result objects.

<br/>

### Properties

| Property | Description | Default | Value/Example |
| ------------------ | -----------------------------------------------------------------| ------------| ----------------|
| id | Unique identifier for the Search | Automatic | 1 |
| date_created | The time & date at which the Search was created | Automatic | 2022-02-28T17:55:04.811262Z |
| date_updated | The time & date at which the Search was updated  | Automatic | 2022-02-28T17:55:07.811262Z |
| query_string | The query to be federated - the only required field! | "" | strategy | 
| query_string_processed | The Search query, modified by any pre-query processing | ""| "" |
| sort | The type of search to be run | relevancy | relevancy, date | 
| results_requested | The number of results, overall, the user has requested | 10 | 25 | 
| searchprovider_list | A list of the providers to search for this query; an empty list, the default, is to search all providers | [] | [ "Enterprise Search Engine PSE" ] |
| status | The execution status of this search, see below | NEW_SEARCH | FULL_RESULTS_READY | 
| pre_query_processor | The name of the Query Processor to apply to the query before federation starts | "" | spellcheck_query_processor |
| post_result_processor | The name of the Result Processor to apply after federation is complete, and all Results have been landed | "" | "" |
| result_url | The url to the associated Result object; not used as of SWIRL P2Preview1 | /swirl/results?search_id=id&result_mixer=specified-result-mixer | /swirl/results?search_id=1&result_mixer=round_robin_mixer |  |
| messages | Messages from SearchProviders | "" | Retrieved 1 of 1 results from: Document DB Search |  
| result_mixer | The name of the Mixer object (see below) to use for ordering results | round_robin_mixer | stack_mixer | 
| retention | The retention setting for this object; 0 = retain indefinitely; see [Search Expiration Service](#search-expiration-service) for details | 0 | 2 (daily deletion) | 

<br/>

### APIs

| URL | Explanation |
| ---------------------------- | -------------------------------------------------------------------------------------- |
| /swirl/search/      | List Search objects, newest first; create a new one using the POST button and form at bottom |
| /swirl/search/id/ | Retrieve Search object; destroy it using the DELETE button; edit it using the PUT button and form at bottom  |

<br/>

## Result Object

Each Result object holds the results from one SearchProvider. They are created at the end of the federated search process, in response to the creation of a Search object.  They are the only SWIRL object that has a foreign key - search_id. 

Only connectors should create Result objects. 

<br/>

### Properties

| Property | Description | Example |
| ------------------ | -----------------------------------------------------------------| ------------- |
| id | Unique identifier for the Result | 1 |
| date_created | The time & date at which the Result was created. Note that Results do not have date_updated |  2022-02-28T17:55:04.811262Z |
| search_id | The id of the associated search; there may be many Result objects with this id | 1 | 
| searchprovider | The name of the search provider that provided this result list | kibana_sample_data_ecommerce |
| query_to_provider | The exact query sent to the search provider | https://www.googleapis.com/customsearch/v1?cx=google-search-engine-id&key=google-json-api-key&q=strategy" |
| result_processor | The name of the Processor specifed in SearchProvider, that normalized the results | generic_result_processor |
| messages | A list of any messages (strings) from the provider | Retrieved 10 results from source... |
| retrieved | The number of results SWIRL retrieved from this provider, for this query | 10 |
| found | The number of results reported by the provider, for this query | 2309 |
| json_results | The normalized JSON results from this provider | See below | 

<br/>

### json_results

| Field | Description | Example |
| ------------------ | -----------------------------------------------------------------| -------------------------------------------|
| rank | The source provider's ranking of this result | 1 |
| score | SWIRL's relevancy ranking of this result; can be from 1 to 10, 10 being a very strong match with the query_string | 
| title | The source-reported title for this result | Technology |
| url | The URL for this report; may be reported by the source and/or calculated by SWIRL | http://pwc.com/etc |
| body | The source-reported result snippet(s), with search term matches highlighted with an asterisk (*) | *Technology* strategy encompasses a full set of Consulting capabilities to help you think through the strategic... |
| date_published | The source-reported time & date of publication of this result | unknown |
| date_retrieved | The time & date at which SWIRL received this result from the source | 2022-02-20 03:45:03.207909 |
| author | The source-reported author of this result | "CNN staff" |
| searchprovider | The name of the Source that reported this result | Strategy Consulting PSE |
| payload | a dictionary of all remaining keys in the provider's response | {} |

<br/>

Note that payload can be totally different from SearchProvider to SearchProvider. It is up to the caller to access the payload and extract whatever is needed, generally by making a new Processor (see below) or adding result_mappings.

<br/>

### APIs

| URL | Explanation |
| ---------------------------- | -------------------------------------------------------------------------------------- |
| /swirl/results/      | List Result objects, newest first; create a new one using the POST button and form at bottom |
| /swirl/results/id/ | Retrieve Result object; destroy it using the DELETE button; edit it using the PUT button and form at bottom  |
| /swirl/results/?search_id=search_id | Retrieve unified Results for Search, ordered by the Mixer specified |
| /swirl/results/?search_id=search_id&result_mixer=mixer_name | Retrieve unified Results for the Search, ordered by the specified result mixer |

<br/>

## Connector Modules

A Connector is responsible for searching a specific type of SearchProvider, retrieving the results, normalizing the results to the SWIRL format. This includes calling query and result processors.

### Included Connectors

| Connector | Description | Arguments |
| --------- | ----------- | ----------- |
| request_get | Searches any web endpoint using http GET with q=query syntax, and JSON response | url, query_string |
| elastic | Searches elastic search query_string queries | url (url or cloud_id), query_template (index_name, query template with default field), query_string, credentials |
| opensearch | Searches Google Programmable Search Engine (PSE) | url (url, search engine id AKA cx, JSONI API key), query_string |
| sqlite3 | Searches SQLite3 databases; note, as of Preview2 does not support the template language with {variable} format... yet | url (database file path), query_template (SQL query), query_mappings (argument to SELECT), query_string, credentials |

Connectors are specified in SearchProvider objects. When a new Search object is created, SWIRL creates a celery_task for each specified search provider. The task calls the connector's search() method, passing it the name of the provider and the serialized Search object, in json format. 

Each Connector is responsible for:

1. Adapting the Search query_string for the SearchProvider by calling the specified query processor
2. Constructing the query for the provider by combining the url and query_template with the query_string 
3. Connecting to the source using an imported python object like requests.get or ES.Search
2. Sending the query to the source
4. Gathering the results
5. Trimming the results into standard format - a list of result dictionaries
6. Calling the specified result processor 
7. Writing the processed results to SWIRL as a new Result object linked to the Search object

<br/>

Here is the stripped-down code for the requests_get connector:

```
    provider = SearchProvider.objects.get(id=provider_id)
    search = Search.objects.get(id=query_data['id'])

    # query processing for this provider
    processed_query = eval(provider.query_processor)(search.query_string_processed)

    # construct the query for the provider
    query_to_provider = provider.query_template
    if '{url}' in provider.query_template:
        query_to_provider = query_to_provider.replace('{url}',provider.url)
    if '{query_string}' in provider.query_template:
        query_to_provider = query_to_provider.replace('{query_string}', urllib.parse.quote_plus(processed_query))   
    # now process query_mappings
    # ... etc ...

    # issue the query
    response = requests.get(query_to_provider, auth=eval(provider.credentials))

    # normalize the response
    ...etc...

    provider_results = eval(provider.result_processor)(trimmed_response, provider, processed_query)

    # store the results as new Result

    result = Result.objects.create(search_id=search, searchprovider=provider.name, query_to_provider=query_to_provider, result_processor=provider.result_processor, messages=messages, found=found, retrieved=retrieved, json_results=provider_results)
    result.save()
```

## Connector Reference

## request_get

The request_get connector uses HTTP GET to request URLs. It supports optional authentication. Here is an example of a SearchProvider using requests_get:

```
{
    "name": "HTTP Get with Auth",
    "connector": "requests_get",
    "url": "http://your-url-here",
    "query_template": "{url}?q={query_string}",
    "result_mappings": "your-mappings-here",
    "credentials": "HTTPDigestAuth('your-username-here', 'your-password-here')"
}
```

Additional parameters can be added directly to the query_template. This connector does not support query_mappings as of SWIRL P2Preview1.

<br/>

## opensearch

The opensearch connector is a wrapper around requests.get that handles the OpenSearch 1.1 format. 

:star: Read more about [OpenSearch 1.1](https://github.com/dewitt/opensearch/blob/master/opensearch-1-1-draft-6.md) 

Here is an example of a SearchProvider using opensearch:

```
{
    "name": "Enterprise Search PSE",
    "connector": "opensearch",
    "url": "https://www.googleapis.com/customsearch/v1",
    "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
    "query_mappings": "cx=your-search-engine-id",
    "result_mappings": "link=url,snippet=body,cacheId,NO_PAYLOAD",
    "credentials": "key=your-google-api-key"
}
```

<br/>

## elastic

The elastic connector is a light wrapper around the python ElasticSearch object. It instatiates and calls the es.search object and passes the arguments.

Here is an example of a SearchProvider using it to connect to ElasticCloud using the cloud_id:

```
{
    "name": "ElasticCloud e-Commerce Demo",
    "connector": "elastic",
    "url": "cloud_id='Test1:dXMtY2VudHJhbDEuZ2NwLmNsb3VkLmVzLmlvJGM4M2MzMTUzODI5ZjQ3ZWY5ODA2YjUyZGNkMWNlNTZlJGY1M2YzZDE3NTllMDQwNWE4ODdiY2MwNGJkMDhkOWU2'",
    "query_template": "index=\"{index_name}\", query={\"query_string\": {\"query\": \"{query_string}\", \"default_field\": \"{default_field}\"}}",
    "query_mappings": "index_name=kibana_sample_data_ecommerce,default_field=customer_full_name",
    "result_mappings": "_source.customer_full_name=title,_source.email=body,_source.manufacturer,_source.products,NO_PAYLOAD",
    "credentials": "http_auth=(\"elastic\", \"your-password-here\")"
}
```

Here is an example of connecting to a local Elasticsearch with x-pack security turned off:

```
{
    "name": "Enron Email ES Local",
    "connector": "elastic",
    "url": "hosts='http://localhost:9200/'",
    "query_template": "index='{index_name}', query={'query_string': {'query': '{query_string}', 'default_field': '{default_field}'}}",
    "query_mappings": "index_name=email,default_field=content,sort_by_date=date_published.keyword",
    "result_mappings": "_source.url=url,_source.date_published=date_published,_source.author=author,_source.subject=title,_source.content=body,_source.to,NO_PAYLOAD",
    "credentials": "http_auth=(\"elastic\", \"your-password-here\")"
}
```

Note the use of json paths in result_mappings. This is essential for elastic since it embeds results in a _source field unless
otherwise configured.

<br/>

## sqlite3

The sqlite connector is built-in to python. It has no network support, however, and must be opened as a file. Here is an example of a very simple SearchProvider using sqlite3:

```
{
    "name": "Funding DB Search",
    "connector": "sqlite3",
    "url": "/Users/sid/code/swirl_server/db.sqlite3",
    "query_template": "select {fields} from funding where city like '%%{query_string}%%' or company like '%%{query_string}%%';",
    "query_mappings": "fields=*,sort_by_date=fundedDate",
    "result_mappings": "city=title,company=body,fundedDate=date_published"
}
```

### Notes

* A fixed sql query is perfectly acceptable, e.g. you can eliminate fields=* and just put 'select * from ...' into the query_template

### Funding Data Set

The TechCrunch Continental USA funding data set was taken from [Insurity SpatialKey](https://support.spatialkey.com/spatialkey-sample-csv-data/). 
It is included with SWIRL in [Data/funding_db.csv](../Data/funding_db.csv) 
This file was processed with [scripts/fix_csv.py](../scripts/fix_csv.py) prior to loading into Sqlite3. 

To load the data set into Sqlite3:

1. Activate [sqlite_web](ADMIN_GUIDE.md#sqlite-web)

From swirl_server root:

```
sqlite_web db.sqlite3
```

2. A browser window should open automatically; if not go to [http://localhost:8080/](http://localhost:8080/)
3. Enter "funding" in the text box in the upper right of the screen and press the "Create" button

![Sqlite loading funding dataset](images/sqlite_import_funding_1.png)

4. Click Choose File and select [Data/fundingUSA1_fixed.csv](../Data/fundingUSA1_fixed.csv)

5. Leave "Yes" in the box below.

6. Click "Import".

![Sqlite loading funding dataset](images/sqlite_import_funding_2.png)

<br/>

Then load the [Funding DB](../SearchProviders/funding_db.json) SearchProvider:


```
{
    "name": "Funding DB Search",
    "connector": "sqlite3",
    "url": "/Users/sid/code/swirl_server/db.sqlite3",
    "query_template": "select {fields} from {table} where {field1} like '%%{query_string}%%' or {field2} like '%%{query_string}%%';",
    "query_mappings": "fields=*,sort_by_date=fundedDate,table=funding,field1=city,field2=company",
    "result_mappings": "company=title,'{city} {fundedDate}: {company} raised usd ${raisedAmt} series {round} funding\n{company} which employs {numEmps} is located in {city}'=body,fundedDate=date_published,NO_PAYLOAD"
}
```

As [described in the User Guide](USER_GUIDE.md#creating-searchproviders).

<br/>

There are several other sample SearchProvider examples including Document DB that has a few articles scraped from the web, and others that target SWIRL's own tables, including SearchProvider, Search and Results. Documentation on these will be forthcoming in future releases.

:star: [SearchProvider JSON Examples](../SearchProviders/)

<br/>

<br/>

### Develop Your Own

You should create a new connector only if you need a new connection type. If you want to search another source for which you already have a connector, like requests_get, just create another SearchProvider object with different url, query or credential mappings.

:star: The [Google PSE SearchProvider JSON](../SearchProviders/google_pse.json) show how you can use one connector to make hundreds of SearchProviders!

<br/>

If you do need to add a new connector type, Connector source modules are in [swirl/connectors](../swirl/connectors/). Copy an existing one to a new file in the same folder, then alter the logic to suit your needs.

* Connectors should only import the objects required for a single connection - for example requests, elasticsearch or sqlite3
* The implementation of the connection should include:
    * Support for results_per_query > 10, including automatic paging
    * Date sorting support 
* Import new connectors in [swirl/connectors/__init__.py](../swirl/connectors/__init__.py)
* Add your connector to the CONNNECTOR_CHOICES block in models.py - note this will require [database migration](ADMIN_GUIDE.md#database-migration) 
* Results from each source should be processed with a result processor - look at the generic_result_processor to see how to process raw results into SWIRL's result schema - it's ok to develop a result processor for each connector as described in the next section
* Finally, results are landed (stored) separately in the database with the search_id the same so they can be joined by a mixer

<br/>

## Processor Modules

Processors operate mostly on in-memory data structures, and avoid loading Search, Result and SearchProvider objects.

<br/>

### Query Processors

Query Processors modify the Search.query_string, writing a new query to query_string_processed. 
This is then used by Connectors when constructing the query to send along to SearchProviders.

The following table lists the Query Processors included with SWIRL Preview 2:

<br/>

| Processor | Description | Notes | 
| --------- | ----------- | ----- | 
| generic_query_processor | Removes whitespace from queries | Stub in Preview3 |
| generic_pre_query_processor | Cleans queries removing all characters but alphanumerics and +-"()_~ | |
| spellcheck_query_processor | Corrects spelling errors in query_string and writes them into query_string_processed. Best deployed as a Search.pre_query_processor, but can be deployed as a SearchProvider query_processor. Experimental in SWIRL Preview 2. | Experimental, not recommended with Database or Google PSE |

<br/>

#### Spellcheck Query Processor

The SpellCheck Query Processor uses [TextBlob](https://textblob.readthedocs.io/en/dev/quickstart.html#spelling-correction). 

<br/>

### Result Processors

Result Processors translate the raw Search results into the SWIRL Result Dictionary format defined in [swirl/processors/utils.py](../swirl/processors/utils.py).

The following table lists the Result Processors included with SWIRL Preview 2:

| Processor | Description | Notes | 
| --------- | ----------- | ----- | 
| generic_result_processor | Searches result dictionary keys for SWIRL keys, and copies them, uses result_mappings if specified, mapping source_key to SWIRL_key as specified; aggegates remaining keys into the payload key | |
| generic_post_result_processor | Intended for processing of multiple landed Result objects | Stub in Preview3 |
| relevancy_processor | Highlights and quickly scores landed Results | Must be configured as a post_result_processor; produces score field |
| cosine_relevancy_processor | Highlights and carefully scores landed Results | Must be configured as a post_result_processor; produces score field |
| swirl_result_matches | Maps json results from sqlite3; experimental in SWIRL Preview 2. | Experimental in Preview3 |

<br/>

#### Generic Relevancy Post-Result Processor

This processor first highlights matches using [processors/utils.py](../swirl/processors/utils.py). Then it uses extremely simple techniques to produce a score from 1 to 10 for each result - 10 representing a result with extensive visible evidence
of the query in the returned results. 

This score is based on the following:

| Score | Description | 
| ----- | ----------- | 
| +1    | Each match in title, body, url or author |
| +1    | Multiple matches in title, body, url or author | 
| +2    | Match in title | 

If you combine use of the relevancy_mixer with search.sort set to "date", you will get the freshest, most relevant items for the search.

This processor is very fast and easy to understand. However, it does not discriminate around meaing, and is sensitive to content that simply repeats your search terms.

<br/>

#### Cosine Relevancy Post-Result Processor

The Cosine Relevancy Processor highlights matches using [processors/utils.py](../swirl/processors/utils.py). It then determines the [cosine similarity](https://en.wikipedia.org/wiki/Cosine_similarity) between embeddings for the query_string_processed and the title, body and author fields. (URL is not used, because it is frequently based on the title by content management systems.) This is refected as a percentage, from 0.0 to 1.0, where 1.0 is a totally relevant document for a given query string.

SWIRL uses [spacy.io](https://spacy.io/) to calculate embeddings, and the cosine similarity measurement was taken from the fantastic and highly recommended 
[Ultimate Guide To Text Similarity With Python - NewsCatcher](https://newscatcherapi.com/blog/ultimate-guide-to-text-similarity-with-python) :-)

The similarity calculations are then weighted using weights set in the RELEVANCY_CONFIG dictionary in [cosine_relevancy_processor](../swirl/processors/relevancy.py) and summarized in this table:

| Field | Weight | Notes | 
| ----- | ------ | ----- | 
| title | 3.0    | 2.0 is not enough |
| body  | 1.0    | Base relevancy score | 
| author | 2.0   | Not heavily tested |

The processor also outputs an explain structure to show the underlying reasons for a relevancy score. 

```
"explain": {
                "matches": {
                    "title": [
                        "new",
                        "york",
                        "new_york"
                    ],
                    "body": [
                        "new",
                        "york",
                        "new_york"
                    ]
                },
                "similarity": 0.74,
                "boosts": [
                    "term_match 0.2",
                    "phrase_match 0.2",
                    "all_terms 0.4"
                ]
            }
```

The above explain structure indicates that the query term "new york" was matched in both title and body, as a phrase and a single term, and the result received boosts for those as well as a larger boost for matching all query terms in a single field. Note that the highest boost is the only one taken. So the final relevancy for this result will be 1.0, since the base similarity 0.74 plus the boost of 0.4 is 1.14 which is truncated to 1.0. 

Complete sample output from this processor is [below](#result-mixer-modules)

For more information see: [User Guide - Understanding Relevancy](USER_GUIDE.md#understanding-relevancy)

<br/>

### Develop Your Own

Processors are located in [swirl/processors](../swirl/processors/). Copy one to a new file in the same folder, then alter the logic to suit your needs.

* Processors should not access model objects, except for post_result_processors
* Import your new processor in [swirl/processors/__init__.py](../swirl/processors/__init__.py)
* Helper functions to create Result dictionaries and highlight text are located in [swirl/processors/util.py](../swirl/processors/utils.py)

<br/>

## Result Mixer Modules

A Mixer joins together the separate Result objects for a given Search, wraps them in metadata and orders them in various ways. 
For example, a mixer might alternate from each source (round_robin_mixer), or the first few results from each (stack_mixer, stack_2_mixer). 

The following table presents the current mixer options:

| Mixer | Description | Notes |
| ----- | ----------- | ----- | 
| relevancy_mixer | Organizes results by [relevancy]() score (descending), then rank (ascending) | The default; depends on relevancy_processor being installed as the search.post_result_processor |
| round_robin_mixer | Organizes results by taking 1 result from each responding source, alternating | Good for searches with search.sort set to 'date' or anytime you want a cross section of results instead of just the ones with the most evidence | 
| stack_mixer | Organizes results by taking n results from each responding source, where n is results_requested / number of sources | Good for cross section of data |
| stack_2_mixer | Organizes results by taking 2 from each responding source, alternating | Good for cross sections of data with 4-6 providers |
| stack_3_mixer | Organizes results by taking 3 from each responding source, alternating | Good for cross sections of data with few providers | 

To invoke the mixer specified using the result_mixer property of the search object, specify the search_id as shown in APIs, above:

```
http://127.0.0.1:8000/swirl/results/?search_id=1
```

If you use the SWIRL defaults, a search will produces a json result that is relevancy ranked, like this:

```
{
    "messages": [
        "##S#W#I#R#L##1#0################################################################",
        "Retrieved 1 of 1 results from: Document DB Search",
        "Retrieved 2 of 2 results from: Enron Email ES Local",
        "Retrieved 4 of 947 results from: Funding DB Search",
        "Retrieved 2 of 2 results from: Enterprise Search PSE",
        "Retrieved 10 of 470 results from: Mergers and Acquisitions PSE",
        "Retrieved 10 of 13,190,000,000 results from: Strategy Consulting PSE",
        "Post processing of results by cosine_relevancy_processor updated 29 results",
        "Results ordered by: relevancy_mixer"
    ],
    "info": {
        "Document DB Search": {
            "found": 1,
            "retrieved": 1,
            "query_to_provider": "select * from documents where title like '%%miami%%' or body like '%%miami%%' limit 10;",
            "result_processor": "generic_result_processor"
        },
        "Enron Email ES Local": {
            "found": 2,
            "retrieved": 2,
            "query_to_provider": "index='email', query={'query_string': {'query': 'miami', 'default_field': 'content'}}",
            "result_processor": "generic_result_processor"
        },
        "Funding DB Search": {
            "found": 947,
            "retrieved": 4,
            "query_to_provider": "select * from funding where city like '%%miami%%' or company like '%%miami%%' limit 10;",
            "result_processor": "generic_result_processor"
        },
        "Enterprise Search PSE": {
            "found": 2,
            "retrieved": 2,
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=0c38029ddd002c006&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&start=1&q=miami",
            "result_processor": "generic_result_processor"
        },
        "Mergers and Acquisitions PSE": {
            "found": 470,
            "retrieved": 10,
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=b384c4e79a5394479&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&start=1&q=miami",
            "result_processor": "generic_result_processor"
        },
        "Strategy Consulting PSE": {
            "found": 13190000000,
            "retrieved": 10,
            "query_to_provider": "https://www.googleapis.com/customsearch/v1?cx=7d473806dcdde5bc6&key=AIzaSyDeB1y9l6OQW0dhVdZ9X_Xb2br_SK1K8YM&start=1&q=miami",
            "result_processor": "generic_result_processor"
        },
        "search": {
            "query_string": "miami",
            "query_string_processed": "miami"
        },
        "results": {
            "next_page": "/swirl/results/?search_id=121&result_mixer=round_robin_mixer&page=2",
            "retrieved": 10
        }
    },
    "results": [
        {
            "rank": 1,
            "score": 1.0,
            "title": "*Miami*",
            "url": "/Users/sid/code/swirl_server/db.sqlite3/947",
            "body": "Batanga",
            "date_published": "2007-08-01 00:00:00",
            "date_retrieved": "2022-03-30 20:11:16.820220",
            "author": "",
            "searchprovider": "Funding DB Search",
            "payload": {
                "raisedAmt": "30000000",
                "round": "c",
                "numEmps": ""
            },
            "matches": [
                "title"
            ]
        },
        {
            "rank": 2,
            "score": 1.0,
            "title": "*Miami*",
            "url": "/Users/sid/code/swirl_server/db.sqlite3/948",
            "body": "Batanga",
            "date_published": "2006-04-01 00:00:00",
            "date_retrieved": "2022-03-30 20:11:16.873468",
            "author": "",
            "searchprovider": "Funding DB Search",
            "payload": {
                "raisedAmt": "5000000",
                "round": "b",
                "numEmps": ""
            },
            "matches": [
                "title"
            ]
        },
        {
            "rank": 2,
            "score": 1.0,
            "title": "*Miami*",
            "url": "https://www.bcg.com/offices/miami/default",
            "body": "Boston Consulting Group is an Equal Opportunity Employer. All qualified applicants will receive consideration for employment without regard to race, color, age, ...",
            "date_published": "unknown",
            "date_retrieved": "2022-03-30 20:11:18.429199",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "XU2MeOybphcJ"
            },
            "matches": [
                "title"
            ]
        },
        {
            "rank": 3,
            "score": 1.0,
            "title": "*Miami*",
            "url": "/Users/sid/code/swirl_server/db.sqlite3/953",
            "body": "Global Roaming",
            "date_published": "2007-02-01 00:00:00",
            "date_retrieved": "2022-03-30 20:11:16.926501",
            "author": "",
            "searchprovider": "Funding DB Search",
            "payload": {
                "raisedAmt": "7500000",
                "round": "a",
                "numEmps": "29"
            },
            "matches": [
                "title"
            ]
        },
        {
            "rank": 4,
            "score": 1.0,
            "title": "*Miami*",
            "url": "/Users/sid/code/swirl_server/db.sqlite3/954",
            "body": "Global Roaming",
            "date_published": "2008-02-01 00:00:00",
            "date_retrieved": "2022-03-30 20:11:16.972467",
            "author": "",
            "searchprovider": "Funding DB Search",
            "payload": {
                "raisedAmt": "23000000",
                "round": "b",
                "numEmps": "29"
            },
            "matches": [
                "title"
            ]
        },
        {
            "rank": 1,
            "score": 0.69,
            "title": "*Miami* | United States | McKinsey & Company",
            "url": "https://www.mckinsey.com/us/miami",
            "body": "Our client work spans many of the region's key sectors, including marketing and sales, supply chain management, manufacturing, high tech, and social sector.",
            "date_published": "unknown",
            "date_retrieved": "2022-03-30 20:11:18.410965",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "3mPKNTCJoRUJ"
            },
            "matches": [
                "title"
            ]
        },
        {
            "rank": 3,
            "score": 0.68,
            "title": "Deloitte *Miami*, FL – Professional Services | Deloitte US",
            "url": "https://www2.deloitte.com/us/en/footerlinks/office-locator/florida/miami.html",
            "body": "In the United States, Deloitte LLP and its subsidiaries have more than 80000 professionals with a single focus: Serving our local, regional, and national ...",
            "date_published": "unknown",
            "date_retrieved": "2022-03-30 20:11:18.446605",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "hHShEMul44cJ"
            },
            "matches": [
                "title"
            ]
        },
        {
            "rank": 5,
            "score": 0.65,
            "title": "Search *Miami* Jobs at PwC",
            "url": "https://jobs.us.pwc.com/location/miami-jobs/932/6252001-4155751-4164138/4",
            "body": "459 jobs ... Related · Data Analytics Consulting - Senior Associate Multiple Locations 03/23/2022 · AML & Risk Compliance - Senior Associate Multiple Locations 03/22/ ...",
            "date_published": "unknown",
            "date_retrieved": "2022-03-30 20:11:18.479163",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "0PE2KKUSfkUJ"
            },
            "matches": [
                "title"
            ]
        },
        {
            "rank": 7,
            "score": 0.56,
            "title": "Jobs in *Miami*, FL - Deloitte Jobs",
            "url": "https://jobsus.deloitte.com/miami/florida/usa/jobs/",
            "body": "1,666 Jobs in *Miami*, FL · nCino Configuration Developer- Senior Solution Specialist · Manager-Software Specialist-HXM · Deloitte Studios Digital Product Manager.",
            "date_published": "unknown",
            "date_retrieved": "2022-03-30 20:11:18.512655",
            "author": "",
            "searchprovider": "Strategy Consulting PSE",
            "payload": {
                "cacheId": "TT3D5Ph8ADwJ"
            },
            "matches": [
                "title",
                "body"
            ]
        },
        {
            "rank": 2,
            "score": 0.54,
            "title": "BET Founder's REIT Pays $72M for *Miami* Beach Hotel",
            "url": "https://www.themiddlemarket.com/news/bet-founders-reit-pays-72m-for-miami-beach-hotel",
            "body": "Jun 23, 2014 ... The group, founded by BET founder Robert L. Johnson, also recently announced deals for hotels in Portland, Ore. and Irvine, Calif.",
            "date_published": "unknown",
            "date_retrieved": "2022-03-30 20:11:18.312918",
            "author": "",
            "searchprovider": "Mergers and Acquisitions PSE",
            "payload": {},
            "matches": [
                "title"
            ]
        }
    ]
}
```

To [specify a different mixer](USER_GUIDE.md#specifying-a-different-mixer), add result_mixer=mixer-name to the URL as noted in the [User Guide](USER_GUIDE.md#specifying-a-different-mixer).

The following table describes the Mixer wrapper in more detail:

<br/>

| Field | Description |
| ------------------ | -----------------------------------------------------------------|
| messages | All messages from the Search and all SearchProviders |
| info | A dictionary of Found and Retrieved counts from each provider | 
| info - search | Information about the search, including the processed query |
| info - results | Information about the results, including the number retrieved and the URL of the next (and previous) pages of results |
| results | Mixed Results from the specified Search |

<br/>

You can view results using a different mixer by adding result_mixer to the request URL, for example:

```
http://127.0.0.1:8000/swirl/results/?search_id=1&result_mixer=stack_mixer
```

### Develop Your Own

Mixers are located in [swirl/mixers](../swirl/mixers/). 
Copy one to a new file in the same folder, then alter the logic to suit your needs.

* To install a mixer, import it in [swirl/mixers/__init__.py](../swirl/mixers/__init__.py)
* The utils.py module has a helper function to create mixer_wrappers
* Look at the [relevancy mixer](../swirl/mixers/relevancy.py) for examples of how to sort Result objects

<br/>

## Changing Defaults

If you want to change the default setting for any object property - for example, setting the Search.retention to a value other than zero.
This is done in [swirl/models.py](../swirl/models.py). 

:warning: This file, and the class models within it, are extremely sensitive, and require [database migration](ADMIN_GUIDE.md#database-migration)

To change a default, alter the default= parameter on the model definition. For example here is the default Retention for SWIRL Preview 2:

```
class Search(models.Model):
    id = models.BigAutoField(primary_key=True)
    ... etc ... 
    RETENTION_CHOICES = [
        (0, 'Do not expire'),
        (1, 'Expire after 1 hour'),
        (2, 'Expire after 1 day'),
        (3, 'Expire after 1 month')
    ]
    retention = models.IntegerField(default=0, choices=RETENTION_CHOICES)
```

To change the default to 'Expire after 1 hour', change default=0 to default=1:

```
class Search(models.Model):
    id = models.BigAutoField(primary_key=True)
    ... etc ... 
    RETENTION_CHOICES = [
        (0, 'Do not expire'),
        (1, 'Expire after 1 hour'),
        (2, 'Expire after 1 day'),
        (3, 'Expire after 1 month')
    ]
    retention = models.IntegerField(default=1, choices=RETENTION_CHOICES)
```

DO NOT put the string choice. 

After making this change, you will have to run [Database Migration](#database-migration).

:warning: If you don't do a migration after making such a change, the change won't take effect, and you may receive
warning or other errors upon startup, and during subsequent operation.

<br/>

<br/>

# Further Reading

:small_blue_diamond: [User Guide](USER_GUIDE.md)
:small_blue_diamond: [Admin Guide](ADMIN_GUIDE.md)

<br/>

<br/>

# Get Support

Please email [swirl-support@probstein.com](mailto:swirl-support@probstein.com) for support.

<br/>