<div align="center">

[![Swirl](https://docs.swirlaiconnect.com/images/transparent_header_3.png)](https://www.swirlaiconnect.com)

<h1>Swirl Community Edition</h1>

### Swirl is open source software that simultaneously searches multiple content sources and returns AI ranked results.

[Quick Start](#-quick-start) · [Slack](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw) · [Key Features](#-key-features) · [Connectors](#-list-of-connectors) · [Integrations](#-integrations) · [Contributing](#-contributing-to-swirl)
</div>

---

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?color=088395&logoColor=blue&style=flat-square)](https://opensource.org/license/apache-2-0/)
[![GitHub Release](https://img.shields.io/github/v/release/swirlai/swirl-search?style=flat-square&color=8DDFCB&label=Release)](https://github.com/swirlai/swirl-search/releases)
[![Docker Build](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml/badge.svg?style=flat-square&branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml)
[![Tests](https://github.com/swirlai/swirl-search/actions/workflows/qa-suite.yml/badge.svg?branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/qa-suite.yml)
[![Static Badge](https://img.shields.io/badge/Join%20Our%20Slack-0E21A0?logo=slack)](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)

<br/>

# 🔎 What is Swirl?

Swirl adapts and distributes user queries to anything with a search API — search engines, databases, NoSQL engines, cloud/SaaS services, data silos, etc. — and uses Large Language Models to re-rank the unified results *without* extracting or indexing *anything*.

![Swirl Diagram](https://docs.swirlaiconnect.com/images/Animation_2.gif)

Swirl can connect to databases (SQL, NoSQL, Google BigQuery), public data services (Google PSE, ArXiv.org, etc.), and enterprise sources (Microsoft 365, Jira, Miro, etc.), and generate insights with AI models like ChatGPT.

<br/>

# 🔗 Integrations

## mike

[mike](https://github.com/willchen96/mike) is an open-source project assistant that uses Swirl for federated search and document import. When connected, mike's project chat gains two tools:

- **`search_external`** — searches all active Swirl providers and returns ranked results into the conversation
- **`import_document`** — fetches a document (PDF, DOCX, DOC) found via Swirl and imports it into the current project

### Demo

▶️ [Swirl Community × Mike OSS: Fetching & Summarizing SharePoint Docs with Claude](https://www.youtube.com/watch?v=biIEPFpQBmQ)

### Prerequisites

- **Swirl Community 4.5 or later** — earlier versions don't include the integration points mike needs. Earlier versions are welcome to add support via PR! 🙂
- **mike built from [willchen96/mike#14](https://github.com/willchen96/mike/pull/14) or later** — this PR contains the Swirl integration changes
- A running mike backend (`npm run dev` in `backend/`)
- Optional: Microsoft 365 OAuth configured in Swirl for M365 document fetch

### Configuration

In mike's `backend/.env`:

```env
# SWIRL federated search (optional — enables search_external and import_document tools)
SWIRL_URL=http://localhost:8000

# Authenticate with a DRF token:
SWIRL_TOKEN=your-swirl-api-token

# Or with username/password Basic auth (takes precedence over SWIRL_TOKEN if both are set):
# SWIRL_USERNAME=admin
# SWIRL_PASSWORD=your-swirl-password
```

### Microsoft 365 prefix syntax

When M365 is configured in Swirl, mike understands these prefixes in the search query:

| Prefix | Source |
|--------|--------|
| `sharepoint:` | SharePoint Sites |
| `onedrive:` | OneDrive |
| `outlook:` | Outlook Messages |
| `teams:` | Microsoft Teams |
| `microsoft:` | All M365 sources |

Example: *"Find the Q3 budget in sharepoint: finance"*

### M365 document fetch

When mike's `import_document` tool receives a SharePoint or OneDrive URL, it proxies the download through Swirl's `/swirl/fetch-document/` endpoint, which handles the Microsoft Graph API three-step fetch using the user's stored OAuth token. No M365 credentials need to be in mike's environment.

<br/>

# 🚀 Quick Start

## Option A — Docker (recommended for evaluation)

> **Requirements:** [Docker Desktop](https://docs.docker.com/get-docker/) must be running.  
> Windows users: configure WSL 2 or Hyper-V per [Docker's Windows requirements](https://docs.docker.com/desktop/install/windows-install/#system-requirements).

```bash
# Download the compose file
curl https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml -o docker-compose.yaml

# Optional: enable RAG with OpenAI
export OPENAI_API_KEY='your-key-here'

# Microsoft 365 OAuth callback (defaults below work for local Docker;
# see the M365 Guide to enable M365 connectors)
export MSAL_CB_PORT=8000
export MSAL_HOST=localhost

# Start Swirl (macOS / Linux / Windows)
docker compose pull && docker compose up
```

Open <http://localhost:8000> and log in with `admin` / `password`.

> **Note:** The Docker version does not retain data or configuration when shut down.

## Option B — Local install (pip)

```bash
git clone https://github.com/swirlai/swirl-search.git
cd swirl-search
pip install -r requirements.txt
python -m spacy download en_core_web_lg

python swirl.py setup
python swirl.py start
```

Open <http://localhost:8000/swirl/> and log in with `admin` / `password`.

> **Requirements:** Python 3.13+, Redis running locally.

<br/>

# ⚙️ Configuration

## SearchProviders

Add credentials to the preloaded SearchProvider fixtures at `/swirl/searchproviders/` or via the Django admin at `/admin/swirl/searchprovider/`. Each provider maps a connector type to a URL, credentials, and query/result mappings.

## Microsoft 365

Swirl supports OAuth2 search across M365 Outlook, OneDrive, SharePoint, and Teams. Setup requires approval from an M365 administrator. See the [M365 Guide](https://docs.swirlaiconnect.com/m365-guide) for full instructions.

## AI / LLM Providers

Configure a `ChatGPT` or `GenAI` SearchProvider with your OpenAI or compatible API key to enable real-time RAG. See the [AI Guide](https://docs.swirlaiconnect.com/ai-guide).

<br/>

# 🔌 List of Connectors

<img src="https://docs.swirlaiconnect.com/images/Connectors_2.png" height=60% width=70%/>

➕ **Need a connector?** [Open an issue](https://github.com/swirlai/swirl-search/issues) or contribute one — see [Contributing](#-contributing-to-swirl).

<br/>

# 🌟 Key Features

| ✦ | Feature |
|:-----:|:--------|
| 📌 | [Microsoft 365 integration and OAUTH2 support](https://docs.swirlaiconnect.com/m365-guide) |
| 🔍 | [SearchProvider configurations](https://github.com/swirlai/swirl-search/tree/main/SearchProviders) for all included Connectors |
| ✏️ | [Adaptation of the query for each provider](https://docs.swirlaiconnect.com/user-guide#search-syntax) including NOT rewriting, AND/OR pass-through |
| ⏳ | [Synchronous or asynchronous search federation](https://docs.swirlaiconnect.com/developer-guide#architecture) via [REST API](http://localhost:8000/swirl/api/docs) |
| 🛎️ | [Optional subscribe feature](https://docs.swirlaiconnect.com/developer-guide#subscribe-to-a-search) to continuously monitor any search for new results |
| 🛠️ | Pipelining of [Processor](https://docs.swirlaiconnect.com/developer-guide#develop-new-processors) stages for real-time query, response and result transformation |
| 🗄️ | Results stored in SQLite3 or PostgreSQL for post-processing and analytics |
| 📖 | [Matching on word stems](https://docs.swirlaiconnect.com/developer-reference#cosinerelevancypostresultprocessor) and stopword handling via NLTK |
| 🚫 | [Duplicate detection](https://docs.swirlaiconnect.com/developer-guide#detect-and-remove-duplicate-results) by field or Cosine Similarity threshold |
| 🔄 | Re-ranking via [Cosine Vector Similarity](https://docs.swirlaiconnect.com/developer-reference#cosinerelevancypostresultprocessor) using spaCy and NLTK |
| 🎚️ | [Result mixers](https://docs.swirlaiconnect.com/developer-reference#mixers-1) — relevancy, date, round-robin |
| ✒️ | [Optional spell correction](https://docs.swirlaiconnect.com/developer-guide#add-spelling-correction) using TextBlob |
| 🔌 | Extensible [Connector](https://github.com/swirlai/swirl-search/tree/main/swirl/connectors) and [Mixer](https://github.com/swirlai/swirl-search/tree/main/swirl/mixers) objects |

<br/>

# 👩‍💻 Contributing to Swirl

**Got an idea or improvement?**

1. Join the [Swirl Slack Community](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)
2. Branch off `develop` with a descriptive name
3. Submit a PR — we follow [Gitflow](https://nvie.com/posts/a-successful-git-branching-model/) loosely

New to GitHub contributions? The [GitHub contributing guide](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) is a great starting point.

<br/>

# 📖 Documentation

[Overview](https://docs.swirlaiconnect.com/) | [Quick Start](https://docs.swirlaiconnect.com/quick-start) | [User Guide](https://docs.swirlaiconnect.com/user-guide) | [Admin Guide](https://docs.swirlaiconnect.com/admin-guide) | [M365 Guide](https://docs.swirlaiconnect.com/m365-guide) | [Developer Guide](https://docs.swirlaiconnect.com/developer-guide) | [Developer Reference](https://docs.swirlaiconnect.com/developer-reference) | [AI Guide](https://docs.swirlaiconnect.com/ai-guide)

<br/>

# 👷‍♂️ Support

* **Slack:** [Swirl Community](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)
* **Email:** [support@swirlaiconnect.com](mailto:support@swirlaiconnect.com)
* **Enterprise / managed service:** [hello@swirlaiconnect.com](mailto:hello@swirlaiconnect.com)
