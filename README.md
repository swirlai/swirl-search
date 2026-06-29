<!-- Drop-in replacement for github.com/swirlai/swirl-search/README.md -->
<!-- Image paths reference the repo's existing docs/images assets so they render unchanged. -->

[![SWIRL](https://github.com/swirlai/swirl-search/raw/main/docs/images/swirl5_header.png)](https://www.swirlaiconnect.com)

# SWIRL Community

## Federated AI search and RAG across your stack, without moving your data

Ask a question. SWIRL searches your apps live, ranks the results, and returns an answer with sources you can click through to. Data stays where it lives. No vector database, no ETL, no second copy to govern. Open source, Apache 2.0, running on your machine in about two minutes.

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg?style=flat-square)](https://opensource.org/license/apache-2.0)
[![GitHub Release](https://img.shields.io/github/v/release/swirlai/swirl-search?style=flat-square&label=Release)](https://github.com/swirlai/swirl-search/releases)
[![GitHub Stars](https://img.shields.io/github/stars/swirlai/swirl-search?style=social)](https://github.com/swirlai/swirl-search/stargazers)
[![Website](https://img.shields.io/badge/Website-swirlaiconnect.com-00215E?style=flat-square)](https://www.swirlaiconnect.com)

[![SWIRL Galaxy UI: ask a question, get an answer with sources](https://github.com/swirlai/swirl-search/raw/main/docs/images/swirl5_galaxy_ui.png)](https://www.swirlaiconnect.com)

[⚡ Quick Start](#-quick-start-docker-in-2-minutes) · [🧱 What you get](#-what-swirl-community-gives-you) · [🆚 Community vs Enterprise](#-community-vs-swirl-5-enterprise) · [🔌 Connectors](https://swirlaiconnect.com/connectors) · [🤝 Contribute](#-contributing)

> This repository is **SWIRL Community**, Apache 2.0 and free to self-host. There is also **SWIRL Enterprise**, which adds a three-pass reranker, canonical answers, an MCP server for agents, and managed support. The [comparison](#-community-vs-swirl-5-enterprise) below lays out the difference, so you can tell which one you need.

## 🤔 Why SWIRL?

Most "AI search" asks you to copy everything into a vector database first, then govern that copy forever. SWIRL skips the copy. It queries your sources live, with the user's own permissions, re-ranks the results, and optionally generates an answer with citations using the LLM of your choice.

| ❌ The usual way | ✅ With SWIRL |
| --- | --- |
| Stand up a vector database | No vector DB needed |
| Move and duplicate your data | Data stays in place |
| Build ETL pipelines | Query live, in place |
| Weeks of infrastructure work | One Docker command, about 2 minutes |
| A new copy to secure and audit | Permissions enforced at the source |

## 🔥 Quick Start: Docker in 2 minutes

Make sure the [Docker app](https://docs.docker.com/get-docker/) is installed and running.

Download the compose file:

```
curl https://raw.githubusercontent.com/swirlai/swirl-search/main/docker-compose.yaml -o docker-compose.yaml
```

Optional, to enable real-time RAG with your own OpenAI key:

```
export MSAL_CB_PORT=8000
export MSAL_HOST=localhost
export OPENAI_API_KEY='<your-OpenAI-API-key>'
```

Start SWIRL:

```
docker-compose pull && docker-compose up
```

Then open <http://localhost:8000/galaxy>, log in with `admin` / `password`, and run a search. SWIRL comes ready to search Arxiv, European PMC and Google News out of the box.

[![SWIRL Galaxy UI: federated, ranked results across your sources](https://github.com/swirlai/swirl-search/raw/main/docs/images/swirl5_galaxy_results.png)](https://www.swirlaiconnect.com)

> Note: the Docker version does not retain data or configuration when shut down. For a persistent install, see the [Quick Start Guide](https://docs.swirlaiconnect.com/quick-start). Watch the [60-second video tutorial](https://www.youtube.com/watch?v=Ypn4XvSJfcQ) to get going.

## 🧱 What SWIRL Community gives you

Apache 2.0, free, yours to run anywhere:

- Federated search and RAG across 100+ connectors, with your data left in place.
- The Galaxy UI, the same interface that powers SWIRL Enterprise.
- Real-time RAG with citations using your own OpenAI key.
- Microsoft 365 integration with OAuth2.
- Re-ranking with cosine vector similarity (spaCy large model plus NLTK), duplicate detection, and result mixers.
- A pipelined Processor architecture for transforming queries, responses and results.
- Synchronous or asynchronous federation over a clean REST API.
- Results stored in SQLite or Postgres for post-processing and analytics.
- Easily extensible Connector and Mixer objects, so adding a source is straightforward.

### What teams build with it

- Knowledge base search across SharePoint, Confluence and Drive, with source links.
- Customer support assistants that search docs and tickets and draft grounded responses.
- Developer assistants over GitHub, Jira and documentation.
- Unified search across every tool, with results that respect existing permissions.

## 🆚 Community vs SWIRL 5 Enterprise

Community is genuinely useful and genuinely open. SWIRL 5 Enterprise is what you graduate to when search becomes infrastructure. We keep the line honest so you always know what you are running.

| Capability | Community (Apache 2.0) | SWIRL 5 Enterprise |
| --- | --- | --- |
| Federated search and RAG, no data movement | Yes | Yes |
| Galaxy UI | Yes | Yes |
| 100+ connectors | Yes | Yes, plus managed connectors |
| RAG with your own LLM key | Yes | Yes |
| Relevancy ranking | Cosine similarity (spaCy, NLTK) | Three-pass pipeline: BM25, then E5 embeddings with hybrid fusion, then a cross-encoder |
| Canonical answers and Pinned Results | Not included | Yes |
| First-class MCP server for agents | Not included | Yes |
| Hallucination warning on generated answers | Not included | Yes |
| Business console with AI-Yield analytics, semantic cache and dedup at scale | Not included | Yes |
| SOC-2 hosting, managed connectors, and support | Not included | Yes |

If you outgrow cosine ranking, want canonical answers, or need your agents to call SWIRL over MCP, that is SWIRL 5.

## When you outgrow Community

Plenty of teams run Community in production and never need more. If you do reach its edges, where you want the three-pass reranker, canonical answers, an MCP server for your agents, the hallucination warning, or managed connectors and support, that is what SWIRL Enterprise adds.

If that is where you are heading, you can [talk to us](https://swirlaiconnect.com/contact-us) for a walkthrough on your own systems. Nothing leaves your environment, and there is no obligation.

## 🔌 Connectors

The full, current list lives at [swirlaiconnect.com/connectors](https://swirlaiconnect.com/connectors). Connectors are easily extensible; see the [Connector objects](https://github.com/swirlai/swirl-search/tree/main/swirl/connectors) and the [Developer Guide](https://docs.swirlaiconnect.com/developer-guide#develop-new-processors). To request a connector, email [support@swirlaiconnect.com](mailto:support@swirlaiconnect.com).

## 📖 Documentation

Full docs: [docs.swirlaiconnect.com](https://docs.swirlaiconnect.com/). Start with the [Quick Start Guide](https://docs.swirlaiconnect.com/quick-start), then the [User Guide](https://docs.swirlaiconnect.com/user-guide) and [Developer Guide](https://docs.swirlaiconnect.com/developer-guide).

## 🤝 Contributing

SWIRL is built in the open and we welcome contributions. Good places to start:

- Browse [open issues](https://github.com/swirlai/swirl-search/issues) and look for `good first issue`.
- Join [GitHub Discussions](https://github.com/swirlai/swirl-search/discussions) to ask questions and share what you are building.
- Write a connector or a mixer; the objects are designed to be extended.

Please read the Code of Conduct and Contributing guide in the repo before opening a pull request.

## 👷 Support and community

- Questions, ideas, or just a hello: [support@swirlaiconnect.com](mailto:support@swirlaiconnect.com).
- Follow along in the [Bringing AI to the Data newsletter](https://www.linkedin.com/newsletters/7201909550860427264/).
- Star the repo to follow releases; we ship often.

## License

SWIRL Community is licensed under the [Apache License 2.0](https://opensource.org/license/apache-2.0). See `LICENSE` and `NOTICE` for details.
