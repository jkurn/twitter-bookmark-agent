# Twitter Bookmark Agent — Telegram RAG Bot

## What We're Building

A Telegram chatbot that lets you chat with your 2,451 Twitter bookmarks. You message it a question, it retrieves the most relevant bookmarks using vector search, and Claude synthesizes an answer grounded in your own collected wisdom — with sources.

**Four capabilities:**
1. **QA** — "What does my collection say about agent security?" → synthesized answer with citations
2. **Search** — "Show me everything from @karpathy about coding" → filtered list with links
3. **Recommend** — "What's related to context engineering?" → related bookmarks by semantic similarity
4. **Summarize** — "Summarize what @levelsio talks about" → synthesis from their bookmarks

---

## Bookmark Data

**Source location:** `/Users/jonathankurniawan/Documents/Claude Cowork/Second Brain/Twitter Bookmarks/`
**Count:** 2,451 `.md` files
**Naming convention:** `BM{id} - @{handle} - {title snippet}.md`

### File Structure

Each bookmark file has:

```yaml
---
title: "BM0 — JJ Englert"
type: bookmark
source: twitter
author: "JJ Englert"
handle: "@JJEnglert"
date: 2026-03-03
category: "AI & Agents"
tags: [twitter-bookmark, ai-agents, jjenglert, claude-cowork, has-image]
url: "https://x.com/JJEnglert/status/..."
has_image: true
has_video: false
status: unreviewed
rating:
---
```

Followed by markdown sections:
- `## Tweet Content` — the actual tweet text (may be truncated with link to full tweet)
- `## Topics` — Obsidian wiki-links to topic MOCs
- `## Related Bookmarks` — More from same author, Similar Topics, Bookmarked Around Same Time
- `## My Notes` — user notes (usually empty)
- `## Action` — review checkboxes

### Known Data Quirks
- Tweet content is sometimes truncated (ends with `⚠️ *Text may be truncated*`)
- `rating` field is often empty
- `status` is almost always `unreviewed`
- Related bookmarks use Obsidian `[[wiki-link]]` syntax — strip these when building embedding text

---

## Architecture

```
You (Telegram)
  ↓ webhook
AWS Lambda (Python, FastAPI + Mangum)
  ↓ classifies intent (regex, no LLM)
  ├─→ [SEARCH]    → filter Pinecone metadata (handle, category, date) → list
  ├─→ [QA]        → embed query → Pinecone vector search → Claude Sonnet → cited answer
  ├─→ [RECOMMEND] → embed reference → Pinecone nearest neighbors → list
  └─→ [SUMMARIZE] → metadata filter by handle → Claude synthesis
Telegram reply with answer + source links
```

---

## Tech Stack

| Layer | Choice | Cost |
|-------|--------|------|
| Interface | Telegram Bot API (webhook) | Free |
| Compute | AWS Lambda + API Gateway | ~$0/mo |
| Bot framework | python-telegram-bot v21+ | Free |
| Web framework | FastAPI + Mangum | Free |
| Embeddings | OpenAI text-embedding-3-small | ~$0.03 one-time |
| Vector DB | Pinecone (free tier) | $0/mo |
| LLM | OpenRouter (model-agnostic) | ~$0.50–2/mo |
| Deploy | AWS SAM CLI | Free |

---

## Project Structure

```
twitter-bookmark-agent/
├── CLAUDE.md
├── requirements.txt
├── template.yaml              # AWS SAM infrastructure
├── src/
│   ├── handler.py             # Lambda entry point (Mangum + FastAPI)
│   ├── bot.py                 # Telegram bot, command handlers
│   ├── intents.py             # Regex intent classifier
│   ├── retrieval.py           # Pinecone queries
│   ├── synthesis.py           # Claude API calls
│   ├── models.py              # Pydantic models
│   └── config.py              # Env vars / config
├── scripts/
│   ├── parse_bookmarks.py     # Parse .md files → structured JSON
│   ├── index_to_pinecone.py   # Embed + upsert to Pinecone
│   └── set_webhook.py         # Register Telegram webhook
└── tests/
    ├── test_intents.py
    ├── test_retrieval.py
    └── test_synthesis.py
```

