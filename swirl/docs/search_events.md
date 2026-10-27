# SWIRL Search Events — public schema reference

**Audience:** integrators consuming SWIRL search via SSE, webhook, or a
future MCP server adapter. **Version:** `v: 1` (see "Evolution rules"
below).

## Community edition

SWIRL Community does not implement the orchestrator this document
describes. This copy exists because the Galaxy UI, which ships in both
editions, cites it as the public contract for search, and because the
Community API needs a written statement of what it does instead:

- `GET /sapi/search/?qs=...` runs the search synchronously and answers
  `200` with the mixed results body (the same shape `GET
  /sapi/results/?search_id=<id>` returns).
- The `async` query parameter is accepted and ignored. There is no
  `202` response, no `links` object, and no
  `/sapi/search/<id>/stream/`, `/results/` or `/stop/` route.
- None of the events below are emitted. `swirl/search_events.py`,
  `swirl/sse.py` and the Channels / Redis transport referenced here are
  Enterprise modules.

Galaxy sends `async=true` on every new search and negotiates on the
answer (DS-5736): a `202` carrying `links.stream` and `links.results`
enters the SSE flow described below; any other status with no `links`
is taken as the synchronous result, with no stream, no progress strip
and no Stop button. That fallback is what keeps Community search
working against a shared Galaxy build.

A copy of this document is maintained in swirl-enterprise at the same
path. When the Enterprise contract changes, update both.

---

## Enterprise contract

A SWIRL search emits structured lifecycle events from the moment the
orchestrator picks up a new search request until it reaches a terminal
state (`search.done`, `search.cancelled`, or `search.error`). The same
event payload is delivered across three transports:

| Transport | Endpoint | When to use |
| --- | --- | --- |
| SSE | `GET /sapi/search/<id>/stream/` | Browser / EventSource clients (Galaxy uses this). |
| Webhook | `POST` to your `callback_url` | Server-to-server integrations (Phase 5). |
| MCP `notifications/progress` | future MCP adapter | Headless agent integrations (not yet implemented). |

A single Channels group on the server fans out to all three — same
events, same ordering, same payload shape.

---

## Event payload

Every event is a JSON document:

```json
{
  "v": 1,
  "search_id": 1234,
  "seq": 7,
  "ts": "2026-05-26T22:14:07.812+00:00",
  "stage": "provider.started",
  "provider_id": 55,
  "provider_name": "iManage Cloud"
}
```

Top-level fields are stable across all stages:

| Field | Type | Notes |
| --- | --- | --- |
| `v` | int | Schema version. `1` for the entire current contract. |
| `search_id` | int | The Search row this event belongs to. |
| `seq` | int | Per-search monotonic counter. Use this — not `ts` — as the canonical ordering key. Webhook deliveries may arrive out of order; SSE deliveries are in order but can be replayed via `Last-Event-ID: <seq>`. |
| `ts` | string | ISO 8601 UTC with millisecond precision. For display only. |
| `stage` | string | One of the stages listed below. Dotted-name namespaces (`search.*`, `provider.*`, `rag.*`) help consumers filter. |

Additional fields are stage-specific (see "Stages" below). Consumers
**MUST** tolerate unknown stages and unknown fields — both can be added
without bumping `v`.

---

## Stages

