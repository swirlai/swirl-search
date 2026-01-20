---
layout: default
title: MCP Server
nav_order: 22
---
<details markdown="block">
  <summary>
    Table of Contents
  </summary>
  {: .text-delta }
- TOC
{:toc}
</details>

<span class="big-text">MCP (Model Context Protocol) Guide</span><br/><span class="med-text">Enterprise Edition</span>

{: .warning }
Please [contact SWIRL](mailto:hello@swirlaiconnect.com) for access to SWIRL Enterprise.

---

This guide explains how to install the SWIRL MCP (Model Context Protocol) proxy server & CLI client and optionally use it with [Crew.AI](https://crew.ai).

{: .warning }
**This guide is still being reviewed**. [Contact support](#support) for additional assistance.

# Overview

The SWIRL MCP server supports three categories of MCP endpoints:

Tools: 
* AI Search
* Retrieve SearchProviders

Resources:
* List and read external HTTP JSON responses
* List and apply prompt templates

# System Requirements

- Python **3.12**
- `pip`
- Access to a Swirl HTTP API (or mock)

# Installation

```bash
git clone https://github.com/swirlai/swirl-mcp-proxy-internal.git
cd swirl-mcp-proxy-internal
python -m venv .venv
source .venv/bin/activate
pip install -r mcp_swirl_proxy_internal/requirements.txt
```

## Configuration Options

```text
SWIRL_API_BASE  - Protocol host and port of the Swirl deployment - default "http://localhost:8000"
SWIRL_API_USERNAME - User name to use to login to the Swirl deployment - default  "admin"
SWIRL_API_PASSWORD - Password to use to login to the Swirl deployment - default "password"
SWIRL_API_BASE_PATH - Base path to use for API calls to the Swirl deployment - default "/api/swirl"
SWIRL_MCP_SERVER_HOST - Host interface for server to listen on - default "127.0.0.1"
SWIRL_MCP_SERVER_PORT - Port for server to listen on - default  9999
SWIRL_MCP_SWIRL_API_TIMEOUT - Timeout for calls to the Swirl API - default 120
SWIRL_MCP_USERNAME - MCP Server login user name - default `swirlmcpuser`
SWIRL_MCP_PASSWORD - MCP Serer login password - default `swirlmcppass`
SWIRL_MCP_DO_AUTH  - Whether to enforce login or not - default true
```

## Building Local Docker Image
To build the local docker image, run the following command:

```bash
./DevUtils/build-docker-image.sh -i service
```

This will build the docker image for the local architecture and export it from buildx into Docker.

```
Environment:         darwin24
Image Type:          service
Image Repo:          swirlai/dev-mcp-proxy-enterprise
Image Version:       develop
Build Dir:           /Users/sid/Code/swirl-mcp-proxy-internal/mcp_swirl_proxy_internal
Branch Name:         develop
Dry Run:             false
Push to Docker Hub:  --load
Tags:                -t swirlai/dev-mcp-proxy-enterprise:develop
Running: pushd /Users/sid/Code/swirl-mcp-proxy-internal/mcp_swirl_proxy_internal
~/Code/swirl-mcp-proxy-internal/mcp_swirl_proxy_internal ~/code/swirl-mcp-proxy-internal
Running: docker buildx inspect devBuilder > /dev/null 2>&1 || docker buildx create --name devBuilder --use
Running: docker buildx build -t swirlai/dev-mcp-proxy-enterprise:develop --platform linux/amd64 .  --load
[+] Building 20.5s (14/14) FINISHED                                                                                                                            docker-container:devBuilder
 => [internal] load build definition from Dockerfile                                                                                                                                  0.0s
 => => transferring dockerfile: 665B                                                                                                                                                  0.0s
 => [internal] load metadata for docker.io/library/python:3.12-slim                                                                                                                   0.9s
 => [auth] library/python:pull token for registry-1.docker.io                                                                                                                         0.0s
 => [internal] load .dockerignore                                                                                                                                                     0.0s
 => => transferring context: 2B                                                                                                                                                       0.0s
 => [1/7] FROM docker.io/library/python:3.12-slim@sha256:e55523f127124e5edc03ba201e3dbbc85172a2ec40d8651ac752364b23dfd733                                                             3.0s
 => => resolve docker.io/library/python:3.12-slim@sha256:e55523f127124e5edc03ba201e3dbbc85172a2ec40d8651ac752364b23dfd733                                                             0.0s
 => => sha256:d6413c75b31d1e291ea1b03e04cc390349f359145bbfe370f768d91c15e47a89 250B / 250B                                                                                            0.1s
 => => sha256:ebb07cd170cc8bb945a29bb5d838d9572bbf28233b4a5c0b2ce678dbbcd59d10 13.66MB / 13.66MB                                                                                      1.3s
 => => sha256:25244d620b7469e583336e7c7018b96cbfe7aa52bd295bd1c85178797030a520 3.51MB / 3.51MB                                                                                        0.7s
 => => sha256:dad67da3f26bce15939543965e09c4059533b025f707aad72ed3d3f3a09c66f8 28.23MB / 28.23MB                                                                                      2.4s
 => => extracting sha256:dad67da3f26bce15939543965e09c4059533b025f707aad72ed3d3f3a09c66f8                                                                                             0.4s
 => => extracting sha256:25244d620b7469e583336e7c7018b96cbfe7aa52bd295bd1c85178797030a520                                                                                             0.0s
 => => extracting sha256:ebb07cd170cc8bb945a29bb5d838d9572bbf28233b4a5c0b2ce678dbbcd59d10                                                                                             0.1s
 => => extracting sha256:d6413c75b31d1e291ea1b03e04cc390349f359145bbfe370f768d91c15e47a89                                                                                             0.0s
 => [internal] load build context                                                                                                                                                     0.0s
 => => transferring context: 63.88kB                                                                                                                                                  0.0s
 => [2/7] WORKDIR /app                                                                                                                                                                0.1s
 => [3/7] COPY requirements.txt .                                                                                                                                                     0.0s
 => [4/7] RUN set -e     && pip install --no-cache-dir --upgrade pip --root-user-action=ignore     && pip install --no-cache-dir -r requirements.txt                                 11.1s
 => [5/7] COPY *.py .                                                                                                                                                                 0.0s 
 => [6/7] COPY scripts/* ./scripts/                                                                                                                                                   0.0s 
 => [7/7] RUN set -e     && chmod +x /app/scripts/*.sh                                                                                                                                0.1s 
 => exporting to docker image format                                                                                                                                                  5.2s 
 => => exporting layers                                                                                                                                                               2.0s 
 => => exporting manifest sha256:eda618c7db40ed9ce2b6856a446571c3685d84461d5c9d011645d84d70414618                                                                                     0.0s 
 => => exporting config sha256:d97b9fc5b53e228998499cc5c84cc0fd09b6fcc0e910c50fcf8d0cdbe4b98e06                                                                                       0.0s
 => => sending tarball                                                                                                                                                                3.2s
 => importing to docker                                                                                                                                                               2.7s
 => => loading layer 7fb72a7d1a8e 294.91kB / 28.23MB                                                                                                                                  2.7s
 => => loading layer 7b35846aeec0 65.54kB / 3.51MB                                                                                                                                    1.9s
 => => loading layer 5eaadadb6079 163.84kB / 13.66MB                                                                                                                                  1.8s
 => => loading layer e7fd3ca5b4d3 250B / 250B                                                                                                                                         1.4s
 => => loading layer 85bf93e26aae 93B / 93B                                                                                                                                           1.4s
 => => loading layer a2a62bba8abb 899B / 899B                                                                                                                                         1.4s
 => => loading layer 17f3031f2922 327.68kB / 30.55MB                                                                                                                                  1.3s
 => => loading layer 4765dc3070be 14.83kB / 14.83kB                                                                                                                                   0.0s
 => => loading layer 5ecd3e3d1370 417B / 417B                                                                                                                                         0.0s
 => => loading layer 86c9d033f588 202B / 202B                                                                                                                                         0.0s

View build details: docker-desktop://dashboard/build/devBuilder/devbuilder0/ij06675xbrkivu6nwki29u1xg

What's next:
    View a summary of image vulnerabilities and recommendations → docker scout quickview 
[2025-06-17T16:35:59 INFO] Docker image built successfully: swirlai/dev-mcp-proxy-enterprise:develop

```


## Running the TCP Server

```bash
python mcp_swirl_proxy_internal/swirl-mcp-server-tcp.py 
```

By default, this server binds to $SWIRL_MCP_SERVER_HOST:$SWIRL_MCP_SERVER_PORT and speaks the MCP JSON-RPC protocol over raw TCP.

The default port is 9999. It's possible to override the host/port on the command-line:

```bash
python mcp_swirl_proxy_internal/swirl-mcp-server-tcp.py 0.0.0.0 9876
```

## Running the MCP server in Docker

Run the MCP server using Docker with the following command:

```bash
docker compose up
```

## Use the Interactive Client

Use our REPL client to talk to your server:
```bash
python mcp_swirl_proxy_internal/swirl_mcp_client_tcp_interactive.py $SWIRL_MCP_SERVER_HOST $SWIRL_MCP_SERVER_PORT
```

# Available Commands

```text
Command | Action
/login                         Login with /login <username> <password>
/tools                         List available tools (use to login)
/resources                     List available resources
/prompts                       List available prompts (names & descriptions)
/call <tool> [json]            Call a tool by name, optional JSON args
/prompt <name> [json]          Fetch a single prompt by name, optional JSON args
/read <uri>                    Read a specific resource by URI
/ping                          Send a ping and wait for pong
/quit                          Exit
```

## Logging In

Use the `/login` command. The username and password are configured in the environment as noted above. If not specified, they default to `swirlmcpuser`:`swirlmcppass`.

```
MCP> /login <swirl-mcp-username> <swirl-mcp-password>
✅ login successful
```

## Listing Tools

To obtain the list of supported tools, use the /tools command:

```
MCP> /tools
- SWIRL_login: Authenticate with the SWIRL MCP server.  Call this once per session before using any other SWIRL_* tool.
- SWIRL_get_sources: Get the list of sources the authenticated user has access to.
- SWIRL_search: SWIRL_search is a federated search engine over your sources. Returns JSON-formatted results.
```

## Calling a Tool

Use the /call command to call a tool. JSON can be provided as an argument, optionally.

### Calling SWIRL_get_sources

This tool will return an array of all SWIRL SearchProviders, with metadata, in JSON format.

```
MCP> /call SWIRL_get_sources
[
  {
    "id": 1,
    "name": "Web - Google Search (google.com/pse)",
    "description": "Searches the web via Google Programmable Search Engine (PSE). Covers recent information only. Covers most any topic or location. Supports any language. Supports long queries. Supports NOT operator.",
    "owner": "admin",
    "shared": true,
    "date_created": "2024-10-05T13:57:21.186122-04:00",
    "date_updated": "2025-06-13T16:16:18.137912-04:00",
    "active": true,
    "default": true,
    "authenticator": null,
    "connector": "RequestsGet",
    "url": "https://www.googleapis.com/customsearch/v1",
    "query_template": "{url}?cx={cx}&key={key}&q={query_string}",
    "query_template_json": {},
    "post_query_template": "{}",
    "http_request_headers": {},
```

### Calling SWIRL_search

This tool will execute a federated search and re-rank using SWIRL AI Search. 

```
MCP> /call SWIRL_search {"query_text": "swirl ai search"}
{
  "messages": [
    "__S_W_I_R_L__A_I__E_N_T_E_R_P_R_I_S_E__4.3-DEV________________________________________________",
    "[2025-06-17 17:00:09.367207] Retrieved 1 of 1 results from: \u65e5\u672c\u306e\u30cb\u30e5\u30fc\u30b9 - Google News (news.google.com)",
    "[2025-06-17 17:00:09.383013] MappingResultProcessor updated 1 results from: \u65e5\u672c\u306e\u30cb\u30e5\u30fc\u30b9 - Google News (news.google.com)",
    "[2025-06-17 17:00:09.409076] CosineRelevancyResultProcessor updated 1 results from: \u65e5\u672c\u306e\u30cb\u30e5\u30fc\u30b9 - Google News (news.google.com)",
    "[2025-06-17 17:00:10.275174] Retrieved 10 of 1210 results from: Jobs - Google Search (google.com/pse)",
    "[2025-06-17 17:00:10.282968] Retrieved 10 of 19 results from: Documentation - SWIRL",
    "[2025-06-17 17:00:10.401111] MappingResultProcessor updated 10 results from: Jobs - Google Search (google.com/pse)",
    "[2025-06-17 17:00:10.401660] DateFinderResultProcessor updated 1 results from: Jobs - Google Search (google.com/pse)",
    "[2025-06-17 17:00:10.418301] MappingResultProcessor updated 10 results from: Documentation - SWIRL",
    "[2025-06-17 17:00:10.418868] DateFinderResultProcessor updated 1 results from: Documentation - SWIRL",
    "[2025-06-17 17:00:10.598234] Retrieved 10 of 75 results from: News - Google News (news.google.com)",
    "[2025-06-17 17:00:10.613930] CosineRelevancyResultProcessor updated 10 results from: Jobs - Google Search (google.com/pse)",
    "[2025-06-17 17:00:10.702806] MappingResultProcessor updated 10 results from: News - Google News (news.google.com)",
    "[2025-06-17 17:00:10.912151] CosineRelevancyResultProcessor updated 10 results from: Documentation - SWIRL",
    "[2025-06-17 17:00:10.949802] CosineRelevancyResultProcessor updated 10 results from: News - Google News (news.google.com)",
    "[2025-06-17 17:00:11.003965] Retrieved 10 of 82 results from: Research - Europe PMC (EuropePMC.org)",
    "[2025-06-17 17:00:11.262063] MappingResultProcessor updated 10 results from: Research - Europe PMC (EuropePMC.org)",
    "[2025-06-17 17:00:11.679401] CosineRelevancyResultProcessor updated 10 results from: Research - Europe PMC (EuropePMC.org)",
    "[2025-06-17 17:00:13.609456] Retrieved 20 of 29600000 results from: Web - Google Search (google.com/pse)",
    "[2025-06-17 17:00:13.849804] MappingResultProcessor updated 20 results from: Web - Google Search (google.com/pse)",
    "[2025-06-17 17:00:13.850722] DateFinderResultProcessor updated 9 results from: Web - Google Search (google.com/pse)",
    "[2025-06-17 17:00:14.423456] CosineRelevancyResultProcessor updated 20 results from: Web - Google Search (google.com/pse)",
    "[2025-06-17 17:00:14.436742] DedupeByFieldPostResultProcessor updated 0 results from: Web - Google Search (google.com/pse)",
    "[2025-06-17 17:00:14.436747] DedupeByFieldPostResultProcessor updated 0 results from: Research - Europe PMC (EuropePMC.org)",
    "[2025-06-17 17:00:14.436749] DedupeByFieldPostResultProcessor updated 0 results from: News - Google News (news.google.com)",
    "[2025-06-17 17:00:14.436751] DedupeByFieldPostResultProcessor updated 2 results from: Documentation - SWIRL",
    "[2025-06-17 17:00:14.436752] DedupeByFieldPostResultProcessor updated 0 results from: Jobs - Google Search (google.com/pse)",
    "[2025-06-17 17:00:14.436753] DedupeByFieldPostResultProcessor updated 0 results from: \u65e5\u672c\u306e\u30cb\u30e5\u30fc\u30b9 - Google News (news.google.com)",
    "[2025-06-17 17:00:14.549174] CosineRelevancyPostResultProcessor updated 59 results",
    "[2025-06-17 17:00:14.551599] Results ordered by: RelevancyConfidenceMixer"
  ],
  "info": {
    "results": {
      "found_total": 29601387,
      "retrieved_total": 59,
      "retrieved": 10,
      "federation_time": 5.7,
      "result_blocks": [
        "ai_summary"
      ],
      "next_page": "http://localhost:8000/swirl/results/?search_id=1288&page=2"
    },
 ```

# Example: SWIRL + MCP + Crew.AI

[Crew.AI]() is an amazing new multi-agent platform! Build an deploy automated, agentic workflows quickly and easily. 

## Running the Example

After completing the above installation, and verifying that SWIRL and the MCP server are running, run the Crew.AI integration example:

```bash
pip install -r mcp_swirl_proxy_internal/requirements-crew.txt
export OPENAI_API_KEY='<openai-api-key>'
python mcp_swirl_proxy_internal/swirl_crew_example.py
```

This script creates two dependent tasks:

1. A research task to identify the sources to query for the topic
2. A research task to answer the 

The output from the first task, a "Research Analyst" is:

```
sid@mac swirl-mcp-proxy-internal % python swirl_crew_example.py
/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python: can't open file '/Users/sid/Code/swirl-mcp-proxy-internal/swirl_crew_example.py': [Errno 2] No such file or directory
sid@mac swirl-mcp-proxy-internal % python mcp_swirl_proxy_internal/swirl_crew_example.py 
INFO:mcp_tool_wrapper:Login response: ✅ login successful
INFO:mcp_tool_wrapper:Login successful.
╭──────────────────────────────────────────────────────────────────────────────── Crew Execution Started ─────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                                                                                         │
│  Crew Execution Started                                                                                                                                                                 │
│  Name: crew                                                                                                                                                                             │
│  ID: d9ae4dc1-1b16-42ef-88b2-4c17a30a671f                                                                                                                                               │
│                                                                                                                                                                                         │
│                                                                                                                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

# Agent: Research Analyst
## Task: Call **SWIRL_get_sources** to list everything I can search. Based on names and descriptions, choose the 3–5 sources most likely to cover *cybersecurity regulations for AI 
models*.  

Return ONLY their numeric IDs, from the id field, separated by commas.  

(e.g. `1,3,4,22`).
🚀 Crew: crew
└── 📋 Task: 4fedc0cd-a4c1-432e-9892-fae8d4873c46
🚀 Crew: crew
└── 📋 Task: 4fedc0cd-a4c1-432e-9892-fae8d4873c46
    Status: Executing Task...
    └── 🧠 Thinking...INFO:httpx:HTTP Request: POST https://api.openai.com/v1/chat/completions "HTTP/1.1 200 OK"
17:11:32 - LiteLLM:INFO: utils.py:1213 - Wrapper: Completed Call, calling success_handler
🚀 Crew: crew
└── 📋 Task: 4fedc0cd-a4c1-432e-9892-fae8d4873c46
    Status: Executing Task...
DNDEBUG : meta=None content=[TextContent(type='text', text='[{"id":1,"name":"Web - Google Search (google.com/pse)","description":"Searches the web via Google Programmable Search Engine 
(PSE). Covers recent information only. Covers most any topic or location. Supports any language. Supports long queries. Supports NOT 
operator.","owner":"admin","shared":true,"date_created":"2024-10-05T13:57:21.186122-04:00","date_updated":"2025-06-13T16:16:18.137912-04:00","active":true,"default":true,"authenticator":n
ull,"connector":"RequestsGet","url":"https://www.googleapis.com/customsearch/v1","query_template":"{url}?cx={cx}&key={key}&q={query_string}","query_template_json":{},"post_query_template"
:"{}","http_request_headers":{},"page_fetch_config_json":{"au.linkedin.com":{"timeout":5},"cache":"true","diffbot":{"scholar.google.com":{"extract_entity":"article"},"token":"bd8d7715ad69
7c54c7101bf18722a80a"},"headers":{"User-Agent":"Swirlbot/1.0

...

# Agent: Research Analyst
## Final Answer: 
1,2,6,4,7

🚀 Crew: crew

🚀 Crew: crew
└── 📋 Task: 4fedc0cd-a4c1-432e-9892-fae8d4873c46
    Assigned to: Research Analyst
    Status: ✅ Completed
    └── 🔧 Used SWIRL_get_sources (1)
╭──────────────────────────────────────────────────────────────────────────────────── Task Completion ────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                                                                                         │
│  Task Completed                                                                                                                                                                         │
│  Name: 4fedc0cd-a4c1-432e-9892-fae8d4873c46                                                                                                                                             │
│  Agent: Research Analyst                                                                                                                                                                │
│                                                                                                                                                                                         │
│                                                                                                                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

The output from the second task, also a "Research Agent", is:

```
# Agent: Research Analyst
## Task: Take the output of the previous task (comma-delimited source list) and call **SWIRL_search** with JSON:
```json
{
  "query_text": "cybersecurity regulations for AI models",
  "query_sources": "${{previous_task_output}}",
}
Summarise the most important findings in 4-6 bullet points.
🚀 Crew: crew
├── 📋 Task: 4fedc0cd-a4c1-432e-9892-fae8d4873c46
🚀 Crew: crew
├── 📋 Task: 4fedc0cd-a4c1-432e-9892-fae8d4873c46
│   Assigned to: Research Analyst
🚀 Crew: crew
🚀 Crew: crew
├── 📋 Task: 4fedc0cd-a4c1-432e-9892-fae8d4873c46
│   Assigned to: Research Analyst
DNDEBUG : meta=None content=[TextContent(type='text', text='{"messages":["__S_W_I_R_L__A_I__E_N_T_E_R_P_R_I_S_E__4.3-DEV________________________________________________","[2025-06-17 
17:11:37.442178] Retrieved 0 of 0 results from: Documentation - SWIRL","[2025-06-17 17:11:37.442468] Retrieved 0 of 0 results from: Documentation - SWIRL","[2025-06-17 17:11:38.355799] 
Retrieved 10 of 2365465 results from: Research - arXiv (arxiv.org)","[2025-06-17 17:11:38.536947] MappingResultProcessor updated 10 results from: Research - arXiv 
(arxiv.org)","[2025-06-17 17:11:38.689793] Retrieved 10 of 65 results from: News - Google News (news.google.com)","[2025-06-17 17:11:38.792395] MappingResultProcessor updated 10 results 
from: News - Google News (news.google.com)","[2025-06-17 17:11:38.929886] Retrieved 10 of 1168 results from: Research - Europe

...

# Agent: Research Analyst
## Final Answer: 
- The evolving landscape of cybersecurity regulations emphasizes the need for transparency in AI model deployment, including specific governance rules to prevent misuse of AI 
technologies.
- A paper from arXiv discusses the urgent regulatory and ethical imperatives surrounding AI integration in cybersecurity, noting major milestones like the EU AI Act and advocating for a 
unified regulatory approach to manage unique risks.
- Research highlights that establishing a balance between AI capabilities and human expertise is crucial for improving cybersecurity defenses; this requires incorporating human insights 
in the AI decision-making process.
- EU regulations, including the General Data Protection Regulation (GDPR) and Cybersecurity Act, significantly impact the adoption of AI technologies, highlighting barriers such as data 
privacy and compliance challenges.
- The implementation of AI in healthcare brings new cybersecurity challenges that necessitate robust policies and transparency regarding AI algorithms to mitigate risks, protecting 
patient data effectively.
- There is a growing recognition that the regulatory landscape must adapt continuously to counteract increasingly sophisticated cyber threats while fostering innovation in AI and IoT 
integrations.


🚀 Crew: crew
├── 📋 Task: 4fedc0cd-a4c1-432e-9892-fae8d4873c46
│   Assigned to: Research Analyst
│   Status: ✅ Completed
│   └── 🔧 Used SWIRL_get_sources (1)
└── 📋 Task: 981d5de6-15e5-4692-875b-8edbbfda60d8
    Assigned to: Research Analyst
    Status: ✅ Completed
    └── 🔧 Used SWIRL_search (1)
╭──────────────────────────────────────────────────────────────────────────────────── Task Completion ────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                                                                                         │
│  Task Completed                                                                                                                                                                         │
│  Name: 981d5de6-15e5-4692-875b-8edbbfda60d8                                                                                                                                             │
│  Agent: Research Analyst                                                                                                                                                                │
│                                                                                                                                                                                         │
│                                                                                                                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

╭──────────────────────────────────────────────────────────────────────────────────── Crew Completion ────────────────────────────────────────────────────────────────────────────────────╮
│                                                                                                                                                                                         │
│  Crew Execution Completed                                                                                                                                                               │
│  Name: crew                                                                                                                                                                             │
│  ID: d9ae4dc1-1b16-42ef-88b2-4c17a30a671f                                                                                                                                               │
│                                                                                                                                                                                         │
│                                                                                                                                                                                         │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯

```




