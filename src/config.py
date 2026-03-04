"""
Central config — reads from environment / .env file.
All other modules import from here; nothing reads os.getenv() directly.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load .env from repo root (works whether run from repo root or src/)
load_dotenv(Path(__file__).parent.parent / ".env")


class Settings(BaseSettings):
    # Bookmark data
    bookmarks_dir: str = "/Users/jonathankurniawan/Documents/Claude Cowork/Second Brain/Twitter Bookmarks"

    # OpenRouter — LLM calls
    openrouter_api_key: str
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "anthropic/claude-sonnet-4-5"

    # OpenAI — embeddings only
    openai_api_key: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "twitter-bookmarks"

    # Telegram
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
