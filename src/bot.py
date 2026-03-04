"""
Telegram bot handlers.

Phase 2: echo bot (replies with the same message).
Phase 3 will wire in intent classification + retrieval + synthesis.

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
    """Handle /start command."""
    await update.message.reply_text(
        "Hey! I'm your Twitter Bookmarks assistant.\n\n"
        "Ask me anything about your 2,450 bookmarks — I'll find the most "
        "relevant ones and give you an answer with sources.\n\n"
        "Try: \"What does my collection say about AI agents?\"\n"
        "Or:  \"Show me everything from @karpathy\"\n\n"
        "Type /help to see all commands."
    )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    await update.message.reply_text(
        "Here's what I can do:\n\n"
        "💬 *Ask a question*\n"
        "\"What does my collection say about agent security?\"\n"
        "→ I'll search your bookmarks and synthesize an answer with citations.\n\n"
        "🔍 *Search*\n"
        "\"Show me everything from @karpathy about coding\"\n"
        "→ Filtered list of matching bookmarks.\n\n"
        "🔗 *Recommend*\n"
        "\"What's related to context engineering?\"\n"
        "→ Semantically similar bookmarks.\n\n"
        "📝 *Summarize*\n"
        "\"Summarize what @levelsio talks about\"\n"
        "→ Synthesis of an author's key themes.\n",
        parse_mode="Markdown",
    )


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle all text messages.
    Phase 2: echo. Phase 3: intent → retrieve → synthesize.
    """
    user_message = update.message.text
    logger.info("Received message: %s", user_message[:100])

    # Phase 2: echo back
    await update.message.reply_text(f"Echo: {user_message}")


# ---------------------------------------------------------------------------
# Local dev: run with polling (no webhook needed)
# Usage: python src/bot.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logger.info("Starting bot in polling mode (local dev)...")
    app = create_app()
    app.run_polling(drop_pending_updates=True)
