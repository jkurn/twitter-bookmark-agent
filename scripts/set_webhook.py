"""
Register the Telegram webhook URL.

Usage:
    python scripts/set_webhook.py <webhook_url>

Example:
    python scripts/set_webhook.py https://abc123.execute-api.us-east-1.amazonaws.com/Prod/webhook
"""

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import settings  # noqa: E402

TELEGRAM_API = f"https://api.telegram.org/bot{settings.telegram_bot_token}"


def set_webhook(url: str) -> None:
    """Register the webhook URL with Telegram."""
    params = {"url": url}
    if settings.telegram_webhook_secret:
        params["secret_token"] = settings.telegram_webhook_secret

    resp = httpx.post(f"{TELEGRAM_API}/setWebhook", json=params)
    data = resp.json()

    if data.get("ok"):
        print(f"Webhook set: {url}")
    else:
        print(f"ERROR: {data}", file=sys.stderr)
        sys.exit(1)


def get_webhook_info() -> None:
    """Print current webhook info."""
    resp = httpx.get(f"{TELEGRAM_API}/getWebhookInfo")
    data = resp.json()
    info = data.get("result", {})
    print(f"Current webhook: {info.get('url') or '(none)'}")
    if info.get("last_error_message"):
        print(f"Last error: {info['last_error_message']}")
    print(f"Pending updates: {info.get('pending_update_count', 0)}")


def delete_webhook() -> None:
    """Remove the webhook (switch to polling mode)."""
    resp = httpx.post(f"{TELEGRAM_API}/deleteWebhook")
    data = resp.json()
    if data.get("ok"):
        print("Webhook deleted. Bot is now in polling mode.")
    else:
        print(f"ERROR: {data}", file=sys.stderr)


def main():
    if not settings.telegram_bot_token:
        print("ERROR: TELEGRAM_BOT_TOKEN not set in .env", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) < 2:
        print("Current webhook info:")
        get_webhook_info()
        print(f"\nUsage: python {sys.argv[0]} <webhook_url>")
        print(f"       python {sys.argv[0]} --delete")
        return

    if sys.argv[1] == "--delete":
        delete_webhook()
    else:
        set_webhook(sys.argv[1])


if __name__ == "__main__":
    main()
