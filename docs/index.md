---
layout: default
title: SWIRL Overview
nav_order: 1
permalink: "/"
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

<span class="big-text">SWIRL Overview</span><br/><span class="med-text">Community Edition | Enterprise Edition</span>

{: .highlight }
Please note: we've renamed our products! **SWIRL AI Connect** is now **SWIRL AI Search** 🔎 and **SWIRL AI Co-Pilot** is now **SWIRL AI Search Assistant** 🤖

---

# What is SWIRL AI Search?

SWIRL is a [federated AI search engine](https://en.wikipedia.org/wiki/Metasearch_engine) you run in your own environment via Docker or Kubernetes. It sits between your LLM/GenAI and your systems (M365, Google Workspace, Box, Salesforce, Confluence/Jira, databases, file shares, etc.) 

SWIRL calls each source in real time using standard authentication mechanisms like OAuth2/app registrations, API keys and service identities. It does not copy or re-index content; data stays in place. Permissions are enforced by the source systems, and no user ever sees anything they weren't already authorized to see. 

SWIRL finally re-ranks the results using real-time, non-generative AI, to find the best result across all sources.

![SWIRL RAG AI Insight with results](images/swirl_40_community_rag.png)

# What is SWIRL AI Search Assistant? 

The SWIRL AI Search Assistant is a conversational front end to SWIRL. It helps the user clarify intent, discuss and select sources, run queries and summarize the most relevant results found. It also provides deeplinked citations and optional follow-up questions. 

No additional data store is required or created. The assistant integrates with any LLM that supports user/assistant roles, tool-calling and JSON schema support.

![SWIRL RAG AI Insight with results](images/swirl_40_enterprise_assistant_rag.png)

# What is the SWIRL AI Warehouse?

The SWIRL AI Warehouse aggregates multiple databases — Oracle, IBM DB2, PostgreSQL, MySQL, Microsoft SQL Server and many more - into a single, real-time analytics layer. With AI Warehouse you can query multiple databases as if they were one using SQL over JDBC. With AI Warehouse, you can swiftly create unified dashboards and report across sources using most Business Intelligence (BI) and reporting tools. 

Users may also ask the Search Assistant questions in natural language, and it can resolve them with SQL queries that span databases - the ultimate way to provide self-service access to a virtual data warehouse.

For more information on the SWIRL AI Warehouse [contact us](mailto:hello@swirlaiconnect.com).

# How Does SWIRL AI Search Provide Insights Without Copying, Ingesting, or Indexing Data?

SWIRL sends each user query to authorized APIs and other configured endpoints, asynchronously, in parallel. After responses arrive, SWIRL re-ranks to find those most relevant to the user's query. Each result is assigned a confidence score, the predicted relevance to the query. 

Re-ranking involves the following:
* Embed the user’s query
* Normalize each source’s response to a common schema
* Embed each result snippet 
* Score and sort by vector similarity, signal frequency, and position
* Adjust for length variation, freshness, items ranked #1 by the reporting source, and related factors

The [Xethub study](https://xethub.com/blog/you-dont-need-a-vector-database) demonstrated that re-ranking "naive" keyword search engines outperforms re-indexing data into a vector database for tasks like question answering.

SWIRL can also run cross-system (Retrieval Augmented Generation (RAG)](TBD) to summarize the most relevant results, or answer questions from them.

![SWIRL AI Search Insight Pipeline](images/swirl_rag_pipeline.png)

When a user requests an AI insight, SWIRL:
* Fetches the full text of the most relevant items 
* Reads the full textm chunks it, and annotates the most relevant portions
* Builds a grounded prompt using the relevant chunks
* Sends the prompt to the approved generative model
* Returns an answer with citations deep linking back to the source items

SWIRL ships with the Galaxy UI and a documented REST API (OpenAPI/Swagger) for integration. SWIRL Enterprise features flexible OAuth2/SSO with OpenID Connect–based auto-provisioning.

# How Does SWIRL AI Search Assistant Work?

The AI Search Assistant enables capable LLMs to help users with source selection by exposing metadata and other information as configured by IT. When a clear objective with sources and queries has been agreed on, the LLM then uses tool calling to execute AI Search queries on the user's behalf. It can also retrieve documents to answer questions and summarize data, if configured. All access is managed through the existing AI Search integration with Single Sign-On (SSO). 

The Assistant stores chats and conversations in SWIRL, and uses the configured LLM to execute RAG with the most relevant/confident documents. It can also write and execute queries in SQL, SPARQL, MongoDB, Elastic, OpenSearch and other supported dialects.

For more information, please refer to the [AI Search Assistant Guide](AI-Search-Assistant).

# What Systems Can SWIRL Integrate With?

SWIRL AI Search integrates with a wide range of systems, including **enterprise applications, cloud platforms, databases, search engines, and AI services**.  

For a full list of supported integrations, visit: [https://swirlaiconnect.com/connectors](https://swirlaiconnect.com/connectors).

# How Do I Connect SWIRL to a New Source?

To connect SWIRL AI Search with an internal data source, you need to **create a SearchProvider record**, which defines how SWIRL interacts with that source. Learn more in the [SearchProvider Guide](./SP-Guide#using-searchproviders).

To integrate SWIRL Enterprise with **Generative AI (GAI) or a Large Language Model (LLM)**, you need to **create an AIProvider record**, which configures SWIRL to communicate with the AI system. Detailed instructions can be found in the [AI Search Guide](AI-Search#connecting-to-generative-ai-gai-and-large-language-models-llms).

# What Is Included in SWIRL Enterprise?

SWIRL **Enterprise Edition** includes:

* **SWIRL AI Search Assistant**, providing an interactive AI-powered search assistant.

* **Support for multiple AI providers** (e.g., Anthropic, Cohere), with configurable roles for **Generative AI (GAI) or Large Language Models (LLMs)**, including:
  - Chat
  - Query rewriting
  - Direct answer retrieval
  - Retrieval-Augmented Generation (RAG)
  - Embeddings for re-ranking 

* **Single Sign-On (SSO) support** with various Identity Providers (IDPs), such as **Ping Federate**, plus auto-provisioning via **OpenID Connect**.  
  *(The Community version only supports M365.)*

* **AI-powered insights from 1,500+ file formats**, including:
  - Structured data including tables and charts
  - Text in images

* **Authentication support for PageFetcher**, enabling secure retrieval of protected content.

* **Configurable prompts**

# How Much Do SWIRL Enterprise Products Cost?

SWIRL Enterprise pricing is here: [https://swirlaiconnect.com/pricing](https://swirlaiconnect.com/pricing). 

# When Should I Use SWIRL AI Search Community Edition?

Use **SWIRL AI Search Community Edition** if you need to search across one or more repositories and apply **Retrieval-Augmented Generation (RAG)** to full-text content—without requiring authentication, indexing the data into another repository, or writing additional code.

# When Should I Use SWIRL Enterprise Edition?  

Use **SWIRL Enterprise Edition** when you have:  

* **Repositories that require authentication** via **Single Sign-On (SSO) or OAuth2**.  
* **A need to extract text** from documents and fetch authenticated pages securely.  
* **A need to apply Retrieval-Augmented Generation (RAG)** to long documents, complex tables, or text extracted from images.  
* **A need to use Generative AI (GAI) or LLMs** beyond OpenAI and Azure OpenAI.  
* **A desire to interact conversationally** with your data using **SWIRL AI Search Assistant**.  

# How Can I Obtain SWIRL Enterprise Edition? 

* Use the [Azure Marketplace Offer](https://azuremarketplace.microsoft.com/en-us/marketplace/apps/swirlcorporation1684335149355.swirl_vm_offer_poc?tab=Overview) to spin-up a Virtual Machine in minutes!
* [Contact SWIRL](mailto:hello@swirlaiconnect.com) for a license key, or delivery on any other platform.

# How Can I Get Help With SWIRL?

* **Visit the Documentation Site**: [docs.swirlaiconnect.com](https://docs.swirlaiconnect.com/)
* **Enterprise**: [Create a Ticket](https://swirlaiconnect.com/support-ticket)
* **Email**: [support@swirlaiconnect.com](mailto:swirlaiconnect.com)

# What Is the SWIRL Architecture and Technology Stack?  

SWIRL products are built on a **Python/Django/Celery/Redis** stack:  

* **Python & Django** – Core framework for application logic and API services.  
* **Celery & Redis** – Handles asynchronous processing and task management.  
* **PostgreSQL (recommended for production)** – Ensures scalability and reliability.  

For a deeper dive into SWIRL’s architecture, check out the [Developer Guide](./Developer-Guide#architecture).

# How Is SWIRL Usually Deployed?  

SWIRL is typically deployed using **Docker**, with **Docker Compose** for easy setup.  

For **SWIRL Enterprise**, deployments are also available as **Kubernetes images**, allowing for scalable, containerized orchestration.  

# Does SWIRL Offer Hosting?  

Yes! For details please [contact us](mailto:hello@swirlaiconnect.com).

{% if site.enableSwirlChat %}
## Ask SWIRL

Have questions about **SWIRL**? Just type below.

{% include swirl_chat.html chat_origin=site.swirlChatOrigin %}
{% endif %}
