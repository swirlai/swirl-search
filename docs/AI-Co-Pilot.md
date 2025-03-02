---
layout: default
title: AI Co-Pilot Guide
nav_order: 10
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

# AI Co-Pilot Guide - Enterprise Edition

{: .warning }
This document applies only to SWIRL AI Co-Pilot, Enterprise Edition. 

# Configuring SWIRL AI Co-Pilot, Enterprise Edition

## Roles for Generative AI / Large Language Models

SWIRL AI Connect defines four core roles for GAI/LLMs. SWIRL AI Co-Pilot adds a **fifth role, "chat,"** which can be assigned to any sufficiently capable LLM.

| Role | Description | Default Provider |
| ------- | ----------- | ---------------- |
| `reader`  | Generates embeddings for SWIRL’s Reader LLM to re-rank search results | spaCy |
| `query`   | Provides query completions for transformations | OpenAI GPT-3.5 Turbo |
| `connector` | Answers direct questions (not RAG) | OpenAI GPT-3.5 Turbo |
| `rag` | Generates responses using Retrieval-Augmented Generation (RAG) with retrieved data | OpenAI GPT-4 |
| `chat` | Powers SWIRL AI Co-Pilot messaging | OpenAI GPT-4 |

## Adding Chat to an AI Provider

1. Open the **AI Providers** management page: [http://localhost:8000/swirl/aiproviders](http://localhost:8000/swirl/aiproviders) (default local installation).

   ![SWIRL AI Providers](https://docs.swirl.today/images/swirl_aiproviders.png)

2. Edit an AI provider by appending its `id` to the URL, e.g.: [http://localhost:8000/swirl/aiproviders/4/](http://localhost:8000/swirl/aiproviders/4/)

   ![SWIRL AIProvider - Azure/OpenAI GPT-4](images/swirl_aiprovider_4.png)

3. **Ensure the following in the provider’s configuration:**

   - `active` is set to `true`
   - `api_key` contains a valid API key
   - `model` and `config` values are correctly filled
   - `"chat"` is included in the `tags` list
   - `"chat"` is included in the `defaults` list

### Example: OpenAI GPT-4 Configured for Chat & RAG

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
    "tags": ["query", "connector", "rag", "chat"],
    "defaults": ["rag", "chat"]
}
```

## Launching Co-Pilot

Once the AI provider is configured correctly, **Co-Pilot should be accessible via a browser**.  

For a default installation, go to: [http://localhost:8000/galaxy/chat](http://localhost:8000/galaxy/chat)

![SWIRL Co-Pilot discussion](images/swirl_40_chat_scop.png)

For more details, see the **AI Connect, Enterprise Edition** section: [Connecting to Enterprise GAI and LLMs](AI-Connect.html#connecting-to-generative-ai-gai-and-large-language-models-llms).

## GAI/LLM Requirements

SWIRL AI Co-Pilot expects AI providers to support:

- **Chat history in reverse chronological order**, following the format used by the [OpenAI Chat Completions API](https://platform.openai.com/docs/guides/chat-completions/getting-started).
- **Prompt size of at least 3K tokens per message**, with 6K+ preferred.
- **Recommended models:** OpenAI GPT-4 (`gpt-4`, `gpt-4o`), Anthropic Claude 3, or Google Gemini Pro/Ultra.

Other LLMs may also work **if they support chat history as described above**. If you test alternative models, please **[let us know](#support)** what works (or doesn’t)!
