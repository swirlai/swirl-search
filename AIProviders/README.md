# AIProvider Fixtures

These JSON files define sample AIProvider configurations that can be loaded into SWIRL.

## Loading fixtures

```bash
python swirl.py load_data AIProviders/preloaded.json
```

Or via the Django admin at `/admin/swirl/aiprovider/`.

## Providers

`preloaded.json` contains template entries for:

- **OpenAI** — GPT-4o and GPT-4o-mini (chat, query rewrite, RAG, connector roles)
- **Anthropic** — Claude 3.5 Sonnet / Haiku 4.5 (all roles)
- **Azure OpenAI** — deployment-name-based config (all roles + embeddings)
- **Ollama** — local LLMs (LLaMA, Qwen, DeepSeek etc.) and local embeddings
- **HuggingFace** — hosted inference + embeddings
- **Gemini** — via AI Studio
- **Cohere** — embeddings
- **spaCy** — local embeddings (active by default, no API key required)
- **Custom LLM** — generic requestpost / custom_llm template

All entries are `"active": false` except spaCy. Fill in `api_key` and set
`"active": true` for the providers you want to use, then restart SWIRL.

Only one provider should have a given role in its `defaults` list. Multiple
providers can share the same `tags` entry — the first default wins, others
form the fallback list.
