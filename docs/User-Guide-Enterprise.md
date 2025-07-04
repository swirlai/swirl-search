---
layout: default
title: User Guide
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

<span class="big-text">User Guide</span><br/><span class="med-text">Enterprise Edition</span>

{: .warning }
Please [contact SWIRL](mailto:hello@swirlaiconnect.com) for access to SWIRL Enterprise.

{: .highlight }
Please note: we've renamed our products! **SWIRL AI Connect** is now **SWIRL AI Search** 🔎 and **SWIRL AI Co-Pilot** is now **SWIRL AI Search Assistant** 🤖

---

# Accessing AI Search Assistant

* Open this URL in a browser: <http://localhost:8000/galaxy/chat/>  

  ![SWIRL AI Search Assistant](images/swirl_40_assistant_start.png)

* Alternatively, click the **user profile icon** (top-right) on the [SWIRL Search page](http://localhost:8000/galaxy/search/), then click **"SWIRL AI Search Assistant"**.

  ![SWIRL AI Search link to SWIRL AI Search Assistant](images/swirl_40_assistant_link.png)

## SWIRL Login

**If the SWIRL login page appears:**  

  <img src="images/swirl_40_login.png" alt="SWIRL Login with SSO" width="300">

  - Enter **username:** `admin`  
  - Enter **password:** `password`  
  - Click **`Login`**  

{: .warning }
If you receive a warning about the password being compromised, follow these steps:  
[Change the super user password](./Admin-Guide#changing-the-super-user-password)

## SSO Login

**If your organization uses SSO:**  

The SWIRL login page will show a button for SSO login.  

  <img src="images/swirl_40_swirl_login.png" alt="SWIRL Login with SSO" width="300">

1. Click the **SSO login button**.  
2. You may need to authenticate:  

    <img src="images/swirl_40_ms_login.png" alt="SSO Provider Login Page" width="300">

3. Once logged in, you will be redirected to the AI Search Assistant:  

    ![SWIRL Assistant with user logged in via SSO](images/swirl_40_chat_start.png)

# Verifying Connectivity 

Click the **profile icon** (top-right) to verify your connection to individual sources, which may vary depending on your SSO configuration. 

Use the **toggle switches** to connect or disconnect from any source, as needed.

  ![SWIRL Assistant with user logged in to Microsoft, not to Box](images/swirl_40_chat_profile.png)

# Starting a Conversation

Use the **input box** to send a message to the Assistant. It will assist you in finding the information you need. When you and the Assistant agree, it will perform a **search** against one or more sources and either **summarize** the results or **answer your question**.

  ![SWIRL Assistant discussion](images/swirl_40_chat_1.png)

# Follow-up Questions

The Assistant will often suggest **follow-up questions**. Click one to view the answer!

  ![SWIRL Assistant follow-up question and response](images/swirl_40_chat_2.png)

# Generating Complex Queries

SWIRL Assistant can generate queries in **any query language** supported by the underlying model.  
For example, OpenAI's latest models can generate queries using most **SQL dialects**:

  ![SWIRL Assistant querying Google BigQuery using SQL](images/swirl_40_chat_SQL.png)

Other supported query languages include:

- **MongoDB MQL**
- **OpenSearch**
- **Elastic ESQL**
- **OpenSearch Query DSL**
- **Solr syntax**  
  
{: .highlight }
For assistance with specific query languages, please [contact SWIRL](mailto:support@swirlaiconnect.com).

# Human Language Support

SWIRL Assistant can **converse and query** in any language supported by the underlying model. For example, OpenAI's latest models can converse in **100+ languages**:

  ![Querying SWIRL Assistant in Japanese](images/swirl_40_chat_query_in_japanese.png)

  ![Asking Assistant to translate an English response to Japanese](images/swirl_40_chat_translate_response_to_japanese.png)

# Other Model Capabilities

SWIRL Assistant does not limit **LLM capabilities**. You can:

- **Summarize** a Assistant chat in various formats (e.g., bullet points, narrative, iambic pentameter), as long as it is within the same chat session.
- **Translate** Assistant responses into other languages.
- **Reformat, revise, or retry** responses.
- **Use memory** to retain information across chat sessions (if supported by the model).

# Handling Errors

Sometimes, Assistant **won't find results**. Don't be alarmed! Try the following:

- **Correct the query**
- **Remove specific terms**
- **Simplify the search**
- **Try a different source**
- **Run the search again**

  ![SWIRL Assistant correcting a spelling error](images/swirl_40_chat_try_different_query.png)

{: .warning }
When querying with **SQL** or other structured query languages, **some models may require occasional correction**:

  ![SWIRL Assistant having SQL corrected by user](images/swirl_40_chat_correct_query.png)

Please [contact support](#support) for assistance using the Assistant with any advanced query language.

# Ending a Conversation

To **end a conversation**, click the **SWIRL logo** at the top of the page. This starts a **new conversation**.

{: .highlight }
Assistant **will not remember** past chat sessions *unless* the model supports memory.

# Resuming an Old Conversation

To **resume a conversation**, construct the chat session URL using the `chat_id`:

[http://localhost:8000/galaxy/chat/?chat_id=1](http://localhost:8000/galaxy/chat/?chat_id=1)

{: .highlight }
**Future versions of SWIRL Galaxy** will include direct access to previous chats from the UI.

# Using AI Search

To access the **Search Interface**, open the following URL:  
[http://localhost:8000/galaxy/chat/](http://localhost:8000/galaxy/chat/)

Alternatively, from the **Assistant page**, click the **profile button**, then click **"SWIRL AI Search"**:

  ![SWIRL AI Search](images/swirl_40_searchlink.png)

**Login and authentication remain the same.** If you are already logged into **Assistant**, you **will remain logged in** when using search.

  ![SWIRL AI Search with results and RAG](images/swirl_40_enterprise_search.png)

## Confidence Scores

Starting in **SWIRL Enterprise 4.0**, SWIRL introduces a **confidence-based relevancy ranking model**. The **confidence score** ranges from **0 (not relevant) to 1.0 (extremely relevant)** and is **comparable across queries**.

### How Confidence Scores Work:

The score **factors in**:
  - **Number of matched query terms**
  - **Term importance**
  - **Contextual similarity between the query and the results**
  - **The source-reported rank**
  - **Other advanced ranking factors**

You can still **sort by relevancy** using the **`VIEW BY:`** dropdown. 

**AI Insights use only results** above a configurable minimum confidence score. 

## Customizing Prompts

**SWIRL AI Search (Enterprise Edition)** allows authorized users to **select a specific prompt** when generating AI Insights.

  ![SWIRL AI Search with results and RAG](images/swirl_40_search_prompts.png)

### Selecting a Prompt
- Use the **drop-down list** below the search box **before clicking** `Generate AI Insight`.

### Viewing or Editing Prompts
- Open: [http://localhost:8000/swirl/prompts/](http://localhost:8000/swirl/prompts/)  
- Or use the **[Admin UI prompts management](http://localhost:8000/admin/swirl/prompt/)**.

To modify prompts, use the **HTML form** or **Raw Data modes** at the bottom of the page.

  ![SWIRL AI Search prompts HTML form](images/swirl_40_prompt_endpoint.png)

{: .warning }
**SWIRL recommends not modifying system prompts.** If you need to reset them, follow the  
[Admin Guide section on resetting prompts](Admin-Guide#resetting-prompts).

## Guiding Retrieval Augmented Generation (RAG) for AI Insight Generation

SWIRL Enterprise 4.2 includes a new field on the search form: `Optional instructions for the AI response`. This field allows you to provide instructions to the LLM that will summarize the retrieved results - without having it be part of the selection criteria. The search box with the hint "What are you searching for today" determines which results are retrieved. 

For example, this query selects the top documents about Karen Sparck Jones, and instructs the configured LLM to report on major inventions.

![SWIRL RAG results for Karen Sparck Jones inventions](images/ksj_rag_example.png)

The RAG result includes [details of her invention of TF/IDF](https://en.wikipedia.org/wiki/Tf%E2%80%93idf) as expected.













