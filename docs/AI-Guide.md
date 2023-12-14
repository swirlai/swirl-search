---
layout: default
title: AI Guide
nav_order: 8
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# AI Retrieval Augmented Generation (RAG) Guide

Swirl supports Real Time [Retrieval Augmented Generation (RAG)](index.md#what-is-retrieval-augmented-generation-rag-does-swirl-support-it) out of the box, using existing search engines, databases and enterprise services. 

## Intended Audience

This guide details how to configure and tune Swirl (v. 3.0 or newer) to perform RAG. It is intended for use by developers and/or system administrators with the ability to configure the system to connect to services like OpenAI's ChatGPT.

# Setting up RAG

1. Install Swirl 3.0 as noted in the [Quick Start Guide](Quick-Start.md#local-installation), including the latest version of the Galaxy UI.

2. Add an OpenAI API key to the `.env` file:
```
OPENAI_API_KEY=your-key-here
```
*Check out [OpenAI's YouTube video](https://youtu.be/nafDyRsVnXU?si=YpvyaRvhX65vtBrb) if you don't have an OpenAI API Key.*

3. When installing for PRODUCTION use, change the following line in `static/api/config/default` from:
```
"webSocketConfig": {
    "url": "ws://localhost:8000/chatgpt-data"
  }
``` 
...to...
```
"webSocketConfig": {
    "url": "wss://localhost:8000/chatgpt-data"
  }
```
*This default `ws:` can be used locally but should NEVER be done in production since it is not secure!*

4. Add the following configuration to the `page_fetch_config_json` parameter of each SearchProvider you wish to have participate in RAG:
```
"page_fetch_config_json": {
        "cache": "false",
        "headers": {
            "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
        },
        "timeout": 10
}, 
```
Adjust the `timeout` value if necessary. Change the `User-Agent` string as needed, and/or authorize it to fetch pages from internal applications.  As of Swirl 3.1.0, page fetch configurations are present for the [European PMC](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/europe_pmc.json) SearchProvider and four of the [Google PSE](https://github.com/swirlai/swirl-search/blob/main/SearchProviders/google_pse.json) SearchProviders.

5. Restart Swirl: 
```
python swirl.py restart
```

6. Go to the Galaxy UI ([http://localhost:8000/galaxy/](http://localhost:8000/galaxy/)). The "Generate AI Response" switch should be "off" as shown:
![Galaxy with RAG Generate AI Response switch off](images/swirl_rag_switch_off.png)

7. Run a search. Results appear quickly after you press the "Search" button ([http://localhost:8000/galaxy/?q=epmc:future+of+ai+care](http://localhost:8000/galaxy/?q=epmc:future+of+ai+care)):
![Galaxy with RAG results ready for selection](images/swirl_rag_pulmonary_1.png)

8. If you wish to manually select the results to RAG with, click the "Select Items" switch to make the shopping cart appear. Results that Swirl thinks should be used in RAG will be pre-checked. Check or uncheck results, and optionally sort and/or filter them.
![Galaxy with RAG results selected](images/swirl_rag_pulmonary_2.png)

9. Click the "Generate AI Response" switch. A spinner will appear. The RAG response will appear in 5-15 seconds :slightly_smiling_face: depending on a variety of factors.
![Galaxy with human directed RAG AI insight](images/swirl_rag_pulmonary_3.png)

10. Verify the RAG insight you received by reviewing the citations at the end RAG response. 

{: .highlight }
To cancel a RAG process, click the "Generate AI Summary" toggle off.

{: .warning }
Swirl's RAG processing utilizes only the *first 10 results* that are selected either automatically or manually using the "Select Items" option.

## Notes

* As of Swirl 3.1.0, RAG processing is now available through a single API call, e.g. `?qs=metasearch&rag=true`.  See the [Developer Guide](https://docs.swirl.today/Developer-Guide.html#get-synchronous-results-with-the-qs-url-parameter) for more details about the `?qs=` parameter.

* As of Swirl 3.1.0, configurations for a default timeout value (30 seconds) and the text to display when the timeout is exceeded were added to RAG processing.  These options are available in the `static/api/config/default` file.
```
"webSocketConfig": {
    "url": "ws://localhost:8000/chatgpt-data",
    "timeout": 30000,
    "timeoutText": "Timeout: No response from Generative AI."
  }
```

* RAG processing with public web data can be problematic due to difficulties extracting article content; for those seeking a solution for public data please [contact Swirl](mailto:hello@swirl.today).

* The community edition of Swirl is intended to RAG with sources you can fetch without authenticating. If you need to perform RAG with content from enterprise services like Microsoft 365, ServiceNow, Salesforce, Atlassian with OAUTH2 and SSO, please [contact us for information about Swirl Enterprise](mailto:hello@swirl.today) - which supports all of that, and more, out of the box.
