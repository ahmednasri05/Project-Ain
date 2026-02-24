"""
Populate the penal_code_embeddings table in Supabase.

Reads Project-Ain/notebooks/filtered_penal_code.json, generates an OpenAI
text-embedding-3-large embedding for each article (combined with its chapter
title for context), then inserts the rows into Supabase.

Usage:
    cd "c:/Users/shels/Documents/wezareit el dakhleya"
    python Project-Ain/db/populate_penal_code_embeddings.py

Prerequisites:
    - Run 10_create_penal_code_embeddings.sql in the Supabase dashboard first.
    - .env must contain OPENAI_API_KEY, SUPABASE_URL, SUPABASE_KEY.
"""

import json
import sys
import time
from pathlib import Path

from tqdm import tqdm

# Project-Ain/ is the package root; add it to sys.path for sibling imports
PROJECT_ROOT = Path(__file__).parent.parent   # …/Project-Ain/
sys.path.insert(0, str(PROJECT_ROOT))

from db.client import get_supabase_client  # noqa: E402
from ai.embedding import embed_texts        # noqa: E402

# ── Configuration ─────────────────────────────────────────────────────────────

JSON_PATH   = PROJECT_ROOT / "notebooks" / "filtered_penal_code.json"
TABLE       = "penal_code_embeddings"
BATCH_SIZE  = 20        # articles per OpenAI API call (max ~2048 per call)
RETRY_SLEEP = 10        # seconds to wait before retrying a failed batch


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_articles(path: Path) -> list[dict]:
    """Flatten the nested JSON into a list of article dicts."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for book in data["books"]:
        for chapter in book["chapters"]:
            for article in chapter["articles"]:
                text = article["text"]
                chapter_title = chapter["chapter_title"]
                rows.append({
                    "article_number":  article["article_number"],
                    "book_title":      book["book_title"],
                    "book_description": book.get("book_description", ""),
                    "chapter_title":   chapter_title,
                    "article_text":    text,
                    # Prefix with chapter for richer semantic context
                    "combined_text":   f"{chapter_title} | {text}",
                })
    return rows


def embed_batch_with_retry(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts, retrying once on failure."""
    try:
        return embed_texts(texts)
    except Exception as exc:
        print(f"\n  Embedding error: {exc}. Retrying in {RETRY_SLEEP}s …")
        time.sleep(RETRY_SLEEP)
        return embed_texts(texts)


# ── Main ──────────────────────────────────────────────────────────────────────

def populate(skip_existing: bool = True) -> None:
    """
    Load articles from JSON, generate embeddings, and insert into Supabase.

    Args:
        skip_existing: When True, articles already in the DB are skipped.
                       Set to False to re-embed and overwrite everything.
    """
    supabase = get_supabase_client()
    articles = load_articles(JSON_PATH)
    print(f"Loaded {len(articles)} articles from {JSON_PATH.name}")

    if skip_existing:
        # Use article_text as the unique key — multiple articles share the
        # same article_number within a chapter (e.g. "86", "86 مكرر", …)
        existing = (
            supabase.table(TABLE)
            .select("article_text")
            .execute()
            .data
        )
        existing_texts = {r["article_text"] for r in existing}
        before = len(articles)
        articles = [
            a for a in articles
            if a["article_text"] not in existing_texts
        ]
        print(f"Skipping {before - len(articles)} already-inserted articles. "
              f"{len(articles)} remaining.")

    if not articles:
        print("Nothing to insert.")
        return

    inserted = 0
    batches = range(0, len(articles), BATCH_SIZE)

    for i in tqdm(batches, desc="Embedding & inserting"):
        batch = articles[i : i + BATCH_SIZE]
        combined_texts = [a["combined_text"] for a in batch]

        embeddings = embed_batch_with_retry(combined_texts)

        rows = [
            {**article, "embedding": embedding}
            for article, embedding in zip(batch, embeddings)
        ]

        supabase.table(TABLE).insert(rows).execute()
        inserted += len(rows)

        # Small pause to stay within OpenAI rate limits
        time.sleep(0.3)

    print(f"\nDone. Inserted {inserted} articles into '{TABLE}'.")


if __name__ == "__main__":
    populate()