---

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Phase 1: Parse all bookmarks to JSON
python scripts/parse_bookmarks.py

# Phase 1: Index to Pinecone (one-time, ~$0.03)
python scripts/index_to_pinecone.py

# Phase 2: Deploy to AWS Lambda
sam build && sam deploy --guided

# Phase 2: Set Telegram webhook
python scripts/set_webhook.py

# Run tests
pytest

# Lint
ruff check . && ruff format .
```

---

## Environment Variables

```bash
# .env (never commit)
BOOKMARKS_DIR="/Users/jonathankurniawan/Documents/Claude Cowork/Second Brain/Twitter Bookmarks"

# OpenRouter — all LLM calls (model-agnostic)
OPENROUTER_API_KEY=
LLM_MODEL=anthropic/claude-sonnet-4-5   # change to any OpenRouter model

# OpenAI — embeddings only
OPENAI_API_KEY=

PINECONE_API_KEY=
PINECONE_INDEX_NAME=twitter-bookmarks
TELEGRAM_BOT_TOKEN=
TELEGRAM_WEBHOOK_SECRET=
```

### Switching models

Change `LLM_MODEL` in `.env` to any model on OpenRouter:
- `anthropic/claude-sonnet-4-5` (default, best reasoning)
- `anthropic/claude-haiku-4-5` (faster, cheaper)
- `openai/gpt-4o`
- `google/gemini-2.0-flash-001`

---

## Embedding Text Format

For each bookmark, concatenate these fields for embedding:

```
{author} (@{handle}) — {category} — {date}
{tweet_content}
Tags: {tags joined with comma}
```

Strip Obsidian wiki-link syntax (`[[...]]`) from all text before embedding.

---

## Intent Classification

No LLM for routing — regex patterns only:

| Pattern | Intent |
|---------|--------|
| starts with "show", "find", "list", "search", "give me" | SEARCH |
| contains "@handle" + "summarize"/"what does"/"tell me about" | SUMMARIZE |
| contains "related to"/"similar to"/"what else"/"more like" | RECOMMEND |
| everything else | QA |

---

## Build Sequence

### Phase 1: Data Pipeline ✅ (do this first, locally)
- [ ] `scripts/parse_bookmarks.py` — read 2,451 .md files, extract YAML + tweet content
- [ ] `scripts/index_to_pinecone.py` — embed with OpenAI, upsert to Pinecone
- **Milestone:** Query Pinecone directly and get relevant bookmarks back

### Phase 2: Basic Bot
- [ ] Create Telegram bot via @BotFather
- [ ] `src/handler.py` + `src/bot.py` — webhook that echoes messages
- [ ] Deploy to Lambda with SAM. Set webhook.
- **Milestone:** Send message → get echo reply

### Phase 3: Search + QA
- [ ] `src/intents.py` — regex classifier
- [ ] `src/retrieval.py` — Pinecone queries
- [ ] `src/synthesis.py` — Claude API with prompt caching
- **Milestone:** Ask about @karpathy on Telegram, get cited answer

### Phase 4: Summarize + Recommend + Polish
- [ ] SUMMARIZE and RECOMMEND flows
- [ ] `/help`, `/stats` commands
- [ ] Rate limiting, error handling, logging

---

## API Keys Needed

1. **Telegram Bot Token** — @BotFather (free)
2. **OpenAI API Key** — for embeddings (~$0.03 to index everything)
3. **Anthropic API Key** — already have this
4. **Pinecone API Key** — free tier at pinecone.io
5. **AWS Account** — free tier

---

## Guardrails

- Bot only answers from bookmarks — system prompt enforces "ONLY use provided context"
- Every answer includes BM ID + author citation
- Graceful failure if Pinecone returns 0 results
- Prompt caching always on for Claude calls (90% cost reduction on system prompt)
- Telegram bot token stored in AWS Secrets Manager in production
