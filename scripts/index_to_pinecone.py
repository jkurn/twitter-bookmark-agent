"""
Embed all parsed bookmarks and upsert to Pinecone.

Reads data/bookmarks.json (output of parse_bookmarks.py),
embeds each record via OpenRouter (text-embedding-3-small),
and upserts to a Pinecone index.

Usage:
    python scripts/index_to_pinecone.py [--dry-run] [--batch-size 100]

Cost estimate: ~$0.03 for all 2,451 bookmarks.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm

# Add src/ to path so we can import config
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from config import settings  # noqa: E402

REPO_ROOT = Path(__file__).parent.parent
BOOKMARKS_FILE = REPO_ROOT / "data" / "bookmarks.json"

EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMS = 1536
PINECONE_INDEX = settings.pinecone_index_name
PINECONE_CLOUD = "aws"
PINECONE_REGION = "us-east-1"


def get_embeddings(client: OpenAI, texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Retries once on rate limit."""
    try:
        response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in response.data]
    except Exception as e:
        if "rate_limit" in str(e).lower():
            print("  Rate limited, sleeping 10s...", file=sys.stderr)
            time.sleep(10)
            response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
            return [item.embedding for item in response.data]
        raise


def bookmark_to_pinecone_metadata(bm: dict) -> dict:
    """
    Extract the metadata fields we want to store alongside the vector.
    Pinecone metadata values must be str, int, float, bool, or list[str].
    """
    return {
        "id": bm["id"],
        "author": bm["author"],
        "handle": bm["handle"],
        "date": bm["date"],
        "category": bm["category"],
        "tags": bm["tags"],
        "url": bm["url"],
        "has_image": bm["has_image"],
        "has_video": bm["has_video"],
        "tweet_content": bm["tweet_content"][:1000],  # Pinecone metadata cap: 40KB total
        "file_name": bm["file_name"],
    }


def ensure_index(pc: Pinecone) -> None:
    """Create the Pinecone index if it doesn't exist."""
    existing = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX in existing:
        print(f"Index '{PINECONE_INDEX}' already exists.")
        return

    print(f"Creating index '{PINECONE_INDEX}' ({EMBEDDING_DIMS} dims, cosine)...")
    pc.create_index(
        name=PINECONE_INDEX,
        dimension=EMBEDDING_DIMS,
        metric="cosine",
        spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION),
    )
    # Wait for it to be ready
    while not pc.describe_index(PINECONE_INDEX).status["ready"]:
        print("  Waiting for index to be ready...")
        time.sleep(2)
    print("  Index ready.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Parse and embed but don't upsert")
    parser.add_argument("--batch-size", type=int, default=100, help="Embedding batch size")
    parser.add_argument("--skip-existing", action="store_true", help="Skip IDs already in Pinecone")
    args = parser.parse_args()

    # Validate env
    if not settings.openrouter_api_key:
        print("ERROR: OPENROUTER_API_KEY not set. Copy .env.example to .env and fill it in.", file=sys.stderr)
        sys.exit(1)
    if not settings.pinecone_api_key:
        print("ERROR: PINECONE_API_KEY not set. Copy .env.example to .env and fill it in.", file=sys.stderr)
        sys.exit(1)

    # Load bookmarks
    if not BOOKMARKS_FILE.exists():
        print(f"ERROR: {BOOKMARKS_FILE} not found. Run parse_bookmarks.py first.", file=sys.stderr)
        sys.exit(1)

    with open(BOOKMARKS_FILE, encoding="utf-8") as f:
        bookmarks = json.load(f)

    print(f"Loaded {len(bookmarks)} bookmarks from {BOOKMARKS_FILE}")

    # Init clients (embeddings via OpenRouter)
    openrouter_client = OpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
    )
    pc = Pinecone(api_key=settings.pinecone_api_key)

    if not args.dry_run:
        ensure_index(pc)
        index = pc.Index(PINECONE_INDEX)

        if args.skip_existing:
            # Fetch existing IDs to skip
            existing_ids = set()
            # Pinecone doesn't have list-all-IDs; we'll just let upsert overwrite
            print("Note: --skip-existing not supported via Pinecone free tier list API. Upserting all.")

    # Process in batches
    batch_size = args.batch_size
    total_upserted = 0
    total_tokens = 0

    print(f"\nEmbedding and upserting in batches of {batch_size}...")

    for i in tqdm(range(0, len(bookmarks), batch_size), unit="batch"):
        batch = bookmarks[i : i + batch_size]
        texts = [bm["embedding_text"] for bm in batch]

        # Rough token estimate (1 token ≈ 4 chars)
        batch_tokens = sum(len(t) for t in texts) // 4
        total_tokens += batch_tokens

        if args.dry_run:
            continue

        # Embed
        embeddings = get_embeddings(openrouter_client, texts)

        # Build upsert vectors
        vectors = []
        for bm, embedding in zip(batch, embeddings):
            vectors.append({
                "id": bm["id"],
                "values": embedding,
                "metadata": bookmark_to_pinecone_metadata(bm),
            })

        # Upsert to Pinecone (max 100 per call)
        index.upsert(vectors=vectors)
        total_upserted += len(vectors)

    print(f"\nDone.")
    if args.dry_run:
        print(f"  DRY RUN — nothing upserted.")
        print(f"  Estimated tokens: ~{total_tokens:,}")
        print(f"  Estimated cost: ~${total_tokens / 1_000_000 * 0.02:.4f}")
    else:
        print(f"  Upserted: {total_upserted} vectors")
        print(f"  Estimated tokens used: ~{total_tokens:,}")
        print(f"  Estimated cost: ~${total_tokens / 1_000_000 * 0.02:.4f}")
        stats = index.describe_index_stats()
        print(f"  Pinecone index total vectors: {stats.total_vector_count}")


if __name__ == "__main__":
    main()
