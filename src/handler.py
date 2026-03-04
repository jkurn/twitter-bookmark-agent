"""
AWS Lambda entry point.

Receives Telegram webhook POSTs via API Gateway, passes them to the bot.
Uses FastAPI + Mangum to handle Lambda ↔ ASGI translation.
"""

import json
import logging

from fastapi import FastAPI, Request, Response
from mangum import Mangum

from bot import create_app
from config import settings

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# FastAPI app (served by Lambda via Mangum)
api = FastAPI(title="Twitter Bookmark Agent")

# Telegram bot app (reused across warm Lambda invocations)
# Initialized lazily on first request if token is missing at import time
telegram_app = None


def get_telegram_app() -> "Application":
    global telegram_app
    if telegram_app is None:
        telegram_app = create_app()
    return telegram_app


@api.on_event("startup")
async def on_startup():
    """Initialize the Telegram bot (runs once per Lambda cold start)."""
    app = get_telegram_app()
    await app.initialize()


@api.on_event("shutdown")
async def on_shutdown():
    """Shut down cleanly."""
    if telegram_app is not None:
        await telegram_app.shutdown()


@api.post("/webhook")
async def telegram_webhook(request: Request) -> Response:
    """Receive Telegram updates via webhook."""
    app = get_telegram_app()

    # Optional: verify webhook secret
    if settings.telegram_webhook_secret:
        secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if secret_token != settings.telegram_webhook_secret:
            logger.warning("Invalid webhook secret token")
            return Response(status_code=403)

    body = await request.json()
    logger.info("Webhook update: %s", json.dumps(body)[:200])

    from telegram import Update
    update = Update.de_json(data=body, bot=app.bot)
    await app.process_update(update)

    return Response(status_code=200)


@api.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Mangum adapter: Lambda handler
handler = Mangum(api, lifespan="auto")
