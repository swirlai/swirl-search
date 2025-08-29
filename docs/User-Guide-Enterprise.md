---
layout: default
title: User Guide
nav_order: 9
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

# Accessing the SWIRL AI Search Assistant

* Open this URL in a browser: <http://localhost:8000/galaxy/chat/>  

  ![SWIRL AI Search Assistant](images/swirl_40_assistant_start.png)

* Alternatively, click the **user profile icon** (top-right) on the [SWIRL Search page](http://localhost:8000/galaxy/search/), then click **"SWIRL AI Search Assistant"**.

  ![SWIRL AI Search link to SWIRL AI Search Assistant](images/swirl_40_assistant_link.png)

## Logging In

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

## Verifying Connectivity 

Click the **profile icon** (top-right) to verify your connection to individual sources, which may vary depending on your SSO configuration. 

Use the **toggle switches** to connect or disconnect from any source, as needed.

  ![SWIRL Assistant with user logged in to Microsoft, not to Box](images/swirl_40_chat_profile.png)

## Starting a Conversation

Use the **input box** to send a message to the Assistant. It will assist you in finding the information you need. When you and the Assistant agree, it will perform a **search** against one or more sources and either **summarize** the results or **answer your question**.

  ![SWIRL Assistant discussion](images/swirl_40_chat_1.png)

## Follow-up Questions

The Assistant will often suggest **follow-up questions**. Click one to view the answer!

  ![SWIRL Assistant follow-up question and response](images/swirl_40_chat_2.png)

## Generating Complex Queries

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

## Human Language Support

SWIRL Assistant can **converse and query** in any language supported by the underlying model. For example, OpenAI's latest models can converse in **100+ languages**:

  ![Querying SWIRL Assistant in Japanese](images/swirl_40_chat_query_in_japanese.png)

  ![Asking Assistant to translate an English response to Japanese](images/swirl_40_chat_translate_response_to_japanese.png)

## Other Model Capabilities

SWIRL Assistant does not limit **LLM capabilities**. You can:

- **Summarize** a Assistant chat in various formats (e.g., bullet points, narrative, iambic pentameter), as long as it is within the same chat session.
- **Translate** Assistant responses into other languages.
- **Reformat, revise, or retry** responses.
- **Use memory** to retain information across chat sessions (if supported by the model).

## Handling Errors

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

## Ending a Chat Conversation

To **end a conversation**, click the **SWIRL logo** at the top of the page. This starts a **new conversation**.

{: .highlight }
Assistant **will not remember** past chat sessions *unless* the model supports memory.

## Resuming and Managing Existing Chat Conversations

To **resume a conversation**, use the "Show/Hide History" link at the top of the Search Assistant page.

![SWIRL AI Search Assistant showing chat history](images/swirl_search_assistant_show_history.png)

Use the controls in the box to delete and rename individual chats. Click the `DELETE_ALL` link to clear your chat history completely.

# Using AI Search

To access the **Search Interface**, open the following URL:  
[http://localhost:8000/galaxy/chat/](http://localhost:8000/galaxy/chat/)

Alternatively, from the **Assistant page**, click the **profile button**, then click **"SWIRL AI Search"**:

  ![SWIRL AI Search](images/swirl_40_searchlink.png)

**Login and authentication remain the same.** If you are already logged into **Assistant**, you **will remain logged in** when using search.

  ![SWIRL AI Search with results and RAG](images/swirl_40_enterprise_search.png)

## Search Syntax  

The following table details SWIRL's search syntax:  

| Syntax | Handling | Notes |  
| ---------- | ---------- | ---------- |  
| **AND, OR** | Passed down to all SearchProviders | SWIRL does not modify or verify whether a provider supports these operators. |  
| **NOT, -term** | Passed down to configured SearchProviders and rewritten if necessary; removed for providers that do not support `NOT` or `-term` | SWIRL verifies compliance and **down-weights or flags responses** that contain terms excluded by `NOT`. |  
| **tag:term** | Passes `term` to SearchProviders configured with that **Tag** in their `tags` field. The untagged portion of the query is discarded. If a query starts with `tag:`, only providers with that Tag are searched. | **Example:** `electric vehicle company:tesla` → Only the term **`tesla`** is sent to SearchProviders with the `company` Tag.<br/> **Example:** `company:facebook` → The query **`facebook`** is only sent to SearchProviders with the `company` Tag. |  

### AND, OR

- **AND** and **OR** operators are **passed unchanged** to all SearchProviders.  
- SWIRL does **not** verify whether a provider supports these operators or correctly applies them.  

### NOT (`NOT` and `-` Syntax)  

- `NOT` remains in queries for SearchProviders that have **`NOT=True`** in their `query_mappings`.  
  - The `NOT` operator applies to **all terms that follow it** (if the provider supports it).  

- `NOT` is rewritten as `-term` for SearchProviders that have:  
  - **`NOT_CHAR=-`** and **`NOT=False`** (or `NOT` unspecified).  
  - The `-term` applies to all terms that follow it.  

- **For SearchProviders without `NOT=True`**, `NOT` and its associated terms are **removed from the query**.  

- SWIRL **scans responses** for compliance with `NOT` statements.  
  - If a response **contains excluded terms**, its **relevancy score is reduced**.  

### Plus/Minus (`+/-`) Syntax 

- **`+` (PLUS) before a term** ensures it **must** be included in results.  
  - It is **passed unchanged** to all SearchProviders.  

- **`-` (MINUS) before a term** functions as `NOT` **for providers that support it**.  
  - If a provider has **`NOT_CHAR=-`** configured in `query_mappings`, `-term` is passed unchanged.  
  - If a provider has **`NOT=True`** but **not** `NOT_CHAR=-`, `-term` is rewritten to `NOT term`.  

- **For providers without `NOT_CHAR=-`**, all `-term` exclusions are **removed** from the query.  

## Using Tags to Select SearchProviders  

**Tags** categorize **SearchProviders** by topic, entity type, or relevant concepts (e.g., `company`, `person`, `financial`).  
These tags can:  
- **Filter SearchProviders**—Only tagged providers are selected when a query starts with `tag:`.  
- **Direct query terms**—SWIRL rewrites portions of the query based on the provider's tags.  

For example, the **funding dataset** included with SWIRL has SearchProviders for **SQLite3, PostgreSQL, and Google BigQuery**, each containing relevant **Tags**:  

```json
{
    "name": "Company Funding Records (cloud/BigQuery)",
    "connector": "BigQuery",
    ...
    "tags": [
        "Company",
        "BigQuery"
    ]
}
```

### How Tags Work in Queries  

#### 1. Filtering by Tag Only 
If a query **begins with `tag:`**, only **SearchProviders with that Tag** are selected—regardless of their `default` status.  

```shell
company:facebook
```
- This limits the query to **SearchProviders with the `company` Tag**.  
- Unrelated providers **are excluded**, even if they are `default=true`.  

#### 2. Combining a Tag with a General Query
A **default search** can be combined with a **tagged search** for specific terms.  

```shell
electric vehicle company:tesla
```
- **Default SearchProviders** receive the full query: `"electric vehicle tesla"`.  
- **SearchProviders with the `company` Tag** receive only `"tesla"`.  

For example, the **BigQuery SearchProvider** will receive:  

```shell
tesla
```

This makes **direct hits** on funding records more likely to **rank higher** in the results.

## Hit Highlighting  

SWIRL **highlights query term matches** in the following fields:  
- **`title`**  
- **`body`**  
- **`author`**  

For example:  

```json
"body": "<em>Performance</em> <em>management</em> is the process of setting goals and expectations for employees and then tracking and measuring their progress. This can be done through regular one-on-one meetings, <em>performance</em> reviews, and other feedback mechanisms."
```

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

## Alternate Sort Orders

By default, **SWIRL sorts results by Confidence Score**. To change this:  

- Click the **`View By`** dropdown.  
- Select:  
  - **`Relevancy`** - Sorts results by a raw relevancy score. This value is not comparable between queries, and is deprecated as of SWIRL 4.
  - **`Date`** – Sorts results chronologically. Results without a `date_published` value are hidden.  
  - **`Top Picks`** – Highlights the most relevant results from each source.  

To see all results again, switch back to **`Confidence`** sorting.  

## Filtering Results by Source  

**SWIRL returns the best results from all available sources** by default. 

To filter results, check the desired `Source` boxes as shown above. The displayed results will update instantly. 

Click `Clear All` to reset the filter and view all results.  

## Guiding Retrieval Augmented Generation (RAG) for AI Insight Generation

SWIRL Enterprise 4.2 includes a new field on the search form: `Optional instructions for the AI response`. This field allows you to provide instructions to the LLM that will summarize the retrieved results - without having it be part of the selection criteria. The search box with the hint "What are you searching for today" determines which results are retrieved. 

For example, this query selects the top documents about Karen Sparck Jones, and instructs the configured LLM to report on major inventions.

![SWIRL RAG results for Karen Sparck Jones inventions](images/ksj_rag_example.png)

The RAG result includes [details of her invention of TF/IDF](https://en.wikipedia.org/wiki/Tf%E2%80%93idf) as expected.

### Using the Shopping Cart

To further guide RAG responses, use the shopping cart to manually select the results to send to the LLM for when generating AI insights.

![SWIRL AI Search result with select items enabled](images/4_1_0-SelectAll.png)

Use the `DESELECT ALL` / `SELECT ALL` link to check or uncheck all results, then adjust as desired.

### Customizing Prompts

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

## Starting a New Search  

Click the **SWIRL logo** to reset the search form and begin a new search.  








