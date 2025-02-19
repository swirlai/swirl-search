---
layout: default
title: Tutorial - Extending SWIRL
nav_order: 20
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# Tutorial: Extending SWIRL

## Before You Start...

We recommend reviewing the following documents prior to pursuing the tutorial.

* [What is SWIRL?](index.md#what-is-swirl-ai-connect)
* [SWIRL Workflow](Developer-Guide.html#workflow)
* [How do I connect SWIRL to some new source?](index.md#how-do-i-connect-swirl-to-some-new-source)
* [Response Mappings](https://docs.swirlaiconnect.com/SP-Guide.html#response-mappings)
* [Result Mappings](https://docs.swirlaiconnect.com/SP-Guide.html#result-mappings)

# Creating a SearchProvider

A SearchProvider is a configuration of a Connector. To connect to a given source, first verify that it supports a Connector that SWIRL already has. (See the next tutorial for information on creating new Connectors.)

For example, if trying to query a website using a URL like `https://host.com/?q=my+query+here` that returns JSON or XML, create a new SearchProvider configuring the `RequestsGet` Connector as follows:

* Copy any of the [Google PSE SearchProviders](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/google.json)

* Modify the `url` and `query_template` to construct the query URL. Using the above example:
```
{
    "url": "https://my-host.com/",
    "query_template": "{url}?q={query_string}",
}
```
To learn more about query and URL parameters, refer to the [SearchProvider Guide](SP-Guide.html).

* If the website offers the ability to page through results, or sort results by date (as well as relevancy), use the `PAGE=` and `DATE_SORT=` query mappings to add support for these features through SWIRL.  

For example:
```
"query_mappings": "DATE_SORT=sort=date,PAGE=start=RESULT_INDEX"
```

For more information, refer to the [SearchProvider Guide, Query Mappings](SP-Guide.html#query-mappings) section.

* Open the query URL in a browser and look through the JSON response. 
If using Visual Studio Code, right-click on the pasted JSON and select `Format Document` to make it easier to read.

* Identify the results list, and number of results found and retrieved. Put these JSON paths in the `response_mappings`. Then, identify the JSON paths to use to extract the SWIRL default fields `title`, `body`, `url`, `date_published` and `author` from each item in the result list and add those to in the `result_mappings`, with the SWIRL field name on the left, and the source JSON path on the right.  For example:
```
"response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
"result_mappings": "url=link,body=snippet,author=displayLink,cacheId,pagemap.metatags[*].['og:type'],pagemap.metatags[*].['og:site_name'],pagemap.metatags[*].['og:description'],NO_PAYLOAD",
```

* Add credentials as required for the service.  The format to use depends on the type of credential. Details are here: [User Guide, Authentication & Credentials](SP-Guide.html#authentication--credentials) section.

* Add a suitable tag that can be used to describe the source or what it knows about.  Spaces are not permitted; good tags are clear and obvious when used in a query, like `company:tesla` or `news:openai`. For more about tags, see: [Organizing SearchProviders with Active, Default and Tags](SP-Guide.html#organizing-searchproviders-with-active-default-and-tags)

* Review the finished SearchProvider:
```
{
        "name": "My New SearchProvider",
        "connector": "RequestsGet",
        "url": "https://host.com/",
        "query_template": "{url}?q={query_string}",
        "query_processors": [
            "AdaptiveQueryProcessor"
        ],
        "query_mappings": "",
        "result_processors": [
            "MappingResultProcessor",
            "CosineRelevancyResultProcessor"
        ],
        "response_mappings": "FOUND=jsonpath.to.number.found,RETRIEVED=jsonpath.to.number.retrieved,RESULTS=jsonpath.to.result.list",
        "result_mappings": "url=link,body=snippet,author=displayLink,NO_PAYLOAD",
        "credentials": "bearer=your-bearer-token-here",
        "tags": [
            "MyTag"
        ]
    }
```

* Go to SWIRL `localhost:8000/swirl/searchproviders/`, logging in if necessary. Put the form at the bottom of the page into `Raw data` mode, and paste the SearchProvider into the box. Click the `POST` button to add it. The SearchProvider page will reload.

* Go to the Galaxy UI at `localhost:8000/galaxy/` and run a search using the Tag you created for the new SearchProvider. Results should again appear in roughly the same period of time.

# Creating a Connector

SWIRL Connectors are responsible for loading a SearchProvider, constructing and transmitting queries to a particular type of service, then saving the response - typically a result list.

{: .highlight }
Consider using your favorite coding AI to generate a Connector by passing it the Connector base classes, and information about the API you are trying to query. 

{: .highlight }
If you are trying to send an HTTP/S request to an endpoint that returns JSON or XML, you don't need to create a Connector. Instead, [Create a SearchProvider](#creating-a-searchprovider) that configures the RequestsGet connector included with SWIRL.

To create a new Connector:

* Create a new Connector file, e.g. `swirl/connectors/my_connector.py`

* Copy the style of the `ChatGPT` connector as a starting point, or `BigQuery` if targeting a database.
```
class MyConnector(Connector):

    def __init__(self, provider_id, search_id, update, request_id=''):
        self.system_guide = MODEL_DEFAULT_SYSTEM_GUIDE
        super().__init__(provider_id, search_id, update, request_id)
```

* In the `__init__` class, load and persist anything that will be needed when connecting and querying the service.

* Import the Python package(s) to connect to the service. 

```
import your-connector-package
```

* Modify the `execute_search` method to connect to the service. 

As you can see from the ChatGPT Connector, it first loads the OpenAI credentials, then constructs a prompt, sends the prompt via `openai.ChatCompletion.create()`, then stores the response. 

```
    def execute_search(self, session=None):

        logger.debug(f"{self}: execute_search()")

        if self.provider.credentials:
            openai.api_key = self.provider.credentials
        else:
            if getattr(settings, 'OPENAI_API_KEY', None):
                openai.api_key = settings.OPENAI_API_KEY
            else:
                self.status = "ERR_NO_CREDENTIALS"
                return

        prompted_query = ""
        if self.query_to_provider.endswith('?'):
            prompted_query = self.query_to_provider
        else:
            if 'PROMPT' in self.query_mappings:
                prompted_query = self.query_mappings['PROMPT'].format(query_to_provider=self.query_to_provider)
            else:
                prompted_query = self.query_to_provider
                self.warning(f'PROMPT not found in query_mappings!')

        if 'CHAT_QUERY_REWRITE_GUIDE' in self.query_mappings:
            self.system_guide = self.query_mappings['CHAT_QUERY_REWRITE_GUIDE'].format(query_to_provider=self.query_to_provider)

        if not prompted_query:
            self.found = 0
            self.retrieved = 0
            self.response = []
            self.status = "ERR_PROMPT_FAILED"
            return
        logger.info(f'CGPT completion system guide:{self.system_guide} query to provider : {self.query_to_provider}')
        self.query_to_provider = prompted_query
        completions = openai.ChatCompletion.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": self.system_guide},
                {"role": "user", "content": self.query_to_provider},
            ],
            temperature=0,
        )
        message = completions['choices'][0]['message']['content'] # FROM API Doc

        self.found = 1
        self.retrieved = 1
        self.response = message.replace("\n\n", "")

        return

```

* ChatGPT depends on the OpenAI API key, which is provided to SWIRL Community via the `.env` file. To follow this pattern, create new values in `.env` then modify `swirl_server/settings.py` to load them as Django settings, and set a reasonable default.

{: .highlight }
In SWIRL Enterprise, use [AIProviders to configure LLMs and RAG](AI-Connect.md#activating-ai-providers) instead of the `.env` file.

* Modify the `normalize_response()` method to store the raw response. This is literally no more (or less) than writing the result objects out as a Python list and storing that in `self.results`:
```
    def normalize_response(self):

        logger.debug(f"{self}: normalize_response()")

        self.results = [
                {
                'title': self.query_string_to_provider,
                'body': f'{self.response}',
                'author': 'CHATGPT',
                'date_published': str(datetime.now())
            }
        ]

        return
```

{: .highlight }
There's no need to do this if `self.response` is already a Python list.

* Add the new Connector to `swirl/connectors/__init__.py`
```
from swirl.connectors.my_connector import MyConnector
```

* Restart SWIRL
```
% python swirl.py restart
```

* Create a SearchProvider to configure the new Connector, then add it to the SWIRL installation as noted in the [Creating a SearchProvider](#creating-a-searchprovider) section above.  Don't forget a useful Tag so that you can easily target the new connector when ready to test.

To learn more about developing Connectors, refer to the [Developer Guide, Developing New Connectors](Developer-Guide.html#develop-new-connectors) section.

# Creating a QueryProcessor

A QueryProcessor is a stage executed either during Pre-Query or Query Processing. The difference between these is that the result of Pre-Query processing is applied to all SearchProviders, and Query Processing is executed by each individual SearchProvider. 

In both cases, the goal is to modify the query sent to some group of SearchProviders. 

Note: if you just want to rewrite the query using lookup tables or regular expressions, consider [using `QueryTransformations` instead](Developer-Guide.html#query-transformation-rules).

To create a new QueryProcessor:

* Create a new module like `swirl/processors/my_query_processor.py`. You can also add your new class to an existing module like `swirl/processors/Generic.py`.

* Copy the `GenericQueryProcessor` class as a starting point, and rename it:
```
class MyQueryProcessor(QueryProcessor):

    type = 'MyQueryProcessor'

    def process(self):
        # TO DO: modify self.query_string, and return it 
        return self.query_string + ' modified'
```

* A common use case for a new QueryProcessor is to use some function or external service to rewrite the query. Here's an example of how to do the former. Given some function in package MyPackage:
```
def my_query_modification_function(query):
    # implementation
    return modified_query
```

* Create a new QueryProcessor that imports the function:

```
from MyPackage import my_query_modification_function

class MyQueryProcessor(QueryProcessor):
    type = 'MyQueryProcessor'
    def process(self):
        new_query_string = my_query_modification(self.query_string)
        if new_query_string:
            return new_query_string
        else:
            return self.query_string
```

* Save the new QueryProcessor.

* If you created a new module, add it to `swirl/processors/__init__.py`.  This can be skipped if you added the new QueryProcessor to an existing module.
```
from swirl.processors.my_processor import *
```

* Add the new Processor to the appropriate `swirl.models` CHOICES block. 

* For Pre-Query processing, add it to the `Search` object (this is required for security reasons):

```
    PRE_QUERY_PROCESSOR_CHOICES = [
        ('GenericQueryProcessor', 'GenericQueryProcessor'),
        ('SpellcheckQueryProcessor', 'SpellcheckQueryProcessor'),
        ('MyQueryProcessor','MyQueryProcessor')
    ]
```

* To make the new Processor a default for new Search objects, add it to the return list in this block:
```
def getSearchPreQueryProcessorsDefault():
    return []
```

* For Query processing in one or more SearchProviders, add it here:

```
    QUERY_PROCESSOR_CHOICES = [
        ('GenericQueryProcessor', 'GenericQueryProcessor'),
        ('SpellcheckQueryProcessor', 'SpellcheckQueryProcessor'),
        ('MyQueryProcessor','MyQueryProcessor')
    ]

```

* To make the new Processor a default for new SearchProvider objects, add it to the return list in this block:
```
def getSearchProviderQueryProcessorsDefault():
    return ["AdaptiveQueryProcessor"]
```

* Add the new QueryProcessor to either a `Search.pre_query_processing` pipeline or at least one `SearchProvider.query_processing` pipeline:

`SearchProvider`:
```
        "query_processors": [
            "AdaptiveQueryProcessor",
            "MyQueryProcessor"
        ],
```

`Search`:
```
  {
        "query_string": "news:ai",
        "pre_query_processors": [
          "MyQueryProcessor"
        ],
  }
```

* Restart SWIRL
```
% python swirl.py restart
```

* Go to the Galaxy UI (`http://localhost:8000/galaxy/`) and run a search; if using a query processor be sure to [target that SearchProvider with a tag](SP-Guide.html#using-tags-to-target-searchproviders). 

For example if you added a QueryProcessor to a SearchProvider `query_processing` pipeline with a Tag of "news", the query would be `http://localhost:8000/swirl/search/?q=news:some+query` instead. Results should appear in a just a few seconds. In the `messages` block, a message indicating that the new QueryProcessor rewrote the query should appear:
```
MyQueryProcessor rewrote <Some-Connector> query to: <modified-query> 
```

# Creating a ResultProcessor

A ResultProcessor is a stage executed by each SearchProvider, after the Connector has retrieved results. ResultProcessors operate on results and transform them as needed for downstream consumption or presentation.

The `GenericResultProcessor` and `MappingResultProcessor` stages are intended to normalize JSON results. `GenericResultProcessor` searches for exact matches to the SWIRL schema (as noted in the SearchProvider example) and copies them over. `MappingResultProcessor` applies `result_mappings` to normalize the results, again as shown in the SearchProvider example above. In general, adding stages *after* these is a good idea, unless the SearchProvider is expected to respond in a SWIRL schema format.

To create a new ResultProcessor:

* Create a new file, e.g. `swirl/processors/my_result_processor.py`

* Copy the `GenericResultProcessor` class as a starting point, and rename it. 

* Implement the `process()` method. This is the only one required. `Process()` operates on `self.results`, which will contain all the results from a given SearchProvider, in Python list format. Modify items in the result list, and report the number updated.

* For example, here is a `process()` method that adds a field 'my_field1' to each result item, with the value "test":
```
    def process(self):

        if not self.results:
            return

        updated = 0
        for item in self.results:
            # TO DO: operate on each item and count number updated
            item['my_field1'] = 'test'
            updated = updated + 1

        # note: there is no need to save in this type of Processor

        # save modified self.results
        self.processed_results = self.results
        # save number of updated
        self.modified = updated

        return self.modified
```

* Save the new module and add it to `swirl/processors/__init__.py`
```
from swirl.processors.my_processor import MyResultProcessor
```

* Add the new module to the following swirl.models CHOICES block (this is required for security reasons.)
```
    RESULT_PROCESSOR_CHOICES = [
        ('GenericResultProcessor', 'GenericResultProcessor'),
        ('DuplicateHalfResultProcessor', 'DuplicateHalfResultProcessor'),
        ('TestResultProcessor', 'TestResultProcessor'),
        ('MappingResultProcessor', 'MappingResultProcessor'),
        ('DateFinderResultProcessor','DateFinderResultProcessor'),
        ('DedupeByFieldResultProcessor', 'DedupeByFieldResultProcessor'),
        ('LenLimitingResultProcessor', 'LenLimitingResultProcessor'),
        ('CleanTextResultProcessor','CleanTextResultProcessor'),
        ('RequireQueryStringInTitleResultProcessor','RequireQueryStringInTitleResultProcessor'),
        ('AutomaticPayloadMapperResultProcessor', 'AutomaticPayloadMapperResultProcessor'),
        ('CosineRelevancyResultProcessor','CosineRelevancyResultProcessor'),
        ('MyResultProcessor','MyResultProcessor')
    ]
```

* To make the new ResultProcessor a default for new SearchProvider objects, add it to the return list in this block:
```
def getSearchProviderResultProcessorsDefault():
    return ["MappingResultProcessor","DateFinderResultProcessor","CosineRelevancyResultProcessor"]
```

* Add the new module to at least one `SearchProvider.result_processing` pipeline:
```
        "result_processors": [
            "MappingResultProcessor",
            "MyResultProcessor",
            "CosineRelevancyResultProcessor"
        ],
         ...etc...
```

* Restart SWIRL
```
% python swirl.py restart
```

* Go to the Galaxy UI (`http://localhost:8000/galaxy/`) and run a search; be sure to target at least one SearchProvider that has the new ResultProcessor. For example if you added a ResultProcessor to a SearchProvider `result_processing` pipeline with the Tag "news", the query would need to be `http://localhost:8000/swirl/search/?q=news:some+query` instead of the above.

* Results should appear in a just a few seconds. In the `messages` block a message indicating that the new ResultProcessor updated a number of results should appear, and the content should be modified as expected.
```
MyResultProcessor updated 5 results from: MyConnector",
```

To learn more about writing Processors, refer to the [Developer Guide](Developer-Guide.html#develop-new-processors)

# Creating a PostResultProcessor

A PostResultProcessor is a stage executed after all SearchProviders have returned results. They operate on all the results for a given Search. 

To create a new ResultProcessor:

* Create a new module like `swirl/processors/my_post_result_processor.py`

* Copy the template below as a starting point, and rename it:
```
class MyPostResultProcessor(PostResultProcessor):

    type = 'MyPostResultProcessor'

    def process(self):

        updated = 0
        for results in self.results:
            if not results.json_results:
                continue
            for item in results.json_results:
                # TO DO: operate on each result item
                item['my_field2'] = "test"
                updated = updated + 1
            # end for
            # call results.save() if any results were modified
            if updated > 0:
                results.save()

        # end for
        ############################################

        self.results_updated = updated
        return self.results_updated
```

* Modify the `process()` method operating on the items and saving each result set as shown. 

* Add the new module to `swirl/processors/__init__.py`
```
from swirl.processors.my_post_result_processor import MyPostResultProcessor
```

* Add the new module to the following `swirl.models` CHOICES block (this is required for security reasons. ):
```
    POST_RESULT_PROCESSOR_CHOICES = [
        ('CosineRelevancyPostResultProcessor', 'CosineRelevancyPostResultProcessor'),
        ('DropIrrelevantPostResultProcessor','DropIrrelevantPostResultProcessor'),
        ('DedupeByFieldPostResultProcessor', 'DedupeByFieldPostResultProcessor'),
        ('DedupeBySimilarityPostResultProcessor', 'DedupeBySimilarityPostResultProcessor'),
        ('MyPostResultProcessor','MyPostResultProcessor')
    ]
```

* To make the new ResultProcessor a default for new SearchProvider objects, add it to the return list in this block:
```
def getSearchPostResultProcessorsDefault():
    return ["DedupeByFieldPostResultProcessor","CosineRelevancyPostResultProcessor,"MyPostResultProcessor"]
```

* Add the new module to a `Search.post_result_processing` pipeline:
```
  {
        "query_string": "news:ai",
        "post_result_processors": [
            "DedupeByFieldPostResultProcessor",
            "CosineRelevancyPostResultProcessor",
            "MyPostResultProcessor"
        ],
        ...etc...
    }
```

* Restart SWIRL
```
% python swirl.py restart
```

* Go to the Galaxy UI (`http://localhost:8000/galaxy/`) and run a search; be sure to target at least one SearchProvider that has the new PostResultProcessor. For example if you added a PostResultProcessor to a Search `post_result_processing` pipeline with the Tag "news", the query would need to be `http://localhost:8000/swirl/search/?q=news:some+query` instead of the above.

* Results should appear in a just a few seconds. In the `messages` block a message indicating that the new PostResultProcessor updated a number of results should appear, and the content should be modified as expected.
```
MyPostResultProcessor updated 10 results from: MySearchProvider
```

To learn more about writing Processors, refer to the [Developer Guide](Developer-Guide.html#develop-new-processors)

