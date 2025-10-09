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

---

# What is SWIRL AI Search?

SWIRL AI Search is a hybrid [metasearch engine](https://en.wikipedia.org/wiki/Metasearch_engine) that seamlessly connects almost any Generative AI or LLM to enterprise data platforms, applications, and information services—without copying, ingesting, or indexing *any* data.

SWIRL runs in your own environment—anywhere Docker or Kubernetes is supported. Setup takes just minutes through a simple configuration process. Users can instantly generate personalized, secure AI-driven insights from the data they’re already authorized to access—without requiring developers, lengthy legal agreements, or complex data transfer/ETL projects.

![SWIRL RAG AI Insight with results](images/swirl_40_community_rag.png)

# What is SWIRL AI Search Assistant? 

SWIRL AI Search Assistant is supportive chat bot that converses with users to identify the best data sources for their inquiry, and the exact query to run. It provides in-line insights, using RAG on the most relevant search results, whenever relevant to the conversation.

As of SWIRL Enterprise 4.0, the AI Search Assistant can generate queries in SQL, SPARQL, and other query languages known by the underlying LLM/model.

![SWIRL RAG AI Insight with results](images/swirl_40_enterprise_assistant_rag.png)

# How Does SWIRL Provide Insights Without Copying, Ingesting, or Indexing Data?

SWIRL AI Search asynchronously sends user queries to authorized APIs and other configured endpoints. Response time depends on the slowest source.

SWIRL then re-ranks results from all responding sources, so users don’t have to, using embeddings from the configured LLM.

The re-ranking process follows these steps:

* Vectorize the user's query (or relevant parts of it).
* Send the text of the user's query and/or the vector to each requested (or default) source.
* Asynchronously gather results from each source.
* Normalize results using **JSONPath** (or **XPath**).
* Vectorize each result snippet (or relevant parts of it).
* Re-rank results based on similarity, frequency, and position, while adjusting for factors like length variation, freshness, and more.

The [Xethub study](https://xethub.com/blog/you-dont-need-a-vector-database), as [explained by Simson Garfinkel](https://www.linkedin.com/pulse/vector-databases-rag-simson-garfinkel-hzule/), demonstrated that re-ranking "naive" keyword search engines outperforms re-indexing data into a vector database for tasks like question answering.

SWIRL AI Search also includes state-of-the-art cross-silo [Retrieval-Augmented Generation (RAG)](https://en.wikipedia.org/wiki/Retrieval-augmented_generation) to generate AI-powered insights such as summarization, question answering, and visualizations of relevant result sets.

![SWIRL AI Search Insight Pipeline](images/swirl_rag_pipeline.png)

When a user requests an AI-generated insight, SWIRL:

* Sends the request to relevant sources.
* Normalizes and unifies the retrieved results.
* Re-ranks the unified results using a **non-generative Reader LLM**.
* Optionally presents them to the user, allowing adjustments to the result set.
* Fetches the full text of results in real time.
* Identifies the most relevant portions of the documents and binds them into a prompt using real-time vector analysis similar to the re-ranking process above.
* Sends the refined prompt to the approved generative AI for insight generation.
* Returns a single set of AI-generated insights with citations.

SWIRL AI Search includes the **Galaxy UI** and fully documented **Swagger APIs**, making it easy to integrate with nearly any front-end or system.

SWIRL AI Search, **Enterprise Edition**, supports flexible, generic **OAuth2** and **SSO**, with auto-provisioning via **OpenID Connect**.

# How Does SWIRL AI Search Assistant Work?

SWIRL AI Search Assistant ensures that the configured **Generative AI (GAI) or LLM** only accesses data the user is authorized to see, leveraging its integration with **SWIRL AI Search**.

SWIRL manages chat context and history, triggering **Retrieval-Augmented Generation (RAG)** through AI Search based on user requests and conversation flow. Users can only receive insights from data they are already authorized to access. Additionally, Assistant retains context only within each user's active session—ensuring conversations remain private and contextualized per user. All access is managed through the existing **Single Sign-On (SSO)** system.

For more information, please refer to the [AI Search Assistant Guide](AI-Search-Assistant).

# What Systems Can SWIRL Integrate With?

SWIRL AI Search integrates with a wide range of systems, including **enterprise applications, cloud platforms, databases, search engines, and AI services**.  

For a full list of supported integrations, visit: [https://swirlaiconnect.com/connectors](https://swirlaiconnect.com/connectors).

# How Do I Connect SWIRL to a New Source?

To connect SWIRL AI Search with an internal data source, you need to **create a SearchProvider record**, which defines how SWIRL interacts with that source. Learn more in the [SearchProvider Guide](./SP-Guide#using-searchproviders).

To integrate SWIRL Enterprise with **Generative AI (GAI) or a Large Language Model (LLM)**, you need to **create an AIProvider record**, which configures SWIRL to communicate with the AI system. Detailed instructions can be found in the [AI Search Guide](AI-Search#connecting-to-generative-ai-gai-and-large-language-models-llms).

# What Is Included in SWIRL Enterprise Products?

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

SWIRL Enterprise pricing varies based on deployment type, features, and support level.  

For more information, visit: [https://swirlaiconnect.com/pricing](https://swirlaiconnect.com/pricing).

# When Should I Use SWIRL AI Search Community Edition?

Use **SWIRL AI Search Community Edition** if you need to search across one or more repositories and apply **Retrieval-Augmented Generation (RAG)** to full-text content—without requiring authentication, indexing the data into another repository, or writing additional code.

You may also freely redistribute solutions that incorporate **SWIRL AI Search Community Edition** under the [Apache 2.0 License](https://github.com/swirlai/swirl-search/blob/main/LICENSE).

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

Yes! For details about **SWIRL Cloud**, please [contact us](mailto:hello@swirlaiconnect.com).

{% if site.enableSwirlChat %}
## Ask SWIRL

Have questions about **SWIRL**? Just type below.

{% include swirl_chat.html chat_origin=site.swirlChatOrigin %}
{% endif %}
