"""
Claude / LLM synthesis calls for QA and SUMMARIZE intents.
All calls go through OpenRouter via src/llm.py.
"""

from llm import chat

SYSTEM_PROMPT = """\
You're Jonathan's bookmark search bot. You answer questions using ONLY the \
bookmark content below. No outside knowledge.

Style rules:
- Be concise. Short sentences. No filler.
- Write like a person talking, not a machine producing a document.
- Never use words like: pivotal, crucial, vital, delve, underscore, landscape, \
foster, enhance, cultivate, nuanced, vibrant, intricate.
- Never use "Not only X, but Y" or "It's not just about X, it's about Y".
- Don't use "Furthermore", "Moreover", "Additionally", "Consequently". \
Use "and", "but", "so", "also", "though" instead.
- Don't announce what you're doing ("I'll now explain..."). Just do it.
- Don't hedge or apologize. If you don't know, say "I don't know".
- Don't end with a summary or offer to help more. Just stop when you're done.
- No emojis.
- Cite inline with @handle (BMID) like: @karpathy (BM42) says X.
- Put source URLs at the end, one per line.\
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
        max_tokens=800,
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
        f"What does {handle} talk about? Give me their main themes and best takes. "
        f"Be specific, use their actual words where you can. Keep it tight."
    )

    return chat(
        messages=[{"role": "user", "content": user_message}],
        system=SYSTEM_PROMPT,
        model=model,
        temperature=0.3,
        max_tokens=800,
    )
