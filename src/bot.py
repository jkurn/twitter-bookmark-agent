"""
Telegram bot handlers.

Message flow: intent classify → retrieve from Pinecone → synthesize with LLM → reply.

Supports two modes:
  - Polling (local dev):  python src/bot.py
  - Webhook (Lambda):     imported by handler.py
"""

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import intents
import retrieval
import synthesis
from config import settings

logger = logging.getLogger(__name__)


def create_app() -> Application:
    """Build the Telegram Application (shared by polling and webhook modes)."""
    app = Application.builder().token(settings.telegram_bot_token).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    return app


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Your bookmarks bot. 2,450 tweets indexed and searchable.\n\n"
        "Just ask me something. Examples:\n"
        "- What do my bookmarks say about AI agents?\n"
        "- Show me everything from @karpathy\n"
        "- Summarize what @levelsio talks about\n\n"
        "/help for more."
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Four things I can do:\n\n"
        "Ask a question\n"
        "\"What do my bookmarks say about agent security?\"\n\n"
        "Search\n"
        "\"Show me everything from @karpathy\"\n\n"
        "Recommend\n"
        "\"What's related to context engineering?\"\n\n"
        "Summarize\n"
        "\"Summarize what @levelsio talks about\""
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Route message through intent → retrieve → synthesize pipeline."""
    user_message = update.message.text
    logger.info("Message: %s", user_message[:100])

    # Show typing indicator
    await update.message.chat.send_action("typing")

    try:
        intent = intents.classify(user_message)
        logger.info("Intent: %s", intent)

        if intent == intents.SEARCH:
            reply = await handle_search(user_message)
        elif intent == intents.SUMMARIZE:
            reply = await handle_summarize(user_message)
        elif intent == intents.RECOMMEND:
            reply = await handle_recommend(user_message)
        else:
            reply = await handle_qa(user_message)

    except Exception as e:
        logger.exception("Error processing message")
        reply = f"Something went wrong: {e}\n\nPlease try again or rephrase your question."

    # Telegram has a 4096 char limit per message
    if len(reply) > 4000:
        reply = reply[:3997] + "..."

    await update.message.reply_text(reply, parse_mode="Markdown", disable_web_page_preview=True)


async def handle_search(message: str) -> str:
    """SEARCH: metadata filter + optional vector search → formatted list."""
    handle = intents.extract_handle(message)
    bookmarks = retrieval.search_by_metadata(
        handle=handle,
        query=message,
        top_k=10,
    )
    return retrieval.format_bookmark_list(bookmarks)


async def handle_qa(message: str) -> str:
    """QA: vector search → LLM synthesis with citations."""
    bookmarks = retrieval.vector_search(message, top_k=8)
    if not bookmarks:
        return "I couldn't find any relevant bookmarks for that question. Try rephrasing or asking about a specific topic/author."
    return synthesis.answer_question(message, bookmarks)


async def handle_summarize(message: str) -> str:
    """SUMMARIZE: get all bookmarks by author → LLM synthesis."""
    handle = intents.extract_handle(message)
    if not handle:
        return "I need an @handle to summarize. Try: \"Summarize what @karpathy talks about\""

    bookmarks = retrieval.search_by_handle(handle, top_k=20)
    if not bookmarks:
        return f"I couldn't find any bookmarks from {handle} in the collection."
    return synthesis.summarize_author(handle, bookmarks)


async def handle_recommend(message: str) -> str:
    """RECOMMEND: vector search for nearest neighbors → formatted list."""
    bookmarks = retrieval.vector_search(message, top_k=10)
    if not bookmarks:
        return "I couldn't find any related bookmarks. Try rephrasing your query."
    return "Here are the most related bookmarks:\n\n" + retrieval.format_bookmark_list(bookmarks)


# ---------------------------------------------------------------------------
# Local dev: run with polling
# Usage: cd src && python bot.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logger.info("Starting bot in polling mode (local dev)...")
    app = create_app()
    app.run_polling(drop_pending_updates=True)
