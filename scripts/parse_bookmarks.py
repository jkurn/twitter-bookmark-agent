"""
Parse all bookmark .md files → bookmarks.json

Reads every BM*.md file, extracts YAML frontmatter + tweet content,
and writes a clean JSON array to data/bookmarks.json.

Usage:
    python scripts/parse_bookmarks.py
"""

import json
import re
import sys
from pathlib import Path

import frontmatter
from tqdm import tqdm

# Paths
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
OUTPUT_FILE = DATA_DIR / "bookmarks.json"

BOOKMARKS_DIR = Path(
    "/Users/jonathankurniawan/Documents/Claude Cowork/Second Brain/Twitter Bookmarks"
)

# Regex to strip Obsidian [[wiki-links]] — keep just the display text if present
WIKI_LINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")


def strip_wiki_links(text: str) -> str:
    """Replace [[Target|Display]] with Display (or Target if no display)."""
    return WIKI_LINK_RE.sub(lambda m: m.group(2) or m.group(1), text)


def extract_tweet_content(body: str) -> str:
    """Extract text under the '## Tweet Content' section."""
    match = re.search(
        r"##\s+Tweet Content\s*\n(.*?)(?=\n---\n|\n##\s|\Z)", body, re.DOTALL
    )
    if not match:
        return ""

    raw = match.group(1).strip()

    # Remove the truncation warning line
    raw = re.sub(r"⚠️.*\n?", "", raw)

    # Strip trailing section separator if it snuck in
    raw = raw.rstrip("-").strip()

    # Strip markdown blockquote markers
    lines = []
    for line in raw.splitlines():
        line = line.lstrip("> ").strip()
        if line:
            lines.append(line)

    return " ".join(lines).strip()


def parse_file(path: Path) -> dict | None:
    """Parse a single bookmark .md file. Returns None on failure."""
    try:
        post = frontmatter.load(str(path))
    except Exception as e:
        print(f"  WARN: could not parse frontmatter in {path.name}: {e}", file=sys.stderr)
        return None

    meta = post.metadata
    body = post.content

    # Extract BM id from filename (BM1015 - @handle - ...)
    bm_match = re.match(r"^(BM\d+)", path.stem)
    bm_id = bm_match.group(1) if bm_match else path.stem

    tweet_content = extract_tweet_content(body)

    # Clean tags: keep as list of strings
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]

    return {
        "id": bm_id,
        "author": str(meta.get("author", "")).strip(),
        "handle": str(meta.get("handle", "")).strip(),
        "date": str(meta.get("date", "")).strip(),
        "category": str(meta.get("category", "")).strip(),
        "tags": tags,
        "url": str(meta.get("url", "")).strip(),
        "has_image": bool(meta.get("has_image", False)),
        "has_video": bool(meta.get("has_video", False)),
        "status": str(meta.get("status", "unreviewed")).strip(),
        "rating": meta.get("rating") or None,
        "tweet_content": strip_wiki_links(tweet_content),
        "file_name": path.name,
    }


def build_embedding_text(bm: dict) -> str:
    """
    Concatenate fields into a single string for embedding.
    This is what gets sent to OpenAI text-embedding-3-small.
    """
    parts = [
        f"{bm['author']} ({bm['handle']}) — {bm['category']} — {bm['date']}",
        bm["tweet_content"],
        f"Tags: {', '.join(bm['tags'])}",
    ]
    return "\n".join(p for p in parts if p.strip())


def main():
    DATA_DIR.mkdir(exist_ok=True)

    md_files = sorted(BOOKMARKS_DIR.glob("BM*.md"))
    if not md_files:
        print(f"ERROR: no BM*.md files found in {BOOKMARKS_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(md_files)} bookmark files. Parsing...")

    bookmarks = []
    skipped = 0

    for path in tqdm(md_files, unit="file"):
        bm = parse_file(path)
        if bm is None:
            skipped += 1
            continue
        bm["embedding_text"] = build_embedding_text(bm)
        bookmarks.append(bm)

    bookmarks.sort(key=lambda b: b["id"])

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(bookmarks, f, ensure_ascii=False, indent=2)

    print(f"\nDone.")
    print(f"  Parsed:  {len(bookmarks)}")
    print(f"  Skipped: {skipped}")
    print(f"  Output:  {OUTPUT_FILE}")

    # Quick sanity check
    empty_content = sum(1 for b in bookmarks if not b["tweet_content"])
    print(f"  Empty tweet_content: {empty_content} ({empty_content/len(bookmarks)*100:.1f}%)")


if __name__ == "__main__":
    main()
