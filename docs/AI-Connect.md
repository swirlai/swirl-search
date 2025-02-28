---
layout: default
title: AI Connect Guide
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

# AI Connect Guide - Enterprise Edition

{: .warning }
**Note:** This document applies only to SWIRL AI Connect, Enterprise Edition.  
[Switch to the AI Connect, Community Edition guide](RAG-Guide.html).

## Configuring SWIRL AI Connect, Enterprise Edition

### Licensing

Add the license provided by SWIRL to the installation’s `.env` file in the following format:

```
SWIRL_LICENSE={"owner": "<owner-name>", "expiration": "<expiration-date>", "key": "<public-key>"}
```

If the license is invalid, a message will appear in `logs/django.log`. Please [contact support](mailto:support@swirlaiconnect.com) if this happens.

### Database

For Proof of Value (POV) testing, SWIRL AI Connect, Enterprise Edition can use SQLite3.  
Please [contact support](#support) for assistance with this configuration.

For production environments, SWIRL recommends **PostgreSQL**.

#### PostgreSQL Configuration

Modify the database settings in `swirl_server/settings.py`:

```
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': '<database-name>',
        'USER': '<database-username>',
        'PASSWORD': '<database-password>',
        'HOST': '<database-hostname>',
        'PORT': '<database-port>',
    }
}
```

For more details, refer to the [Admin Guide - Configuring Django](https://docs.swirl.today/Admin-Guide.html#configuring-django).

## OpenID Connect

To enable OpenID Connect for authentication and auto-provisioning, update the following variables in the instance’s `.env` file:

```
OIDC_RP_CLIENT_ID=''
OIDC_RP_CLIENT_SECRET=''
OIDC_OP_AUTHORIZATION_ENDPOINT=''
OIDC_OP_TOKEN_ENDPOINT=''
OIDC_OP_USER_ENDPOINT=''
OIDC_RP_SIGN_ALGO=''
OIDC_OP_JWKS_ENDPOINT=''
LOGIN_REDIRECT_URL=''
LOGOUT_REDIRECT_URL=''
OIDC_USERNAME_ALGO=''
OIDC_STORE_ACCESS_TOKEN=''
OIDC_STORE_ID_TOKEN=''
OIDC_AUTHENTICATION_CALLBACK_URL=''
```

## Connecting to Microsoft IDP

For Microsoft Identity Provider (IDP) authentication, set the following **OS environment variables** (do not place these in `.env`):

```
export MSAL_CB_PORT=8000
export MSAL_HOST=localhost
```

## Connecting to M365

To connect SWIRL to your **Microsoft 365 (M365) tenant**, follow the instructions in the [Microsoft 365 Guide](https://docs.swirl.today/M365-Guide.html).

## Connecting to Other Authentication Systems

To integrate SWIRL with an Identity Provider (IDP) or Single Sign-On (SSO) system, you need to configure an **Authenticator object**.

To manage authenticators, go to: [http://localhost:8000/swirl/aiproviders](http://localhost:8000/swirl/aiproviders) (default local installation).

### Authenticator Fields

| Field | Description |
| ----- | ----------- |
| `idp` | Name of the authenticator object (used as the URL) |
| `name` | Display name of the authenticator |
| `active` | Boolean; if `false`, the authenticator is disabled, and no authentication switch appears in the UI |
| `callback_path` | URL path where the IDP should redirect with user tokens |
| `client_id` | Client ID for authentication |
| `client_secret` | Shared secret for authentication |
| `app_uri` | Location of the SWIRL application |
| `auth_uri` | URL of the authentication system |
| `token_uri` | URL for retrieving authentication tokens |
| `user_data_url` | URL for retrieving user profile data |
| `user_data_params` | Parameters needed from the user profile |
| `user_data_headers` | Headers required for requesting tokens (e.g., `"Authorization"`) |
| `user_data_method` | HTTP method used to request user profile data |
| `initiate_auth_close_flow_params` | Parameters for CAS2 and other custom authentication flows |
| `exchange_code_params` | Parameters for exchanging authorization codes in custom flows |
| `is_code_challenge` | Boolean; determines if exchange code parameters are required (default: `True`) |
| `scopes` | List of authorization scopes |
| `should_expire` | Boolean; determines if tokens need refreshing (default: `True`) |
| `use_basic_auth` | Boolean; enables basic authentication instead of SSO |

## Microsoft 365 Authentication

SWIRL includes a preconfigured **Microsoft Authenticator**:

```
{
    "idp": "Microsoft",
    "name": "Microsoft",
    "active": false,
    "callback_path": "/swirl/callback/microsoft-callback",
    "client_id": "<your-client-id>",
    "client_secret": "<your-client-secret>",
    "app_uri": "http://localhost:8000",
    "auth_uri": "https://login.microsoftonline.com/common/oauth2/v2.0/authorize",
    "token_uri": "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    "user_data_url": "https://graph.microsoft.com/v1.0/me",
    "user_data_params": {
        "$select": "displayName,mail,userPrincipalName"
    },
    "user_data_headers": {
        "Authorization": "Bearer {access_token}"
    },
    "user_data_method": "GET",
    "initiate_auth_code_flow_params": {},
    "exchange_code_params": {},
    "is_code_challenge": true,
    "scopes": "User.Read Mail.Read Files.Read.All Calendars.Read Sites.Read.All Chat.Read offline_access",
    "should_expire": true,
    "use_basic_auth": true
}
```

### Activating the Microsoft Authenticator

To enable Microsoft authentication, register a **new SWIRL app** in **Azure**. Refer to the [M365 Guide](M365-Guide.html) for detailed setup instructions.

## Other Authenticators

For authentication with **Elastic, OpenSearch, CAS2, Salesforce, ServiceNow, Okta, Auth0, Ping Federate**, and other systems, please [contact support](#support).  

# Connecting to Generative AI (GAI) and Large Language Models (LLMs)

## Roles for Generative AI / Large Language Models

GAI/LLMs in SWIRL serve four distinct roles:

| Role | Description | Default Provider |
| ---- | ----------- | ---------------- |
| `reader`  | Generates embeddings for SWIRL’s Reader LLM to enhance search result re-ranking | spaCy |
| `query`   | Provides query completions for transformations | OpenAI GPT-3.5 Turbo |
| `connector` | Answers direct questions without RAG | OpenAI GPT-3.5 Turbo |
| `rag` | Generates Retrieval-Augmented Generation (RAG) responses using retrieved data | OpenAI GPT-4 |

## Managing AI Providers

To manage AI providers (view, edit, add, or delete), go to the `swirl/aiproviders` endpoint:  
[http://localhost:8000/swirl/aiproviders](http://localhost:8000/swirl/aiproviders) (default local installation).

![SWIRL AI Providers](https://docs.swirl.today/images/swirl_aiproviders.png)

## Supported Generative AI (GAI) and LLMs

SWIRL, via LiteLLM and direct connections, supports major GAI/LLMs, including:

- OpenAI
- Azure/OpenAI
- AWS Bedrock
- Google Gemini
- Anthropic Claude
- Cohere
- Meta Llama
- Hugging Face
- Locally fine-tuned models

For assistance with any of these or additional models, please [contact support](#support).

### External Model Resources

- [Full list of Supported Embeddings](https://docs.litellm.ai/docs/embedding/supported_embedding)
- [Full list of Supported GAI/LLMs](https://docs.litellm.ai/docs/providers)

## Editing AI Providers

To edit an AI provider, append its `id` to the `swirl/aiproviders` URL. Example: [http://localhost:8000/swirl/aiproviders/4/](http://localhost:8000/swirl/aiproviders/4/)

![SWIRL AIProvider - Azure/OpenAI GPT-4](images/swirl_aiprovider_4.png)

### Available Actions:

- **Delete** the AI provider permanently
- **Modify** and **update** the AI provider configuration

## Activating AI Providers

To activate a preloaded AI provider:

1. Ensure `active` is set to `true`
2. Provide a valid `api_key`
3. Specify the `model` and required `config` settings
4. Assign the provider’s role in the `tags` list
5. Set the provider as the default for a role in the `defaults` list (if applicable)

### Example: Preloaded OpenAI GPT-4 Provider

```json
{
    "id": 16,
    "name": "OpenAI GPT-4",
    "owner": "admin",
    "shared": true,
    "date_created": "2024-03-04T15:15:16.940393-05:00",
    "date_updated": "2024-03-04T15:15:16.940410-05:00",
    "active": true,
    "api_key": "<your-openai-api-key>",
    "model": "gpt-4",
    "config": {},
    "tags": ["query", "connector", "rag"],
    "defaults": ["rag"]
}
```

## Switching AI Provider Defaults

To switch providers for the same role, update the `active` property.

Example: Switching between OpenAI GPT-4 and Azure/OpenAI GPT-4 for RAG:

```json
{
    "id": 4,
    "name": "Azure/OpenAI GPT-4",
    "owner": "admin",
    "shared": true,
    "date_created": "2024-03-04T15:15:13.587586-05:00",
    "date_updated": "2024-03-04T15:15:13.587595-05:00",
    "active": false,
    "api_key": "<your-azure-openai-api-key>",
    "model": "azure/gpt-4",
    "config": {
        "api_base": "https://swirltest-openai.openai.azure.com",
        "api_version": ""
    },
    "tags": ["query", "connector", "rag", "chat"],
    "defaults": ["rag", "chat"]
}
```

### Steps to Switch

1. Set `active` to `true` for Azure/OpenAI GPT-4 and **PUT** the update.
2. Set `active` to `false` for OpenAI GPT-4 and **PUT** the update.

Now, Azure/OpenAI GPT-4 is active for RAG, while OpenAI GPT-4 is inactive. Future versions of SWIRL will introduce prioritization and fallback between providers.

## Installing AI Providers via Copy/Paste

To manually install an AI provider using JSON:

1. Open the AI Providers endpoint: [http://localhost:8000/swirl/aiproviders/](http://localhost:8000/swirl/aiproviders/)
2. Click the `Raw data` tab at the bottom of the page
3. Paste the AI provider’s JSON
4. Press the `POST` button

SWIRL will respond with the registered AI provider.

### Bulk Loading AI Providers

Use the [`swirl_load.py`](https://github.com/swirlai/swirl-search/blob/main/swirl_load.py) script to load multiple AI providers.

## Using the Bearer Token Service to Update AI Providers

SWIRL AI Connect, Enterprise Edition, includes a **Bearer Token Service** that refreshes tokens automatically.

### How It Works

1. Sends a `POST` request to an Identity Provider (IDP) URL with user credentials.
2. Extracts a `bearer_token` from the response.
3. Updates the `api_key` of the configured AI provider.

### Configuration

#### 1. Add the following settings to `.env`:

```
BT_IDP_URL=''
BT_IDP_CLIENT_ID=''
BT_IDP_CLIENT_SECRET=''
```

#### 2. Specify the AI Provider IDs to update:

```
BT_AIP=9
```

For multiple providers, use a comma-separated list:

```
BT_AIP='9,10'
```

#### 3. Schedule Token Refresh in `swirl_server/settings.py`:

By default, the service runs every **20 minutes**. Adjust the schedule in `CELERY_BEAT_SCHEDULE`:

```python
CELERY_BEAT_SCHEDULE = {
    # Bearer Token Service (default: every 20 minutes)
    'bt_service': {
         'task': 'bt_service',
         'schedule': crontab(minute='*/20'),
    },
}
```

#### 4. Start the `celery-beats` service:

```
python swirl.py start celery-beats
```

#### 5. Restart the logs:

If `python swirl.py logs` is running, restart it to view `celery-beats` messages. 

Most Bearer Token service logs appear in `logs/celery-worker.log`.

This ensures automatic updates for AI provider credentials, reducing manual intervention.

# Managing Prompts

## Default Prompts

{: .warning }
**Warning:** If you edit a default system prompt, your changes will be lost when SWIRL is updated.

View the default prompts at:  
[http://localhost:8000/swirl/prompts/](http://localhost:8000/swirl/prompts/)

## Creating New Saved Prompts

To create a new saved prompt:

1. Open [http://localhost:8000/swirl/prompts/](http://localhost:8000/swirl/prompts/)
2. Use the form at the bottom of the page to create a new prompt **or** paste raw JSON and click `POST`.

### Example: Creating a Pirate-Themed Prompt

Modify the default prompt to generate responses in pirate-speak:

```json
{
    "name": "pirate",
    "...": "... etc ...",
    "footer": "--- Final Instructions ---
In your response, pretend you are a pirate comedian, but keep it clean!",
    "tags": ["search-rag"]
}
```

This will produce:

![SWIRL Prompt Object](images/swirl_prompt_form.png)

## Specifying a Saved Prompt in a Query

Test a saved prompt using the **prompt operator**:

```
swirl ai connect prompt:pirate
```

The response should be generated in pirate-speak:

![SWIRL RAG response in pirate speak](images/swirl_prompt_pirate.png)

## Understanding Saved Prompts

SWIRL prompts consist of three key components:

| Field | Description |
| ----- | ----------- |
| `prompt` | The main body of the prompt. Use `{query}` to represent the SWIRL query. |
| `note` | Text appended to RAG data chunks, annotated by the [Text Analyzer](#text-summarization). |
| `footer` | Additional instructions appended after the prompt and RAG data. This is ideal for formatting guidance. |

## Using a Prompt in a Query Processor or Connector

To specify a prompt when using **Generative AI (GAI)** for query rewriting or direct question answering:

1. Follow the steps in [Connecting to Enterprise AI](#connecting-to-enterprise-ai).
2. Refer to the **Developer Reference** section on [GAI SearchProvider Tags](https://docs.swirl.today/Developer-Reference.html#chatgpt-query_mapping).

This ensures prompts are correctly applied when interacting with AI-based query transformations.

# Optimizing RAG

## Using Summaries

Set `SWIRL_ALWAYS_FALL_BACK_TO_SUMMARY` to `True` to enable SWIRL to use result summaries for RAG. This is the best option for sources where full-page fetching is restricted due to authentication limitations.

## Distribution Strategy

The **distribution strategy** determines how SWIRL selects pages from search results per source. Configure this by setting `SWIRL_RAG_DISTRIBUTION_STRATEGY` to one of the following:

- **`Distributed`** – Maintains the original sort order and evenly selects pages from each source.  
  - Example: If two sources return results, SWIRL selects five pages from each, adding them to the prompt until token limits are reached.
  - The sort order remains unchanged, and `swirl_score` is **not used**.

- **`RoundRobin`** – Selects pages in a round-robin fashion across sources.  
  - Respects the source’s internal sort order but **ignores `swirl_score`**.

- **`Sorted`** (default) – Selects pages based on **`swirl_score`**, ensuring only results with a `swirl_score` greater than 50 are used.

## Model Maximum Pages and Tokens

- **Set the RAG model**: Use `SWIRL_RAG_MODEL` to specify the generative AI model for RAG.
- **Limit the number of pages considered**: Configure `SWIRL_RAG_MAX_TO_CONSIDER` to control how many pages are used.
- **Control token usage**: Use `SWIRL_RAG_TOK_MAX` to set the maximum number of tokens in the prompt sent to ChatGPT.

## Notes

- When adjusting `SWIRL_RAG_MODEL` or `SWIRL_RAG_TOK_MAX`, ensure values remain within the model’s token limit.
- SWIRL uses model-specific encodings to count tokens but also respects user-defined limits.
- The default `SWIRL_RAG_TOK_MAX` is set **below** the model’s maximum to prevent excessive latency in responses.

# Configuring the Authenticating Page Fetcher for RAG with Enterprise Content

SWIRL AI Connect, Enterprise Edition, includes a **Page Fetcher** that retrieves results from sources requiring authentication.

![SWIRL AI Connect Insight Pipeline](images/swirl_rag_pipeline.png)

The Page Fetcher authenticates using the **user’s token** or a configured authentication method for each source.

The following sections explain how to configure **Page Fetching** for specific SearchProviders.

## Google PSE SearchProviders

For **public source data** via **Google PSE SearchProviders**, the recommended configuration uses [Diffbot](https://www.diffbot.com/)—a page fetching and content cleaning service.

### Configuration with Diffbot

```json
"page_fetch_config_json": {
    "cache": "false",
    "fallback": "diffbot",
    "diffbot": {
        "token": "<Diffbot-API-Token-Here>",
        "scholar.google.com": {
            "extract_entity": "article"
        }
    },
    "headers": {
        "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
    },
    "www.businesswire.com": {
        "timeout": 60
    },
    "www.linkedin.com": {
        "timeout": 5
    },
    "rs.linkedin.com": {
        "timeout": 5
    },
    "uk.linkedin.com": {
        "timeout": 5
    },
    "au.linkedin.com": {
        "timeout": 5
    },
    "timeout": 30
}
```

To obtain a **Diffbot token**, sign up at:  
[https://www.diffbot.com/](https://www.diffbot.com/)

### Configuration Without Diffbot

If you prefer **not** to use Diffbot, use the following configuration:

```json
"page_fetch_config_json": {
    "cache": "false",
    "headers": {
        "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
    },
    "www.businesswire.com": {
        "timeout": 60
    },
    "www.linkedin.com": {
        "timeout": 5
    },
    "rs.linkedin.com": {
        "timeout": 5
    },
    "uk.linkedin.com": {
        "timeout": 5
    },
    "au.linkedin.com": {
        "timeout": 5
    },
    "timeout": 30
}
```

{: .highlight } 
**Note:** For more details on configuring Google PSE SearchProviders, refer to the [SearchProvider Guide](SP-Guide.html#activating-a-google-programmable-search-engine-pse-searchprovider).

## Notes

- **`cache` is set to `false`** by default as of Release 3.0.
- **`fallback: "diffbot"` enables automatic failover**—SWIRL attempts normal fetching first, using Diffbot only if the initial fetch fails.  
  - This improves speed, as Diffbot requests are slower and should only be used when necessary.
- **`headers` define request headers** sent with each page request.
- **Domain-specific `timeout` values** serve two purposes:
  - Allowing slow but valuable sources (e.g., `www.businesswire.com`) to return data.
  - Enforcing quick failures for unsupported sites (e.g., `www.linkedin.com`), so Diffbot can be used instead.
- **Diffbot requires a paid account** with an associated API token.

This configuration ensures efficient, authenticated page fetching while minimizing request costs.

# M365 Configurations

{: .warning }
**Warning:** Diffbot should **not** be used with Microsoft sources.

{: .highlight } 
**Note:** The `content_url` field is a template URL that dynamically constructs a URL using search result data. SWIRL uses this URL to fetch actual content.

## Microsoft Outlook Messages

Add the following configuration to the **Microsoft Outlook Messages** SearchProvider:

```json
"page_fetch_config_json": {
    "cache": "false",
    "headers": {
        "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
    },
    "timeout": 10
}
```

## Microsoft Calendar

Add the following configuration to the **Microsoft Calendar** SearchProvider:

```json
"page_fetch_config_json": {
    "cache": "false",
    "content_url": "https://graph.microsoft.com/v1.0/me/events/'{hitId}'",
    "headers": {
        "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
    },
    "timeout": 30
}
```

## Microsoft OneDrive

### Configuration Options

| Field | Description |
| ----- | ----------- |
| `content_url` | The URL to fetch the page content if different from the URL mapped to SWIRL’s `url` field. |
| `mimetype_url` | The URL to fetch the **mimetype** of the content. |
| `mimetype_path` | JSON path to extract the **mimetype** from the fetched object. |
| `mimetype_whitelist` | List of **mimetypes** allowed for content fetching. |

### OneDrive Configuration

- The configuration below enables fetching **HTML, PDFs, and Microsoft Office documents**.
- **Binary content (PDF, DOCX, PPTX, etc.) requires a configured text extractor** for RAG.

```json
"page_fetch_config_json": {
    "cache": "false",
    "content_url": "https://graph.microsoft.com/v1.0/drives/'{resource.parentReference.driveId}'/items/'{resource.id}'/content",
    "mimetype_url": "https://graph.microsoft.com/v1.0/drives/'{resource.parentReference.driveId}'/items/'{resource.id}'",
    "mimetype_path": "'{file.mimeType}'",
    "mimetype_whitelist": [
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "image/png",
        "text/html"
    ],
    "headers": {
        "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
    },
    "timeout": 30
}
```

## Microsoft SharePoint

Add the following configuration to the **Microsoft SharePoint** SearchProvider:

```json
"page_fetch_config_json": {
    "cache": "false",
    "content_url": "https://graph.microsoft.com/beta/sites/'{hitId}'/drives",
    "headers": {
        "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
    },
    "timeout": 10
}
```

## Microsoft Teams Chat

Add the following configuration to the **Microsoft Teams Chat** SearchProvider:

```json
"page_fetch_config_json": {
    "cache": "false",
    "content_url": "https://graph.microsoft.com/beta/chats/'{resource.chatId}'/messages",
    "headers": {
        "User-Agent": "Swirlbot/1.0 (+http://swirl.today)"
    },
    "timeout": 10
}
```

This ensures SWIRL correctly fetches authenticated content from Microsoft sources while maintaining security and efficiency.

# Extracting Enterprise Content with Apache Tika

SWIRL integrates [Apache Tika](https://tika.apache.org/) to extract text from various file types. The following sections explain how to deploy and configure it.

## Running Apache Tika

For **local installations**, start Tika using Docker:

```sh
docker run -d -p 9998:9998 apache/tika
```

To use a **remote Tika instance**, set `TIKA_SERVER_ENDPOINT` in SWIRL’s `.env` file:

```sh
TIKA_SERVER_ENDPOINT='http://your-tika-server:9998/'
```

Restart SWIRL after making changes.

## SearchProvider Configuration

Refer to the **Microsoft OneDrive** section for a **Page Fetcher** configuration that integrates Tika for extracting text from **PDFs, Microsoft Office documents, and other file formats** retrieved via the **Microsoft Graph API**.

To support additional file types, expand the **whitelist** to include any [document format that Tika supports](https://tika.apache.org/1.10/formats.html).

## Configuring Passage Detection with Reader LLM

SWIRL AI Connect, Enterprise Edition, includes **passage detection** in the **Reader LLM**, which enhances RAG accuracy by identifying relevant sections of text.

### Running Passage Detection Locally

Start the **passage detection service** using Docker:

```sh
docker run -p 7029:7029 -e SWIRL_TEXT_SERVICE_PORT=7029 swirlai/swirl-integrations:topic-text-matcher
```

## Configuration Options

The following environment variables allow customization of **Reader LLM** and **RAG settings**:

| Variable | Description | Example |
| -------- | ----------- | ------- |
| `SWIRL_TEXT_SUMMARIZATION_URL` | URL where the passage detection service is running | `http://localhost:7029/` |
| `SWIRL_TEXT_SUMMARIZATION_TIMEOUT` | Maximum response wait time for RAG | `60s` |
| `SWIRL_TEXT_SUMMARIZATION_MAX_SIZE` | Maximum text block size sent for summarization | `4K` |
| `SWIRL_TEXT_SUMMARIZATION_TRUNCATION` | If `true`, only text containing summarization tags is included in the RAG prompt | `true` |
| `SWIRL_RAG_MODEL` | ChatGPT model identifier used for RAG | `"gpt-4"` |
| `SWIRL_RAG_TOK_MAX` | Maximum number of tokens sent to ChatGPT | `4000` |
| `SWIRL_RAG_MAX_TO_CONSIDER` | Maximum search results considered for RAG | `10` |
| `SWIRL_RAG_DISTRIBUTION_STRATEGY` | Defines how search results are selected for RAG: `Distributed`, `RoundRobin`, or `Sorted` | `RoundRobin` |

### About `SWIRL_RAG_DISTRIBUTION_STRATEGY`

If set to **`Distributed`**, and the number of documents is **less than `SWIRL_RAG_MAX_TO_CONSIDER`**, SWIRL **backfills** results by iterating through the next available results.

## Example `.env` Configuration

```ini
SWIRL_TEXT_SUMMARIZATION_URL='http://localhost:7029/'
SWIRL_TEXT_SUMMARIZATION_TRUNCATION=True
SWIRL_RAG_DISTRIBUTION_STRATEGY='RoundRobin'
TIKA_SERVER_ENDPOINT='http://localhost:9998/'
```

This configuration ensures **Apache Tika** and **Reader LLM passage detection** are correctly integrated into SWIRL AI Connect.

# Text Summarization

When `SWIRL_TEXT_SUMMARIZATION_URL` is set to a **Text Analyzer URL**, SWIRL sends text to the **Text Analyzer** before further RAG processing.  
This allows SWIRL to **tag important parts of the text** that are most relevant to the query before they are included in the ChatGPT prompt.

### Example: Tagged Text in a Prompt

```text
--- Content Details ---
Type: Web Page
Domain: swirl.today
Query Terms: 'Swirl'
Important: Text between <SW-IMPORTANT> and </SW-IMPORTANT> is most pertinent to the query.

--- Content ---
<SW-IMPORTANT>WHO IS SWIRL? </SW-IMPORTANT>
<SW-IMPORTANT>Getting to know Swirl Swirl is a powerful solution for identifying and using information. </SW-IMPORTANT>
<SW-IMPORTANT>Swirl was launched in 2022 and operates under the Apache 2.0 license. </SW-IMPORTANT>
<SW-IMPORTANT>At Swirl we follow an iterative approach to software development adhering to the principles of agile methodology. </SW-IMPORTANT>
We believe in delivering high-quality releases through each stage of our development lifecycle.
```

# Text Truncation

When **text truncation** is enabled, **only** text that contains at least one important tagged section (as shown above) is included in the ChatGPT prompt.  

### **Enabling Text Truncation**

To activate this feature, ensure **both** conditions are met:

1. `SWIRL_TEXT_SUMMARIZATION_URL` is set to a valid **Text Analyzer** URL.
2. `SWIRL_TEXT_SUMMARIZATION_TRUNCATION` is set to `true`.

### **Log Entries for Truncated Content**

When a text chunk is excluded due to summarization truncation, logs will show entries like this:

```text
2023-10-19 09:34:01,828 INFO     RAG: url:https://www.wendoverart.com/wtfh0301 problem:RAG Chunk not added for 'Swirl' : SUMMARIZATION TRUNCATION
```

This configuration ensures that **only the most relevant content** is included in RAG, improving accuracy and efficiency.