| Stage | When | Stage-specific fields |
| --- | --- | --- |
| `search.starting` | Orchestrator picked up the search. | `query`, `rag_requested`, `providers_requested` |
| `search.pre_processing` | Pre-query processors running. | `processors` |
| `search.federating` | Provider fan-out dispatched (emitted from `run_search` once the provider list is resolved). | `provider_count`, `providers: [{id, name, connector}]` |
| `provider.started` | A federate task picked up a provider. | `provider_id`, `provider_name`, `connector` |
| `provider.page` | Connector finished a page of results (only emitted by paginated connectors — currently not emitted; ships with DS-5608 cooperative-cancel follow-up). | `provider_id`, `page`, `retrieved_so_far` |
| `provider.completed` | Connector returned. | `provider_id`, `provider_name`, `status` (`OK` / `ERROR` / `PROVIDER_TIMEOUT`), `retrieved`, `found` |
| `provider.error` | Connector raised. | `provider_id`, `provider_name`, `error` |
| `search.post_processing` | Dedup / rerank / mixer stage (reserved — not yet emitted). | `processor` |
| `rag.started` | RAG synthesis beginning. | `prompt_id`, `instructions` (truncated) |
| `rag.token` | Streaming text delta from the synthesis LLM call. One event per non-empty chunk (LiteLLM normalizes Anthropic / OpenAI / Azure chunk shapes to `chunk.choices[0].delta.content`); metadata-only chunks are dropped silently. Bypassed when the structured-RAG `response_format` is in scope (LLM call is blocking in that branch) or when the AI provider's engine is `requestpost` (no streaming support). | `text` |
| `rag.citation` | One citation resolved from the LLM output (Phase 4 v2 — not yet emitted; rag.done's `citation_count` is the present granularity). | `index`, `url`, `title` |
| `rag.done` | RAG complete. | `citation_count` |
| `rag.error` | Non-terminal RAG failure — the AI summary couldn't be produced but the search continues. The orchestrator still publishes `search.done` after. | `error` |
| `search.done` | Search terminal-state — results available. | `result_count` |
| `search.cancelled` | User-initiated stop honoured. | `cancelled_at_stage` |
| `search.error` | Fatal failure (terminal). | `error`, `reason` |

The terminal set is `{search.done, search.cancelled, search.error}`.
Exactly one terminal event fires per search; if a webhook is registered,
that delivery is guaranteed (subject to your endpoint accepting it within
the retry policy).

---

## Transport details

### SSE — `GET /sapi/search/<id>/stream/`

Standard `text/event-stream`. Each event lands as:

```
event: <stage>
id: <seq>
data: <json payload>

```

A keepalive comment (`: keepalive`) is emitted every 30 seconds. On
reconnect, send the last `seq` you received as `Last-Event-ID` — the
server replays buffered events with seq greater than that value before
tailing the live stream. The buffer holds the most recent 50 events with
TTL `SEARCH_TIMEOUT + 60s`.

EventSource clients in browsers cannot set custom headers; rely on the
Django session cookie that was already in place for the search POST.

### Webhook (Phase 5)

`POST` to your `callback_url` with body identical to the event JSON
above. Headers:

```
Content-Type: application/json
X-Swirl-Event: <stage>
X-Swirl-Search-Id: <id>
X-Swirl-Delivery: <uuid>
X-Swirl-Timestamp: <unix_seconds>
X-Swirl-Signature: sha256=<hmac_hex>
```

The HMAC is computed over `f"{X-Swirl-Timestamp}.{raw_body}"` using your
shared secret. **Reject deliveries where the timestamp is more than 300
seconds in the past** — without this check, a captured delivery could be
replayed indefinitely.

Retries: 1s / 5s / 25s on 5xx or network failure, then drop. 4xx
responses are not retried. Deliveries are at-least-once — dedupe by
`X-Swirl-Delivery` UUID.

### MCP (future)

When a SWIRL MCP server lands, search tools will translate these events
into MCP `notifications/progress` messages. The wire schema above is
designed so the adapter is mechanical: stage names map to progress
labels, and the rest of the event payload travels in `_meta`.

---

## Evolution rules

What we **guarantee**:

- New top-level fields can appear on existing events. Consumers tolerate.
- New `stage` values can be added. Consumers tolerate.
- `v: 1` semantics never change in place. A breaking change ships `v: 2`
  as a parallel publish stream during a deprecation window.

What we **never** do silently:

- Remove fields, rename stages, or change field types without bumping
  `v`.
- Repurpose stage names. Once `provider.page` means "between-pages
  checkpoint," it means that forever in `v: 1`.
