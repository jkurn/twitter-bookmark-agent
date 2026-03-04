"""
Claude / LLM synthesis calls for QA and SUMMARIZE intents.
All calls go through OpenRouter via src/llm.py.
"""

from llm import chat

SYSTEM_PROMPT = """\
You are Jonathan's Twitter Bookmarks assistant. You have access to a curated \
collection of 2,450 Twitter bookmarks on AI, productivity, and building.

Rules:
- Answer ONLY using the bookmark content provided below. Do not use outside knowledge.
- Always cite the bookmark ID and author for every claim (e.g. "According to @karpathy (BM42)...").
- If the provided bookmarks don't contain relevant information, say so honestly.
- Be concise. Lead with the answer, then cite sources.
- Format source links at the end of your response.\
"""


def _format_bookmarks_context(bookmarks: list[dict]) -> str:
    """Render retrieved bookmarks into a compact context block."""
    parts = []
    for bm in bookmarks:
        parts.append(
            f"[{bm['id']} | {bm['author']} ({bm['handle']}) | {bm['date']} | {bm['category']}]\n"
            f"{bm['tweet_content']}\n"
            f"URL: {bm['url']}"
        )
    return "\n\n---\n\n".join(parts)


def answer_question(query: str, bookmarks: list[dict], model: str | None = None) -> str:
    """
    QA: synthesize an answer to `query` from retrieved `bookmarks`.
    Returns a formatted string ready to send to Telegram.
    """
    context = _format_bookmarks_context(bookmarks)
    user_message = f"Bookmarks retrieved for your question:\n\n{context}\n\n---\n\nQuestion: {query}"

    return chat(
        messages=[{"role": "user", "content": user_message}],
        system=SYSTEM_PROMPT,
        model=model,
        temperature=0.2,
        max_tokens=1500,
    )


def summarize_author(handle: str, bookmarks: list[dict], model: str | None = None) -> str:
    """
    SUMMARIZE: synthesize a profile of an author from all their bookmarks.
    Returns a formatted string ready to send to Telegram.
    """
    if not bookmarks:
        return f"I couldn't find any bookmarks from {handle} in the collection."

    context = _format_bookmarks_context(bookmarks)
    user_message = (
        f"Here are all {len(bookmarks)} bookmarks from {handle}:\n\n{context}\n\n---\n\n"
        f"Synthesize what {handle} talks about across these bookmarks. "
        f"Identify their 3-5 key themes and their most notable insights. "
        f"Be specific — quote or paraphrase their actual words where possible."
    )

    return chat(
        messages=[{"role": "user", "content": user_message}],
        system=SYSTEM_PROMPT,
        model=model,
        temperature=0.3,
        max_tokens=1500,
    )
