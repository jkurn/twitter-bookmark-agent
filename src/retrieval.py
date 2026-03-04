"""
Pinecone retrieval logic.
Handles vector search, metadata filtering, and embedding queries.
All API calls go through OpenRouter (embeddings + LLM).
"""

import logging

from openai import OpenAI
from pinecone import Pinecone

from config import settings

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "openai/text-embedding-3-small"

# Lazy-initialized clients
_openrouter_client: OpenAI | None = None
_pinecone_index = None


def _get_openrouter() -> OpenAI:
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenAI(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
    return _openrouter_client


def _get_index():
    global _pinecone_index
    if _pinecone_index is None:
        pc = Pinecone(api_key=settings.pinecone_api_key)
        _pinecone_index = pc.Index(settings.pinecone_index_name)
    return _pinecone_index


def embed_query(text: str) -> list[float]:
    """Embed a single query string via OpenRouter."""
    client = _get_openrouter()
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    return response.data[0].embedding


def vector_search(query: str, top_k: int = 8, filter: dict | None = None) -> list[dict]:
    """
    Embed query and search Pinecone. Returns bookmark metadata dicts.
    """
    embedding = embed_query(query)
    index = _get_index()

    results = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter,
    )

    bookmarks = []
    for match in results.matches:
        meta = match.metadata
        meta["score"] = match.score
        bookmarks.append(meta)

    logger.info("Vector search for '%s': %d results (top score: %.3f)",
                query[:50], len(bookmarks),
                bookmarks[0]["score"] if bookmarks else 0)

    return bookmarks


def search_by_handle(handle: str, top_k: int = 20) -> list[dict]:
    """
    Retrieve all bookmarks from a specific @handle using metadata filter.
    Uses a dummy vector (all zeros) since we're filtering, not searching.
    """
    index = _get_index()

    if not handle.startswith("@"):
        handle = f"@{handle}"

    results = index.query(
        vector=[0.0] * 1536,
        top_k=top_k,
        include_metadata=True,
        filter={"handle": {"$eq": handle}},
    )

    bookmarks = [match.metadata for match in results.matches]
    logger.info("Handle search for %s: %d results", handle, len(bookmarks))
    return bookmarks


def search_by_metadata(
    handle: str | None = None,
    category: str | None = None,
    top_k: int = 10,
    query: str | None = None,
) -> list[dict]:
    """
    Search with optional metadata filters.
    If query is provided, does vector search with filters.
    If no query, does metadata-only filter.
    """
    filter_dict = {}
    if handle:
        if not handle.startswith("@"):
            handle = f"@{handle}"
        filter_dict["handle"] = {"$eq": handle}
    if category:
        filter_dict["category"] = {"$eq": category}

    if query:
        return vector_search(query, top_k=top_k, filter=filter_dict or None)

    index = _get_index()
    results = index.query(
        vector=[0.0] * 1536,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict,
    )
    return [match.metadata for match in results.matches]


def format_bookmark_list(bookmarks: list[dict], max_items: int = 10) -> str:
    """Format bookmarks as a readable Telegram message."""
    if not bookmarks:
        return "No bookmarks found matching your query."

    lines = []
    for i, bm in enumerate(bookmarks[:max_items], 1):
        content_preview = bm.get("tweet_content", "")[:120]
        if len(bm.get("tweet_content", "")) > 120:
            content_preview += "..."
        lines.append(
            f"{i}. *{bm.get('author', '?')}* ({bm.get('handle', '?')}) — {bm.get('date', '?')}\n"
            f"   {content_preview}\n"
            f"   [View on X]({bm.get('url', '')})"
        )

    header = f"Found {len(bookmarks)} bookmark{'s' if len(bookmarks) != 1 else ''}"
    if len(bookmarks) > max_items:
        header += f" (showing top {max_items})"

    return header + ":\n\n" + "\n\n".join(lines)
