---
layout: default
title: SearchProviders
nav_order: 21
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

<span class="big-text">SearchProviders Guide</span><br/><span class="med-text">Community Edition | Enterprise Edition</span>

---

{: .highlight }
SWIRL queries may be subject to rate limits or throttling imposed by the sources being queried.

SearchProviders are the core of SWIRL, enabling easy connections to various data sources **without writing any code**.

Each SearchProvider is a JSON object. SWIRL includes preconfigured providers for sources like Elastic, Solr, PostgreSQL, BigQuery, NLResearch.com, Miro.com, Atlassian, and more.

{: .highlight }
SWIRL comes with **active** SearchProviders for **arXiv.org, European PMC, and Google News** that work "out of the box" if internet access is available. 

Additionally, **inactive** SearchProviders for **Google Web Search and SWIRL Documentation** use Google Programmable Search Engine (PSE). These require a **Google API key**. See the [SearchProvider Guide](#activating-a-google-programmable-search-engine-pse-searchprovider) for setup details.

[SearchProvider Example JSON](https://github.com/swirlai/swirl-search/tree/main/SearchProviders)

# Preloaded SearchProviders

| SearchProvider | Description | Notes |
|---------------|-------------|-------|
| **arxiv.json** | Searches the [arXiv.org](https://arxiv.org/) repository of scientific papers | No authentication required |
| **asana.json** | Searches tasks in [Asana](https://asana.com/) | Requires Asana personal access token |
| **atlassian.json** | Searches Atlassian [Confluence Cloud](https://www.atlassian.com/software/confluence), [Jira Cloud](https://www.atlassian.com/software/jira), and [Trello](https://trello.com/) | Requires a bearer token and/or Trello API key |
| **blockchain-bitcoin.json** | Searches [Blockchain.com](https://www.blockchain.com/) for Bitcoin addresses and transactions | Requires Blockchain.com API key |
| **chatgpt.json** | OpenAI ChatGPT AI chatbot | Requires OpenAI API key |
| **company_snowflake.json** | Queries the [Snowflake](https://www.snowflake.com/en/) `FreeCompanyResearch` dataset | Requires Snowflake username and password |
| **crunchbase.json** | Searches organizations via [Crunchbase](https://www.crunchbase.com/) API | Requires Crunchbase API key |
| **document_db.json** | SQLite3 document database | [Sample Data](https://github.com/swirlai/swirl-search/tree/main/Data/documents_db.csv) |
| **elastic_cloud.json** | ElasticSearch (cloud version) | [Enron Email Dataset](./Developer-Reference#enron-email-data-set) |
| **elasticsearch.json** | ElasticSearch (local install) | [Enron Email Dataset](./Developer-Reference#enron-email-data-set) |
| **europe_pmc.json** | Searches [EuropePMC.org](https://europepmc.org/) for life sciences literature | No authentication required |
| **funding_db_bigquery.json** | BigQuery funding database | [Funding Dataset](./Developer-Reference#funding-data-set) |
| **funding_db_postgres.json** | PostgreSQL funding database | [Funding Dataset](./Developer-Reference#funding-data-set) |
| **funding_db_sqlite3.json** | SQLite3 funding database | [Funding Dataset](./Developer-Reference#funding-data-set) |
| **github.json** | Searches public repositories for Code, Commits, Issues, and PRs | Requires GitHub bearer token |
| **google_news.json** | Queries [Google News](https://news.google.com/) | No authentication required |
| **google_pse.json** | Web search via Google Programmable Search Engine (PSE) | Requires Google API key |
| **google_workspace.json** | Queries [Google Workspace](https://workspace.google.com/) | See the [Google Workspace Guide](GoogleWorkspace-Guide) | 
| **hacker_news.json** | Queries [Hacker News](https://hn.algolia.com/) | No authentication required |
| **http_get_with_auth.json** | Generic HTTP GET with authentication | Requires URL and credentials |
| **http_post_with_auth.json** | Generic HTTP POST with authentication | Requires URL and credentials |
| **hubspot.json** | Searches the HubSpot CRM for Companies, Contacts, and Deals | Requires API token with [these scopes](images/HubSpot-scopes.png) |
| **internet_archive.json** | Queries the [Internet Archive](https://archive.org/) | No authentication required |
| **littlesis.json** | Queries [LittleSis.org](https://littlesis.org/) database of influential business and government figures | No authentication required |
| **microsoft.json** | Queries Microsoft 365 (Outlook, OneDrive, SharePoint, Teams) | See the [M365 Guide](./M365-Guide) |
| **miro.json** | Searches [Miro.com](https://miro.com) boards | Requires bearer token |
| **movies_mongodb.json** | Queries [MongoDB Atlas](https://www.mongodb.com/) `sample_mflix.movies` dataset | Requires MongoDB credentials |
| **newsdata_io.json** | Searches [Newsdata.io](https://newsdata.io/) | Requires API key |
| **nlresearch.json** | Searches [NLResearch.com](https://northernlight.com/) premium content | Requires credentials |
| **open_sanctions.json** | Queries [OpenSanctions.org](https://www.opensanctions.org/) | Requires API key |
| **opensearch.json** | OpenSearch 2.x | [Developer Guide](./Developer-Reference#elastic--opensearch) |
| **oracle.json** | Queries Oracle 23c Free (and earlier versions) | Requires Oracle credentials |
| **preloaded.json** | All preloaded SearchProviders | Default in SWIRL |
| **servicenow.json** | Searches ServiceNow Knowledge and Service Catalog | Requires username and password |
| **solr.json** | Queries Apache Solr (local install) | Requires host, port, collection |
| **solr_with_auth.json** | Secured Solr instance | Requires credentials |
| **youtrack.json** | Searches [JetBrains YouTrack](https://www.jetbrains.com/youtrack/) | Requires bearer token |

This table provides a high-level overview of the available SearchProviders. Detailed configurations can be found in the [SearchProviders repository](https://github.com/swirlai/swirl-search/tree/main/SearchProviders).

# Activating a SearchProvider

To activate a preloaded SearchProvider, [edit it](#editing) and change:

```json
    "active": false
```

to

```json
    "active": true
```

Click the `PUT` button to save the change. You can also use the `HTML Form` at the bottom of the page for convenience.

![SearchProvider HTML form](images/swirl_sp_html_form.png)

# Activating a Google Programmable Search Engine (PSE) SearchProvider

SWIRL includes an **inactive** Google PSE configuration that allows searching the web or a defined "slice" of it.  
Google PSE **is not free** and requires a **valid Google API key**.

## Create a Google Programmable Search Engine (PSE)
1. Go to [Google Programmable Search Engine](https://programmablesearchengine.google.com/about/)  
2. Click **Get Started** and log in with your Google account  
3. Follow the steps to create a PSE and note the `cx` parameter (your Google PSE ID)

## Create a Google API Key
1. Visit the [Google API Custom Search overview](https://developers.google.com/custom-search/v1/overview)  
2. Follow the instructions to generate an API key  

## Activate the Google PSE SearchProvider

1. [Edit the Google PSE provider](#editing)
2. Change:
   ```json
       "active": false
   ```
   to:
   ```json
       "active": true
   ```
   Or use the **HTML form** at the bottom of the page.
3. Update the `query_mappings` field with your Google PSE ID (`cx` parameter):
   ```json
       "query_mappings": "cx=<your-Google-PSE-id>"
   ```
4. Update the `credentials` field with your Google API key, using the `key=` prefix:
   ```json
       "credentials": "key=<your-Google-API-key>"
   ```
5. Click the `PUT` button to save the changes.
6. Reload SWIRL Galaxy—your new source will appear in the source selector.

# Copy/Paste Install

If you have a **SearchProvider JSON file**, you can copy and paste it into the form at the bottom of the **SearchProvider endpoint**.

![SWIRL API](images/swirl_spl_empty.png)

## Steps:
1. Go to [http://localhost:8000/swirl/searchproviders/](http://localhost:8000/swirl/searchproviders/)
2. Click the `Raw data` tab at the bottom of the page.
3. Paste the SearchProvider JSON (either a single record or a list of records).
4. Click the `POST` button.
5. SWIRL will confirm the new SearchProvider(s).

# Bulk Loading

Use the [`swirl_load.py`](https://github.com/swirlai/swirl-search/blob/main/swirl_load.py) script to bulk-load SearchProviders.

## Steps:
1. Open a terminal and navigate to your SWIRL home directory:
   ```shell
   cd <swirl-home>
   ```
2. Run the following command:
   ```shell
   python swirl_load.py SearchProviders/provider-name.json -u admin -p your-admin-password
   ```
3. The script will load all configurations from the specified file.
4. Visit [http://localhost:8000/swirl/searchproviders/](http://localhost:8000/swirl/searchproviders/) to verify.

## Example:
![SWIRL SearchProviders List - Google PSE Example 1](images/swirl_sp_pse-1.png)
![SWIRL SearchProviders List - Google PSE Example 2](images/swirl_sp_pse-2.png)

# Editing a SearchProvider

To edit a SearchProvider, append its `id` to the end of the `/swirl/searchproviders` URL.  

For example:  
`http://localhost:8000/swirl/searchproviders/1/`

![SWIRL SearchProvider Instance - Google PSE](images/swirl_sp_instance.png)

## Available Actions:
* **DELETE** the SearchProvider permanently.
* **Modify** the configuration and click `PUT` to save changes.

# Query Templating

Most SearchProviders require a **query_template**, which binds to **query_mappings** during the federation process.  

For example, the original `query_template` for the MongoDB movie SearchProvider:

```json
    "query_template": "{'$text': {'$search': '{query_string}'}}"
```

This format is a **string**, not valid JSON. The **single quotes** are required because the JSON itself uses **double quotes**.

Starting in **SWIRL 3.2.0**, MongoDB SearchProviders now use the **query_template_json** field, which stores the template as **valid JSON**:

```json
"query_template_json": {
    "$text": {
        "$search": "{query_string}"
    }
}
```

# Organizing SearchProviders with Active, Default, and Tags

SearchProviders have three properties that control their participation in queries:

| Property  | Description |
|-----------|------------|
| **Active**  | `true/false` – If `false`, the SearchProvider will not receive queries, even if specified in a `searchprovider_list`. |
| **Default** | `true/false` – If `false`, the SearchProvider will only be queried if explicitly listed in `searchprovider_list`. |
| **Tags**    | List of strings grouping providers by topic. Tags can be used in `searchprovider_list`, as a `providers=` [URL parameter](./Developer-Guide#create-a-search-object-with-the-q-url-parameter), or as `tag:term` in a query. |

## Best Practices for SearchProvider Organization:

- **General-purpose providers** should have `"Default": true` to be included in broad searches.  
- **Topic-specific providers** should have `"Default": false` and use `"Tags": ["topic1", "topic2"]`.  
- Users can target specific providers using a mix of **Tags**, **SearchProvider names**, or **IDs**.

This ensures broad searches use the best general providers, while topic-specific searches can target precise data sources.

# Query Mappings

SearchProvider `query_mappings` are key-value pairs that define how queries are structured for a given SearchProvider.  

These mappings configure **field replacements and query transformations** that SWIRL's processors (such as `AdaptiveQueryProcessor`) use to adapt the query format to each provider's requirements.

## Available `query_mappings` Options

| Mapping Format | Description | Example |
|---------------|-------------|---------|
| **key = value** | Replaces `{key}` in the `query_template` with `value`. | ```"query_template": "{url}?cx={cx}&key={key}&q={query_string}","query_mappings": "cx=google-pse-key"``` |
| **DATE_SORT=url-snippet** | Inserts the specified string into the URL when date sorting is enabled. | `"query_mappings": "DATE_SORT=sort=date"` |
| **RELEVANCY_SORT=url-snippet** | Inserts the specified string into the URL when relevancy sorting is enabled. | `"query_mappings": "RELEVANCY_SORT=sort=relevancy"` |
| **PAGE=url-snippet** | Enables pagination by inserting either `RESULT_INDEX` (absolute result number) or `RESULT_PAGE` (page number). | `"query_mappings": "PAGE=start=RESULT_INDEX"` |
| **NOT=True** | Indicates that the provider supports basic `NOT` operators. | `elon musk NOT twitter` |
| **NOT_CHAR=-** | Defines a character for `NOT` operators. | `elon musk -twitter` |

# Query Field Mappings

In `query_mappings`, **keys enclosed in braces** within `query_template` are replaced with mapped values.

## Example Configuration

```json
"url": "https://www.googleapis.com/customsearch/v1",
"query_template": "{url}?cx={cx}&key={key}&q={query_string}",
"query_processors": [
        "AdaptiveQueryProcessor"
    ],
"query_mappings": "cx=0c38029ddd002c006,DATE_SORT=sort=date,PAGE=start=RESULT_INDEX",
```

## Example Query Output

At query execution time, this configuration generates:

```shell
https://www.googleapis.com/customsearch/v1?cx=0c38029ddd002c006&q=some_query_string
```

## Key Configuration Guidelines:

- The `url` field is **specific to each SearchProvider** and should contain **static parameters** that never change.
- `query_mappings` allow **dynamic replacements** using query-time values.
- The `query_string` is populated by SWIRL as described in the [Developer Guide](./Developer-Guide#workflow).

# HTTP Request Headers

The optional `http_request_headers` field allows **custom HTTP headers** to be sent along with a query.  

For example, the **GitHub SearchProvider** uses this to request **enhanced search snippets**, which are then mapped to SWIRL's `body` field:

```json
"http_request_headers": {
    "Accept": "application/vnd.github.text-match+json"
},

"result_mappings": "title=name,body=text_matches[*].fragment, ..."
```

This feature ensures **richer, more relevant search results** by enabling source-specific header configurations.

# Result Processors

Each SearchProvider can define its own **Result Processing pipeline**. A typical configuration looks like this:

```json
"result_processors": [
    "MappingResultProcessor",
    "CosineRelevancyResultProcessor"
],
```

## Enabling Relevancy Ranking

If **Relevancy Ranking** is required:

1. The `CosineRelevancyResultProcessor` **must be the last item** in the `result_processors` list.
2. The `CosineRelevancyPostResultProcessor` **must be included** in the `Search.post_result_processors` method, located in `swirl/models.py`.

For more details, refer to the **[Relevancy Ranking Guide](./User-Guide#relevancy-ranking)**.

## Additional ResultProcessors

SWIRL provides other **ResultProcessors** that may be useful in specific cases. See the **[Developer Guide](./Developer-Guide#results)** for more details.

# Authentication & Credentials

The `credentials` property stores authentication information required by a SearchProvider.  

## Supported Authentication Formats

*Key-Value Format (Appended to URL)*

Used when an API key is passed as a query parameter.

**Example: Google PSE SearchProvider**

```json
"credentials": "key=your-google-api-key-here",
"query_template": "{url}?cx={cx}&key={key}&q={query_string}",
```

*Bearer Token (Sent in HTTP Header)*

Supported by the `RequestsGet` and `RequestsPost` connectors.

**Example: [Miro SearchProvider](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/miro.json)**

```json
"credentials": "bearer=your-miro-api-token",
```

*X-Api-Key Format (Sent in HTTP Header)*

```json
"credentials": "X-Api-Key=<your-api-key>",
```

*HTTP Basic/Digest/Proxy Authentication*

Supported by `RequestsGet`, `ElasticSearch`, and `OpenSearch` connectors.

**Example: [Solr with Auth SearchProvider](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/solr_with_auth.json)**

```json
"credentials": "HTTPBasicAuth('solr-username','solr-password')",
```

*Other Authentication Methods*

For advanced authentication techniques, consult the **[Developer Guide](./Developer-Guide#develop-new-connectors)**.

# Response Mappings

SearchProvider `response_mappings` determine how each source's response is **normalized into JSON**.  
They are processed by the **Connector's `normalize_response` method**.

## Example: Google PSE Response Mappings

```json
"response_mappings": "FOUND=searchInformation.totalResults,RETRIEVED=queries.request[0].count,RESULTS=items",
```

## Response Mapping Options

| Mapping | JSONPath Source | Required? | Example |
|---------|---------------|-----------|---------|
| **FOUND** | Total number of results available for the query (default: same as `RETRIEVED` if not specified) | No | `searchInformation.totalResults=FOUND` |
| **RETRIEVED** | Number of results **returned** for this query (default: length of `RESULTS` list) | No | `queries.request[0].count=RETRIEVED` |
| **RESULTS** | Path to the list of **result items** | Yes | `items=RESULTS` |
| **RESULT** | Path to the document (if result items are stored within a dictionary/wrapper) | No | `document=RESULT` |

Proper response mappings ensure **consistent search results** across different sources.

# Result Mappings

SearchProvider `result_mappings` define how JSON result sets from external sources are mapped to SWIRL's **standard result schema**. Each mapping follows **JSONPath** conventions.

# Configuration Options

Use the following configuration options to override default SP behavior. 

They must be placed in the "config" block.

## Retrieval Augmented Generation (RAG)

The following configuration items change the RAG defaults for a single SearchProvider:

```
"swirl": { 
    "rag": {
        "swirl_rag_max_to_consider": <integer-max-to-consider>,
        "swirl_rag_fetch_timeout": <integer-rag-fetch-timeout>,
        "swirl_rag_score_inclusion_threshold": <float-rag-score-inclusion-threshold>,
        "swirl_rag_distribution_strategy": <rag-distribution-strategy>,
        "swirl_rag_inclusion_field": "<swirl_confidence_score|swirl_score>"
     }
}
```

The following are valid RAG distribution strategies that can be selected by `swirl_rag_distribution_strategy`:
* `distributed`
* `roundrobin`
* `sorted`
* `roundrobinthreshold`

For example:

```
"swirl": {
    "rag": {
        "swirl_rag_inclusion_field": "swirl_score",
        "swirl_rag_distribution_strategy": "sorted",
        "swirl_rag_score_inclusion_threshold": 2500,
        "swirl_rag_max_to_consider": 4,
        "swirl_rag_fetch_timeout": 1
    }
},
```

## Page Fetching

The following configuration items allow modification of the page fetching defaults for a single SearchProvider:

```
"config": {
        "swirl": {
            "fetch_url_body": {
               "body_pagefetch_min_tokens": <min-tokens>,
               "body_pagefetch_token_length":  <token-length>,
               "body_pagefetch_fallback_token_length": <fallback-token-length>,
               "body_pagefetch_generation_method":"<generation-method>",
               "body_pagefetch_text_extract_timeout": <text-extraction-timeout>
             }
        }
    }
```

The following are valid generation methods that may be selected using `body_pagefetch_generation_method`:
* TERM_COUNT
* TERM_VECTOR

For example:

```
"config": {
        "swirl": {
            "fetch_url_body": {
               "body_pagefetch_min_tokens": 5,
               "body_pagefetch_token_length":64,
               "body_pagefetch_fallback_token_length":128,
               "body_pagefetch_generation_method":"TERM_COUNT",
               "body_pagefetch_text_extract_timeout":30
             }
        }
    }
```

## Google Calendar

The following configuration items allow modification of the Google Calendar defaults:

```
"config": {
        "swirl": {
            "google_calendar": {
               "calendar_lookback_days": <lookback-days>,
               "calendar_lookahead_days": <lookahead-days>
            }
        }
    }
```

In both cases, specify the number of days. For example:

```
"config": {
        "swirl": {
            "google_calendar": {
               "calendar_lookback_days": 30,
               "calendar_lookahead_days": 30
            }
        }
    }
```

## Retrieving More Results for a Single Provider Search

{: .warning }
This feature is only supported in SWIRL Enterprise.

To retrieve more results when the user (or the Search Assistant) selects a single SearchProvider for a search, add the following to the `config` block:

```
"config":{
  "swirl": {
    "connector_use": {
      "single_provider_results_requested": 50
    }
  }
}
```

SWIRL will retrieve the number of results specified by `single_provider_results_requested`, instead of `results_per_query`.

To disable this behavior, remove the configuration item.

In addition you can pass `single_provider_results_requested=<int>` to a `GET /api/swirl/search` REST request. If  there is also exactly one Search Provider ID in the Search Provider list the number of results passed in will be fetched. If the value is also set in the configuration of that Search Provider, the passed in value is used.


# Default SWIRL Fields

| Field Name | Description |
|------------|------------|
| **author** | Author of the item (not always reliable for web content). |
| **body** | Main content extracted from the result. |
| **date_published** | Original publication date (not always reliable for web content). |
| **date_retrieved** | Date and time SWIRL retrieved the result. |
| **title** | Title of the item. |
| **url** | URL of the result item. |

# Example: Google PSE Result Mapping

```json
"result_mappings": "url=link,body=snippet,author=displayLink,cacheId,pagemap.metatags[*].['og:type'],pagemap.metatags[*].['og:site_name'],pagemap.metatags[*].['og:description'],NO_PAYLOAD"
```

Here, `url=link` and `body=snippet` map **Google PSE result fields** to **SWIRL result fields**.

## XML to JSON Conversion

{: .highlight }
The [`requests.py`](https://github.com/swirlai/swirl-search/blob/main/swirl/connectors/requests.py) connector **automatically converts XML to JSON** for mapping.

{: .highlight }
It also handles **list-of-list responses**, where the first list element contains **field names**.

Example:

```json
[
    ["urlkey", "timestamp", "original", "mimetype", "statuscode"],
    ["today,swirl)/", "20221012214440", "http://swirl.today/", "text/html"]
]
```

This format is **automatically converted** into a structured JSON array.

# Constructing URLs from Mappings

If a SearchProvider **does not return full URLs**, JSONPath syntax can construct them dynamically.

**Example: Europe PubMed Central**

```json
"url='https://europepmc.org/article/{source}/{id}'"
```

Here, `{source}` and `{id}` are **values from the JSON result**, inserted into the URL dynamically.

# Aggregating Field Values

To aggregate **list values into a single string**, use JSONPath syntax.

**Example: Google PSE Metadata Aggregation**

```json
"pagemap.metatags[*].['og:type']"
```

This merges all `og:type` values from the metadata into a single result field.

**Example: ArXiv Author Aggregation**

```json
"author[*].name"
```

This collects all author names into a single field.

# Multiple Mappings

SWIRL allows **multiple source fields** to map to a **single SWIRL field**.

```json
"result_mappings": "body=content|description,..."
```

- If **one field is populated**, it maps to `body`.
- If **both fields contain data**, the second field is moved to **PAYLOAD** as `<swirl-field>_<source_field>`.

**Example Result Object:**

```json
{
    "swirl_rank": 1,
    "title": "What The Mid-Term Elections Mean For U.S. Energy",
    "url": "https://www.forbes.com/sites/davidblackmon/2022/11/13/what-the-mid-term-elections-mean-for-us-energy/",
    "body": "Leaders in U.S. domestic energy sectors should expect President Joe Biden to feel emboldened...",
    "payload": {
        "body_description": "Leaders in U.S. domestic energy sectors should expect President Joe Biden to feel emboldened..."
    }
}
```

# Result Mapping Options

| Mapping Format | Description | Example |
|---------------|-------------|---------|
| **swirl_key = source_key** | Maps a field from the source provider to SWIRL. | `"body=_source.email"` |
| **swirl_key = source_key1\|source_key2** | Maps multiple fields; the first populated field is mapped, others go to PAYLOAD. | `"body=content|description"` |
| **swirl_key='template {variable}'** | Formats multiple values into a **single string**. | `"'{x}: {y}'=title"` |
| **source_key** | Maps a field from the raw source result into PAYLOAD. | `"cacheId, _source.products"` |
| **sw_urlencode** | URL-encodes the specified value. | `"url=sw_urlencode(<hitId>)"` |
| **sw_btcconvert** | Converts **Satoshi to Bitcoin**. | `"sw_btcconvert(<fee>)"` |
| **NO_PAYLOAD** | Disables automatic copying of **all** source fields to PAYLOAD. | `"NO_PAYLOAD"` |
| **FILE_SYSTEM** | Treats the SearchProvider as a **file system**, increasing `body` weight in ranking. | `"FILE_SYSTEM"` |
| **LC_URL** | Converts `url` to lowercase. | `"LC_URL"` |
| **BLOCK** | Used in SWIRL's **RAG processing**; stores output in the **info block** of the result object. | `"BLOCK=ai_summary"` |
| **DATASET** | Formats **columnar responses** into a single result. | `"DATASET"` |

## Controlling `date_published` Display

As of **SWIRL 2.1**, different values can be mapped to `date_published` and `date_published_display`.

```json
"result_mappings": "... date_published=foo.bar.date1,date_published_display=foo.bar.date2 ..."
```

This results in:

```json
"date_published": "2010-01-01 00:00:00",
"date_published_display": "c2010"
```

# Result Schema

The **JSON result schema** is defined in:

- [`swirl/processors/utils.py`](https://github.com/swirlai/swirl-search/tree/main/swirl/processors/utils.py)
- [`swirl/models.py`](https://github.com/swirlai/swirl-search/tree/main/swirl/models.py)

[Result Mixers](./Developer-Reference#mixers-1) further process and merge data from multiple sources.

# PAYLOAD Field

The **PAYLOAD field** stores **all unmapped result data** from the source.

## Using `NO_PAYLOAD` Effectively

To **exclude unnecessary fields** from PAYLOAD:

1. Run a **test query** **without `NO_PAYLOAD`** to inspect raw fields.
2. Add specific mappings for the fields you need.
3. Enable `"NO_PAYLOAD"` to discard **unmapped data**.

{: .highlight }
SWIRL copies all source data to PAYLOAD **by default** unless `NO_PAYLOAD` is specified.
