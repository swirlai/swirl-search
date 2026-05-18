<div align="center">

[![SWIRL — open-source enterprise metasearch and RAG](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/large_header.png)](https://www.swirlaiconnect.com)

# Swirl Community Edition

### Open-source federated metasearch and RAG over your enterprise sources — without moving your data.

[Quick Start](#-quick-start) · [Configuration](#-configuration) · [Connectors](#-connectors) · [Integrations](#-integrations) · [Key Features](#-key-features) · [Contributing](#-contributing)

</div>

---

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?color=088395&logoColor=blue&style=flat-square)](https://opensource.org/license/apache-2-0/)
[![GitHub Release](https://img.shields.io/github/v/release/swirlai/swirl-search?style=flat-square&color=8DDFCB&label=Release)](https://github.com/swirlai/swirl-search/releases)
[![Docker Build](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml/badge.svg?style=flat-square&branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/docker-image.yml)
[![Tests](https://github.com/swirlai/swirl-search/actions/workflows/qa-suite.yml/badge.svg?branch=main)](https://github.com/swirlai/swirl-search/actions/workflows/qa-suite.yml)
[![Static Badge](https://img.shields.io/badge/Join%20Our%20Slack-0E21A0?logo=slack)](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)

📦 **Latest:** [Release Notes](https://docs.swirlaiconnect.com/release-notes) · what's new in each Community release.

<br/>

## 🔎 What is Swirl?

Swirl adapts and distributes user queries to anything with a search API — search engines, databases, NoSQL engines, cloud/SaaS services, data silos. It uses Large Language Models to re-rank the unified results *without* extracting or indexing *anything*.

Swirl exposes its federated search and RAG via REST API and via the [Model Context Protocol (MCP)](https://modelcontextprotocol.io), so Claude Desktop, Claude Code, Cursor, and other MCP clients can answer questions against your private sources through [swirl-mcp-server](#swirl-mcp-server) — no data movement, no per-source plumbing in the agent.

![SWIRL architecture: queries fan out to enterprise connectors, results are re-ranked with LLM relevancy](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/Animation_2.gif)

![SWIRL Galaxy UI in 4.5: a RAG AI Summary answer with cited sources from federated M365 results](https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/swirl_45_galaxy_ai_summary.png)

Swirl can connect to databases (SQL, NoSQL, Google BigQuery), public data services (Google PSE, arXiv, etc.), and enterprise sources (Microsoft 365, Jira, Miro, etc.), and generate insights with AI models like ChatGPT.

<br/>

## 🚀 Quick Start

| Component | Tested versions |
|---|---|
| Python | 3.13+ |
| Docker Compose | v2.20+ |
| OS | macOS, Linux, Windows (WSL2) |

### Option A — Docker (recommended)

**The only one-command path.** Option B below requires Python 3.13+, Redis, and a spaCy model download.

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

> **Note:** The Docker quickstart is intended for evaluation and development. The container does not retain data or configuration when shut down. For persistent deployment, see the [Installation - Community](https://docs.swirlaiconnect.com/installation-community) guide, the [Admin Guide](https://docs.swirlaiconnect.com/admin-guide), or the [Kubernetes Deployment](https://docs.swirlaiconnect.com/kubernetes-guide) guide for cluster setups.

### Option B — Developer install (from source)

For Swirl contributors and anyone customizing the platform. Requires Python 3.13+, a running Redis, and the spaCy `en_core_web_lg` model.

```bash
git clone https://github.com/swirlai/swirl-search.git
cd swirl-search
pip install -r requirements.txt
python -m spacy download en_core_web_lg

python swirl.py setup
python swirl.py start
```

Open <http://localhost:8000/swirl/> and log in with `admin` / `password`.

<br/>

## 🩺 Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Error: bind: address already in use` on `docker compose up` | Port 8000 already taken by another process | Stop the conflicting process, or override the port in `docker-compose.yaml` (`"8001:8000"`) and open `http://localhost:8001`. |
| AI Summary empty / "No response from Generative AI" | `OPENAI_API_KEY` (or Azure equivalents) not set in the Swirl environment | `export OPENAI_API_KEY=…` **before** `docker compose up`. The key must be in Swirl's env, not your shell after start. |
| Credentials changed in the UI disappear after restart | The Docker quickstart does not persist state | Reapply credentials after each `docker compose up`, or move to a persistent deployment (see the [Admin Guide](https://docs.swirlaiconnect.com/admin-guide)). |
| M365 login loops, "redirect URI mismatch", or AADSTS50011 | Azure App Registration's redirect URI doesn't match `MSAL_HOST` / `MSAL_CB_PORT` | Make the Azure redirect URI exactly match `http://{MSAL_HOST}:{MSAL_CB_PORT}/swirl/microsoft/callback` (see the [M365 Guide](https://docs.swirlaiconnect.com/m365-guide)). |
| `python swirl.py start` errors out talking to Redis | Local Redis isn't running (Option B only) | Start Redis first: `redis-server` (Homebrew/apt-get) or run the Redis Docker image and point Swirl at it. |

<br/>

## ⚙️ Configuration

### SearchProviders

Add credentials to the preloaded SearchProvider fixtures at `/swirl/searchproviders/` or via the Django admin at `/admin/swirl/searchprovider/`. Each provider maps a connector type to a URL, credentials, and query/result mappings. Full configuration reference: [SearchProviders Guide](https://docs.swirlaiconnect.com/sp-guide).

### Microsoft 365

Swirl supports OAuth2 search across M365 Outlook, OneDrive, SharePoint, and Teams. Setup requires approval from an M365 administrator. See the [M365 Guide](https://docs.swirlaiconnect.com/m365-guide) for full instructions.

### M365 Quick Reference

When M365 is configured, Swirl recognizes these tag-prefix shortcuts in the search query, routing to just the matching providers:

| Prefix | Source |
|--------|--------|
| `sharepoint:` | SharePoint Sites |
| `onedrive:` | OneDrive |
| `outlook:` | Outlook Messages |
| `teams:` | Microsoft Teams |
| `microsoft:` | All M365 sources |

Example: `sharepoint: Q3 budget` searches only SharePoint for "Q3 budget". The same `<tag>:<query>` syntax works for any tag configured on a SearchProvider (e.g., `arxiv:`, `github:`, `epmc:`).

### AI / LLM Providers

Configure a `ChatGPT` or `GenAI` SearchProvider with your OpenAI or compatible API key to enable real-time RAG. See the [AI Guide](https://docs.swirlaiconnect.com/rag-guide).

<br/>

## 🔌 Connectors

Swirl ships with 40+ pre-configured SearchProviders covering public web, scientific literature, Microsoft 365, developer tools, CRMs, databases, vector stores, and more. A representative selection:

| Category | Connectors | What it searches |
|---|---|---|
| Public web | Google PSE, Internet Archive, Google News, Hacker News | Web pages, news, RSS feeds, archived content |
| Scientific | arXiv, EuropePMC | Preprints and biomedical literature |
| Microsoft 365 | SharePoint, OneDrive, Outlook (mail + calendar), Teams | M365 OAuth2 across files, messages, events, chats |
| Developer | GitHub (Code, Issues, PRs, Commits), JetBrains YouTrack | Source, tickets, pull requests, articles |
| Atlassian | Confluence, Jira, Trello | Wiki, issues, task boards |
| CRM / Ops | HubSpot (Deals, Companies, Contacts), ServiceNow, Crunchbase | Pipelines, accounts, knowledge / catalog, organizations |
| Databases | Google BigQuery, Snowflake, MongoDB, SQLite3, Apache Solr | Structured records via parameterized queries |
| Search engines | Elasticsearch, OpenSearch | Existing search clusters |
| Vector | Pinecone, Qdrant | Semantic / embedding stores |
| Entities | LittleSis, OpenSanctions | People, companies, sanctioned entities |
| Legal | CourtListener (US), National Archives (UK) | Case law and government records |
| Other | Asana, Miro, Blockchain (Transactions + Wallets) | Tasks, drawings, on-chain data |

<img src="https://raw.githubusercontent.com/swirlai/swirl-search/main/docs/images/Connectors_2.png" alt="Grid of SWIRL connector logos for the supported enterprise and public data sources" height=60% width=70%/>

➕ **Need a connector?** [Open an issue](https://github.com/swirlai/swirl-search/issues) or contribute one — see [Contributing](#-contributing).

<br/>

## 🔗 Integrations

### swirl-mcp-server

[swirl-mcp-server](https://github.com/swirlai/swirl-mcp-server) is a [Model Context Protocol](https://modelcontextprotocol.io) adapter for Swirl. It exposes Swirl's federated search and RAG as MCP tools so Claude Desktop, Claude Code, Cursor, and other MCP clients can answer questions against your Swirl-connected sources without any data leaving your network.

#### Demo

![SWIRL MCP Server — rag_answer tool returning a federated RAG answer in the MCP Inspector](https://raw.githubusercontent.com/swirlai/swirl-mcp-server/main/docs/images/mcp_inspector_rag.png)

#### Prerequisites

- **Swirl Community 4.x** running — see [Quick Start](#-quick-start) above
- **Python 3.10+** on the machine running the MCP server
- **For `rag=true` (generated answers):** Swirl itself needs an `OPENAI_API_KEY` (or Azure OpenAI equivalents) — set it in Swirl's environment before `docker compose up`. Plain `search` works without one.

#### Configuration

Install: `pipx install git+https://github.com/swirlai/swirl-mcp-server`. Then add to Claude Desktop's config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS, `%APPDATA%\Claude\claude_desktop_config.json` on Windows):

```json
{
  "mcpServers": {
    "swirl": {
      "command": "swirl-mcp",
      "env": {
        "SWIRL_BASE_URL": "http://localhost:8000",
        "SWIRL_USERNAME": "<your-swirl-username>",
        "SWIRL_PASSWORD": "<your-swirl-password>"
      }
    }
  }
}
```

Restart Claude Desktop and `swirl` should appear in the tools menu. Read more in the [MCP Server guide](https://docs.swirlaiconnect.com/mcp-guide) or at [swirlai/swirl-mcp-server](https://github.com/swirlai/swirl-mcp-server) — six MCP tools (`search`, `rag_answer`, `list_providers`, `create_search`, `get_results`, `list_searches`), with Claude Code and Cursor configs in [`examples/`](https://github.com/swirlai/swirl-mcp-server/tree/main/examples).

### mike

[mike](https://github.com/willchen96/mike) is an open-source project assistant that uses Swirl for federated search and document import. When connected, mike's project chat gains two tools:

- **`search_external`** — searches all active Swirl providers and returns ranked results into the conversation
- **`import_document`** — fetches a document (PDF, DOCX, DOC) found via Swirl and imports it into the current project

#### Demo

▶️ [Swirl Community × Mike OSS: Fetching & Summarizing SharePoint Docs with Claude](https://www.youtube.com/watch?v=biIEPFpQBmQ)

#### Prerequisites

- **Swirl Community 4.5 or later** — earlier versions don't include the integration points mike needs. Earlier versions are welcome to add support via PR! 🙂
- **mike built from [willchen96/mike#14](https://github.com/willchen96/mike/pull/14) or later** — this PR contains the Swirl integration changes
- A running mike backend (`npm run dev` in `backend/`)
- Optional: Microsoft 365 OAuth configured in Swirl for M365 document fetch

#### Configuration

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

mike consumes Swirl's [M365 Quick Reference](#m365-quick-reference) tag-prefix syntax (`sharepoint:`, `onedrive:`, etc.) directly in user queries.

#### M365 document fetch

When mike's `import_document` tool receives a SharePoint or OneDrive URL, it proxies the download through Swirl's `/swirl/fetch-document/` endpoint, which handles the Microsoft Graph API three-step fetch using the user's stored OAuth token. No M365 credentials need to be in mike's environment.

<br/>

## 🌟 Key Features

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
| 🎚️ | [Result mixers](https://docs.swirlaiconnect.com/developer-reference#mixers_1) — relevancy, date, round-robin |
| ✒️ | [Optional spell correction](https://docs.swirlaiconnect.com/developer-guide#spellcheck-example) using TextBlob |
| 🔌 | Extensible [Connector](https://github.com/swirlai/swirl-search/tree/main/swirl/connectors) and [Mixer](https://github.com/swirlai/swirl-search/tree/main/swirl/mixers) objects |

<br/>

## 👩‍💻 Contributing

1. Join the [Swirl Slack Community](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)
2. Branch off `develop` with a descriptive name
3. Submit a PR — we follow [Gitflow](https://nvie.com/posts/a-successful-git-branching-model/) loosely

New to GitHub? The [GitHub contributing guide](https://docs.github.com/en/get-started/quickstart/contributing-to-projects) is a great starting point.

<br/>

## 📖 Documentation

**Get started** — [Overview](https://docs.swirlaiconnect.com/) · [Quick Start](https://docs.swirlaiconnect.com/quick-start) · [Installation - Community](https://docs.swirlaiconnect.com/installation-community) · [Release Notes](https://docs.swirlaiconnect.com/release-notes)

**Use Swirl** — [User Guide](https://docs.swirlaiconnect.com/user-guide) · [AI Search](https://docs.swirlaiconnect.com/ai-search) · [AI Search Assistant](https://docs.swirlaiconnect.com/ai-search-assistant) · [Glossary](https://docs.swirlaiconnect.com/glossary)

**Configure connectors** — [SearchProviders](https://docs.swirlaiconnect.com/sp-guide) · [M365](https://docs.swirlaiconnect.com/m365-guide) · [AI / RAG](https://docs.swirlaiconnect.com/rag-guide) · [MCP Server](https://docs.swirlaiconnect.com/mcp-guide)

**Operate** — [Admin Guide](https://docs.swirlaiconnect.com/admin-guide) · [Kubernetes](https://docs.swirlaiconnect.com/kubernetes-guide) · [Monitoring](https://docs.swirlaiconnect.com/monitoring-guide) · [Security](https://docs.swirlaiconnect.com/security-guide) · [Troubleshooting](https://docs.swirlaiconnect.com/troubleshooting)

**Build & contribute** — [Developer Guide](https://docs.swirlaiconnect.com/developer-guide) · [Developer Reference](https://docs.swirlaiconnect.com/developer-reference) · [Tutorials](https://docs.swirlaiconnect.com/tutorials) · [Contributions](https://docs.swirlaiconnect.com/contributions)

<br/>

## 👷‍♂️ Support

* **Slack:** [Swirl Community](https://join.slack.com/t/swirlmetasearch/shared_invite/zt-1qk7q02eo-kpqFAbiZJGOdqgYVvR1sfw)
* **Email:** [support@swirlaiconnect.com](mailto:support@swirlaiconnect.com)
* **Enterprise / managed service:** [hello@swirlaiconnect.com](mailto:hello@swirlaiconnect.com)
