---
layout: default
title: Glossary
nav_order: 18
---
<details markdown="block">
  <summary>
    Glossary
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

<span class="big-text">Glossary</span><br/><span class="med-text">Community Edition | Enterprise Edition</span>

---

| **Term** | **Definition** |
|----------|----------------|
| [**AIProvider**](AI-Search#managing-ai-providers) | A configuration of a **Generative AI (GAI) or LLM**. It includes metadata identifying the model type, API key, and other settings. *(Enterprise Edition only)* |
| [**Authenticator**](AI-Search#connecting-to-other-authentication-systems) | A configuration of a Single Sign On (SSO) or Identity Provider (IDP) like Microsoft, Okta or Ping Federate *(Enterprise Edition only)* | 
| **Chat** | A SWIRL object that stores **message objects** exchanged within the AI Search Assistant. | 
| **Connector** | A SWIRL module that interacts with a **specific data source**, wrapping existing Python libraries (e.g., `requests.get`, `elasticsearch`). |
| [**Confidence**](User-Guide-Enterprise#confidence-scores) | A **prediction of relevancy** for a SWIRL search result, ranging from **0 to 1**. *(Enterprise Edition only)* |
| **Message** | A SWIRL object containing a **message** sent **to or from** a GAI/LLM. *(Enterprise Edition only)* |
| [**Mixer**](Developer-Reference#mixers-1) | Combines results from multiple **SearchProviders** into a **unified result set**, applying **relevancy ranking**. |
| **Page Fetcher** | A SWIRL module that **retrieves a copy** of a specific document for additional processing. The *Enterprise Edition* can authenticate when fetching |  
| **Processors** | Modules that process **search queries and results**, transforming them (e.g., **removing control characters, spell-checking, or normalizing formats**). |
| [**Prompt**](User-Guide-Enterprise#customizing-prompts) | A SWIRL object that configures a **GAI or LLM** for use in **AI-assisted search roles**, such as **Retrieval-Augmented Generation (RAG) or chat**. *(Enterprise Edition only)* |
| **Pipelines** | Execute **pre-defined sequences** of **Processors** to transform search input or result content dynamically. |
| **Query** | The **search terms** entered by a user. In search engines, the act of searching is distinct from the search terms themselves, which are called a **query**. |
| [**Search**](Developer-Guide#manage-search-objects) | A SWIRL object that **defines a search execution request**, containing a `query_string` (search text) and optional metadata. |
| [**SearchProvider**](SP-Guide) | A configuration of a **Connector**, defining a **searchable source** and including metadata such as authentication credentials and endpoint details. |
| [**Subscribe**](Developer-Guide#subscribe-to-a-search) | A key property of **Search** objects. When set to `true`, SWIRL periodically **re-runs the search**, sorting by date to retrieve newer data while removing duplicates. Currently, users must **poll for updates**, but future releases will support: <br> - **Callbacks** when new results are available. <br> - **Automatic AI Insights regeneration.** |
| **Result** | Represents a **retrieved search result** from a `SearchProvider` within a **federated search**. |
| [**Relevancy Ranking**](User-Guide#relevancy-ranking) | A scoring system that **determines the importance** of a search result compared to others. Learn more: [Relevance in Information Retrieval](https://en.wikipedia.org/wiki/Relevance_(information_retrieval)). |
