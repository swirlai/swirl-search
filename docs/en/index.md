# Swirl Documentation
{:.no_toc}

**Contents**
* TOC
{:toc}

## What is Metasearch? Is it the same as Federated Search?

[Metasearch](https://en.wikipedia.org/wiki/Federated_search) is a technical approach in which a search engine (or "broker") accepts a query from some user (or system), distributes the query to other search engines, waits for the responses, then returns a normalized, unified and ideally relevancy-ranked set of results.

![Metasearch diagram](../images/swirl_arch_diagram.jpg)

The metasearch approach differs from traditional [enterprise search engines](https://en.wikipedia.org/wiki/Enterprise_search) that process [copies of all the source data](https://en.wikipedia.org/wiki/Extract,_transform,_load) and [index it](https://en.wikipedia.org/wiki/Search_engine_indexing), which can be costly and time-consuming. 

Metasearch leaves the source data in place and relies on each source's own search engine to get access. This makes federated search less suited for deep navigation - across a large e-commerce or data set catalog, for example - but ideal for delivering cross-silo results with a fraction of the effort. It is also excellent for information enrichment, entity analysis (such as competitive, customer, industry or market intelligence) and integrating unstructured data for content curation, data science and machine learning applications.

## What is Swirl Metasearch?

[Swirl Metasearch](https://github.com/swirlai/swirl-search) is a metasearch engine built on the Python/Django stack and released under the Apache 2.0 license in 2022.

 Swirl includes connectors to many popular systems including search engines, databases and other enterprise cloud services - anything with a query API.

![Swirl Sources](../images/swirl_source_no_m365-galaxy_dark.png)

Use Swirl's APIs to run searches and track their progress in real-time, then retrieve unified results re-ranked by Swirl's built-in cosine-vector similarity model based on [spaCy](https://spacy.io/), plus term and phrase boosts.

![Swirl Results](../images/swirl_results_no_m365-galaxy_dark.png)

Swirl provides a `swirl_score` and `swirl_rank` for each item, as well as the original source's ranking, so users can see instantly what was most relevant across all sources. 

``` shell
 "results": [
        {
            "swirl_rank": 1,
            "swirl_score": 1020.4933333333332,
            "searchprovider": "Enterprise Search Engines - Google PSE",
            "searchprovider_rank": 1,
            "title": "Swirl <em>Metasearch</em>: Home",
            "url": "https://swirl.today/",
            "body": "Swirl <em>Metasearch</em> connects data silos, returns AI-ranked results to a single experience and simplifies search deployments for applications.",
            "date_published": "unknown",
            "date_published_display": "",
            "date_retrieved": "2023-07-10 17:19:00.331417",
            "author": "swirl.today",
           ...
            },
```

Search developers can render Swirl's JSON results in any existing UI or framework without having to normalize the field names. Data scientists and engineers, search managers, analysts and implementers who have worked with Elastic or Solr will find it easy to add results from any source with a typical search API to their existing search infrastructure. 

# Documentation

| [Home](index.md) | [Quick Start](1.-Quick-Start.md) | [User Guide](2.-User-Guide.md) | [Admin Guide](3.-Admin-Guide.md) | [M365 Guide](4.-M365-Guide.md) | [Developer Guide](5.-Developer-Guide.md) | [Developer Reference](6.-Developer-Reference.md) |

# Support

* [Join the Swirl Metasearch Community on Slack!](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)

* Email: [support@swirl.today](mailto:support@swirl.today) with issues, requests, questions, etc. - we'd love to hear from you!

<br/>