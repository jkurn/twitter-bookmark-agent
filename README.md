# Twitter Bookmark Agent

Chat with the agent here: t.me/chatwithbookmark_bot

A Telegram chatbot that lets you chat with your Twitter/X bookmarks using RAG (Retrieval-Augmented Generation). Ask it a question, and it retrieves the most relevant bookmarks via vector search and synthesizes an answer with citations.

Built for a personal collection of 2,450+ bookmarks on AI, productivity, and building.

## What It Does

| Capability | Example | How It Works |
|------------|---------|-------------|
| **QA** | "What does my collection say about agent security?" | Vector search + LLM synthesis with citations |
| **Search** | "Show me everything from @karpathy about coding" | Metadata filtering on Pinecone |
| **Recommend** | "What's related to context engineering?" | Nearest-neighbor semantic search |
| **Summarize** | "Summarize what @levelsio talks about" | Author filter + LLM synthesis |

Every answer cites the specific bookmarks it's drawing from (author, BM ID, and link to the original tweet).

## Architecture

```
Telegram message
  |
  v
AWS Lambda (FastAPI + Mangum)
  |
  |--> Intent classifier (regex, no LLM needed)
  |       |
  |       |--> SEARCH    --> Pinecone metadata filter --> formatted list
  |       |--> QA        --> Pinecone vector search --> LLM synthesis --> cited answer
  |       |--> RECOMMEND --> Pinecone nearest neighbors --> formatted list
  |       `--> SUMMARIZE --> Pinecone author filter --> LLM synthesis
  |
  v
Telegram reply with answer + source links
```

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Interface | Telegram Bot API (webhook) | Mobile-first, instant access |
| Compute | AWS Lambda + API Gateway | Scales to zero, ~$0/mo |
| Embeddings | OpenAI `text-embedding-3-small` | Best cost-to-quality ratio |
| Vector DB | Pinecone (free tier) | 2GB storage, no cold starts |
| LLM | OpenRouter (model-agnostic) | Swap models with one env var |
| Deploy | AWS SAM CLI | One-command deploys |

**Estimated cost: $0.50-$3/month** at light usage (almost entirely LLM API costs).

## Getting Started

### Prerequisites

- Python 3.11+
- A directory of Twitter bookmark `.md` files with YAML frontmatter (see [Bookmark Format](#bookmark-format))
- API keys for: [OpenRouter](https://openrouter.ai), [OpenAI](https://platform.openai.com) (embeddings only), [Pinecone](https://pinecone.io) (free tier), Telegram (via [@BotFather](https://t.me/BotFather))

### Setup

```bash
git clone https://github.com/jkurn/twitter-bookmark-agent.git
cd twitter-bookmark-agent

pip install -r requirements.txt

cp .env.example .env
# Fill in your API keys in .env
```

### Phase 1: Index Your Bookmarks

```bash
# Parse bookmark .md files into structured JSON
python scripts/parse_bookmarks.py

# Preview embedding cost (~$0.03 for 2,450 bookmarks)
python scripts/index_to_pinecone.py --dry-run

# Embed and upsert to Pinecone
python scripts/index_to_pinecone.py
```

### Phase 2: Deploy the Bot

```bash
# Deploy to AWS Lambda
sam build && sam deploy --guided

# Register the Telegram webhook
python scripts/set_webhook.py
```

## Switching LLM Models

All LLM calls go through [OpenRouter](https://openrouter.ai), so you can swap models by changing one line in `.env`:

```bash
# Default — best reasoning
LLM_MODEL=anthropic/claude-sonnet-4-5

# Faster and cheaper
LLM_MODEL=anthropic/claude-haiku-4-5

# Or use any other provider
LLM_MODEL=openai/gpt-4o
LLM_MODEL=google/gemini-2.0-flash-001
```

No code changes needed.

## Project Structure

```
twitter-bookmark-agent/
├── src/
│   ├── config.py              # Centralized settings (pydantic-settings)
│   ├── llm.py                 # OpenRouter client (OpenAI-compatible)
│   ├── synthesis.py           # QA and summarize LLM calls
│   ├── retrieval.py           # Pinecone query logic
│   ├── intents.py             # Regex-based intent classifier
│   ├── bot.py                 # Telegram bot handlers
│   └── handler.py             # Lambda entry point (Mangum + FastAPI)
├── scripts/
│   ├── parse_bookmarks.py     # Parse .md files --> data/bookmarks.json
│   ├── index_to_pinecone.py   # Embed + upsert to Pinecone
│   └── set_webhook.py         # Register Telegram webhook URL
├── tests/
├── requirements.txt
├── template.yaml              # AWS SAM infrastructure definition
└── .env.example
```

## Bookmark Format

The parser expects `.md` files with YAML frontmatter:

```yaml
---
author: "Andrej Karpathy"
handle: "@karpathy"
date: 2026-02-15
category: "AI & Agents"
tags: [twitter-bookmark, ai-agents, karpathy]
url: "https://x.com/karpathy/status/..."
---
```

With a `## Tweet Content` section containing the tweet text. The parser handles Obsidian wiki-links, truncation warnings, and blockquote markers automatically.

## Design Principles

1. **Simplest possible loop.** One Lambda, one vector DB, one LLM. No multi-agent orchestration.
2. **No LLM where regex works.** Intent classification is pure pattern matching.
3. **Every component is swappable.** Pinecone to Supabase, OpenAI embeddings to Voyage, Claude to any LLM via OpenRouter.
4. **Grounded answers only.** The system prompt enforces "answer ONLY from provided bookmarks" — no hallucination.
5. **Transparent citations.** Every response includes which bookmarks were used (BM ID + author + link).

## License

MIT
